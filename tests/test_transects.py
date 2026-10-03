"""Phase 4 tests - SYNTHETIC shorelines with known answers (all must pass)."""
import geopandas as gpd
import numpy as np
import pytest
from shapely.geometry import LineString, Point, box

from aparri import metrics as M
from aparri import transects as T
from aparri.io import load_config


def cfg_for_tests(**over):
    cfg = load_config()
    cfg = {**cfg, "years": [1990, 2000, 2010, 2020, 2025]}
    cfg["transects"] = {**cfg["transects"], "spacing_m": 50, "length_seaward_m": 600, "length_landward_m": 300}
    cfg["baseline"] = {**cfg["baseline"], "smooth_m": 200, "offset_landward_m": 100}
    cfg["scope"] = {**cfg["scope"], "include_estuarine_banks": True}
    for k, v in over.items():
        cfg[k] = v
    return cfg


def straight_parts(rate_m_per_yr, years=(1990, 2000, 2010, 2020, 2025), length=5000.0, sea_north=True):
    """Shoreline along y = y0 + rate*(year-1990); sea is NORTH when sea_north (land south)."""
    rows = []
    for y in years:
        yy = 1000.0 + rate_m_per_yr * (y - 1990)
        rows.append({"year": y, "scope": "open_coast", "geometry": LineString([(0, yy), (length, yy)])})
    g = gpd.GeoDataFrame(rows, crs=32651)
    land = box(-5000, -5000, length + 5000, 1000.0 - 1.0 if False else 1000.0 - 1)   # south of the 1990 line
    return g, land


def mirror(g, land):
    """Flip north<->south: land is now NORTH of the line, sea SOUTH."""
    from shapely import affinity
    g2 = g.copy(); g2["geometry"] = [affinity.scale(x, 1, -1, origin=(0, 0)) for x in g.geometry]
    return g2, affinity.scale(land, 1, -1, origin=(0, 0))


def run(g, land, cfg=None, name="vector_clean"):
    cfg = cfg or cfg_for_tests()
    return T.compute(cfg, g, g, land, None, shoreline_set=name)


def test_retreat_two_m_per_year():
    g, land = straight_parts(-2.0)          # shoreline moves SOUTH (landward) 2 m/yr
    r = run(g, land)
    v = r["transects"][r["transects"].valid_epr]
    assert len(v) > 80
    assert np.allclose(v.EPR_m_yr, -2.0, atol=1e-6) and np.allclose(v.lrr, -2.0, atol=1e-6)
    assert np.allclose(v.NSM_m, -70.0, atol=1e-6)


def test_advance_one_point_five():
    g, land = straight_parts(+1.5)
    v = run(g, land)["transects"]
    v = v[v.valid_epr]
    assert np.allclose(v.EPR_m_yr, 1.5, atol=1e-6) and np.allclose(v.lrr, 1.5, atol=1e-6)


def test_orientation_land_either_side_gives_identical_signed_results():
    g, land = straight_parts(-2.0)
    a = run(g, land)["transects"].sort_values("seq").EPR_m_yr.values
    g2, land2 = mirror(g, land)
    r2 = run(g2, land2)
    b = r2["transects"].sort_values("seq").EPR_m_yr.values
    assert np.allclose(a, b, atol=1e-6) and np.allclose(a, -2.0, atol=1e-6)


def test_curved_coast_matches_radius_change():
    """Concentric circular arcs (radius shrinks 1.5 m/yr toward... sea is OUTSIDE the circle)."""
    cx, cy, R0 = 0.0, 0.0, 6000.0
    rows = []
    for y in (1990, 2000, 2010, 2020, 2025):
        R = R0 - 1.5 * (y - 1990)                      # coast retreats toward the centre (land) = erosion
        th = np.linspace(np.radians(20), np.radians(70), 400)
        rows.append({"year": y, "scope": "open_coast", "geometry": LineString(np.column_stack([cx + R * np.cos(th), cy + R * np.sin(th)]))})
    g = gpd.GeoDataFrame(rows, crs=32651)
    land = Point(cx, cy).buffer(R0, 256)                # land = inside of the 1990 coast circle
    v = run(g, land)["transects"]
    v = v[v.valid_epr]
    assert len(v) > 60
    assert abs(v.EPR_m_yr.median() + 1.5) < 0.01, v.EPR_m_yr.describe()
    assert np.abs(v.EPR_m_yr + 1.5).max() < 0.05


