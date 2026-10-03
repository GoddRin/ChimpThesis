"""Phase 5: thesis-style figures (300 dpi PNG + PDF).

Visual language follows the original Figs. 4.1/4.2: green Low / orange Medium / red High, barangay labels,
legend, 2.5 km scale bar, north arrow, a locator inset.  No basemap tiles are used (no network needed): the
barangay polygons and the coast are drawn directly, so the figures regenerate anywhere with ``make maps``.
"""
from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import box
from shapely.ops import unary_union

from .io import ensure_dir, load_config, read_vector, repo_path
from .runreport import RunReport

YEAR_COLORS = {1990: "#1f3a93", 2000: "#2ecc40", 2010: "#8e44ad", 2020: "#e31a1c", 2025: "#ffa500"}
RISK_COLORS = {"Low": "#2e8b57", "Medium": "#ffa500", "High": "#e31a1c"}
PALETTE_CB = {"Low": "#4575b4", "Medium": "#fdae61", "High": "#d73027"}     # colour-blind-safer alternative
FOOTER = "Municipality of Aparri\nProvince of Cagayan\nPhilippines"


def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt


def scalebar(ax, length_m: float, loc=(0.03, 0.04), label: str | None = None, fs: int = 9) -> None:
    """Scale bar in map units (metres) anchored at an axes-fraction position."""
    x0, x1 = ax.get_xlim(); y0, y1 = ax.get_ylim()
    sx = x0 + (x1 - x0) * loc[0]; sy = y0 + (y1 - y0) * loc[1]
    h = (y1 - y0) * 0.012
    ax.plot([sx, sx + length_m], [sy, sy], color="k", lw=2.2, solid_capstyle="butt", zorder=20)
    for xx in (sx, sx + length_m / 2, sx + length_m):
        ax.plot([xx, xx], [sy, sy + h], color="k", lw=1.2, zorder=20)
    lab = label or (f"{length_m/1000:g} km" if length_m >= 1000 else f"{length_m:g} m")
    ax.text(sx, sy + h * 1.6, "0", ha="center", fontsize=fs, zorder=20); ax.text(sx + length_m, sy + h * 1.6, lab, ha="center", fontsize=fs, zorder=20)


def north_arrow(ax, loc=(0.94, 0.88), size=0.09) -> None:
    ax.annotate("", xy=(loc[0], loc[1] + size), xytext=(loc[0], loc[1]), xycoords="axes fraction", textcoords="axes fraction",
                arrowprops=dict(arrowstyle="-|>", color="k", lw=1.8, mutation_scale=18), zorder=25)
    ax.text(loc[0], loc[1] + size + 0.015, "N", transform=ax.transAxes, ha="center", fontsize=12, fontweight="bold", zorder=25)


def draw_land(ax, all_brg, study, label=True, fs=8):
    all_brg.plot(ax=ax, facecolor="#f1efe6", edgecolor="#c9c4b2", lw=0.4, zorder=1)
    ax.set_xlabel(""); ax.set_ylabel("")
    study.plot(ax=ax, facecolor="#d9d9d9", edgecolor="#555555", lw=0.8, ls="--", alpha=0.85, zorder=2)
    if label:
        for _, b in study.iterrows():
            p = b.geometry.representative_point()
            ax.annotate(b.ADM4_EN, (p.x, p.y), fontsize=fs, ha="center", color="#222222", zorder=30,
                        bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.6))


def locator_inset(fig, rect, all_brg_ll, study_ll, extent_ll):
    ax = fig.add_axes(rect)
    all_brg_ll.plot(ax=ax, facecolor="#f1efe6", edgecolor="#9a9a9a", lw=0.3)
    study_ll.plot(ax=ax, facecolor="#9ecae1", edgecolor="#08519c", lw=0.4)
    x0, y0, x1, y1 = extent_ll
    ax.add_patch(plt_rect(x0, y0, x1, y1))
    ax.set_xlabel(""); ax.set_ylabel(""); ax.set_xticks([]); ax.set_yticks([]); ax.set_title("Municipality of Aparri (study barangays blue)", fontsize=6.5)
    ax.set_aspect("equal")
    return ax


