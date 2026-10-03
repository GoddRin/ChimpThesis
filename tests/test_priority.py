import pandas as pd

from aparri import priority as P


def test_minmax_and_ranking():
    assert P.minmax(pd.Series([1.0, 2.0, 3.0])).tolist() == [0.0, 0.5, 1.0]
    assert P.minmax(pd.Series([2.0, 2.0])).tolist() == [0.0, 0.0]
    ext = pd.DataFrame({"Medium risk (km)": [1.0, 0.0, 0.5], "High risk (km)": [0.0, 0.0, 0.0], "% classes that may flip": [0.0, 50.0, 100.0]}, index=["A", "B", "C"])
    tm = pd.DataFrame({"barangay": ["A", "A", "B", "B", "C", "C"], "valid_epr": True, "EPR_m_yr": [-4.0, -4.0, -1.0, 0.5, -2.0, -2.0]})
    t = P.priority_table(ext, tm, {"rate": 1.0, "extent": 1.0})
    assert t.index.tolist() == ["A", "C", "B"] and t.loc["A", "priority_score"] == 1.0 and t.loc["B", "priority_score"] == 0.0
    t2 = P.priority_table(ext, tm, {"rate": 1.0, "extent": 0.0})           # weights matter
    assert t2.index[0] == "A"
