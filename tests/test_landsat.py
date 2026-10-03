"""Phase 3C helper tests (SYNTHETIC index fields; the Landsat step itself was NOT run)."""
import numpy as np
import pandas as pd
from affine import Affine

from aparri import landsat as L


def test_indices_formulas():
    g, n, s = np.array([0.3]), np.array([0.1]), np.array([0.05])
    assert np.isclose(L.ndwi(g, n)[0], (0.3 - 0.1) / (0.3 + 0.1))
    assert np.isclose(L.mndwi(g, s)[0], (0.3 - 0.05) / (0.3 + 0.05))
    assert np.isclose(L.aweish(np.array([0.1]), g, n, s, np.array([0.02]))[0], 0.1 + 2.5 * 0.3 - 1.5 * 0.15 - 0.25 * 0.02)


def test_otsu_between_two_modes():
    rng = np.random.default_rng(0)
    water = rng.normal(0.5, 0.08, 4000); land = rng.normal(-0.4, 0.1, 4000)
    t = L.otsu(np.concatenate([water, land]))
    assert -0.1 < t < 0.2


def test_subpixel_contour_accuracy():
    """A tilted straight boundary: contour must sit within 0.05 pixel (1.5 m) of the truth."""
    tr = Affine(30, 0, 350000, 0, -30, 2030000)
    rows, cols = np.indices((60, 60))
    xc = 350000 + (cols + 0.5) * 30; yc = 2030000 - (rows + 0.5) * 30
    # signed distance to the line y = 0.3 x + b  (index changes linearly across it => exact sub-pixel contour)
    b = 2030000 - 0.3 * 350900 - 300
    d = (yc - (0.3 * xc + b)) / np.sqrt(1 + 0.09)
    index = d / 100.0
    lines = L.contour_lines(index, 0.0, tr, min_len_m=100)
    assert len(lines) == 1
    pts = np.array(lines[0].coords)
    resid = (pts[:, 1] - (0.3 * pts[:, 0] + b)) / np.sqrt(1.09)
    assert np.abs(resid).max() < 1.5


def test_scene_quality_flags_thin_years():
    s = pd.DataFrame({"year": [1990, 1990, 2025, 2025, 2025], "scene_id": list("abcde"), "date": ["1990-03-01", "1990-04-01", "2025-03-02", "2025-04-02", "2025-05-02"],
                      "sensor": ["L5", "L5", "L8", "L9", "L8"], "cloud_cover": [10, 20, 5, 6, 7]})
    q = L.scene_quality(s, 3).set_index("year")
    assert not q.loc[1990, "enough_images"] and q.loc[2025, "enough_images"] and q.loc[2025, "sensors"] == "L8,L9"
