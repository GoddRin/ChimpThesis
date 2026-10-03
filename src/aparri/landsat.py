"""Phase 3C (OPTIONAL): defensible shoreline re-derivation from Landsat index rasters.

STATUS: **not executed on real data** - the Landsat catalogues and Earth Engine are unreachable from
the analysis sandbox (see docs/decisions.md D-04).  What is provided and unit-tested here is the part
that does not need the internet: turning per-year water-index rasters into SUB-PIXEL shorelines with a
per-year (Otsu) threshold.  The imagery step is ``scripts/gee_v2.js`` (run by the students in their own
Earth Engine account); its exported rasters go to ``data/raw/landsat_v2/`` and ``make landsat`` does the rest.

Why this is better than the legacy method (see docs/01b_gee_audit.md):
  * seasonal composite (one fixed window every year) instead of a whole-year median;
  * a per-year Otsu threshold instead of a fixed NDWI > 0;
  * a sub-pixel *contour* of the index (marching squares) instead of a 2-pixel edge band;
  * image count / dates / sensors recorded per year;
  * the index rasters are saved, so every step is auditable.
Expected positional uncertainty is still about one pixel (30 m); config.uncertainty_m.pixel = 30 is applied
ONLY to this set (rule: set automatically per shoreline_set).
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import LineString
from shapely.ops import linemerge, unary_union
from skimage import measure
from skimage.filters import threshold_otsu

from .clean import CleanLog, common_extent_table, orient_nw_se, tag_parts, write_gpkg
from .io import ensure_dir, load_config, read_vector, repo_path
from .runreport import RunReport


# --------------------------------------------------------------------------- water indices
def ndwi(green: np.ndarray, nir: np.ndarray) -> np.ndarray:
    """McFeeters NDWI = (G - NIR) / (G + NIR)."""
    return _nd(green, nir)


def mndwi(green: np.ndarray, swir1: np.ndarray) -> np.ndarray:
    """Xu's MNDWI = (G - SWIR1) / (G + SWIR1): suppresses built-up/sand better than NDWI."""
    return _nd(green, swir1)


def aweish(blue, green, nir, swir1, swir2) -> np.ndarray:
    """Feyisa's AWEIsh = B + 2.5 G - 1.5 (NIR + SWIR1) - 0.25 SWIR2."""
    return blue + 2.5 * green - 1.5 * (nir + swir1) - 0.25 * swir2


def _nd(a, b):
    a = a.astype("float64"); b = b.astype("float64")
    with np.errstate(divide="ignore", invalid="ignore"):
        return (a - b) / (a + b)


# --------------------------------------------------------------------------- threshold & contour
def otsu(values: np.ndarray, valid: np.ndarray | None = None, nbins: int = 256) -> float:
    """Otsu threshold of the index inside a window around the coast (bimodal land/water histogram)."""
    v = values[valid] if valid is not None else values[np.isfinite(values)]
    v = v[np.isfinite(v)]
    if v.size < 50 or np.ptp(v) == 0:
        raise ValueError("not enough valid pixels for an Otsu threshold")
    return float(threshold_otsu(v, nbins=nbins))


def contour_lines(index: np.ndarray, level: float, transform, min_len_m: float = 90.0) -> list[LineString]:
    """Marching-squares contour of ``index`` at ``level`` as map-coordinate lines (sub-pixel).

    ``skimage.measure.find_contours`` works in pixel-index space where pixel centres are integers; we
    convert to map coordinates with the raster transform (centre = +0.5)."""
    idx = np.where(np.isfinite(index), index, np.nan)
    out = []
    for c in measure.find_contours(idx, level):
        x = transform.c + (c[:, 1] + 0.5) * transform.a
        y = transform.f + (c[:, 0] + 0.5) * transform.e
        if len(x) >= 2:
            ls = LineString(np.column_stack([x, y]))
            if ls.length >= min_len_m:
                out.append(ls)
    return out


# --------------------------------------------------------------------------- scene bookkeeping
def scene_quality(scenes: pd.DataFrame, min_images: int) -> pd.DataFrame:
    """Per-year data-quality table from the scene list exported by the GEE script
    (columns: year, scene_id, date, sensor, cloud_cover)."""
    g = scenes.groupby("year").agg(images=("scene_id", "nunique"), first_date=("date", "min"), last_date=("date", "max"),
                                   sensors=("sensor", lambda s: ",".join(sorted(set(s)))), mean_cloud_pct=("cloud_cover", "mean")).reset_index()
    g["enough_images"] = g["images"] >= min_images
    return g


