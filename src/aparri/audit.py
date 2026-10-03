"""Phase 2: forensic audit of the legacy vector shorelines (B) and risk polygons (C).

Read-only.  Every check returns plain pandas/GeoPandas objects so it can be unit
tested; ``run()`` writes the CSV tables, the diagnostic maps and ``docs/01_data_audit.md``.
Verdicts are CONFIRMED / REFUTED / INCONCLUSIVE and are computed from the numbers,
not typed by hand, so the document cannot drift from the evidence.

Terms (first use):  EPR = End Point Rate = (later position - earlier position) / years,
in m/yr, negative = landward = erosion.  NSM = Net Shoreline Movement = that distance.
"""
from __future__ import annotations

import math
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from pyproj import Geod
from rasterio.features import rasterize, shapes
from shapely.geometry import MultiPoint, Point, shape
from shapely.ops import unary_union

from .io import ensure_dir, load_config, read_vector, repo_path
from .runreport import RunReport

LEVEL_ORDER = ["LOW", "Med", "Hig", "High"]


# --------------------------------------------------------------------------- helpers
def pixel_area_ha(transform, lat: float, lon: float) -> float:
    """Geodesic area (ha) of one raster pixel near (lon, lat).  Pixels in EPSG:4326 are
    not square in metres, so ``res**2`` would be wrong."""
    dx, dy = transform.a, -transform.e
    ring = [(lon, lat), (lon + dx, lat), (lon + dx, lat + dy), (lon, lat + dy)]
    area, _ = Geod(ellps="WGS84").polygon_area_perimeter([p[0] for p in ring], [p[1] for p in ring])
    return abs(area) / 1e4


def _vertices(geom) -> np.ndarray:
    pts: list = []
    parts = geom.geoms if hasattr(geom, "geoms") else [geom]
    for p in parts:
        if p.geom_type == "Polygon":
            pts += list(p.exterior.coords)
            for r in p.interiors:
                pts += list(r.coords)
        elif p.geom_type == "LineString":
            pts += list(p.coords)
    return np.array(pts)[:, :2] if pts else np.empty((0, 2))


def grid_alignment(gdf: gpd.GeoDataFrame, x0: float, y0: float, res: float, tol: float = 0.02) -> dict:
    """Fraction of vertices lying on a raster lattice (origin x0,y0; cell size ``res``).
    Vectorised raster cells score ~1; hand-drawn lines score ~tol*2 by chance."""
    v = np.vstack([_vertices(g) for g in gdf.geometry]) if len(gdf) else np.empty((0, 2))
    if len(v) == 0:
        return {"n_vertices": 0, "on_grid_x": np.nan, "on_grid_y": np.nan, "on_grid_both": np.nan}
    fx = ((v[:, 0] - x0) / res) % 1
    fy = ((y0 - v[:, 1]) / res) % 1
    ox = np.minimum(fx, 1 - fx) < tol
    oy = np.minimum(fy, 1 - fy) < tol
    return {"n_vertices": len(v), "on_grid_x": float(ox.mean()), "on_grid_y": float(oy.mean()),
            "on_grid_both": float((ox & oy).mean())}


