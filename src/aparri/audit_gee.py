"""Phase 2B: forensic audit of the Google Earth Engine raster pipeline (product A).

Inputs: the nine GeoTIFFs, the barangay CSV/SHP and ``Code.docx`` in ``data/raw/gee_outputs``.
Read-only.  Writes tables to ``outputs/tables/gee_*.csv``, maps to ``outputs/maps/gee_*.png``
and ``docs/01b_gee_audit.md`` (numbers are computed, never typed).

Vocabulary: **NSM** (net shoreline movement) = metres moved between 1990 and 2025;
**EPR** = NSM / 35 years (m/yr; negative = erosion).  A **pixel** here is a Landsat-grid cell
of about 28.5 m x 29.8 m (0.085 ha).
"""
from __future__ import annotations

import math
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
import shapely
from pyproj import Geod, Transformer
from scipy import ndimage
from shapely.geometry import Point
from shapely.ops import unary_union

from . import audit as A
from .io import ensure_dir, load_config, read_vector, repo_path
from .runreport import RunReport
from .scope import CoastScope

YEARS = [1990, 2000, 2010, 2020, 2025]


# --------------------------------------------------------------------------- loading
class GeeRasters:
    """The nine GeoTIFFs on one common grid, plus pixel-centre coordinates."""

    def __init__(self, gee_dir: Path, work_crs: int):
        self.dir = gee_dir
        def rd(name):
            with rasterio.open(gee_dir / name) as ds:
                return ds.read(1), ds
        self.epr, ds = rd("Aparri_EPR_1990_2025.tif")
        self.nsm, _ = rd("Aparri_NSM_1990_2025.tif")
        self.change, _ = rd("Aparri_Erosion_Accretion_1990_2025.tif")
        self.risk, _ = rd("Aparri_Erosion_Risk_1990_2025.tif")
        self.shore = {y: rd(f"Aparri_Shoreline_{y}.tif")[0] for y in YEARS}
        self.transform, self.crs, self.bounds, self.res = ds.transform, ds.crs, ds.bounds, ds.res
        self.shape = self.epr.shape
        rows, cols = np.indices(self.shape)
        self.lon = self.transform.c + (cols + 0.5) * self.transform.a
        self.lat = self.transform.f + (rows + 0.5) * self.transform.e
        tr = Transformer.from_crs(4326, work_crs, always_xy=True)
        self.x, self.y = tr.transform(self.lon, self.lat)
        self.px_ha = A.pixel_area_ha(self.transform, float(self.lat.mean()), float(self.lon.mean()))
        g = Geod(ellps="WGS84")
        cy, cx = self.lat.mean(), self.lon.mean()
        self.px_m_ew = g.inv(cx, cy, cx + self.transform.a, cy)[2]
        self.px_m_ns = g.inv(cx, cy, cx, cy + abs(self.transform.e))[2]


# --------------------------------------------------------------------------- 2: raster audit
def inventory(r: GeeRasters) -> pd.DataFrame:
    rows = []
    for p in sorted(r.dir.glob("*.tif")):
        with rasterio.open(p) as ds:
            a = ds.read(1)
            u = np.unique(a)
            rows.append({"file": p.name, "crs": str(ds.crs), "width": ds.width, "height": ds.height, "dtype": ds.dtypes[0],
                         "nodata": ds.nodata, "pixel_deg": ds.res[0], "pixel_m_EW": r.px_m_ew, "pixel_m_NS": r.px_m_ns,
                         "distinct_values": len(u), "min": float(a.min()), "max": float(a.max())})
    return pd.DataFrame(rows)


