"""Phase 3A tests on SYNTHETIC lines."""
import geopandas as gpd
import numpy as np
from shapely.geometry import LineString, box

from aparri import clean as C
from aparri.io import load_config


def test_fragments_are_merged_when_ends_touch():
    a = np.array([[0, 0], [100, 0]], float)
    b = np.array([[102, 0], [200, 0]], float)         # 2 m gap < snap_tol 5
    far = np.array([[0, 500], [100, 500]], float)
    chains, joins = C.snap_merge([(1, a), (2, b), (3, far)], tol=5)
    assert len(chains) == 2 and len(joins) == 1 and abs(joins[0]["gap_m"] - 2) < 1e-9
    lengths = sorted(round(np.hypot(*np.diff(c, axis=0).T).sum()) for _, c in chains)
    assert lengths == [100, 200]


def test_small_loop_removed_and_large_loop_kept():
    # path crosses itself at (10, 0); the loop (10,0)->(20,0)->(20,10)->(10,10)->(10,0) is 40 m long
    c = np.array([[0, 0], [20, 0], [20, 10], [10, 10], [10, -10], [40, -10]], float)
    out, removed, kept = C.remove_small_loops(c, max_len=50)
    assert len(removed) == 1 and abs(removed[0]["length_m"] - 40) < 1e-6 and not kept
    assert not C.self_intersections(out)
    big = c * 10                                       # same shape, loop now 400 m: real geography, only reported
    out2, removed2, kept2 = C.remove_small_loops(big, max_len=50)
    assert not removed2 and len(kept2) == 1 and abs(kept2[0]["length_m"] - 400) < 1e-6


def test_duplicate_stretch_detected_longest_kept():
    long = LineString([(0, 0), (1000, 0)])
    a = LineString([(0, 25), (400, 25)])               # digitised again 25 m away
    b = LineString([(400, 25), (1000, 25)])
    kept, dropped = C.drop_duplicate_fragments([(0, long), (1, a), (2, b)], tol=60, cover=0.8)
    assert [k[0] for k in kept] == [0] and {d["fid"] for d in dropped} == {1, 2}


def test_orient_nw_se():
    c = np.array([[100, 0], [0, 50]], float)           # x - y goes 100 -> -50 : reversed
    assert C.orient_nw_se(c)[0, 0] == 0


def test_hig_is_quarantined_not_guessed():
    cfg = load_config()
    gdf = gpd.GeoDataFrame({"id": [None] * 3, "1990": ["1990", "2025", "Hig"]},
                           geometry=[LineString([(0, 0), (1000, -300), (2000, -500)]),
                                     LineString([(0, 20), (1000, -280), (2000, -480)]),
                                     LineString([(500, -100), (900, -250)])], crs=32651)
    gdf = gdf.to_crs(4326)
    log = C.CleanLog()
    res = C.clean_shorelines(gdf, cfg, box(-1e7, -1e7, 1e7, 1e7), log)
    assert len(res["quarantine"]) == 1
    q = log.frame()
    assert (q.action == "quarantine").sum() == 1 and q[q.action == "quarantine"].needs_human_review.all()
    assert set(res["chains"].year) == {1990, 2025}


def test_manual_override_assigns_year_and_is_logged():
    cfg = load_config()
    cfg = {**cfg, "manual_year_overrides": {"feature_2": 2010}}
    gdf = gpd.GeoDataFrame({"id": [None] * 3, "1990": ["1990", "2025", "Hig"]},
                           geometry=[LineString([(0, 0), (1000, -300), (2000, -500)]),
                                     LineString([(0, 20), (1000, -280), (2000, -480)]),
                                     LineString([(0, 10), (1000, -290), (2000, -490)])], crs=32651).to_crs(4326)
    log = C.CleanLog()
    res = C.clean_shorelines(gdf, cfg, box(-1e7, -1e7, 1e7, 1e7), log)
    assert 2010 in set(res["chains"].year) and len(res["quarantine"]) == 0
    assert "manual_year_override" in set(log.frame().action)


def test_covered_intervals_and_overlap():
    a = np.array([0.0, 0.0]); ax = np.array([1.0, 0.0])
    iv = C.covered_intervals([LineString([(0, 0), (1000, 0)]), LineString([(1050, 0), (3000, 0)])], a, ax, gap_m=100)
    assert len(iv) == 1 and abs(C.total(iv) - 3.0) < 1e-9
    assert abs(C.total(C.interval_overlap(iv, [(1.0, 2.0)])) - 1.0) < 1e-9