def plt_rect(x0, y0, x1, y1):
    import matplotlib.patches as mp
    return mp.Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, ec="red", lw=1.2)


class Data:
    """Everything the figures need, loaded once."""

    def __init__(self, cfg: dict):
        w = cfg["crs_work"]; P = cfg["paths"]
        self.cfg = cfg
        self.all_brg = read_vector(P["barangays_all"], w)
        self.study = read_vector(P["barangays_study"], w)
        name = cfg["shoreline_set"]
        self.seg = gpd.read_file(repo_path(f"data/processed/{name}/risk_segments.gpkg"))
        self.tr = gpd.read_file(repo_path(f"data/processed/{name}/risk_transects.gpkg"))
        from .transects import SET_FILES
        self.parts = gpd.read_file(repo_path(SET_FILES[name]), layer="shoreline_parts")
        self.name = name
        self.bounds = unary_union([self.parts.unary_union, self.study.unary_union]).bounds if False else self.parts.total_bounds


def _extent(d: Data, pad=900.0):
    x0, y0, x1, y1 = d.parts.total_bounds
    return x0 - pad, y0 - pad, x1 + pad, y1 + pad


def fig_4_1(d: Data, out_png, out_pdf=None) -> None:
    plt = _plt()
    cfg = d.cfg
    fig = plt.figure(figsize=(11.69, 8.27))
    ax = fig.add_axes([0.03, 0.43, 0.94, 0.5])
    x0, y0, x1, y1 = _extent(d)
    draw_land(ax, d.all_brg, d.study)
    for y, c in YEAR_COLORS.items():
        sub = d.parts[d.parts.year == y]
        op = sub[sub.scope == "open_coast"]; es = sub[sub.scope != "open_coast"]
        op.plot(ax=ax, color=c, lw=1.1, zorder=5, label=str(y)); es.plot(ax=ax, color=c, lw=0.6, ls="--", zorder=4)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([]); ax.set_xlabel(""); ax.set_ylabel("")
    # zoom windows
    wins = zoom_windows(d)
    for k, (cx, cy, hw, name) in enumerate(wins):
        ax.add_patch(plt_rect(cx - hw, cy - hw * 0.62, cx + hw, cy + hw * 0.62)); ax.text(cx, cy + hw * 0.62 + 120, "ABC"[k], ha="center", fontsize=11, fontweight="bold", color="red", zorder=40)
    scalebar(ax, 2500); north_arrow(ax, loc=(0.70, 0.62))
    ax.legend(title="Shoreline position (open coast solid, river banks dashed)", loc="lower left", bbox_to_anchor=(0.01, 0.12), fontsize=8, title_fontsize=8, ncol=5, framealpha=0.9)
    ax.set_title("Multi-Temporal Shoreline Change Map of Selected Coastal Barangays in Aparri, Cagayan", fontsize=13, fontweight="bold")
    ax.text(0.99, 0.01, FOOTER, transform=ax.transAxes, fontsize=7, style="italic", va="bottom", ha="right")
    for k, (cx, cy, hw, name) in enumerate(wins):
        a = fig.add_axes([0.04 + k * 0.325, 0.05, 0.3, 0.3])
        draw_land(a, d.all_brg, d.study, fs=7)
        for y, c in YEAR_COLORS.items():
            d.parts[d.parts.year == y].plot(ax=a, color=c, lw=1.4, zorder=5)
        a.set_xlim(cx - hw, cx + hw); a.set_ylim(cy - hw * 0.62, cy + hw * 0.62); a.set_aspect("equal"); a.set_xticks([]); a.set_yticks([]); a.set_xlabel(""); a.set_ylabel("")
        scalebar(a, 500 if hw <= 1400 else 1000, fs=7)
        a.set_title(f"{'ABC'[k]}  {name}", fontsize=9, loc="left")
    try:
        ll = lambda g: g.to_crs(4326)
        b = ll(d.study).total_bounds
        locator_inset(fig, [0.80, 0.60, 0.16, 0.22], ll(d.all_brg), ll(d.study), tuple(b))
    except Exception:
        pass
    fig.savefig(out_png, dpi=300);
    if out_pdf:
        fig.savefig(out_pdf)
    plt.close(fig)