def legend_check(r: GeeRasters, low_max: float, med_max: float) -> dict:
    """Verify the undocumented class codes from the data themselves."""
    ch, nsm, epr, risk = r.change, r.nsm, r.epr, r.risk
    out = {
        "code1_all_nsm_nonpositive": bool((nsm[ch == 1] <= 0).all()),
        "code2_all_nsm_nonnegative": bool((nsm[ch == 2] >= 0).all()),
        "code1_nsm_exactly_zero": int(((ch == 1) & (nsm == 0)).sum()),
        "code2_nsm_exactly_zero": int(((ch == 2) & (nsm == 0)).sum()),
        "nonzero_nsm_where_code0": int(((ch == 0) & (nsm != 0)).sum()),
        "code0_all_nsm_zero": bool((nsm[ch == 0] == 0).all()),
        "n_code": {int(k): int((ch == k).sum()) for k in (0, 1, 2)},
        "ha_code": {int(k): float((ch == k).sum() * r.px_ha) for k in (0, 1, 2)},
    }
    absE = np.abs(epr)
    exp = np.ones_like(risk)
    exp[(epr < 0) & (absE >= low_max) & (absE <= med_max)] = 2
    exp[(epr < 0) & (absE > med_max)] = 3
    out["risk_matches_rule_pixels"] = int((exp == risk).sum())
    out["risk_pixels"] = int(risk.size)
    out["epr_equals_nsm_over_35"] = bool(np.allclose(epr, nsm / 35.0, atol=1e-4))
    out["risk_class_counts"] = {int(k): int((risk == k).sum()) for k in (1, 2, 3)}
    out["risk_class_ha"] = {int(k): float((risk == k).sum() * r.px_ha) for k in (1, 2, 3)}
    return out


def quantisation(r: GeeRasters) -> dict:
    nz = r.nsm[r.nsm != 0]
    q = (nz / 30.0) ** 2
    return {
        "n_nonzero": int(nz.size),
        "share_nsm_over30_squared_is_integer": float((np.abs(q - np.round(q)) < 1e-3).mean()),
        "smallest_abs_nsm": float(np.abs(nz).min()),
        "distinct_epr": int(len(np.unique(r.epr))),
        "distinct_nsm": int(len(np.unique(r.nsm))),
        "smallest_abs_epr": float(np.abs(r.epr[r.epr != 0]).min()),
        "thirty_over_35": 30 / 35,
    }


def zone_grid(r: GeeRasters, scope: CoastScope) -> np.ndarray:
    return scope.classify_xy(r.x.ravel(), r.y.ravel()).reshape(r.shape)


def extremes(r: GeeRasters, zones: np.ndarray, thr: float = -14.0) -> pd.DataFrame:
    m = r.epr < thr
    rows, cols = np.where(m)
    df = pd.DataFrame({"row": rows, "col": cols, "lon": r.lon[m], "lat": r.lat[m], "EPR_m_yr": r.epr[m],
                       "NSM_m": r.nsm[m], "change_code": r.change[m], "zone": zones[m]})
    return df.sort_values("EPR_m_yr").reset_index(drop=True)


def edge_noise(r: GeeRasters, zones: np.ndarray) -> pd.DataFrame:
    """Per year: edge-pixel counts, connected pieces, share in each zone."""
    rows = []
    for y in YEARS:
        m = r.shore[y] > 0
        lab, n = ndimage.label(m, structure=np.ones((3, 3)))
        sizes = np.bincount(lab.ravel())[1:]
        z = zones[m]
        row = {"year": y, "edge_pixels": int(m.sum()), "components": int(n), "median_component_px": float(np.median(sizes)),
               "components_le_5px": int((sizes <= 5).sum()), "largest_component_px": int(sizes.max())}
        for k in ("open_coast", "sea", "inner_water", "land"):
            row[f"share_{k}"] = float((z == k).mean())
        rows.append(row)
    return pd.DataFrame(rows)


