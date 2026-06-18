"""Phase-S.1 — journal/bearing boundary conditions (`R-S-1`, parent `R-CON-3`)."""
from __future__ import annotations

import numpy as np

from wingmast_design.structural.frame import BeamSection, solve_frame
from wingmast_design.structural.journal_bc import (
    JournalBC,
    apply_journal_springs,
    solve_frame_journal,
)

_E, _G = 70.0e9, 27.0e9


def _toy_mast():
    # a vertical mast (span +Z): heel(−4), partners(−0.9), root(0), mid(11), tip(22)
    nodes = np.array([[0, 0, -4.0], [0, 0, -0.9], [0, 0, 0.0], [0, 0, 11.0], [0, 0, 22.0]])
    elements = np.array([[0, 1], [1, 2], [2, 3], [3, 4]])
    sections = [BeamSection.circular(0.08)] * 4
    return nodes, elements, sections


def _bc():
    return JournalBC(partners_node=1, heel_node=0)


def test_radial_reactions_balance_the_transverse_load():
    """The two spanwise-separated journals react a transverse load as a couple (equilibrium)."""
    nodes, elements, sec = _toy_mast()
    loads = np.zeros((5, 6))
    loads[4, 0] = 10_000.0  # 10 kN transverse (Fx) at the tip
    _, R = solve_frame_journal(nodes, elements, sec, E=_E, G=_G, journal=_bc(), loads=loads)
    assert abs((R["heel_Fx"] + R["partners_Fx"]) + 10_000.0) < 1.0   # ΣFx = −applied (equilibrium)
    assert R["heel_Fx"] * R["partners_Fx"] < 0                       # opposite signs → a couple


def test_heel_reacts_axial_thrust():
    nodes, elements, sec = _toy_mast()
    loads = np.zeros((5, 6))
    loads[4, 2] = -5_000.0  # axial (gravity down the span)
    _, R = solve_frame_journal(nodes, elements, sec, E=_E, G=_G, journal=_bc(), loads=loads)
    assert abs(R["heel_Fz"] - 5_000.0) < 1.0                         # the heel reacts the thrust


def test_pivot_rotation_is_free_not_clamped():
    """A torque about the span axis rotates the base (finite actuator stiffness reacts it) —
    the mast is free to weathervane, unlike a rigid clamp where the base rotation would be 0."""
    nodes, elements, sec = _toy_mast()
    loads = np.zeros((5, 6))
    loads[4, 5] = 5_000.0  # 5 kN·m torque about the span axis
    res, R = solve_frame_journal(nodes, elements, sec, E=_E, G=_G, journal=_bc(), loads=loads)
    assert abs(R["pivot_Mz"] + 5_000.0) < 1.0                        # actuator reacts the full torque
    assert abs(res.displacements[0, 5]) > 0.0                        # base rotates (free-ish), not clamped


def test_journal_bc_differs_from_a_root_clamp():
    """The journal-supported mast responds differently than a root-clamped one — the buckling
    boundary the audit warns about is genuinely a different BC (re-verified by eigen in S.6)."""
    nodes, elements, sec = _toy_mast()
    loads = np.zeros((5, 6))
    loads[4, 0] = 1_000.0
    res_j, _ = solve_frame_journal(nodes, elements, sec, E=_E, G=_G, journal=_bc(), loads=loads)
    res_c = solve_frame(nodes, elements, sec, E=_E, G=_G, fixed_nodes=np.array([0]), loads=loads)
    assert abs(res_j.max_translation_m - res_c.max_translation_m) > 1.0e-3


def test_springs_make_the_free_system_solvable():
    """Without the bearing springs the free-free system is singular; adding them stabilises all
    rigid-body modes except the (drive-restrained) pivot rotation."""
    from wingmast_design.structural.frame import assemble_frame_K

    nodes, elements, sec = _toy_mast()
    K, _, _ = assemble_frame_K(nodes, elements, sec, E=_E, G=_G)
    Kj = apply_journal_springs(K, _bc())
    # the augmented diagonal gained exactly the 6 spring stiffnesses
    assert Kj.diagonal().sum() > K.diagonal().sum()
    # and a transverse solve produces a finite, bounded response
    loads = np.zeros((5, 6))
    loads[4, 0] = 100.0
    res, _ = solve_frame_journal(nodes, elements, sec, E=_E, G=_G, journal=_bc(), loads=loads)
    assert np.all(np.isfinite(res.displacements))