def zoom_windows(d: Data) -> list[tuple[float, float, float, str]]:
    tr = d.tr
    def center(b):
        t = tr[tr.barangay == b]
        return float(t.bx.mean()), float(t.by.mean())
    a = center("Bulala Norte"); c = center("Maura")
    s = tr[tr.sector == "S1"]
    mouth = tr.loc[tr.quality_flag.str.contains("crossing")]
    m = (float(mouth.bx.mean()), float(mouth.by.mean())) if len(mouth) else center("Linao")
    return [(a[0], a[1], 1300.0, "Bulala Norte coast"), (m[0] + 400, m[1] - 100, 2000.0, "Linao spit / river mouth"), (c[0], c[1], 1300.0, "Maura coast")]


def fig_4_2(d: Data, out_png, out_pdf=None, palette=RISK_COLORS, cb=False) -> None:
    plt = _plt()
    fig = plt.figure(figsize=(11.69, 8.27))
    ax = fig.add_axes([0.03, 0.30, 0.94, 0.63])
    x0, y0, x1, y1 = _extent(d)
    draw_land(ax, d.all_brg, d.study)
    last = d.parts[(d.parts.year == d.cfg["years"][-1])]
    last[last.scope != "open_coast"].plot(ax=ax, color="#9e9e9e", lw=0.7, ls=":", zorder=3)
    seg = d.seg
    for cls, col in palette.items():
        sub = seg[(seg.risk_class == cls)]
        solid = sub[sub.confidence != "low"]; lowc = sub[sub.confidence == "low"]
        if len(solid):
            solid.plot(ax=ax, color=col, lw=6.0, zorder=8)
        if len(lowc):
            lowc.plot(ax=ax, color=col, lw=6.0, ls=(0, (1, 1)), zorder=8)
    nod = seg[seg.risk_class.isna()]
    if len(nod):
        nod.plot(ax=ax, color="#7f7f7f", lw=4.0, zorder=7)
    acc = seg[seg.trend == "accreting"]
    if len(acc):
        mids = [g.interpolate(0.5, normalized=True) for g in acc.geometry]
        ax.scatter([m.x for m in mids], [m.y for m in mids], marker="^", s=14, color="#08519c", zorder=12)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([]); ax.set_xlabel(""); ax.set_ylabel("")
    scalebar(ax, 2500); north_arrow(ax)
    ax.set_title("Coastal Erosion Risk Map of Selected Coastal Barangays in Aparri, Cagayan", fontsize=13, fontweight="bold")
    ax.text(0.99, 0.01, FOOTER, transform=ax.transAxes, fontsize=7, style="italic", va="bottom", ha="right")
    from matplotlib.lines import Line2D
    h = [Line2D([0], [0], color=palette["Low"], lw=4, label="Low (< 2 m/year)"), Line2D([0], [0], color=palette["Medium"], lw=4, label="Medium (2–5 m/year)"),
         Line2D([0], [0], color=palette["High"], lw=4, label="High (> 5 m/year)"), Line2D([0], [0], color="#7f7f7f", lw=3, label="Not classified (flagged transects)"),
         Line2D([0], [0], color="k", lw=4, ls=(0, (1, 1)), label="dotted = low confidence"),
         Line2D([0], [0], marker="^", color="w", markerfacecolor="#08519c", markersize=7, label="accreting segment"),
         Line2D([0], [0], color="#9e9e9e", lw=1, ls=":", label="river banks (out of scope)")]
    ax.legend(handles=h, loc="lower left", bbox_to_anchor=(0.01, 0.1), fontsize=8, framealpha=0.92, title="Erosion rate class, 1990–2025", title_fontsize=8)
    # bar chart of km per class per barangay
    bx = fig.add_axes([0.07, 0.06, 0.55, 0.17])
    from .risk import length_by_class
    km = length_by_class(seg).reindex(d.cfg["table_4_2_order"]).fillna(0.0)
    bottom = np.zeros(len(km))
    for cls in ("Low", "Medium", "High"):
        bx.bar(km.index, km[cls], bottom=bottom, color=palette[cls], label=cls); bottom += km[cls].values
    bx.bar(km.index, km["No data"], bottom=bottom, color="#7f7f7f", label="Not classified")
    bx.set_ylim(0, float((km.sum(axis=1)).max()) * 1.12); bx.set_ylabel("shoreline (km)", fontsize=8); bx.tick_params(axis="x", labelrotation=25, labelsize=7); bx.tick_params(axis="y", labelsize=7)
    bx.set_title("Kilometres of shoreline per class and barangay", fontsize=8, loc="left")
    note = fig.text(0.66, 0.07, "Classification = erosion rate only (EPR 1990–2025 per 50 m transect).\nIt is NOT a full exposure/vulnerability assessment.\n"
                    "Positional error and image dates were not supplied; see Table 4.2 notes.", fontsize=7.5, va="bottom")
    fig.savefig(out_png, dpi=300)
    if out_pdf:
        fig.savefig(out_pdf)
    plt.close(fig)


