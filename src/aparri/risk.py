"""Phase 5: risk classification, shoreline segments and layers.

Rule (thesis Table 3.1; thresholds from ``config.risk``):  let e = max(0, -EPR) be the erosion rate in m/yr.
  Low     e <  2
  Medium  2 <= e <= 5     (both ends inclusive, like the Earth Engine script)
  High    e >  5
Accreting transects (EPR > 0) follow ``risk.accretion_class`` (default Low) and are ALSO tagged
``trend = "accreting"`` so the map never hides growth behind the word "Low".

Important honesty note: this classifies **erosion rate only**.  The thesis itself says the class "does not
represent a comprehensive assessment of exposure or vulnerability" (Chapter III, p. 41).
"""
from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from shapely.geometry import LineString
from shapely.ops import linemerge, substring, unary_union

from . import metrics as M
from .io import ensure_dir, load_config, read_vector, repo_path
from .runreport import RunReport
from .transects import SET_FILES, available_sets, compute, load_parts

CLASSES = ["Low", "Medium", "High"]


def classify(epr: np.ndarray | float, low_max: float, medium_max: float, accretion_class: str = "Low"):
    """Vectorised classification of EPR values (negative = erosion)."""
    a = np.asarray(epr, dtype=float)
    e = np.maximum(0.0, -a)
    out = np.where(e < low_max, "Low", np.where(e <= medium_max, "Medium", "High")).astype(object)
    out[np.isnan(a)] = None
    out = np.where(a > 0, accretion_class, out)
    out[np.isnan(a)] = None
    return out


def trend(epr: np.ndarray) -> np.ndarray:
    a = np.asarray(epr, float)
    return np.where(np.isnan(a), None, np.where(a < 0, "eroding", np.where(a > 0, "accreting", "stable")))


SERIOUS = ("crossing", "start_not_on_land", "sharp_bend")


def confidence_table(tr: pd.DataFrame, cfg: dict, status: str, unc_epr: float | None) -> pd.DataFrame:
    """Per-transect class bounds and a plain-language confidence (high / medium / low).

    Uncertainty used (in this order): the configured one (COMPLETE) or its lower bound (PARTIAL); if NOT_PROVIDED
    a clearly labelled WHAT-IF of one Landsat pixel per date (``risk.confidence_scenario_unc_m``).
    The scenario is a conservative stand-in, not a measurement; the column ``unc_basis`` says which was used."""
    r = cfg["risk"]
    scen = r.get("confidence_scenario_unc_m")
    T = float(tr["T_years"].iloc[0]) if len(tr) else 35.0
    if status in ("COMPLETE", "PARTIAL") and unc_epr is not None:
        u, basis = float(unc_epr), "configured" if status == "COMPLETE" else "configured (lower bound)"
    elif scen:
        u, basis = float(np.sqrt(2) * scen / T), f"what-if: {scen:g} m per date"
    else:
        u, basis = np.nan, "none"
    e = np.maximum(0.0, -tr["EPR_m_yr"].values)
    lo = classify(-(np.maximum(e - u, 0)), r["low_max"], r["medium_max"], r["accretion_class"]) if np.isfinite(u) else np.full(len(tr), None)
    hi = classify(-(e + u), r["low_max"], r["medium_max"], r["accretion_class"]) if np.isfinite(u) else np.full(len(tr), None)
    # accreting transects: both bounds follow the accretion class unless the error band reaches erosion
    flips = np.array([(a is not None and b is not None and a != b) for a, b in zip(lo, hi)])
    qf = tr["quality_flag"].fillna("")
    serious = qf.apply(lambda s: any(k in s for k in SERIOUS)).values
    minor = ((tr["multi_hit_years"].fillna("") != "") | (tr["missing"].fillna("") != "")).values
    conf = np.where(~tr["valid_epr"].values | serious, "low", np.where(minor | flips, "medium", "high"))
    return pd.DataFrame({"class_lower_bound": lo, "class_upper_bound": hi, "class_may_flip": flips, "confidence": conf,
                         "unc_epr_used_m_yr": u, "unc_basis": basis}, index=tr.index)


def classify_transects(tr: gpd.GeoDataFrame, cfg: dict, status: str, unc_epr: float | None) -> gpd.GeoDataFrame:
    r = cfg["risk"]
    tr = tr.copy()
    raw = classify(tr["EPR_m_yr"].values, r["low_max"], r["medium_max"], r["accretion_class"])
    tr["risk_class_raw"] = raw                                           # what the number alone would give
    # A transect fan (crossing) or a start point not on land has no meaningful rate: leave it UNCLASSIFIED
    tr["risk_class"] = np.where(tr["valid_epr"].values, raw, None)
    tr["risk_class_lrr"] = classify(tr["lrr"].values, r["low_max"], r["medium_max"], r["accretion_class"])
    tr["trend"] = trend(tr["EPR_m_yr"].values)
    cf = confidence_table(tr, cfg, status, unc_epr)
    for c in cf.columns:
        tr[c] = cf[c].values
    tr["class_agrees_epr_lrr"] = (tr["risk_class"] == tr["risk_class_lrr"]) | tr["risk_class_lrr"].isna()
    return tr


