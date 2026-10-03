"""Phase 3B tests on SYNTHETIC rasters."""
import numpy as np
from shapely.geometry import LineString

from aparri import compare as CMP
from aparri import raster_shore as R


def band(shape=(30, 60), row=15):
    m = np.zeros(shape, bool)
    m[row:row + 2, 2:58] = True             # a 2-pixel thick edge band, like the Earth Engine masks
    return m


def test_skeleton_is_one_pixel_and_traces_to_one_line():
    from skimage.morphology import skeletonize
    sk = skeletonize(band())
    edges = R.trace_edges(sk)
    assert len(edges) == 1 and len(edges[0]) >= 50
    assert sk.sum() <= 60


def test_short_spur_pruned_long_branch_kept():
    from skimage.morphology import skeletonize
    m = band()
    m[8:15, 30] = True                      # 7-px stub going up from the band
    m[3:15, 45] = True                      # 12-px branch
    sk = skeletonize(m)
    pruned, n = R.prune_spurs(sk, min_px=9)
    assert n >= 1
    assert pruned[5, 45] and not pruned[9, 30]       # long branch survives, short stub removed


def test_speckle_ring_removed_but_big_region_kept():
    m = np.zeros((40, 40), bool)
    m[10:15, 10:15] = True; m[11:14, 11:14] = False          # ring enclosing 9 px
    m[20:38, 5:35] = True; m[22:36, 7:33] = False            # big ring enclosing 14x26=364 px
    out, n = R.remove_speckle_rings(m, max_area_px=50)
    assert n == 1 and not out[10:15, 10:15].any() and out[20:38, 5:35].any()


def test_signed_offset_sign_convention():
    ref = LineString([(0, 0), (1000, 0)])
    north = LineString([(0, 25), (1000, 25)])          # 25 m to the north
    n_sea = np.array([0.0, 1.0])                        # sea is north
    off = CMP.signed_offsets([north], [ref], n_sea, step_m=100)
    assert np.allclose(off.signed_m, 25) and np.allclose(off.dist_m, 25)
    off2 = CMP.signed_offsets([north], [ref], -n_sea, step_m=100)
    assert np.allclose(off2.signed_m, -25)
    s = CMP.summarize(off)
    assert s["share_over_60m"] == 0 and abs(s["rmse_m"] - 25) < 1e-9