def fig_profile(d: Data, out_png, out_pdf=None) -> None:
    plt = _plt()
    cfg = d.cfg
    tr = d.tr
    fig, ax = plt.subplots(figsize=(13, 5.2))
    cols = {"Bulala Sur": "#fde0dd", "Bulala Norte": "#e5f5e0", "Linao": "#deebf7", "Punta": "#fff7bc", "San Antonio": "#efedf5", "Maura": "#fee6ce", "Dodan": "#e0f3db", "Paddaya": "#f0f0f0"}
    for b, c in cols.items():
        t = tr[tr.barangay == b]
        if len(t):
            ax.axvspan(t.axis_km.min(), t.axis_km.max(), color=c, alpha=0.9, zorder=0)
            ax.text((t.axis_km.min() + t.axis_km.max()) / 2, 1.0, b, rotation=0, ha="center", fontsize=8, va="bottom", transform=ax.get_xaxis_transform())
    v = tr[tr.valid_epr].sort_values("axis_km").copy()
    f = tr[~tr.valid_epr & tr.EPR_m_yr.notna()]
    # break the lines where there is no valid transect for > 150 m (river mouth, flagged fans): never draw across a gap
    gap = v.axis_km.diff() > 0.15
    vv = v.copy()
    vv.loc[gap, ["EPR_m_yr", "lrr"]] = np.nan
    ax.plot(vv.axis_km, vv.EPR_m_yr, "-", color="#1f3a93", lw=1.8, label="EPR 1990–2025 (valid transects)")
    ax.plot(vv.axis_km, vv.lrr, "-", color="#2ecc40", lw=1.0, alpha=0.9, label="LRR (all years)")
    ax.scatter(f.axis_km, f.EPR_m_yr, s=10, color="#bdbdbd", zorder=3, label="EPR of flagged transects (not used)")
    try:
        from .transects import SET_FILES
        other = "raster_clean" if d.name != "raster_clean" else "vector_clean"
        o = pd.read_csv(repo_path(f"data/processed/{other}/transect_metrics.csv"))
        o = o[o.valid_epr]
        ax.scatter(o.axis_km, o.EPR_m_yr, s=7, color="#d62728", zorder=4, label=f"independent set ({other}) EPR")
    except Exception:
        pass
    u = np.sqrt(2) * 30 / 35
    ax.axhspan(-u, u, color="0.8", alpha=0.5, zorder=1, label=f"±{u:.2f} m/yr = one-pixel (30 m) what-if band")
    for yv, lab, col in ((-2, "Low | Medium  (−2)", "#ffa500"), (-5, "Medium | High  (−5)", "#e31a1c")):
        ax.axhline(yv, color=col, ls="--", lw=1.2); ax.text(ax.get_xlim()[1], yv, lab, ha="right", va="bottom", fontsize=8, color=col)
    ax.axhline(0, color="k", lw=0.6)
    ax.set_ylim(-6, 6); ax.set_xlabel("distance along the coast from the NW end (km)"); ax.set_ylabel("EPR (m/year)   negative = erosion")
    ax.set_title("Shoreline change rate along the open coast of the eight study barangays, 1990–2025", fontsize=11, pad=22)
    ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=3, framealpha=0.95)
    fig.tight_layout(); fig.savefig(out_png, dpi=300, bbox_inches="tight")
    if out_pdf:
        fig.savefig(out_pdf)
    plt.close(fig)


