"""Phase 5 tests: class boundaries and bookkeeping (SYNTHETIC values)."""
import numpy as np
import pandas as pd

from aparri import risk as R
from aparri import tables as TB
from aparri.io import load_config


def test_boundaries_exactly_two_and_five_are_medium():
    epr = np.array([-1.999999, -2.0, -2.000001, -4.999999, -5.0, -5.000001, 0.0, 0.3, np.nan])
    c = R.classify(epr, 2.0, 5.0, "Low")
    assert list(c[:8]) == ["Low", "Medium", "Medium", "Medium", "Medium", "High", "Low", "Low"] and c[8] is None


def test_accretion_follows_config_and_is_tagged():
    epr = np.array([+3.0, -3.0])
    assert list(R.classify(epr, 2, 5, "Low")) == ["Low", "Medium"]
    assert list(R.classify(epr, 2, 5, "Medium")) == ["Medium", "Medium"]
    assert list(R.trend(epr)) == ["accreting", "eroding"]


def test_confidence_flips_and_flags():
    cfg = load_config()
    tr = pd.DataFrame({"EPR_m_yr": [-1.9, -3.5, -2.1, -3.0], "valid_epr": [True, True, True, False],
                       "quality_flag": ["", "", "", "crossing"], "multi_hit_years": ["", "", "", ""], "missing": ["", "", "", ""],
                       "T_years": [35.0] * 4})
    out = R.confidence_table(tr, cfg, "NOT_PROVIDED", None)
    assert out.unc_basis.iloc[0].startswith("what-if")
    u = np.sqrt(2) * 30 / 35
    assert out.class_may_flip.tolist() == [True, False, True, True]         # ±1.21: 1.9 and 2.1 and 3.0 (1.79..4.21) straddle 2; 3.5 (2.29..4.71) does not
    assert out.confidence.tolist() == ["medium", "high", "medium", "low"]
    out2 = R.confidence_table(tr, cfg, "COMPLETE", 0.1)
    assert out2.class_may_flip.tolist() == [True, False, False, False] and out2.unc_basis.iloc[0] == "configured"      # u = 0.1 m/yr


def test_table_columns_and_hectares():
    cfg = load_config()
    import geopandas as gpd
    from shapely.geometry import LineString
    tr = pd.DataFrame({"barangay": ["Maura"] * 3 + ["Dodan"], "valid_epr": [True, True, False, True], "EPR_m_yr": [-1.0, -3.0, np.nan, -6.0],
                       "lrr": [-1.0, -3.0, np.nan, -6.0], "flagged": [False, False, True, False], "confidence": ["high", "medium", "low", "high"],
                       "class_may_flip": [False, True, False, False]})
    seg = gpd.GeoDataFrame({"barangay": ["Maura", "Maura", "Dodan"], "risk_class": ["Low", "Medium", "High"], "length_m": [1000.0, 500.0, 250.0],
                            "geometry": [LineString([(0, 0), (1, 0)])] * 3}, crs=32651)
    df = TB.barangay_table(tr, seg, cfg).set_index("Barangay")
    assert abs(df.loc["Maura", "Low risk (km)"] - 1.0) < 1e-9 and abs(df.loc["Maura", "Medium risk (km)"] - 0.5) < 1e-9
    assert abs(df.loc["Maura", "Medium risk (ha, 100 m strip)"] - 0.5 * 1000 * 100 / 1e4) < 1e-9          # 5 ha
    assert df.loc["Maura", "n valid"] == 2 and df.loc["Maura", "n flagged"] == 1
    assert df.loc["Dodan", "Max EPR (m/yr)"] == -6.0
    assert df.loc["Bulala Sur", "data quality"].startswith("NO DATA")


def test_qml_is_well_formed_xml(tmp_path):
    from xml.etree import ElementTree as ET
    p = tmp_path / "x.qml"
    R.write_qml(p)
    root = ET.parse(p).getroot()
    assert root.tag == "qgis" and len(root.findall(".//category")) == 4 and len(root.findall(".//symbols/symbol")) == 4