def repair(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """In-memory repair of invalid polygons (never written back; the count is reported)."""
    from shapely import make_valid
    out = gdf.copy()
    fixed = []
    for g in out.geometry:
        if g is not None and not g.is_valid:
            g = make_valid(g)
            if g.geom_type == "GeometryCollection":
                polys = [x for x in g.geoms if x.geom_type in ("Polygon", "MultiPolygon")]
                g = unary_union(polys) if polys else g
        fixed.append(g)
    out["geometry"] = fixed
    return out


def n_vertices(geom) -> int:
    return len(_vertices(geom))


def dbf_fields(shp: Path | str) -> list[dict]:
    """Field name/type/width read straight from the .dbf header (explains the 'Hig'/'Med'
    spellings: a 3-character text field silently truncates 'High' and 'Medium')."""
    import struct
    b = Path(shp).with_suffix(".dbf").read_bytes()
    out, i = [], 32
    while b[i] != 0x0D:
        out.append({"name": b[i:i + 11].split(b"\0")[0].decode(), "type": chr(b[i + 11]), "width": b[i + 16], "decimals": b[i + 17]})
        i += 32
    return out


def verdict(condition: bool | None) -> str:
    return "INCONCLUSIVE" if condition is None else ("CONFIRMED" if condition else "REFUTED")


# --------------------------------------------------------------------------- check 1-3: risk layer
def risk_attribute_audit(risk: gpd.GeoDataFrame, work_crs: int, pixel_ha: float) -> dict:
    """Attribute-level audit of the legacy risk polygons (check 1)."""
    u = risk.to_crs(work_crs)
    df = pd.DataFrame({
        "Risk_Level": risk["Risk_Level"].astype("string"),
        "EPR_90_25": risk["EPR_90_25"],
        "count": risk["count"],
        "Risk_Code": risk["Risk_Code"],
        "label": risk["label"],
        "geom_type": risk.geom_type,
        "area_ha": u.area / 1e4,
    })
    df["n_vertices"] = [n_vertices(g) for g in risk.geometry]
    df["ha_per_count"] = df["area_ha"] / df["count"]
    df["pixel_type"] = (df["ha_per_count"] / pixel_ha - 1).abs() < 0.02   # area == count x pixel?
    df["valid"] = risk.is_valid.values
    out = {"table": df}
    out["by_label"] = df.groupby("Risk_Level", dropna=False).agg(
        polygons=("area_ha", "size"), area_ha=("area_ha", "sum"), pixels_in_count=("count", "sum")).reset_index()
    out["crosstab"] = pd.crosstab(df["Risk_Level"], df["EPR_90_25"].round(6))
    out["by_type"] = df.groupby(["Risk_Level", df["EPR_90_25"].round(6), "pixel_type"]).agg(
        polygons=("area_ha", "size"), area_ha=("area_ha", "sum"), count=("count", "sum"),
        median_vertices=("n_vertices", "median"), min_ha=("area_ha", "min"), max_ha=("area_ha", "max")).reset_index()
    out["geom_types"] = df["geom_type"].value_counts().to_dict()
    out["n_invalid"] = int((~df["valid"]).sum())
    out["nan_rows"] = int(df[["Risk_Level", "EPR_90_25", "count"]].isna().any(axis=1).sum())
    out["distinct_epr"] = sorted(df["EPR_90_25"].round(6).unique().tolist())
    out["distinct_code"] = sorted(df["Risk_Code"].unique().tolist())
    out["distinct_label"] = sorted(df["label"].unique().tolist())
    out["label_variants"] = sorted(df["Risk_Level"].dropna().unique().tolist())
    return out


def threshold_consistency(risk: pd.DataFrame, low_max: float, medium_max: float) -> dict:
    """Check 2: does each polygon's own EPR agree with its label under Table 3.1?

    The legacy EPR is positive everywhere; under the thesis sign convention positive means
    accretion.  We test both readings: (a) EPR as an erosion *magnitude*, (b) as signed.
    """
    def cls(m: float) -> str:
        return "LOW" if m < low_max else ("Med" if m <= medium_max else "Hig")
    d = risk.copy()
    d["class_if_magnitude"] = d["EPR_90_25"].abs().map(cls)
    d["label3"] = d["Risk_Level"].astype(str).str[:3].replace({"Hig": "Hig", "Med": "Med", "LOW": "LOW"})
    d["violates_as_magnitude"] = d["class_if_magnitude"] != d["label3"]
    d["signed_reading"] = np.where(d["EPR_90_25"] > 0, "accretion (positive)", np.where(d["EPR_90_25"] < 0, "erosion (negative)", "stable"))
    return {
        "n": len(d),
        "n_violations": int(d["violates_as_magnitude"].sum()),
        "violations_by_label": d[d["violates_as_magnitude"]].groupby("Risk_Level").agg(
            polygons=("area_ha", "size"), area_ha=("area_ha", "sum")).reset_index(),
        "all_positive": bool((d["EPR_90_25"] > 0).all()),
        "n_negative": int((d["EPR_90_25"] < 0).sum()),
        "table": d,
    }


def raster_reproduction(risk: gpd.GeoDataFrame, risk_tif: Path, epr_tif: Path) -> dict:
    """Check 3b: can the polygons be reproduced from the Earth Engine risk raster?"""
    with rasterio.open(risk_tif) as ds:
        rk = ds.read(1)
        tr, shape_, bounds = ds.transform, rk.shape, ds.bounds
    with rasterio.open(epr_tif) as ds:
        epr = ds.read(1)
    lab = {"LOW": 1, "Med": 2, "Hig": 3}
    conf = pd.DataFrame(0, index=["LOW", "Med", "Hig"], columns=[1, 2, 3])
    cover = np.zeros(shape_, bool)
    epr_under: dict[str, np.ndarray] = {}
    for name in lab:
        sub = risk[risk["Risk_Level"].astype(str).str[:3] == name]
        m = rasterize(((g, 1) for g in sub.geometry), out_shape=shape_, transform=tr).astype(bool)
        cover |= m
        for c in (1, 2, 3):
            conf.loc[name, c] = int((rk[m] == c).sum())
        epr_under[name] = epr[m]
    # polygon area outside the raster footprint
    foot = gpd.GeoSeries([shape({"type": "Polygon", "coordinates": [[(bounds.left, bounds.bottom), (bounds.right, bounds.bottom), (bounds.right, bounds.top), (bounds.left, bounds.top)]]})], crs=4326)
    inter = risk.geometry.intersection(foot.iloc[0])
    outside_ha = (risk.to_crs(32651).area.sum() - inter.set_crs(4326).to_crs(32651).area.sum()) / 1e4
    return {
        "confusion": conf,
        "raster_class_pixels": {int(c): int((rk == c).sum()) for c in (1, 2, 3)},
        "raster_class_inside_any_polygon": {int(c): int((cover & (rk == c)).sum()) for c in (2, 3)},
        "epr_under": {k: {"n": int(v.size), "min": float(v.min()) if v.size else np.nan,
                           "median": float(np.median(v)) if v.size else np.nan, "max": float(v.max()) if v.size else np.nan}
                      for k, v in epr_under.items()},
        "polygon_area_outside_raster_ha": float(outside_ha),
        "raster_bounds": tuple(bounds),
    }


# --------------------------------------------------------------------------- check 4: shoreline layer
def normalise_lines(raw: gpd.GeoDataFrame, work_crs: int) -> gpd.GeoDataFrame:
    """Give the legacy line layer sane column names; keep the original value untouched.

    The legacy file has a column literally named "1990" holding the year text (QGIS import
    used the first data row as a header) and an unused ``id``.
    """
    year_col = next((c for c in raw.columns if re.fullmatch(r"\d{4}", str(c))), None)
    g = raw.to_crs(work_crs).copy()
    g["fid"] = range(len(g))
    g["year_raw"] = g[year_col].astype(str) if year_col else "?"
    g["year"] = pd.to_numeric(g["year_raw"], errors="coerce")
    return g[["fid", "year_raw", "year", "geometry"]]


def _endpoints(geom) -> list[Point]:
    c = list(geom.coords)
    return [Point(c[0]), Point(c[-1])]


def dup_vertices(geom, tol: float = 0.01) -> int:
    c = np.array(geom.coords)[:, :2]
    d = np.hypot(*np.diff(c, axis=0).T)
    return int((d < tol).sum())


def fragment_table(lines: gpd.GeoDataFrame, overlap_tol_m: float = 15.0) -> pd.DataFrame:
    """Per-feature facts: length, vertices, simplicity (self-crossing), endpoint gaps,
    and how much of the feature runs on top of another feature of the SAME year."""
    rows = []
    for year_raw, grp in lines.groupby("year_raw", sort=True):
        ends = [(r.fid, k, p) for _, r in grp.iterrows() for k, p in zip("se", _endpoints(r.geometry))]
        for _, r in grp.iterrows():
            others = unary_union([x for i, x in zip(grp.index, grp.geometry) if i != r.name]) if len(grp) > 1 else None
            overlap = float(r.geometry.intersection(others.buffer(overlap_tol_m)).length / r.geometry.length) if others is not None else 0.0
            gaps = {}
            for k, p in zip("se", _endpoints(r.geometry)):
                cand = [p.distance(q) for f, kk, q in ends if f != r.fid]
                gaps[k] = min(cand) if cand else np.nan
            rows.append({
                "fid": r.fid, "year_raw": year_raw, "length_km": r.geometry.length / 1000,
                "n_vertices": n_vertices(r.geometry),
                "mean_vertex_spacing_m": r.geometry.length / max(n_vertices(r.geometry) - 1, 1),
                "is_simple": bool(r.geometry.is_simple), "dup_vertices": dup_vertices(r.geometry),
                "gap_start_m": gaps["s"], "gap_end_m": gaps["e"],
                "overlap_with_same_year_frac": overlap,
                "x0": r.geometry.coords[0][0], "y0": r.geometry.coords[0][1],
                "x1": r.geometry.coords[-1][0], "y1": r.geometry.coords[-1][1],
            })
    return pd.DataFrame(rows)


def unique_length_km(grp: gpd.GeoDataFrame, tol_m: float = 60.0) -> float:
    """Length of a year's lines after discarding stretches that run on top of an already
    counted feature (greedy, longest first).  Measures digitising the same coast twice."""
    covered = None
    total = 0.0
    for g in sorted(grp.geometry, key=lambda x: -x.length):
        new = g if covered is None else g.difference(covered.buffer(tol_m))
        total += new.length
        covered = g if covered is None else unary_union([covered, g])
    return total / 1000


def year_table(lines: gpd.GeoDataFrame, frag: pd.DataFrame) -> pd.DataFrame:
    g = frag.groupby("year_raw").agg(
        features=("fid", "size"), total_km=("length_km", "sum"), vertices=("n_vertices", "sum"),
        non_simple_features=("is_simple", lambda s: int((~s).sum())), dup_vertices=("dup_vertices", "sum"),
        max_overlap_frac=("overlap_with_same_year_frac", "max")).reset_index()
    g["mean_vertex_spacing_m"] = g["total_km"] * 1000 / (g["vertices"] - g["features"]).clip(lower=1)
    g["unique_km"] = [unique_length_km(lines[lines.year_raw == y]) for y in g["year_raw"]]
    g["duplicated_km"] = g["total_km"] - g["unique_km"]
    return g


def along_axis_coverage(lines: gpd.GeoDataFrame) -> tuple[pd.DataFrame, np.ndarray]:
    """Common extent: project every segment on the NW->SE axis of the study coast and
    report each year's covered interval (km).  This is a coarse 1-D view that avoids
    pretending that river-bank lines are 'coast'."""
    allv = np.vstack([_vertices(g) for g in lines.geometry])
    # axis from the two extreme vertices along (x - y): NW end (min) and SE end (max)
    s = allv[:, 0] - allv[:, 1]
    a, b = allv[np.argmin(s)], allv[np.argmax(s)]
    ax = (b - a) / np.linalg.norm(b - a)
    rows = []
    for yr, grp in lines.groupby("year_raw"):
        ts = np.concatenate([(_vertices(g) - a) @ ax for g in grp.geometry]) / 1000
        rows.append({"year_raw": yr, "t_min_km": ts.min(), "t_max_km": ts.max(), "span_km": ts.max() - ts.min()})
    df = pd.DataFrame(rows)
    num = df[df.year_raw.str.fullmatch(r"\d{4}")]
    common = (num.t_min_km.max(), num.t_max_km.min())
    df.attrs["common_extent_km"] = common
    return df, ax


def hig_candidates(lines: gpd.GeoDataFrame, hig_fid: int, buffer_m: float = 100.0) -> pd.DataFrame:
    """Which year is the odd-labelled feature most likely to be?  We DO NOT reassign it.

    Evidence: (i) how close it runs to each year's lines, (ii) which year has NO line in
    the neighbourhood (each year should have exactly one coast line there, so the missing
    year is a candidate for the stray feature)."""
    hig = lines.loc[lines.fid == hig_fid, "geometry"].iloc[0]
    zone = hig.buffer(buffer_m)
    pts = [Point(c) for c in list(hig.coords)]
    rows = []
    for yr, grp in lines[lines.year.notna()].groupby("year_raw"):
        u = unary_union(list(grp.geometry))
        d = np.array([u.distance(p) for p in pts])
        rows.append({"year_raw": yr, "median_dist_to_hig_m": float(np.median(d)), "p95_dist_m": float(np.percentile(d, 95)),
                     "share_hig_within_30m": float((d < 30).mean()),
                     "length_of_year_inside_hig_zone_m": float(u.intersection(zone).length)})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- check 5-6: joins & claims
def _poly_dist_matrix(gdf: gpd.GeoDataFrame, brg: gpd.GeoDataFrame) -> pd.DataFrame:
    return pd.DataFrame({b.ADM4_EN: gdf.geometry.distance(b.geometry).values for _, b in brg.iterrows()}, index=gdf.index)


def attribute_area(geom, brg_u: gpd.GeoDataFrame, tol_m: float, cell: float = 10.0) -> dict:
    """Split one polygon's area between barangays by assigning every ``cell`` x ``cell`` m
    sample to the NEAREST barangay polygon within ``tol_m`` (0 m inside).  Cells with no
    barangay within tolerance are returned under ``None``.  Needed because the legacy coast
    polygons straddle two barangays and sit just outside the land polygons."""
    import shapely
    minx, miny, maxx, maxy = geom.bounds
    xs = np.arange(minx + cell / 2, maxx, cell)
    ys = np.arange(miny + cell / 2, maxy, cell)
    gx, gy = np.meshgrid(xs, ys)
    pts = shapely.points(gx.ravel(), gy.ravel())
    inside = shapely.contains_xy(geom, gx.ravel(), gy.ravel())
    pts = pts[inside]
    if len(pts) == 0:
        return {None: geom.area / 1e4}
    dmat = np.vstack([shapely.distance(pts, b.geometry) for _, b in brg_u.iterrows()])
    near = dmat.argmin(axis=0)
    ok = dmat.min(axis=0) <= tol_m
    names = list(brg_u.ADM4_EN)
    out: dict = {}
    for i, n in enumerate(names):
        v = int(((near == i) & ok).sum())
        if v:
            out[n] = v * cell * cell / 1e4
    out[None] = int((~ok).sum()) * cell * cell / 1e4
    scale = (geom.area / 1e4) / max(sum(out.values()), 1e-12)   # make cells add up exactly
    return {k: v * scale for k, v in out.items() if v > 0}


def join_polygons(risk_u: gpd.GeoDataFrame, brg_u: gpd.GeoDataFrame, tol_m: float) -> pd.DataFrame:
    """Compare the two ways of attributing risk polygons to barangays.

    *Straight intersection* clips each polygon by the barangay polygons (area in ha).
    *Nearest-within-tolerance* gives each polygon the barangay whose boundary is nearest
    (if within ``tol_m``) - needed because the coast IS the barangay edge, so shoreline
    features fall just outside the land polygons."""
    rows = []
    for i, r in risk_u.iterrows():
        lvl = str(r["Risk_Level"])
        straight = {}
        for _, b in brg_u.iterrows():
            a = r.geometry.intersection(b.geometry).area / 1e4
            if a > 0:
                straight[b.ADM4_EN] = a
        split = attribute_area(r.geometry, brg_u, tol_m)
        for k, v in straight.items():
            rows.append({"poly": i, "Risk_Level": lvl, "method": "straight", "barangay": k, "area_ha": v})
        s_tot = sum(straight.values())
        a_tot = r.geometry.area / 1e4
        if a_tot - s_tot > 1e-6:
            rows.append({"poly": i, "Risk_Level": lvl, "method": "straight", "barangay": None, "area_ha": a_tot - s_tot})
        for k, v in split.items():
            rows.append({"poly": i, "Risk_Level": lvl, "method": "nearest_tol", "barangay": k, "area_ha": v})
    return pd.DataFrame(rows)


def lines_vs_barangays(lines: gpd.GeoDataFrame, brg_u: gpd.GeoDataFrame, tol_m: float) -> pd.DataFrame:
    """Length (km) of each year's shoreline inside each study barangay (straight) and within tolerance."""
    rows = []
    numeric = lines[lines.year.notna()]
    for yr, grp in numeric.groupby("year_raw"):
        u = unary_union(list(grp.geometry))
        for _, b in brg_u.iterrows():
            rows.append({"year": yr, "barangay": b.ADM4_EN,
                         "inside_km": u.intersection(b.geometry).length / 1000,
                         "within_tol_km": u.intersection(b.geometry.buffer(tol_m)).length / 1000,
                         "min_distance_m": u.distance(b.geometry)})
    return pd.DataFrame(rows)


def thesis_claims(join: pd.DataFrame, brg_names: list[str]) -> tuple[pd.DataFrame, list[str]]:
    """Check 6: what the legacy layer shows per barangay vs what Chapter IV says.

    Chapter IV: High in Bulala Sur and Bulala Norte; Medium in Bulala Norte, Punta, San Antonio,
    Maura, Dodan, Paddaya; Low in Linao.  We tabulate nearest-join area by class and list
    each contradiction found."""
    j = join[join.method == "nearest_tol"].copy()
    j["brg"] = j["barangay"].fillna("(no barangay within tolerance)")
    j["cls"] = j["Risk_Level"].str[:3].replace({"Hig": "High", "Med": "Medium", "LOW": "Low"})
    t = j.pivot_table(index="brg", columns="cls", values="area_ha", aggfunc="sum", fill_value=0.0)
    for c in ("Low", "Medium", "High"):
        if c not in t:
            t[c] = 0.0
    t = t.reindex(brg_names + [x for x in t.index if x not in brg_names])[["Low", "Medium", "High"]].fillna(0.0)
    claims = {
        "High": ["Bulala Sur", "Bulala Norte"],
        "Medium": ["Bulala Norte", "Punta", "San Antonio", "Maura", "Dodan", "Paddaya"],
        "Low": ["Linao"],
    }
    notes: list[str] = []
    for cls, names in claims.items():
        for n in names:
            v = float(t.loc[n, cls]) if n in t.index else 0.0
            if v <= 0:
                notes.append(f"Thesis says {cls} risk occurs in {n}, but the legacy layer has 0.00 ha of {cls} attributed to {n}.")
    for n in brg_names:
        v = t.loc[n] if n in t.index else None
        if v is not None and v["High"] > 0 and n not in claims["High"]:
            notes.append(f"The legacy layer puts {v['High']:.1f} ha of High risk in {n}; the thesis does not list High risk there.")
        if v is not None and v["Medium"] > 0 and n not in claims["Medium"]:
            notes.append(f"The legacy layer puts {v['Medium']:.1f} ha of Medium risk in {n}; the thesis does not list it.")
    return t, notes


# --------------------------------------------------------------------------- check 7: QGIS forensics
def qgis_forensics(qgz: Path, project_dir: Path) -> dict:
    """Unzip the project in memory and read layers, CRS, broken links, layouts."""
    with zipfile.ZipFile(qgz) as z:
        name = next(n for n in z.namelist() if n.endswith(".qgs"))
        root = ET.fromstring(z.read(name))
    layers = []
    for ml in root.iter("maplayer"):
        ds = ml.findtext("datasource") or ""
        is_file = not (ds.startswith("crs=") or ds.startswith("styleUrl") or "url=" in ds)
        exists = None
        if is_file:
            exists = (project_dir / ds).resolve().exists()
        layers.append({"layer": ml.findtext("layername"), "type": ml.get("type"), "source": ds,
                       "crs": ml.findtext("srs/spatialrefsys/authid"), "is_local_file": is_file, "found_on_disk": exists,
                       "renderer_field": (ml.find("renderer-v2").get("attr") if ml.find("renderer-v2") is not None else None)})
    layouts = []
    for lay in root.find("Layouts") or []:
        title = next((i.get("labelText") for i in lay.iter("LayoutItem") if i.get("id") == "Title"), None)
        maps_ = [i for i in lay.iter("LayoutItem") if i.get("type") == "65639"]
        layouts.append({"layout": lay.get("name"), "title": title,
                        "map_items": len(maps_),
                        "layer_set_locked": any(m.get("keepLayerSet") == "true" for m in maps_),
                        "follows_preset": any(m.get("followPreset") == "true" for m in maps_)})
    return {
        "qgis_version": root.get("version"), "saved": root.get("saveDateTime"), "saved_by": root.get("saveUser"),
        "project_crs": root.findtext("projectCrs/spatialrefsys/authid"),
        "layers": pd.DataFrame(layers), "layouts": pd.DataFrame(layouts),
        "visibility_presets": [p.get("name") for p in root.iter("visibility-preset")],
        "has_processing_history": any("istory" in e.tag for e in root.iter()),
    }


# --------------------------------------------------------------------------- maps
def _style():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt


YEAR_COLORS = {"1990": "#1f3a93", "2000": "#2ecc40", "2010": "#8e44ad", "2020": "#e74c3c", "2025": "#f39c12", "Hig": "#000000"}


def map_risk_by_label(risk_u: gpd.GeoDataFrame, brg_u: gpd.GeoDataFrame, out: Path) -> None:
    plt = _style()
    fig, ax = plt.subplots(figsize=(13, 6))
    brg_u.boundary.plot(ax=ax, color="0.4", lw=0.7)
    col = {"LOW": "#2e8b57", "Med": "#ff9900", "Hig": "#d62728"}
    for lvl, c in col.items():
        sub = risk_u[risk_u.Risk_Level.astype(str) == lvl]
        if len(sub):
            sub.plot(ax=ax, color=c, alpha=0.75, edgecolor="k", linewidth=0.2, label=f"{lvl}  (n={len(sub)})")
    big = risk_u[risk_u["pixel_type"] == False]  # noqa: E712
    big.boundary.plot(ax=ax, color="k", lw=1.4)
    for _, b in brg_u.iterrows():
        c = b.geometry.representative_point()
        ax.annotate(b.ADM4_EN, (c.x, c.y), fontsize=7, color="0.2")
    ax.set_title("AUDIT: legacy risk polygons by label (thick black outline = polygons whose area is NOT count x pixel area, i.e. not pixel-derived)", fontsize=9)
    ax.legend(loc="lower left", fontsize=8); ax.set_aspect("equal"); ax.set_xlabel("Easting (m, EPSG:32651)"); ax.set_ylabel("Northing (m)")
    fig.tight_layout(); fig.savefig(out, dpi=150); plt.close(fig)


def map_fragments(lines: gpd.GeoDataFrame, out: Path, zoom: tuple | None = None, title: str = "") -> None:
    plt = _style()
    ncols = 3
    years = [y for y in ["1990", "2000", "2010", "2020", "2025", "Hig"] if (lines.year_raw == y).any()]
    fig, axes = plt.subplots(2, ncols, figsize=(16, 8), sharex=True, sharey=True)
    for ax, y in zip(axes.ravel(), years):
        sub = lines[lines.year_raw == y]
        for i, (_, r) in enumerate(sub.iterrows()):
            xs, ys = r.geometry.xy
            ax.plot(xs, ys, color=plt.cm.tab10(i), lw=1.1, label=f"fid {r.fid} ({r.geometry.length/1000:.1f} km)")
            ax.plot(xs[0], ys[0], "o", color=plt.cm.tab10(i), ms=6, mec="k"); ax.plot(xs[-1], ys[-1], "s", color=plt.cm.tab10(i), ms=6, mec="k")
        ax.set_title(f"{y}: {len(sub)} fragments, {sub.length.sum()/1000:.1f} km  (o start, s end)", fontsize=9)
        ax.legend(fontsize=6, loc="lower left"); ax.set_aspect("equal"); ax.tick_params(labelsize=6)
        if zoom:
            ax.set_xlim(zoom[0], zoom[2]); ax.set_ylim(zoom[1], zoom[3])
    for ax in axes.ravel()[len(years):]:
        ax.axis("off")
    fig.suptitle(title or "AUDIT: legacy shoreline fragments by year with endpoints (EPSG:32651)", fontsize=11)
    fig.tight_layout(); fig.savefig(out, dpi=140); plt.close(fig)


def map_barangay_edges(lines: gpd.GeoDataFrame, brg_u: gpd.GeoDataFrame, out: Path) -> None:
    plt = _style()
    fig, ax = plt.subplots(figsize=(13, 6))
    brg_u.plot(ax=ax, color="#e8e0c8", edgecolor="0.3", lw=0.7)
    for y, c in YEAR_COLORS.items():
        sub = lines[lines.year_raw == y]
        if len(sub):
            sub.plot(ax=ax, color=c, lw=0.9, label=y)
    for _, b in brg_u.iterrows():
        p = b.geometry.representative_point()
        ax.annotate(b.ADM4_EN, (p.x, p.y), fontsize=7)
    ax.set_title("AUDIT: study-barangay polygons and legacy shorelines: the coast is the barangay EDGE, so straight intersection loses it", fontsize=9)
    ax.legend(fontsize=7, ncol=6, loc="lower left"); ax.set_aspect("equal")
    fig.tight_layout(); fig.savefig(out, dpi=150); plt.close(fig)


# --------------------------------------------------------------------------- orchestration
def run() -> Path:  # pragma: no cover - exercised by `make audit`
    cfg = load_config()
    rep = RunReport("audit", cfg)
    work = cfg["crs_work"]
    P = cfg["paths"]
    for k in ("shorelines_vector", "risk_legacy", "barangays_study", "barangays_all", "qgz"):
        rep.add_input(P[k])
    tbl = ensure_dir("outputs/tables"); mp = ensure_dir("outputs/maps")

    risk_orig = read_vector(P["risk_legacy"])
    risk = repair(risk_orig)          # invalid count is reported from the original in the attribute audit
    brg = read_vector(P["barangays_study"], work)
    raw_lines = read_vector(P["shorelines_vector"])
    lines = normalise_lines(raw_lines, work)
    risk_u = risk.to_crs(work)

    gee = repo_path(P["gee_dir"])
    with rasterio.open(gee / "Aparri_Erosion_Risk_1990_2025.tif") as ds:
        px_ha = pixel_area_ha(ds.transform, (ds.bounds.top + ds.bounds.bottom) / 2, (ds.bounds.left + ds.bounds.right) / 2)
        x0, y0, res = ds.bounds.left, ds.bounds.top, ds.res[0]
    rep.add_input(gee / "Aparri_Erosion_Risk_1990_2025.tif"); rep.add_input(gee / "Aparri_EPR_1990_2025.tif")

    # ---- 1
    a = risk_attribute_audit(risk_orig, work, px_ha)
    tab = a["table"]
    a["by_label"].to_csv(tbl / "audit_risk_by_label.csv", index=False)
    a["crosstab"].to_csv(tbl / "audit_risk_label_x_epr.csv")
    a["by_type"].to_csv(tbl / "audit_risk_by_type.csv", index=False)
    tab.to_csv(tbl / "audit_risk_polygons.csv", index=False)
    pix = tab[tab.pixel_type]; non = tab[~tab.pixel_type]
    count_is_pixels = len(pix) > 0 and (pix["ha_per_count"].std() < 1e-3)
    # ---- 2
    t = threshold_consistency(tab.assign(area_ha=tab.area_ha), cfg["risk"]["low_max"], cfg["risk"]["medium_max"])
    t["violations_by_label"].to_csv(tbl / "audit_threshold_violations.csv", index=False)
    # ---- 3
    g_all = grid_alignment(risk, x0, y0, res)
    g_pix = grid_alignment(risk[tab.pixel_type.values], x0, y0, res)
    g_non = grid_alignment(risk[~tab.pixel_type.values], x0, y0, res)
    g_lines = grid_alignment(raw_lines, x0, y0, res)
    rr = raster_reproduction(risk, gee / "Aparri_Erosion_Risk_1990_2025.tif", gee / "Aparri_EPR_1990_2025.tif")
    rr["confusion"].to_csv(tbl / "audit_risk_vs_raster_confusion.csv")
    # ---- 4
    frag = fragment_table(lines); frag.to_csv(tbl / "audit_shoreline_fragments.csv", index=False)
    yt = year_table(lines, frag); yt.to_csv(tbl / "audit_shoreline_years.csv", index=False)
    cov, _ax = along_axis_coverage(lines); cov.to_csv(tbl / "audit_shoreline_coverage.csv", index=False)
    hig_fid = int(lines.loc[lines.year.isna(), "fid"].iloc[0]) if lines.year.isna().any() else None
    hc = hig_candidates(lines, hig_fid) if hig_fid is not None else pd.DataFrame()
    hc.to_csv(tbl / "audit_hig_candidates.csv", index=False)
    # ---- 5
    tol = cfg["barangay_join_tolerance_m"]
    jn = join_polygons(risk_u.assign(Risk_Level=risk_u.Risk_Level.astype(str)), brg, tol)
    jn.to_csv(tbl / "audit_risk_join.csv", index=False)
    lb = lines_vs_barangays(lines, brg, tol); lb.to_csv(tbl / "audit_lines_vs_barangays.csv", index=False)
    # ---- 6
    claims_tab, notes = thesis_claims(jn, cfg["study_barangays"])
    claims_tab.to_csv(tbl / "audit_thesis_claims.csv")
    # ---- 7
    qf = qgis_forensics(repo_path(P["qgz"]), repo_path(P["qgz"]).parent)
    qf["layers"].to_csv(tbl / "audit_qgis_layers.csv", index=False); qf["layouts"].to_csv(tbl / "audit_qgis_layouts.csv", index=False)
    # ---- 8 maps
    risk_u2 = risk_u.assign(pixel_type=tab.pixel_type.values)
    map_risk_by_label(risk_u2, brg, mp / "audit_risk_by_label.png")
    map_fragments(lines, mp / "audit_shoreline_fragments_by_year.png")
    map_fragments(lines, mp / "audit_river_mouth_zoom.png", zoom=(347000, 2026500, 360000, 2035000),
                  title="AUDIT: river-mouth / Linao area zoom (EPSG:32651)")
    map_barangay_edges(lines, brg, mp / "audit_barangay_edges.png")
    for f in list(tbl.glob("audit_*.csv")) + list(mp.glob("audit_*.png")):
        rep.add_output(f)

    dbf_risk = dbf_fields(repo_path(P["risk_legacy"]))
    dbf_lines = dbf_fields(repo_path(P["shorelines_vector"]))
    ctx = dict(dbf_risk=dbf_risk, dbf_lines=dbf_lines, n_invalid=a["n_invalid"], cfg=cfg, a=a, t=t, g_all=g_all, g_pix=g_pix, g_non=g_non, g_lines=g_lines, rr=rr, frag=frag, yt=yt, cov=cov,
               hc=hc, hig_fid=hig_fid, jn=jn, lb=lb, claims_tab=claims_tab, notes=notes, qf=qf, px_ha=px_ha,
               count_is_pixels=count_is_pixels, pix=pix, non=non, lines=lines, brg=brg, tol=tol)
    doc = write_report(ctx)
    rep.add_output(doc)
    rep.count("risk_polygons", len(risk)); rep.count("line_features", len(lines))
    rep.warn_if_null(cfg["uncertainty_m"], "uncertainty_m")
    out = rep.write()
    print("audit done ->", doc)
    return out


def write_report(c: dict) -> Path:  # pragma: no cover
    from .audit_report import render
    return render(c)


if __name__ == "__main__":  # pragma: no cover
    run()