def test_missing_year_gives_lrr_from_remaining_and_null_below_three():
    g, land = straight_parts(-2.0)
    g4 = g[g.year != 2000]
    v = run(g4, land)["transects"]
    v = v[v.valid_epr]
    assert np.allclose(v.lrr, -2.0, atol=1e-6) and (v.n_dates == 4).all()
    g2 = g[g.year.isin([1990, 2025])]
    v2 = run(g2, land)["transects"]
    v2 = v2[v2.valid_epr]
    assert v2.lrr.isna().all() and (v2.lrr_note != "").all() and np.allclose(v2.EPR_m_yr, -2.0, atol=1e-6)


def test_loop_gives_multi_hit_flag_and_rule():
    g, land = straight_parts(0.0)
    # 2025 shoreline gets a tongue (hook) that doubles back across the same transects
    tongue = LineString([(0, 1000), (2000, 1000), (2100, 1100), (2400, 1100), (2500, 1000), (2300, 900), (2200, 1050), (5000, 1000)])
    g = g.copy()
    g.loc[g.year == 2025, "geometry"] = [tongue]
    r = run(g, land)
    tr = r["transects"]
    assert tr.multi_hit_years.str.contains("2025").any()
    cfg_far = cfg_for_tests(); cfg_far["transects"] = {**cfg_far["transects"], "multi_hit_rule": "farthest"}
    rf = run(g, land, cfg_far)["transects"]
    mh = tr.multi_hit_years.str.contains("2025").values
    assert (rf.d_2025.values[mh] >= tr.d_2025.values[mh] - 1e-9).all() and (rf.d_2025.values[mh] > tr.d_2025.values[mh] + 1).any()


def test_landward_test_is_decided_by_land_polygon_not_assumed():
    g, land = straight_parts(-2.0)
    r = run(g, land)
    s = r["sectors"][0]
    assert s.land_check[1] != s.land_check[2]
    # sea normal points north for land to the south
    assert s.n_sea[:, 1].mean() > 0.99
    g2, land2 = mirror(g, land)
    assert run(g2, land2)["sectors"][0].n_sea[:, 1].mean() < -0.99


def test_uncertainty_never_invented():
    e, st = M.year_uncertainty({"georeferencing": None, "digitizing": None, "pixel": None, "tidal": None})
    assert e is None and st == "NOT_PROVIDED"
    e, st = M.year_uncertainty({"georeferencing": None, "digitizing": None, "pixel": 30.0, "tidal": None})
    assert e == 30.0 and st == "PARTIAL"
    e, st = M.year_uncertainty({"georeferencing": 5.0, "digitizing": 10.0, "pixel": 30.0, "tidal": 2.0})
    assert st == "COMPLETE" and abs(e - np.sqrt(25 + 100 + 900 + 4)) < 1e-9
    assert abs(M.epr_uncertainty(30.0, 30.0, 35.0) - 30 * np.sqrt(2) / 35) < 1e-12
    g, land = straight_parts(-2.0)
    r = run(g, land, name="vector_clean")
    assert r["unc_status"] == "NOT_PROVIDED" and r["transects"].epr_unc_m_yr.isna().all()
    r2 = run(g, land, name="raster_clean")
    assert r2["unc_status"] == "PARTIAL" and abs(r2["epr_unc"] - 30 * np.sqrt(2) / 35) < 1e-9
    assert r2["transects"].exceeds_unc_lower_bound.astype(bool).all()          # 2 m/yr > 1.21 m/yr


def test_time_axis_uses_dates_only_when_all_given():
    ys = [1990, 2025]
    t, src = M.time_axis(ys, {1990: "1990-03-01", 2025: None})
    assert src == "year_difference" and t[1] - t[0] == 35
    t, src = M.time_axis(ys, {1990: "1990-03-01", 2025: "2025-03-01"})
    assert src == "acquisition_dates" and abs((t[1] - t[0]) - 35.0) < 0.01


def test_lrr_confidence_interval_and_r2():
    t = np.array([1990., 2000., 2010., 2020., 2025.])
    D = np.array([[0, -20, -40, -60, -70.0], [0, -25, -35, -65, -68.0]])
    tab = M.lrr_table(D, t)
    assert abs(tab.lrr[0] + 2.0) < 1e-9 and tab.lrr_r2[0] > 0.9999
    assert tab.lrr_ci_low[1] < tab.lrr[1] < tab.lrr_ci_high[1] and tab.lrr_r2[1] < 1