# --------------------------------------------------------------------------- segments
def build_segments(tr: gpd.GeoDataFrame, shoreline_2025: list[LineString], cfg: dict) -> gpd.GeoDataFrame:
    """Split the end-year open-coast shoreline into one segment per transect (cut halfway between neighbours).

    Each segment inherits the attributes of its transect.  Transects without an end-year crossing get no segment."""
    year = cfg["years"][-1]
    col = f"d_{year}"
    pieces = []
    u = unary_union(shoreline_2025)
    merged = linemerge(u) if u.geom_type == "MultiLineString" else u
    pieces = list(merged.geoms) if merged.geom_type == "MultiLineString" else [merged]
    hits = tr[tr[col].notna()].copy()
    hits["hx"] = hits.bx + hits.nx * hits[col]; hits["hy"] = hits.by + hits.ny * hits[col]
    pts = shapely.points(hits.hx.values, hits.hy.values)
    dist = np.vstack([shapely.distance(pts, p) for p in pieces])
    hits["piece"] = dist.argmin(axis=0)
    hits["param"] = [pieces[k].project(shapely.Point(x, y)) for k, x, y in zip(hits.piece, hits.hx, hits.hy)]
    rows = []
    for k, g in hits.groupby("piece"):
        g = g.sort_values("param")
        pr = g.param.values
        L = pieces[k].length
        bounds = np.concatenate([[max(pr[0] - 25.0, 0.0)], (pr[:-1] + pr[1:]) / 2.0, [min(pr[-1] + 25.0, L)]])
        for (_, r), a, b in zip(g.iterrows(), bounds[:-1], bounds[1:]):
            if b - a < 1.0 or (b - a) > 4 * cfg["transects"]["spacing_m"]:      # a gap (river mouth / missing) - do not bridge it
                if b - a > 4 * cfg["transects"]["spacing_m"]:
                    a2, b2 = max(r.param - 25.0, 0), min(r.param + 25.0, L)
                    a, b = a2, b2
                else:
                    continue
            seg = substring(pieces[k], a, b)
            if seg.length < 1:
                continue
            rows.append({**{c: r[c] for c in tr.columns if c not in ("geometry",)}, "geometry": seg, "length_m": seg.length})
    out = gpd.GeoDataFrame(rows, crs=cfg["crs_work"])
    return out


def length_by_class(seg: gpd.GeoDataFrame, by: str = "barangay") -> pd.DataFrame:
    s = seg.copy()
    s["cls"] = s.risk_class.fillna("No data")
    t = s.pivot_table(index=by, columns="cls", values="length_m", aggfunc="sum", fill_value=0.0) / 1000.0
    for c in CLASSES + ["No data"]:
        if c not in t:
            t[c] = 0.0
    return t[CLASSES + ["No data"]]


# --------------------------------------------------------------------------- legacy comparison
def legacy_comparison(rebuilt_seg: gpd.GeoDataFrame, risk_legacy: gpd.GeoDataFrame, gee_csv: pd.DataFrame, study: gpd.GeoDataFrame, cfg: dict) -> pd.DataFrame:
    """Per barangay: class implied by the legacy risk polygons, by the Earth Engine CSV, and by the rebuild."""
    from . import audit as A
    tol = cfg["barangay_join_tolerance_m"]
    ru = risk_legacy.to_crs(cfg["crs_work"]); ru = A.repair(ru)
    rows = []
    jn = A.join_polygons(ru.assign(Risk_Level=ru.Risk_Level.astype(str)), study, tol)
    jn = jn[jn.method == "nearest_tol"]
    jn["cls"] = jn.Risk_Level.str[:3].replace({"Hig": "High", "Med": "Medium", "LOW": "Low"})
    leg_area = jn.pivot_table(index="barangay", columns="cls", values="area_ha", aggfunc="sum", fill_value=0.0)
    km = length_by_class(rebuilt_seg)
    g = gee_csv.set_index("Barangay")
    for b in cfg["table_4_2_order"]:
        la = leg_area.loc[b] if b in leg_area.index else pd.Series(dtype=float)
        leg_worst = "High" if la.get("High", 0) >= 1 else ("Medium" if la.get("Medium", 0) >= 1 else ("Low" if la.get("Low", 0) > 0 else "none"))
        eg = g.loc[b] if b in g.index else None
        if eg is None or pd.isna(eg.get("Mean_EPR_m_yr")):
            gee_cls, gee_note = "no data", "point outside the Earth Engine box"
        else:
            gee_cls = "High" if eg.High_Risk_ha > 0 else ("Medium" if eg.Medium_Risk_ha > 0 else "Low")
            gee_note = "1 km circle around one point"
        k = km.loc[b] if b in km.index else pd.Series({c: 0.0 for c in CLASSES})
        tot = float(k[CLASSES].sum())
        dom = k[CLASSES].idxmax() if tot > 0 else "no data"
        worst = "High" if k["High"] > 0.05 else ("Medium" if k["Medium"] > 0.05 else ("Low" if tot > 0 else "no data"))
        rows.append({"barangay": b, "legacy_polygons_ha_Low": la.get("Low", 0.0), "legacy_polygons_ha_Medium": la.get("Medium", 0.0),
                     "legacy_polygons_ha_High": la.get("High", 0.0), "legacy_class": leg_worst, "gee_csv_class": gee_cls,
                     "gee_csv_basis": gee_note, "rebuilt_km_Low": k["Low"], "rebuilt_km_Medium": k["Medium"], "rebuilt_km_High": k["High"],
                     "rebuilt_class_dominant": dom, "rebuilt_class_worst": worst,
                     "agree_legacy_vs_rebuilt": (leg_worst == worst), "agree_gee_vs_rebuilt": (gee_cls == worst)})
    df = pd.DataFrame(rows)
    df["explanation"] = [explain(r) for _, r in df.iterrows()]
    return df


