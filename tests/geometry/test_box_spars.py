"""Phase-G.3 — box-spar + longeron-channel + outer-shell sections (`R-GG-3`, parent
`R-GEO-5`)."""
from __future__ import annotations

import numpy as np

from wingmast_design.geometry.box_spars import (
    BoxSparLayout,
    box_spar_sections,
    longeron_void_area,
    mast_box_spar_sections,
)
from wingmast_design.geometry.rotating_mast import RotatingMastSpec


def _section(n_spars=3, blend_radius=0.04):
    return mast_box_spar_sections(
        RotatingMastSpec(), z=0.0, layout=BoxSparLayout(n_spars=n_spars, blend_radius=blend_radius)
    )


def test_at_least_three_box_spars():
    assert len(_section(n_spars=3).cells) == 3
    s5 = _section(n_spars=5)
    assert len(s5.cells) == 5
    assert len(s5.channels) == 4              # n_spars - 1 internal webs
    assert len(s5.webs) == 4


def test_n_spars_below_three_rejected():
    import pytest

    with pytest.raises(AssertionError):
        box_spar_sections(RotatingMastSpec()._contour(0.0), BoxSparLayout(n_spars=2))


def test_longeron_void_scales_with_blend_radius():
    """The R-GEO-5 coupling: channel void ∝ blend_radius² (strictly increasing)."""
    rs = [0.02, 0.04, 0.08]
    voids = [longeron_void_area(r) for r in rs]
    assert voids[0] < voids[1] < voids[2]
    # quadratic: doubling r quadruples the void
    assert abs(voids[1] / voids[0] - 4.0) < 1e-9
    assert abs(voids[2] / voids[1] - 4.0) < 1e-9
    # the section carries the same coupled void on its channels
    sec = _section(blend_radius=0.06)
    assert all(abs(ch.void_area - longeron_void_area(0.06)) < 1e-12 for ch in sec.channels)


def test_bigger_blend_gives_bigger_channel_in_section():
    small = _section(blend_radius=0.03).channels[0].void_area
    big = _section(blend_radius=0.06).channels[0].void_area
    assert big > small


def test_webs_lie_between_le_and_te():
    sec = _section(n_spars=4)
    oml = sec.outer_shell
    x_le, x_te = oml[:, 0].min(), oml[:, 0].max()
    assert len(sec.webs) == 3
    assert np.all(sec.webs > x_le) and np.all(sec.webs < x_te)
    assert np.all(np.diff(sec.webs) > 0)      # ordered LE→TE


def test_cells_fit_within_oml_envelope():
    sec = _section(n_spars=3)
    oml = sec.outer_shell
    allc = np.vstack(sec.cells)
    assert allc[:, 0].min() >= oml[:, 0].min() - 1e-6
    assert allc[:, 0].max() <= oml[:, 0].max() + 1e-6
    assert allc[:, 1].min() >= oml[:, 1].min() - 1e-6
    assert allc[:, 1].max() <= oml[:, 1].max() + 1e-6


def test_internal_cells_have_blend_curve_corners():
    """The web↔OML corners are rounded (blend-curve), and a larger blend radius trims the
    corner back further — 'convex spars with blend-curve corners' (R-GEO-5)."""
    from wingmast_design.geometry.box_spars import _split_upper_lower, _y_on

    def corner_gap(r: float) -> float:
        sec = _section(n_spars=3, blend_radius=r)
        cell = sec.cells[1]                                  # center cell
        wr = sec.webs[1]                                     # its right web
        upper, _ = _split_upper_lower(sec.outer_shell)
        sharp = np.array([wr, _y_on(upper, np.array([wr]))[0]])  # un-rounded top-right corner
        return float(np.min(np.hypot(cell[:, 0] - sharp[0], cell[:, 1] - sharp[1])))

    # the rounded cell stays further from the sharp corner as the blend radius grows
    assert corner_gap(0.06) > corner_gap(0.01) > 0.0


def test_outer_shell_is_the_oml():
    sec = _section()
    oml = RotatingMastSpec()._contour(0.0)
    chord = RotatingMastSpec().chord_at_z(0.0)
    expect = (oml - np.array([RotatingMastSpec().rotation_center_xc, 0.0])) * chord
    assert np.allclose(sec.outer_shell, expect)