def line_context(r: GeeRasters, mask: np.ndarray, lines: gpd.GeoDataFrame, scope: CoastScope, band_m: float = 150.0) -> dict:
    """For pixels in ``mask``: is the nearest legacy shoreline (any year) on the open coast,
    on a river/estuary bank, or is there none within ``band_m``?  Independent of Earth Engine."""
    num = unary_union(list(lines[lines.year.notna()].geometry))
    zone_buf = scope.chain.buffer(scope.tol)
    open_g = num.intersection(zone_buf)
    other_g = num.difference(zone_buf)
    pts = shapely.points(r.x[mask], r.y[mask])
    d_open = shapely.distance(pts, open_g) if not open_g.is_empty else np.full(len(pts), np.inf)
    d_oth = shapely.distance(pts, other_g) if not other_g.is_empty else np.full(len(pts), np.inf)
    near_open = (d_open <= band_m) & (d_open <= d_oth)
    near_oth = (d_oth <= band_m) & (d_oth < d_open)
    n = len(pts)
    return {"n": n, "near_open_coast_line": int(near_open.sum()), "near_river_estuary_line": int(near_oth.sum()),
            "no_mapped_shoreline_within_band": int(n - near_open.sum() - near_oth.sum())}


def plausibility(r: GeeRasters, zones: np.ndarray, lines: gpd.GeoDataFrame, scope: CoastScope) -> pd.DataFrame:
    """Where do the High/Medium pixels and the erosion/accretion pixels sit?"""
    items = {"Risk High (3)": r.risk == 3, "Risk Medium (2)": r.risk == 2,
             "Erosion pixels (code 1)": r.change == 1, "Accretion pixels (code 2)": r.change == 2}
    rows = []
    for name, m in items.items():
        z = zones[m]
        row = {"set": name, "pixels": int(m.sum()), "ha": float(m.sum() * r.px_ha)}
        for k in ("open_coast", "sea", "inner_water", "land"):
            row[f"{k}_px"] = int((z == k).sum())
            row[f"{k}_pct"] = float((z == k).mean() * 100) if m.sum() else np.nan
        lc = line_context(r, m, lines, scope)
        for k, v in lc.items():
            row[f"line_{k}"] = v
        rows.append(row)
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- 4: barangay statistics
def circle_weights(r: GeeRasters, lon: float, lat: float, radius_m: float, work_crs: int, sub: int = 4) -> np.ndarray:
    """Fraction of every pixel covered by a circle of ``radius_m`` (sub x sub supersampling).

    Earth Engine's ``reduceRegion`` weights pixels by the fraction inside the region, so
    pixel-centre-in-circle would not reproduce its numbers."""
    tr = Transformer.from_crs(4326, work_crs, always_xy=True)
    cx, cy = tr.transform(lon, lat)
    circ = Point(cx, cy).buffer(radius_m, 64)
    minx, miny, maxx, maxy = circ.bounds
    inv = Transformer.from_crs(work_crs, 4326, always_xy=True)
    lo0, la0 = inv.transform(minx, miny); lo1, la1 = inv.transform(maxx, maxy)
    w = np.zeros(r.shape)
    # candidate pixel window
    c0 = int(math.floor((lo0 - r.bounds.left) / abs(r.transform.a))) - 1
    c1 = int(math.ceil((lo1 - r.bounds.left) / abs(r.transform.a))) + 1
    r0 = int(math.floor((r.bounds.top - la1) / abs(r.transform.e))) - 1
    r1 = int(math.ceil((r.bounds.top - la0) / abs(r.transform.e))) + 1
    r0, r1, c0, c1 = max(r0, 0), min(r1, r.shape[0]), max(c0, 0), min(c1, r.shape[1])
    if r0 >= r1 or c0 >= c1:
        return w
    offs = (np.arange(sub) + 0.5) / sub
    for i in range(r0, r1):
        for j in range(c0, c1):
            lon_s = r.bounds.left + (j + offs) * abs(r.transform.a)
            lat_s = r.bounds.top - (i + offs) * abs(r.transform.e)
            lo, la = np.meshgrid(lon_s, lat_s)
            xx, yy = tr.transform(lo.ravel(), la.ravel())
            w[i, j] = shapely.contains_xy(circ, xx, yy).mean()
    return w


