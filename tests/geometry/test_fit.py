"""Phase-G.4 — geometric-fit validator (`R-GG-4`, parent `R-CON-1`)."""
from __future__ import annotations

from wingmast_design.geometry.cells import CellLayout
from wingmast_design.geometry.fit import FitResult, check_fit
from wingmast_design.geometry.rotating_mast import RotatingMastSpec


def test_reference_design_fits():
    res = check_fit(RotatingMastSpec(), CellLayout(n_cells=3))   # mast-scale defaults
    assert isinstance(res, FitResult)
    assert res.feasible
    assert res.margin > 0.0


def test_inflated_blend_radius_fails():
    res = check_fit(RotatingMastSpec(), CellLayout(n_cells=3, blend_radius=0.5))
    assert not res.feasible
    assert res.margin < 0.0
    assert res.binding_reason.startswith("fillet")


def test_inflated_shell_wall_fails():
    res = check_fit(RotatingMastSpec(), CellLayout(n_cells=3, shell_wall=0.5))
    assert not res.feasible
    assert res.binding_reason == "wall_room"


def test_inflated_cell_wall_fails():
    # R-GG-6 acceptance: an inflated *spar* wall must also bite (not only shell).
    res = check_fit(RotatingMastSpec(), CellLayout(n_cells=3, cell_wall=0.5))
    assert not res.feasible
    assert res.binding_reason == "wall_room"


def test_reference_members_are_valid():
    # R-CON-1 "must not intersect": the validator actually inspects the cell polygons.
    res = check_fit(RotatingMastSpec(), CellLayout(n_cells=3))
    assert res.members_valid


def test_simple_polygon_helper_detects_self_intersection():
    import numpy as np

    from wingmast_design.geometry.fit import _is_simple_polygon

    assert _is_simple_polygon(np.array([[0, 0], [1, 0], [1, 1], [0, 1]]))   # square
    assert not _is_simple_polygon(np.array([[0, 0], [1, 1], [1, 0], [0, 1]]))  # bowtie


def test_binding_station_is_the_thin_tip_for_reference():
    s = RotatingMastSpec()
    res = check_fit(s, CellLayout(n_cells=3))
    # the tip is the thinnest section → tightest vertical fillet room
    assert abs(res.binding_z - s.span) < 1e-6
    assert res.binding_reason == "fillet_vertical"


def test_more_spars_tighten_horizontal_room():
    s = RotatingMastSpec()
    # a mast-scale blend radius that fits 3 wide bands but tightens for 6 narrow ones
    layout3 = CellLayout(n_cells=3, blend_radius=0.05)
    layout6 = CellLayout(n_cells=6, blend_radius=0.05)
    assert check_fit(s, layout3).margin > check_fit(s, layout6).margin
