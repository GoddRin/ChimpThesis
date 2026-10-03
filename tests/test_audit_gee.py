"""Unit tests for Phase 2B helpers on a tiny synthetic raster (SYNTHETIC; not real data)."""
from types import SimpleNamespace

import numpy as np
import pandas as pd
from affine import Affine

from aparri import audit_gee as G


def fake(nsm, change, risk=None):
    nsm = np.array(nsm, float)
    epr = nsm / 35
    change = np.array(change, np.uint8)
    if risk is None:
        a = np.abs(epr)
        risk = np.ones_like(change)
        risk[(epr < 0) & (a >= 2) & (a <= 5)] = 2
        risk[(epr < 0) & (a > 5)] = 3
    return SimpleNamespace(nsm=nsm, epr=epr, change=change, risk=risk, px_ha=0.085)


def test_legend_check_consistent():
    r = fake([[0, -90, 30], [-300, 0, 0]], [[0, 1, 2], [1, 0, 0]])
    leg = G.legend_check(r, 2.0, 5.0)
    assert leg["code1_all_nsm_nonpositive"] and leg["code2_all_nsm_nonnegative"]
    assert leg["epr_equals_nsm_over_35"] and leg["risk_matches_rule_pixels"] == leg["risk_pixels"]
    assert leg["n_code"] == {0: 3, 1: 2, 2: 1}


def test_risk_boundaries_exact_two_and_five():
    # EPR exactly -2.0 and -5.0 (NSM = -70, -175) must be Medium; -2.0001/-5.0001 side by side.
    r = fake([[-70.0, -175.0, -175.1, -69.9]], [[1, 1, 1, 1]])
    assert r.risk.tolist() == [[2, 2, 3, 1]]


def test_quantisation_pixel_multiples():
    q = G.quantisation(fake([[0, -30, 30 * np.sqrt(2), -60]], [[0, 1, 2, 1]]))
    assert q["share_nsm_over30_squared_is_integer"] == 1.0 and q["smallest_abs_nsm"] == 30


def test_circle_weights_area():
    tr = Affine(0.0003, 0, 121.6, 0, -0.0003, 18.4)
    shape = (60, 60)
    rows, cols = np.indices(shape)
    r = SimpleNamespace(shape=shape, transform=tr, bounds=SimpleNamespace(left=121.6, top=18.4),
                        )
    w = G.circle_weights(r, 121.609, 18.391, 300.0, 32651, sub=3)
    pix_m2 = 0.0003 * 111320 * np.cos(np.radians(18.4)) * 0.0003 * 110574
    area = w.sum() * pix_m2
    assert abs(area - np.pi * 300**2) / (np.pi * 300**2) < 0.05