def stats_from_weights(r: GeeRasters, w: np.ndarray) -> dict:
    m = w > 0
    if not m.any():
        return {k: np.nan for k in ["Mean_EPR", "Min_EPR", "Max_EPR", "Mean_NSM", "Min_NSM", "Max_NSM"]} | {
            "Low_ha": 0.0, "Medium_ha": 0.0, "High_ha": 0.0, "Erosion_ha": 0.0, "Accretion_ha": 0.0, "area_ha": 0.0}
    ww = w[m]
    return {
        "Mean_EPR": float((r.epr[m] * ww).sum() / ww.sum()), "Min_EPR": float(r.epr[m].min()), "Max_EPR": float(r.epr[m].max()),
        "Mean_NSM": float((r.nsm[m] * ww).sum() / ww.sum()), "Min_NSM": float(r.nsm[m].min()), "Max_NSM": float(r.nsm[m].max()),
        "Low_ha": float(((r.risk == 1) * w).sum() * r.px_ha), "Medium_ha": float(((r.risk == 2) * w).sum() * r.px_ha),
        "High_ha": float(((r.risk == 3) * w).sum() * r.px_ha), "Erosion_ha": float(((r.change == 1) * w).sum() * r.px_ha),
        "Accretion_ha": float(((r.change == 2) * w).sum() * r.px_ha), "area_ha": float(w.sum() * r.px_ha),
    }


def reproduce_csv(r: GeeRasters, cfg: dict) -> pd.DataFrame:
    rows = []
    for name, (lon, lat) in cfg["legacy_barangay_points"].items():
        w = circle_weights(r, lon, lat, cfg["legacy_barangay_points_buffer_m"], cfg["crs_work"])
        rows.append({"Barangay": name, **stats_from_weights(r, w)})
    return pd.DataFrame(rows)


def official_stats(r: GeeRasters, brg: gpd.GeoDataFrame, tol_m: float) -> pd.DataFrame:
    """Same statistics over the OFFICIAL barangay polygons.  Each pixel centre goes to the
    barangay containing it, or the nearest within ``tol_m`` (coast pixels fall just outside
    the land polygons)."""
    pts = shapely.points(r.x.ravel(), r.y.ravel())
    d = np.vstack([shapely.distance(pts, b.geometry) for _, b in brg.iterrows()])
    near = d.argmin(axis=0)
    ok = d.min(axis=0) <= tol_m
    names = list(brg.ADM4_EN)
    rows = []
    for i, n in enumerate(names):
        m = ((near == i) & ok).reshape(r.shape)
        inside = (d[i] == 0).reshape(r.shape)
        w = m.astype(float)
        s = stats_from_weights(r, w)
        s["pixels_in_polygon_exact"] = int(inside.sum())
        s["polygon_ha"] = float(brg.geometry.iloc[i].area / 1e4)
        s["raster_cover_of_polygon_pct"] = float(inside.sum() * r.px_ha / (brg.geometry.iloc[i].area / 1e4) * 100)
        eros = m & (r.change == 1)
        for lab, code in (("Medium", 2), ("High", 3)):
            s[f"{lab}_ha_exact"] = float(((inside) & (r.risk == code)).sum() * r.px_ha)
        s["Mean_EPR_eroding_px"] = float(r.epr[eros].mean()) if eros.any() else np.nan
        rows.append({"Barangay": n, **s})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- maps
def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt


def map_zones(r: GeeRasters, zones: np.ndarray, scope: CoastScope, out: Path) -> None:
    plt = _plt()
    from matplotlib.colors import ListedColormap
    code = {"open_coast": 0, "sea": 1, "inner_water": 2, "land": 3}
    z = np.vectorize(code.get)(zones)
    fig, ax = plt.subplots(1, 2, figsize=(17, 6))
    ext = [r.bounds.left, r.bounds.right, r.bounds.bottom, r.bounds.top]
    tr = Transformer.from_crs(32651, 4326, always_xy=True)
    cx, cy = scope.chain.xy
    lon, lat = tr.transform(list(cx), list(cy))
    ax[0].imshow(z, cmap=ListedColormap(["#2ca02c", "#aec7e8", "#ff7f0e", "#c7c7c7"]), extent=ext, interpolation="nearest")
    ax[0].plot(lon, lat, "m-", lw=1); ax[0].set_title("Zones used for plausibility tests (green open coast, light-blue sea, orange river/estuary, grey land); magenta = sea-facing outline", fontsize=8)
    ch = np.ma.masked_equal(r.change, 0)
    ax[1].imshow(ch, cmap=ListedColormap(["#d62728", "#1f77b4"]), vmin=1, vmax=2, extent=ext, interpolation="nearest")
    ax[1].plot(lon, lat, "m-", lw=1)
    ax[1].set_title("Earth Engine change raster: red = 'erosion' (2,052 px), blue = 'accretion' (31,240 px)", fontsize=8)
    for a in ax:
        a.set_xlim(ext[0], ext[1]); a.set_ylim(ext[2], ext[3])
    fig.tight_layout(); fig.savefig(out, dpi=130); plt.close(fig)