# --------------------------------------------------------------------------- derivation
def derive_from_index_rasters(in_dir: Path, years: list[int], scope, cfg: dict, log: CleanLog) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, pd.DataFrame]:  # pragma: no cover
    import rasterio
    lc = cfg["landsat"]
    chains, parts, quality = [], [], []
    zone = scope.chain.buffer(lc.get("otsu_window_m", 3000))
    for y in years:
        p = in_dir / f"{lc['index']}_{y}.tif"
        if not p.exists():
            log.add("missing_input", y, str(p.name), 0, 0, "index raster not found - year skipped", review=True)
            continue
        with rasterio.open(p) as ds:
            arr = ds.read(1).astype("float64")
            if ds.nodata is not None:
                arr[arr == ds.nodata] = np.nan
            tr = ds.transform
            crs = ds.crs.to_epsg()
        if crs != cfg["crs_work"]:
            raise ValueError(f"{p.name} is EPSG:{crs}; export it in EPSG:{cfg['crs_work']} (see scripts/gee_v2.js)")
        rows, cols = np.indices(arr.shape)
        x = tr.c + (cols + 0.5) * tr.a; y_ = tr.f + (rows + 0.5) * tr.e
        import shapely
        win = shapely.contains_xy(zone, x.ravel(), y_.ravel()).reshape(arr.shape)
        thr = otsu(arr, win)
        ls = contour_lines(arr, thr, tr)
        log.add("contour", y, p.name, 0.0, sum(l.length for l in ls), f"Otsu threshold {thr:.3f}; {len(ls)} contour lines")
        merged = linemerge(ls) if ls else None
        geoms = list(merged.geoms) if merged is not None and merged.geom_type == "MultiLineString" else ([merged] if merged is not None else [])
        n = 0
        for g in geoms:
            if not g.intersects(zone):
                log.add("component_dropped", y, "landsat", g.length, 0.0, "contour does not touch the open-coast zone")
                continue
            n += 1
            g = LineString(orient_nw_se(np.array(g.coords)[:, :2]))
            cid = f"{y}-{n}"
            chains.append({"year": y, "chain_id": cid, "source_fids": p.name, "length_m": g.length, "n_vertices": len(g.coords), "geometry": g})
            for k, (sub, tag, ln) in enumerate(tag_parts(g, scope, cfg["clean"].get("min_scope_run_m", 150.0)), start=1):
                parts.append({"year": y, "chain_id": cid, "part_id": f"{cid}-{k}", "scope": tag, "scope_source": "rule", "length_m": sub.length, "geometry": sub})
        quality.append({"year": y, "otsu_threshold": thr, "contour_km": sum(g.length for g in geoms) / 1000})
    return gpd.GeoDataFrame(chains, crs=cfg["crs_work"]), gpd.GeoDataFrame(parts, crs=cfg["crs_work"]), pd.DataFrame(quality)


def run() -> None:  # pragma: no cover
    cfg = load_config()
    rep = RunReport("landsat", cfg)
    lc = cfg["landsat"]
    in_dir = repo_path(lc["input_dir"])
    tifs = sorted(in_dir.glob(f"{lc['index']}_*.tif")) if in_dir.exists() else []
    status = ensure_dir("outputs/reports") / "landsat_v2_status.txt"
    if not tifs:
        msg = (f"Phase 3C NOT RUN: no '{lc['index']}_<year>.tif' rasters in {lc['input_dir']}.\n"
               "1. Open scripts/gee_v2.js in the Earth Engine Code Editor (own account) and run the exports.\n"
               "2. Download the rasters + scenes.csv from Drive into that folder.\n3. Run `make landsat`.\n")
        status.write_text(msg)
        rep.warn(msg.splitlines()[0]); rep.write(); print(msg)
        return
    from .audit import normalise_lines
    from .scope import CoastScope
    lines = normalise_lines(read_vector(cfg["paths"]["shorelines_vector"]), cfg["crs_work"])
    land = unary_union(list(read_vector(cfg["paths"]["barangays_all"], cfg["crs_work"]).geometry))
    scope = CoastScope(list(lines.geometry), land, cfg["scope"]["hull_tolerance_m"], cfg["scope"].get("concave_ratio", 0.1))
    log = CleanLog()
    chains, parts, q = derive_from_index_rasters(in_dir, cfg["years"], scope, cfg, log)
    sc = in_dir / "scenes.csv"
    if sc.exists():
        qual = scene_quality(pd.read_csv(sc), lc.get("min_images_per_year", 3)); q = q.merge(qual, on="year", how="left")
        rep.add_input(sc)
    else:
        rep.warn("scenes.csv missing: image counts / dates / sensors per year are NOT recorded")
    q.to_csv(ensure_dir("outputs/tables") / "landsat_v2_quality.csv", index=False)
    write_gpkg("data/interim/shorelines_landsat_v2.gpkg", {"shorelines_clean": chains, "shoreline_parts": parts}, log.frame())
    rep.write()


if __name__ == "__main__":  # pragma: no cover
    run()