def explain(r: pd.Series) -> str:
    parts = []
    if r.gee_csv_class == "no data":
        parts.append("The Earth Engine statistics have no value for this barangay (its point lies outside the analysis box).")
    if r.legacy_class != r.rebuilt_class_worst:
        parts.append(f"The legacy polygons imply {r.legacy_class}, the rebuilt transects give {r.rebuilt_class_worst} (dominant: {r.rebuilt_class_dominant}).")
    else:
        parts.append(f"Legacy polygons and rebuilt transects agree ({r.legacy_class}).")
    if r.gee_csv_class not in ("no data",) and r.gee_csv_class != r.rebuilt_class_worst:
        parts.append(f"The 1 km-circle statistics imply {r.gee_csv_class}, because they classify an area around a point, not the shoreline.")
    return " ".join(parts)


# --------------------------------------------------------------------------- QGIS style
QML = """<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis version="3.34.0" styleCategories="Symbology">
 <renderer-v2 type="categorizedSymbol" attr="risk_class" symbollevels="0" forceraster="0" enableorderby="0" referencescale="-1">
  <categories>
   <category symbol="0" value="Low" label="Low (&lt; 2 m/year)" render="true" uuid="{{a1111111-1111-4111-8111-111111111111}}"/>
   <category symbol="1" value="Medium" label="Medium (2-5 m/year)" render="true" uuid="{{a2222222-2222-4222-8222-222222222222}}"/>
   <category symbol="2" value="High" label="High (&gt; 5 m/year)" render="true" uuid="{{a3333333-3333-4333-8333-333333333333}}"/>
   <category symbol="3" value="" label="No data" render="true" uuid="{{a4444444-4444-4444-8444-444444444444}}"/>
  </categories>
  <symbols>
{symbols}
  </symbols>
  <source-symbol>
{src}
  </source-symbol>
 </renderer-v2>
 <blendMode>0</blendMode>
 <featureBlendMode>0</featureBlendMode>
 <layerOpacity>1</layerOpacity>
</qgis>
"""
SYMBOL = """   <symbol type="line" name="{n}" alpha="1" force_rhr="0" clip_to_extent="1">
    <data_defined_properties><Option type="Map"><Option value="" name="name" type="QString"/><Option name="properties"/><Option value="collection" name="type" type="QString"/></Option></data_defined_properties>
    <layer class="SimpleLine" enabled="1" pass="0" locked="0">
     <Option type="Map">
      <Option value="0" name="align_dash_pattern" type="QString"/>
      <Option value="round" name="capstyle" type="QString"/>
      <Option value="5;2" name="customdash" type="QString"/>
      <Option value="MM" name="customdash_unit" type="QString"/>
      <Option value="0" name="draw_inside_polygon" type="QString"/>
      <Option value="round" name="joinstyle" type="QString"/>
      <Option value="{rgb},255" name="line_color" type="QString"/>
      <Option value="solid" name="line_style" type="QString"/>
      <Option value="{w}" name="line_width" type="QString"/>
      <Option value="MM" name="line_width_unit" type="QString"/>
      <Option value="0" name="use_custom_dash" type="QString"/>
     </Option>
    </layer>
   </symbol>"""


