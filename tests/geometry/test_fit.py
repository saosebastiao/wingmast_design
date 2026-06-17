"""Phase-G.4 — geometric-fit validator (`R-GG-4`, parent `R-CON-1`)."""
from __future__ import annotations

from wingmast_design.geometry.box_spars import BoxSparLayout
from wingmast_design.geometry.fit import FitResult, check_fit
from wingmast_design.geometry.rotating_mast import RotatingMastSpec


def test_reference_design_fits():
    res = check_fit(RotatingMastSpec(), BoxSparLayout(n_spars=3, blend_radius=0.04, shell_wall=0.004))
    assert isinstance(res, FitResult)
    assert res.feasible
    assert res.margin > 0.0


def test_inflated_blend_radius_fails():
    res = check_fit(RotatingMastSpec(), BoxSparLayout(n_spars=3, blend_radius=0.5))
    assert not res.feasible
    assert res.margin < 0.0
    assert res.binding_reason.startswith("fillet")


def test_inflated_shell_wall_fails():
    res = check_fit(RotatingMastSpec(), BoxSparLayout(n_spars=3, shell_wall=0.5))
    assert not res.feasible
    assert res.binding_reason == "shell_room"


def test_binding_station_is_the_thin_tip_for_reference():
    s = RotatingMastSpec()
    res = check_fit(s, BoxSparLayout(n_spars=3, blend_radius=0.04, shell_wall=0.004))
    # the tip is the thinnest section → tightest vertical fillet room
    assert abs(res.binding_z - s.span) < 1e-6
    assert res.binding_reason == "fillet_vertical"


def test_more_spars_tighten_horizontal_room():
    s = RotatingMastSpec()
    # a blend radius that fits 3 wide bands but not 6 narrow ones
    layout3 = BoxSparLayout(n_spars=3, blend_radius=0.18, shell_wall=0.004)
    layout6 = BoxSparLayout(n_spars=6, blend_radius=0.18, shell_wall=0.004)
    assert check_fit(s, layout3).margin > check_fit(s, layout6).margin
