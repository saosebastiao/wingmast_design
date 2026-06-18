"""Phase-A.5 — directional, at-the-CoP, distributed mast load vectors (`R-AE-5`/`R-S-2`)."""
from __future__ import annotations

import numpy as np

from wingmast_design.aero.load_vectors import (
    AeroBalance,
    nodal_load_vectors,
    operational_mast_load,
)

_M = 160.5e3  # OP-2 design base bending at the partners, N·m (the RM-capped input)
_BAL = AeroBalance(pivot_xc=0.25, cop_xc=0.28)   # CoP 0.03c aft of the pivot


def test_base_moment_is_reproduced_exactly():
    """The distribution is scaled so its moment about the base datum = the input — the governing
    OP-2 base moment is recovered by construction, not approximated."""
    load = operational_mast_load(_M, _BAL)
    assert abs(load.base_bending_Nm - _M) < 1.0


def test_total_force_and_arm_are_derived_not_pinned_to_the_CE():
    """Force + resultant arm are *derived* from the ∝chord (taper-0.6) shape; the arm lands near
    but inboard of a pure resultant-at-CE model (~10.7 m design CE) — it is NOT pinned to it."""
    load = operational_mast_load(_M, _BAL, span_m=22.0)
    assert 14.0e3 < load.total_normal_N < 15.0e3        # ~14.6 kN (more inboard ⇒ > M/CE)
    assert 10.5 < load.resultant_arm_m < 11.5           # ~11.0 m above the partners, near the CE


def test_torsion_comes_from_the_cop_offset():
    """The hinge torque is the CoP-vs-pivot offset × the (chord-normal) load — zero when the
    CoP is on the pivot, and increasing as it moves aft."""
    on_pivot = operational_mast_load(_M, AeroBalance(pivot_xc=0.25, cop_xc=0.25))
    assert abs(on_pivot.total_torsion_Nm) < 1.0

    small = operational_mast_load(_M, AeroBalance(pivot_xc=0.25, cop_xc=0.28))
    larger = operational_mast_load(_M, AeroBalance(pivot_xc=0.25, cop_xc=0.33))
    assert 0.0 < small.total_torsion_Nm < larger.total_torsion_Nm


def test_offset_model_gives_a_small_hinge_torque():
    """A 'slightly behind' CoP ⇒ a SMALL hinge moment (~1.3 kN·m) under THIS offset model. NOTE:
    this is not directly comparable to the Cm=−0.16 torque the operational scenario carries — the
    offset model omits the camber (Cm0) moment a cambered soft wingsail holds even at zero lift,
    and assumes a CL-independent CoP. The A.5 distributed-torsion planform must pin that term."""
    load = operational_mast_load(_M, _BAL)
    assert 0.5e3 < load.total_torsion_Nm < 3.0e3


def test_directional_components():
    load = operational_mast_load(_M, _BAL, lift_drag_ratio=15.0)
    # drag is a small chordwise fraction of the chord-normal (lift/heeling) load
    assert abs(load.total_chordwise_N - load.total_normal_N / 15.0) < 1.0
    assert load.total_chordwise_N < 0.2 * load.total_normal_N


def test_nodal_lumping_conserves_and_maps_to_the_right_dofs():
    load = operational_mast_load(_M, _BAL)
    node_z = np.array([0.0, 5.5, 11.0, 16.5, 22.0])
    nl = nodal_load_vectors(load, node_z)
    assert nl.shape == (5, 6)
    # conserves to machine precision (edge-interpolated tributary integration)
    assert abs(nl[:, 1].sum() - load.total_normal_N) < 1e-6 * load.total_normal_N   # Fy = normal
    assert abs(nl[:, 5].sum() - load.total_torsion_Nm) < 1e-6 * abs(load.total_torsion_Nm) + 1e-6
    assert np.all(nl[:, 1] >= -1e-9)                                  # bending load all one way
    # it is distributed: more than one node carries the bending load
    assert np.count_nonzero(nl[:, 1] > 1.0) >= 3


def test_nodal_lumping_preserves_the_base_moment():
    """Lumping must also preserve the base bending moment about the partners — not just the force
    (the structurally relevant invariant)."""
    load = operational_mast_load(_M, _BAL)
    node_z = np.linspace(0.0, 22.0, 12)
    nl = nodal_load_vectors(load, node_z)
    lumped_moment = float(np.sum(nl[:, 1] * (node_z - load.base_z_m)))
    assert abs(lumped_moment - _M) < 0.01 * _M    # within 1% (nodal lever discretisation)


def test_unsorted_nodes_are_handled():
    load = operational_mast_load(_M, _BAL)
    node_z = np.array([22.0, 0.0, 11.0])
    nl = nodal_load_vectors(load, node_z)
    assert abs(nl[:, 1].sum() - load.total_normal_N) < 1e-6 * load.total_normal_N
