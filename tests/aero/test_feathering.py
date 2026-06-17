"""Phase-A.4 — feathering-robustness model / decision gate D-2 (`R-AE-4`, parent `R-LOAD-2a/2b`).

The verdict is a **conditional** sensitivity: operational governs at the reference inputs but
flips below the derived RM / c_mast breakevens. AoA_max is an *assumed* control target; the
robustness metrics (stability, slope, Scruton) are *reported*, not silent verdict inputs.
"""
from __future__ import annotations

import dataclasses

from wingmast_design.aero.feathering import (
    FeatheringConfig,
    crossover_aoa_deg,
    feathering_verdict,
    is_stable,
    restoring_margin_xc,
    scruton_number,
)
from wingmast_design.aero.operational import SailingConditions, op2
from wingmast_design.aero.survival import BareMast

OP2 = op2().design_bending_Nm


def test_baseline_is_stable_and_operational_at_reference():
    v = feathering_verdict(op2_bending_Nm=OP2)
    assert v.stable                                    # pivot 0.25c forward of effective AC 0.35c
    assert abs(v.restoring_margin_xc - 0.10) < 1e-9
    assert v.design_aoa_deg == 3.0                     # ASSUMED control target (not a model output)
    assert v.governing_case == "operational"


def test_derived_constraints_are_the_real_output():
    """The model's load-bearing outputs are the crossover + the RM/c_mast breakevens."""
    v = feathering_verdict(op2_bending_Nm=OP2)
    assert 3.5 < v.crossover_aoa_deg < 4.0             # survival overtakes OP-2 at ~3.7°
    assert v.crossover_aoa_deg > v.design_aoa_deg      # operational-governed, thin margin
    assert abs(v.breakeven_rm_Nm - 161.0e3) < 5.0e3    # RM below which it flips (D-1)
    assert abs(v.breakeven_c_mast_m - 1.24) < 0.05     # c_mast above which it flips (D-4)
    assert "RM ≥" in v.conditions and "c_mast ≤" in v.conditions


def test_verdict_flips_below_rm_breakeven():
    """Honest D-1 sensitivity: at the basis lower RM bracket (150) operational does NOT govern."""
    op2_lo = op2(dataclasses.replace(SailingConditions(), rm_max_Nm=150.0e3)).design_bending_Nm
    assert feathering_verdict(op2_bending_Nm=op2_lo).governing_case == "survival_fault"
    op2_hi = op2(dataclasses.replace(SailingConditions(), rm_max_Nm=200.0e3)).design_bending_Nm
    assert feathering_verdict(op2_bending_Nm=op2_hi).governing_case == "operational"


def test_verdict_flips_above_c_mast_breakeven():
    """Honest D-4 sensitivity: a larger bare-mast chord flips it survival-governed."""
    assert feathering_verdict(mast=BareMast(c_mast_m=1.0), op2_bending_Nm=OP2).governing_case == "operational"
    assert feathering_verdict(mast=BareMast(c_mast_m=1.4), op2_bending_Nm=OP2).governing_case == "survival_fault"


def test_loss_of_redundancy_flips_to_survival_fault():
    v = feathering_verdict(dataclasses.replace(FeatheringConfig(), redundant=False), op2_bending_Nm=OP2)
    assert v.design_aoa_deg == 12.0                    # a single-channel failure can reach the stop
    assert v.governing_case == "survival_fault"


def test_static_instability_locks_broadside():
    cfg = dataclasses.replace(FeatheringConfig(), vane_ac_shift_xc=0.0, pivot_xc=0.30)
    assert not is_stable(cfg)                           # pivot aft of the AC, no vane
    assert feathering_verdict(cfg, op2_bending_Nm=OP2).governing_case == "locked"


def test_restoring_requires_pivot_forward_of_effective_ac():
    fwd = dataclasses.replace(FeatheringConfig(), pivot_xc=0.20)
    aft = dataclasses.replace(FeatheringConfig(), pivot_xc=0.40, vane_ac_shift_xc=0.0)
    assert restoring_margin_xc(fwd) > 0 and is_stable(fwd)
    assert restoring_margin_xc(aft) < 0 and not is_stable(aft)


def test_scruton_uses_feathered_thickness_and_is_robust():
    """Corrected length scale: the feathered cross-stream dimension is the thickness
    (tc·c_mast), NOT the stock diameter — Sc ≈ 60 (robust), so VIV is not a feathered concern."""
    sc = scruton_number(FeatheringConfig(), BareMast(c_mast_m=1.0))
    assert sc > 30.0                                   # robust (≳ 10–20); the earlier ~4 was an artifact
    # a thicker / smaller-chord section sheds differently
    assert scruton_number(FeatheringConfig(), BareMast(c_mast_m=2.0)) < sc   # bigger D ⇒ lower Sc


def test_crossover_helper_matches_op2():
    import math

    from wingmast_design.aero.feathering import LIFT_SLOPE_PER_RAD
    from wingmast_design.aero.survival import survival_bending

    m = BareMast()
    a = crossover_aoa_deg(m, 1621.0, OP2)
    cl = LIFT_SLOPE_PER_RAD * math.radians(a)
    assert abs(survival_bending(1621.0, cl, m) - OP2) < 1.0e3