def map_edge_noise(r: GeeRasters, out: Path) -> None:
    plt = _plt()
    fig, axs = plt.subplots(2, 3, figsize=(18, 7))
    ext = [r.bounds.left, r.bounds.right, r.bounds.bottom, r.bounds.top]
    for ax, y in zip(axs.ravel(), YEARS):
        ax.imshow(np.ma.masked_equal(r.shore[y], 0), cmap="autumn", extent=ext, interpolation="nearest", vmin=0, vmax=1)
        ax.set_title(f"{y}: {int((r.shore[y] > 0).sum()):,} edge pixels", fontsize=9)
    axs.ravel()[-1].axis("off")
    fig.suptitle("Earth Engine 'shoreline' masks (edge pixels of the NDWI>0 water mask)")
    fig.tight_layout(); fig.savefig(out, dpi=120); plt.close(fig)


def map_hotspots(r: GeeRasters, brg: gpd.GeoDataFrame, out: Path) -> None:
    plt = _plt()
    from matplotlib.colors import ListedColormap
    fig, ax = plt.subplots(1, 2, figsize=(17, 7))
    ext = [r.bounds.left, r.bounds.right, r.bounds.bottom, r.bounds.top]
    b4326 = brg.to_crs(4326)
    for a, (xl, yl, ttl) in zip(ax, [((121.575, 121.665), (18.335, 18.39), "Estuary / Linao / Punta"), ((121.58, 121.72), (18.33, 18.39), "Whole raster")]):
        a.imshow(np.ma.masked_equal(r.risk, 1), cmap=ListedColormap(["#ff9900", "#d62728"]), vmin=2, vmax=3, extent=ext, interpolation="nearest")
        b4326.boundary.plot(ax=a, color="k", lw=0.8)
        for _, b in b4326.iterrows():
            p = b.geometry.representative_point(); a.annotate(b.ADM4_EN, (p.x, p.y), fontsize=7)
        a.set_xlim(*xl); a.set_ylim(*yl); a.set_title(f"{ttl}: orange = Medium, red = High (Earth Engine risk raster)", fontsize=9)
    fig.tight_layout(); fig.savefig(out, dpi=130); plt.close(fig)


def map_stats_compare(legacy: pd.DataFrame, repro: pd.DataFrame, official: pd.DataFrame, out: Path) -> None:
    plt = _plt()
    names = list(legacy.Barangay)
    fig, ax = plt.subplots(1, 2, figsize=(15, 5))
    x = np.arange(len(names)); w = 0.27
    for k, (df, lab, col) in enumerate([(legacy, "legacy CSV (1 km circle)", "#d62728"), (repro, "reproduced (1 km circle)", "#ff9900"),
                                         (official.set_index("Barangay").loc[names].reset_index(), "official polygon + 500 m", "#1f77b4")]):
        col_low = "Low_Risk_ha" if "Low_Risk_ha" in df else "Low_ha"
        ax[0].bar(x + (k - 1) * w, df[col_low], w, label=lab, color=col)
        col_hi = "High_Risk_ha" if "High_Risk_ha" in df else "High_ha"
        ax[1].bar(x + (k - 1) * w, df[col_hi], w, label=lab, color=col)
    for a, t in zip(ax, ["'Low risk' hectares", "'High risk' hectares"]):
        a.set_xticks(x); a.set_xticklabels(names, rotation=30, ha="right", fontsize=8); a.set_title(t); a.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(out, dpi=130); plt.close(fig)