def write_qml(path) -> None:
    cols = [("0", "46,139,87", "1.6"), ("1", "255,165,0", "1.8"), ("2", "227,26,28", "2.0"), ("3", "170,170,170", "1.0")]
    syms = "\n".join(SYMBOL.format(n=n, rgb=rgb, w=w) for n, rgb, w in cols)
    src = SYMBOL.format(n="0", rgb="128,128,128", w="1.0")
    path.write_text(QML.format(symbols=syms, src=src), encoding="utf-8")


# --------------------------------------------------------------------------- orchestration
def run() -> None:  # pragma: no cover
    cfg = load_config()
    rep = RunReport("risk", cfg)
    work = cfg["crs_work"]; P = cfg["paths"]
    from .transects import PIXEL_SETS
    land = unary_union(list(read_vector(P["barangays_all"], work).geometry))
    study = read_vector(P["barangays_study"], work)
    base_parts = load_parts(SET_FILES[cfg["baseline"].get("source_set", "vector_clean")])
    legacy = read_vector(P["risk_legacy"])
    gee_csv = pd.read_csv(repo_path(P["gee_stats_csv"]))
    for f in (P["risk_legacy"], P["gee_stats_csv"], P["barangays_study"], P["barangays_all"]):
        rep.add_input(f)
    all_seg = []
    for name in available_sets():
        parts = load_parts(SET_FILES[name]); rep.add_input(SET_FILES[name])
        res = compute(cfg, parts, base_parts, land, study, shoreline_set=name)
        tr = classify_transects(res["transects"], cfg, res["unc_status"], res["epr_unc"])
        keep = parts[(parts.year == cfg["years"][-1]) & (parts.scope == "open_coast")]
        seg = build_segments(tr, list(keep.geometry), cfg)
        seg["shoreline_set"] = name
        out = ensure_dir(f"data/processed/{name}")
        seg.to_file(out / "risk_segments.gpkg", layer="risk_segments", driver="GPKG")
        tr.to_file(out / "risk_transects.gpkg", layer="transects", driver="GPKG")
        all_seg.append(seg)
        rep.count(f"{name}_segments", len(seg)); rep.count(f"{name}_km_by_class", seg.groupby(seg.risk_class.fillna("No data")).length_m.sum().div(1000).round(2).to_dict())
        flips = int(tr.class_may_flip.sum()); rep.count(f"{name}_class_may_flip", flips)
        if name == cfg["shoreline_set"]:
            primary_tr, primary_seg, primary_res = tr, seg, res
    ensure_dir("data/processed")
    primary_seg.to_file(repo_path("data/processed/risk_segments.gpkg"), layer="risk_segments", driver="GPKG")
    primary_tr.to_file(repo_path("data/processed/transects.gpkg"), layer="transects", driver="GPKG")
    import shutil
    shutil.copy(repo_path(f"data/processed/{cfg['shoreline_set']}/shoreline_points.csv"), repo_path("data/processed/shoreline_points.csv"))
    lay = ensure_dir("outputs/layers")
    gp = lay / "Aparri_Erosion_Risk_v2.gpkg"
    if gp.exists():
        gp.unlink()
    primary_seg.to_file(gp, layer="risk_segments", driver="GPKG")
    primary_tr.to_file(gp, layer="transects", driver="GPKG", mode="a")
    study[["ADM4_EN", "ADM4_PCODE", "geometry"]].rename(columns={"ADM4_EN": "barangay"}).to_file(gp, layer="study_barangays", driver="GPKG", mode="a")
    parts = load_parts(SET_FILES[cfg["shoreline_set"]])
    for y in cfg["years"]:
        sub = parts[(parts.year == y)]
        sub[["year", "scope", "part_id", "geometry"]].to_file(gp, layer=f"shoreline_{y}", driver="GPKG", mode="a")
    write_qml(lay / "Aparri_Erosion_Risk_v2.qml")
    cmp = legacy_comparison(primary_seg, legacy, gee_csv, study, cfg)
    cmp.to_csv(ensure_dir("outputs/tables") / "legacy_vs_rebuilt_by_barangay.csv", index=False)
    pd.concat(all_seg).drop(columns="geometry").to_csv(ensure_dir("outputs/tables") / "risk_segments_all_sets.csv", index=False)
    rep.count("legacy_comparison", cmp[["barangay", "legacy_class", "gee_csv_class", "rebuilt_class_worst", "rebuilt_class_dominant"]].to_dict("records"))
    for f in (gp, lay / "Aparri_Erosion_Risk_v2.qml"):
        rep.add_output(f)
    rep.write()
    print(cmp[["barangay", "legacy_class", "gee_csv_class", "rebuilt_class_dominant", "rebuilt_class_worst", "rebuilt_km_Low", "rebuilt_km_Medium", "rebuilt_km_High"]].round(2).to_string(index=False))


if __name__ == "__main__":  # pragma: no cover
    run()
