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


# --- the extensible operational-scenario framework (R-AE-1/2) ----------------------

def test_registry_op1_op2_match_basis_via_resolver():
    """op1()/op2() are registry lookups; the RM-capped resolver reproduces basis §3 exactly."""
    from wingmast_design.aero.operational import OPERATIONAL_SCENARIOS, op1, op2

    assert [s.name for s in OPERATIONAL_SCENARIOS] == ["OP-1", "OP-2"]
    assert abs(op1().design_bending_Nm - 114.643e3) < 10.0
    assert abs(op2().design_bending_Nm - 160.5e3) < 10.0


def test_q_limited_ceiling_is_min_coupled():
    """heeling = min(split·RM, split·aero_capacity): the righting moment always caps; a q-limited
    case binds only when the wind cannot drive the rig to the RM ceiling (Article IV)."""
    from wingmast_design.aero.operational import (
        HeelingCeiling,
        OperationalScenario,
        resolve_operational,
    )

    cond = SailingConditions()
    rm_share_bending = 0.60 * cond.rm_max_Nm / cond.heeling_lever_m * cond.operational_arm_m * cond.daf

    # weak wind (q·area·cl below RM share) ⇒ q-limited, BELOW the RM-capped value
    weak = OperationalScenario("weak", split=0.60, ceiling=HeelingCeiling.q_limited(150.0, 45.0, 1.1))
    assert resolve_operational(weak, cond).design_bending_Nm < rm_share_bending

    # strong wind (q·area·cl above RM share) ⇒ equilibrium still binds: identical to RM-capped
    strong = OperationalScenario("strong", split=0.60, ceiling=HeelingCeiling.q_limited(5000.0, 75.0, 1.5))
    rm_capped = OperationalScenario("rm", split=0.60, ceiling=HeelingCeiling.rm_capped())
    assert abs(resolve_operational(strong, cond).design_bending_Nm
               - resolve_operational(rm_capped, cond).design_bending_Nm) < 1.0


def test_per_scenario_daf_and_torque_override():
    from wingmast_design.aero.operational import (
        HeelingCeiling,
        OperationalScenario,
        resolve_operational,
        scenario_torque_Nm,
    )

    base = OperationalScenario("a", split=0.70, ceiling=HeelingCeiling.rm_capped())
    gusty = dataclasses.replace(base, daf=2.0)
    assert abs(resolve_operational(gusty).design_bending_Nm
               - (2.0 / 1.5) * resolve_operational(base).design_bending_Nm) < 1.0
    # torque carries its own camber operating point
    assert scenario_torque_Nm(base) > 0.0
