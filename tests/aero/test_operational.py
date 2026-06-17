"""Phase-A.1 — operational sailboat load model (`R-AE-1`, parent `R-LOAD-1`, basis §3).

Asserts the RM-capped load chain reproduces `docs/engineering_basis.md` §3 to the digit and
that every operational load scales **linearly** with `RM_max` (the dominant sensitivity, `D-1`).
"""
from __future__ import annotations

import dataclasses

from wingmast_design.aero.operational import (
    SailingConditions,
    op1,
    op2,
    operational_load,
    operational_torque_Nm,
    rm_sensitivity_band,
)


def test_op1_reproduces_basis_chain():
    o = op1()
    # basis §3: 200 → 50:50 100 kN·m → ÷14.0 m = 7.14 kN → ×10.7 m = 76.5 → ×DAF 1.5 = 115
    assert abs(o.heeling_moment_Nm - 100.0e3) < 1.0
    assert abs(o.transverse_force_N - 7.142857e3) < 1.0
    assert abs(o.base_bending_static_Nm - 76.4286e3) < 10.0
    assert abs(o.design_bending_Nm - 114.643e3) < 10.0   # rounds to the basis 115 kN·m


def test_op2_governs_and_matches_basis():
    o = op2()
    # basis §3: 0.70 × 200 = 140 → 160.5 kN·m design
    assert abs(o.design_bending_Nm - 160.5e3) < 10.0
    assert o.design_bending_Nm > op1().design_bending_Nm    # worst single mast governs


def test_loads_scale_linearly_with_rm():
    base = op2().design_bending_Nm
    doubled = operational_load(
        0.70, dataclasses.replace(SailingConditions(), rm_max_Nm=400.0e3)
    ).design_bending_Nm
    assert abs(doubled - 2.0 * base) < 1.0                  # exact linearity in RM_max


def test_rm_sensitivity_band():
    lo, hi = rm_sensitivity_band(0.70)                      # RM 150 → 225
    assert abs(lo - 120.0e3) < 1.0e3                        # 160 × 150/200
    assert abs(hi - 180.6e3) < 1.0e3                        # basis 180 @ RM 225
    assert lo < op2().design_bending_Nm < hi               # central 200 sits inside


def test_operational_torque_formula():
    # T = q·A·c·|Cm_axis|; static at q=74 Pa, then ×DAF for design.
    static = operational_torque_Nm(74.0, 75.0, 3.2, daf=False)
    design = operational_torque_Nm(74.0, 75.0, 3.2)
    assert abs(static - 74.0 * 75.0 * 3.2 * 0.16) < 1.0
    assert abs(design - 1.5 * static) < 1.0
    assert design > 0.0
