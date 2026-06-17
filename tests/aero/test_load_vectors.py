"""Phase-A.5 — directional, at-the-CoP, distributed mast load vectors (`R-AE-5`/`R-S-2`)."""
from __future__ import annotations

import numpy as np

from wingmast_design.aero.load_vectors import (
    AeroBalance,
    nodal_load_vectors,
    operational_mast_load,
)

_F = 15.0e3  # transverse (heeling) resultant, N
_BAL = AeroBalance(pivot_xc=0.25, cop_xc=0.28)   # CoP 0.03c aft of the pivot


def test_normal_force_is_conserved():
    load = operational_mast_load(_F, _BAL)
    assert abs(load.total_normal_N - _F) < 1.0          # ∫ w(z) dz = the transverse resultant


def test_load_resultant_sits_at_the_centre_of_effort():
    load = operational_mast_load(_F, _BAL, span_m=22.0)
    arm = load.base_bending_Nm / load.total_normal_N    # centroid height of the distributed load
    assert 9.5 < arm < 11.0                              # ≈ the CE (~10.7 m), not the 22 m tip


def test_torsion_comes_from_the_cop_offset():
    """The hinge torque is the CoP-vs-pivot offset × the (chord-normal) force — zero when the
    CoP is on the pivot, and increasing as it moves aft."""
    on_pivot = operational_mast_load(_F, AeroBalance(pivot_xc=0.25, cop_xc=0.25))
    assert abs(on_pivot.total_torsion_Nm) < 1.0

    small = operational_mast_load(_F, AeroBalance(pivot_xc=0.25, cop_xc=0.28))
    larger = operational_mast_load(_F, AeroBalance(pivot_xc=0.25, cop_xc=0.33))
    assert 0.0 < small.total_torsion_Nm < larger.total_torsion_Nm


def test_slightly_aft_cop_gives_a_small_hinge_torque():
    """A 'slightly behind' CoP ⇒ a SMALL, controllable hinge moment (the design intent) — far
    below the ~4.3 kN·m the old Cm=−0.16 implied."""
    load = operational_mast_load(_F, _BAL)
    assert 0.5e3 < load.total_torsion_Nm < 3.0e3


def test_directional_components():
    load = operational_mast_load(_F, _BAL, lift_drag_ratio=15.0)
    # drag is a small chordwise fraction of the chord-normal (lift/heeling) load
    assert abs(load.total_chordwise_N - _F / 15.0) < 1.0
    assert load.total_chordwise_N < 0.2 * load.total_normal_N


def test_nodal_lumping_conserves_and_maps_to_the_right_dofs():
    load = operational_mast_load(_F, _BAL)
    node_z = np.array([0.0, 5.5, 11.0, 16.5, 22.0])
    nl = nodal_load_vectors(load, node_z)
    assert nl.shape == (5, 6)
    assert abs(nl[:, 1].sum() - load.total_normal_N) < 0.05 * _F      # Fy = normal (bending)
    assert abs(nl[:, 5].sum() - load.total_torsion_Nm) < 0.05 * abs(load.total_torsion_Nm) + 50.0  # Mz = torsion
    assert np.all(nl[:, 1] >= -1e-9)                                  # bending load all one way
    # it is distributed: more than one node carries the bending load
    assert np.count_nonzero(nl[:, 1] > 1.0) >= 3


def test_unsorted_nodes_are_handled():
    load = operational_mast_load(_F, _BAL)
    node_z = np.array([22.0, 0.0, 11.0])
    nl = nodal_load_vectors(load, node_z)
    assert abs(nl[:, 1].sum() - load.total_normal_N) < 0.1 * _F
