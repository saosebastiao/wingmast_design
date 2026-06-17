"""Phase-A.4 — feathering-robustness model / decision gate D-2 (`R-AE-4`, parent `R-LOAD-2a/2b`)."""
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
from wingmast_design.aero.operational import op2
from wingmast_design.aero.survival import BareMast

OP2 = op2().design_bending_Nm


def test_baseline_is_stable_and_operational_governed():
    v = feathering_verdict(op2_bending_Nm=OP2)
    assert v.stable                                    # pivot 0.25c forward of effective AC 0.35c
    assert abs(v.restoring_margin_xc - 0.10) < 1e-9
    assert v.aoa_max_deg == 3.0                        # small steady excursion (reliable control)
    assert v.governing_case == "operational"           # the D-2 chosen stance


def test_crossover_margin_is_thin():
    """An honest D-2 sensitivity: operational governs only while AoA_max < the crossover AoA,
    and the margin is small (~0.7°) — feathering must hold AoA below it."""
    v = feathering_verdict(op2_bending_Nm=OP2)
    assert 3.5 < v.crossover_aoa_deg < 4.0
    assert v.crossover_aoa_deg > v.aoa_max_deg         # operational-governed...
    assert (v.crossover_aoa_deg - v.aoa_max_deg) < 1.5  # ...but with little headroom


def test_loss_of_redundancy_flips_to_survival_fault():
    v = feathering_verdict(dataclasses.replace(FeatheringConfig(), redundant=False), op2_bending_Nm=OP2)
    assert v.aoa_max_deg == 12.0                       # a single-channel failure can reach the stop
    assert v.governing_case == "survival_fault"


def test_static_instability_locks_broadside():
    cfg = dataclasses.replace(FeatheringConfig(), vane_ac_shift_xc=0.0, pivot_xc=0.30)
    assert not is_stable(cfg)                           # pivot aft of the AC, no vane
    v = feathering_verdict(cfg, op2_bending_Nm=OP2)
    assert v.aoa_max_deg == 90.0
    assert v.governing_case == "locked"


def test_restoring_requires_pivot_forward_of_effective_ac():
    fwd = dataclasses.replace(FeatheringConfig(), pivot_xc=0.20)   # well forward
    aft = dataclasses.replace(FeatheringConfig(), pivot_xc=0.40, vane_ac_shift_xc=0.0)
    assert restoring_margin_xc(fwd) > 0 and is_stable(fwd)
    assert restoring_margin_xc(aft) < 0 and not is_stable(aft)


def test_scruton_number_flags_viv_susceptibility():
    # Sc = 2·m·ζ/(ρ·D²); the baseline (~4) is LOW (robust ≳ 10–20) — VIV is a real concern.
    sc = scruton_number(FeatheringConfig())
    assert 3.0 < sc < 6.0
    # more mass + damping raises it (2× mass × 2× damping ⇒ ~4×)
    stiff = dataclasses.replace(FeatheringConfig(), mass_per_len_kgm=120.0, structural_damping_ratio=0.04)
    assert scruton_number(stiff) > 3.0 * sc


def test_crossover_helper_matches_op2():
    import math

    from wingmast_design.aero.feathering import LIFT_SLOPE_PER_RAD
    from wingmast_design.aero.survival import survival_bending

    m = BareMast()
    a = crossover_aoa_deg(m, 1621.0, OP2)
    cl = LIFT_SLOPE_PER_RAD * math.radians(a)
    assert abs(survival_bending(1621.0, cl, m) - OP2) < 1.0e3   # at the crossover, survival == OP-2