# --------------------------------------------------------------------------- orchestration
def run() -> Path:  # pragma: no cover
    cfg = load_config()
    rep = RunReport("audit_gee", cfg)
    P = cfg["paths"]; work = cfg["crs_work"]
    gee = repo_path(P["gee_dir"])
    for f in sorted(gee.glob("*")):
        if f.is_file():
            rep.add_input(f)
    r = GeeRasters(gee, work)
    tbl = ensure_dir("outputs/tables"); mp = ensure_dir("outputs/maps")

    lines = A.normalise_lines(read_vector(P["shorelines_vector"]), work)
    all_brg = read_vector(P["barangays_all"], work)
    study = read_vector(P["barangays_study"], work)
    land = unary_union(list(all_brg.geometry))
    scope = CoastScope(list(lines.geometry), land, cfg["scope"]["hull_tolerance_m"], cfg["scope"].get("concave_ratio", 0.1))
    zones = zone_grid(r, scope)

    inv = inventory(r); inv.to_csv(tbl / "gee_raster_inventory.csv", index=False)
    leg = legend_check(r, cfg["risk"]["low_max"], cfg["risk"]["medium_max"])
    qn = quantisation(r)
    ext = extremes(r, zones); ext.to_csv(tbl / "gee_extreme_epr_pixels.csv", index=False)
    noise = edge_noise(r, zones); noise.to_csv(tbl / "gee_edge_noise.csv", index=False)
    plaus = plausibility(r, zones, lines, scope); plaus.to_csv(tbl / "gee_plausibility.csv", index=False)

    legacy = pd.read_csv(repo_path(P["gee_stats_csv"]))
    legacy_n = legacy.rename(columns={"Mean_EPR_m_yr": "Mean_EPR", "Min_EPR_m_yr": "Min_EPR", "Max_EPR_m_yr": "Max_EPR",
                                       "Mean_NSM_m": "Mean_NSM", "Min_NSM_m": "Min_NSM", "Max_NSM_m": "Max_NSM",
                                       "Low_Risk_ha": "Low_ha", "Medium_Risk_ha": "Medium_ha", "High_Risk_ha": "High_ha",
                                       "Erosion_Area_ha": "Erosion_ha", "Accretion_Area_ha": "Accretion_ha"}).drop(columns=[".geo", "system:index"])
    repro = reproduce_csv(r, cfg)
    comp = legacy_n.merge(repro, on="Barangay", suffixes=("_csv", "_repro"))
    comp.to_csv(tbl / "gee_csv_reproduction.csv", index=False)
    official = official_stats(r, study, cfg["barangay_join_tolerance_m"])
    official.to_csv(tbl / "gee_stats_official_polygons.csv", index=False)
    side = legacy_n.merge(official, on="Barangay", suffixes=("_legacy", "_official"))
    side.to_csv(tbl / "gee_stats_side_by_side.csv", index=False)

    map_zones(r, zones, scope, mp / "gee_zones_and_change.png")
    map_edge_noise(r, mp / "gee_edge_noise_by_year.png")
    map_hotspots(r, study, mp / "gee_high_medium_pixels.png")
    legacy_plot = legacy.rename(columns={"Low_Risk_ha": "Low_Risk_ha"})
    map_stats_compare(legacy_plot, repro.rename(columns={"Low_ha": "Low_ha", "High_ha": "High_ha"}), official, mp / "gee_stats_comparison.png")
    for f in list(tbl.glob("gee_*.csv")) + list(mp.glob("gee_*.png")):
        rep.add_output(f)

    ctx = dict(cfg=cfg, r=r, inv=inv, leg=leg, qn=qn, ext=ext, noise=noise, plaus=plaus, legacy=legacy_n, repro=repro,
               comp=comp, official=official, study=study, zones=zones)
    from .audit_gee_report import render
    doc = render(ctx)
    rep.add_output(doc)
    rep.count("pixels", int(r.epr.size))
    return rep.write()


if __name__ == "__main__":  # pragma: no cover
    run()