def fig_legacy_vs_rebuilt(d: Data, risk_legacy: gpd.GeoDataFrame, out_png) -> None:
    plt = _plt()
    from . import audit as A
    fig, axs = plt.subplots(2, 1, figsize=(13, 10), sharex=True, sharey=True)
    x0, y0, x1, y1 = _extent(d, 600)
    leg = A.repair(risk_legacy.to_crs(d.cfg["crs_work"]))
    col = {"LOW": "#2e8b57", "Med": "#ffa500", "Hig": "#e31a1c"}
    for ax in axs:
        draw_land(ax, d.all_brg, d.study)
    for k, c in col.items():
        sub = leg[leg.Risk_Level.astype(str) == k]
        if len(sub):
            sub.plot(ax=axs[0], color=c, alpha=0.8, edgecolor="k", lw=0.2, zorder=6)
    for cls, c in RISK_COLORS.items():
        s = d.seg[d.seg.risk_class == cls]
        if len(s):
            s.plot(ax=axs[1], color=c, lw=4.2, zorder=8)
    n = d.seg[d.seg.risk_class.isna()]
    if len(n):
        n.plot(ax=axs[1], color="#7f7f7f", lw=3, zorder=7)
    axs[0].set_title("LEGACY risk polygons (as shipped; green Low 69 / orange 'Med' 53 / red 'Hig' 2)", fontsize=10, loc="left")
    axs[1].set_title("REBUILT: 50 m transects, EPR 1990–2025, Table 3.1 classes", fontsize=10, loc="left")
    for ax in axs:
        ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([]); ax.set_xlabel(""); ax.set_ylabel("")
        scalebar(ax, 2500); north_arrow(ax)
    fig.tight_layout(); fig.savefig(out_png, dpi=200); plt.close(fig)


def run() -> None:  # pragma: no cover
    cfg = load_config()
    rep = RunReport("maps", cfg)
    d = Data(cfg)
    out = ensure_dir("outputs/maps")
    for f in (f"data/processed/{d.name}/risk_segments.gpkg",):
        rep.add_input(f)
    fig_4_1(d, out / "Fig_4_1_v2_multitemporal_shorelines.png", out / "Fig_4_1_v2_multitemporal_shorelines.pdf")
    fig_4_2(d, out / "Fig_4_2_v2_erosion_risk_map.png", out / "Fig_4_2_v2_erosion_risk_map.pdf")
    fig_4_2(d, out / "Fig_4_2_v2_erosion_risk_map_colorblind.png", None, palette=PALETTE_CB, cb=True)
    fig_profile(d, out / "Fig_4_3_epr_profile_along_coast.png", out / "Fig_4_3_epr_profile_along_coast.pdf")
    fig_legacy_vs_rebuilt(d, read_vector(cfg["paths"]["risk_legacy"]), out / "Fig_legacy_vs_rebuilt.png")
    for f in out.glob("Fig_*"):
        rep.add_output(f)
    rep.write()
    print("maps written to", out)


if __name__ == "__main__":  # pragma: no cover
    run()
