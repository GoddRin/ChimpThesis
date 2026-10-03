"""Unit tests for the Phase 2 audit helpers (synthetic data only)."""
import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import LineString, Polygon, box

from aparri import audit


def test_grid_alignment_detects_lattice():
    cells = gpd.GeoDataFrame(geometry=[box(10 + i, 50 - j, 11 + i, 49 - j) for i in range(3) for j in range(3)], crs=4326)
    r = audit.grid_alignment(cells, x0=10, y0=50, res=1.0)
    assert r["on_grid_both"] == 1.0
    free = gpd.GeoDataFrame(geometry=[Polygon([(10.33, 49.41), (11.37, 49.4), (11.1, 48.77)])], crs=4326)
    assert audit.grid_alignment(free, 10, 50, 1.0)["on_grid_both"] == 0.0


def test_unique_length_removes_double_digitising():
    a = LineString([(0, 0), (1000, 0)])
    b = LineString([(0, 20), (1000, 20)])          # same coast digitised again 20 m away
    c = LineString([(1000, 0), (2000, 0)])
    g = gpd.GeoDataFrame({"year_raw": ["2010"] * 3}, geometry=[a, b, c], crs=32651)
    assert abs(audit.unique_length_km(g, 60) - 2.0) < 0.1
    assert abs(audit.unique_length_km(g, 5) - 3.0) < 0.1


def test_fragment_table_gaps_and_simple():
    a = LineString([(0, 0), (100, 0)])
    b = LineString([(150, 0), (300, 0), (300, 50), (200, -50)])      # crosses itself? no: make a loop
    loop = LineString([(0, 500), (100, 500), (100, 600), (50, 450), (50, 600)])
    g = gpd.GeoDataFrame({"fid": [0, 1, 2], "year_raw": ["1990", "1990", "2000"], "year": [1990, 1990, 2000]},
                         geometry=[a, b, loop], crs=32651)
    t = audit.fragment_table(g).set_index("fid")
    assert abs(t.loc[0, "gap_end_m"] - 50) < 1e-6
    assert not t.loc[2, "is_simple"]


def test_threshold_consistency_flags_med_below_two():
    d = pd.DataFrame({"Risk_Level": ["LOW", "Med", "Med", "Hig"], "EPR_90_25": [0.857, 0.857, 2.5, 5.7], "area_ha": [1, 1, 1, 1]})
    r = audit.threshold_consistency(d, 2.0, 5.0)
    assert r["n_violations"] == 1 and r["all_positive"]


def test_attribute_area_splits_between_barangays():
    brg = gpd.GeoDataFrame({"ADM4_EN": ["W", "E"]}, geometry=[box(0, 0, 100, 100), box(100, 0, 200, 100)], crs=32651)
    poly = box(50, 20, 150, 80)
    r = audit.attribute_area(poly, brg, 500)
    assert abs(r["W"] - r["E"]) < 0.05 and abs(sum(r.values()) - poly.area / 1e4) < 1e-6
    far = audit.attribute_area(box(5000, 5000, 5100, 5100), brg, 500)
    assert list(far) == [None]


def test_dbf_field_width_truncation(tmp_path):
    p = "data/raw/risk_zip/Aparri_MultiTemporal_Erosion_Risk_1990_2025.shp"
    f = {x["name"]: x for x in audit.dbf_fields(p)}
    assert f["Risk_Level"]["width"] == 3 and f["Risk_Level"]["type"] == "C"
