"""Operational sailboat load model — the righting-moment-capped load chain (`R-AE-1`,
parent `R-LOAD-1`, basis §3).

The binding ceiling on the operational rig load is **equilibrium, not wind**: the steady aero
heeling moment cannot exceed the hull's maximum righting moment ``RM_max``. So the per-mast
operational load is a fixed chain off ``RM_max`` and the load **split** (`R-AE-2`):

    heeling moment / mast = split · RM_max
    transverse aero force = (heeling moment / mast) / heeling_lever
    base/partners bending = transverse force · operational_arm           (static)
    design bending        = static · DAF                                 (`R-AE-6`)

Reproduces `docs/engineering_basis.md` §3 exactly: at RM_max = 200 kN·m, split 0.50 ⇒
**OP-1 ≈ 115 kN·m**, split 0.70 ⇒ **OP-2 ≈ 160 kN·m** (OP-2 governs the spar). ``RM_max`` is
the **dominant linear sensitivity** on every operational load (`D-1`/`D-AE-a`) — all OP-* scale
linearly with it; the central 200 kN·m carries a 150–225 bracket.

This is the operational chain only; the tandem slot split feeds it (`R-AE-2`), the survival
envelope is separate and analytical (`aero/survival.py`, `R-AE-3`), and the typed collection
assembles them (`R-AE-7`).
"""
from __future__ import annotations

from dataclasses import dataclass

#: Nominal (50:50) and worst-single-mast (70:30 forward:aft) operational splits (`R-AE-2`).
SPLIT_NOMINAL = 0.50      # OP-1
SPLIT_WORST = 0.70        # OP-2 (forward rig in true tandem)


@dataclass(frozen=True)
class SailingConditions:
    """The operational equilibrium parameters (basis §1–§3). All from `RM_max` down."""

    rm_max_Nm: float = 200.0e3        # whole-boat max righting moment (D-1; dominant sensitivity)
    heeling_lever_m: float = 14.0     # CE above WL + CLR below WL (the heeling-moment arm)
    operational_arm_m: float = 10.7   # CE above partners (the cantilever bending arm)
    daf: float = 1.5                  # gust/seaway dynamic amplification (R-AE-6)
    cm_axis: float = -0.16            # section moment coeff about the rotation axis (torque)


@dataclass(frozen=True)
class OperationalLoad:
    """The operational load for one mast at a given split."""

    name: str
    split: float
    heeling_moment_Nm: float          # per mast = split · RM_max
    transverse_force_N: float         # usable transverse aero force / mast
    base_bending_static_Nm: float     # at the partners, before DAF
    design_bending_Nm: float          # static · DAF — the sizing value


def operational_load(split: float, cond: SailingConditions, *, name: str = "") -> OperationalLoad:
    """The RM-capped operational load chain for one mast at the given load ``split``."""
    heeling = split * cond.rm_max_Nm
    transverse = heeling / cond.heeling_lever_m
    base_static = transverse * cond.operational_arm_m
    design = base_static * cond.daf
    return OperationalLoad(
        name=name or f"op_split_{split:.2f}",
        split=split,
        heeling_moment_Nm=heeling,
        transverse_force_N=transverse,
        base_bending_static_Nm=base_static,
        design_bending_Nm=design,
    )


def op1(cond: SailingConditions | None = None) -> OperationalLoad:
    """OP-1: the 50:50 nominal operational case (deflection/twist-governing)."""
    return operational_load(SPLIT_NOMINAL, cond or SailingConditions(), name="OP-1")


def op2(cond: SailingConditions | None = None) -> OperationalLoad:
    """OP-2: the 70:30 worst-single-mast case — **governs the spar** (strength + buckling)."""
    return operational_load(SPLIT_WORST, cond or SailingConditions(), name="OP-2")


def operational_torque_Nm(q_Pa: float, area_m2: float, chord_m: float,
                          cond: SailingConditions | None = None, *, daf: bool = True) -> float:
    """Operational torque about the rotation axis: ``T = q·A·c·|Cm_axis|`` (basis §3 ⇒ ~4.3 kN·m
    static, ~6–9 kN·m design). Sizes the ±45° torsion plies / twist / rotation bearing."""
    cond = cond or SailingConditions()
    t_static = q_Pa * area_m2 * chord_m * abs(cond.cm_axis)
    return t_static * (cond.daf if daf else 1.0)


def rm_sensitivity_band(split: float, cond: SailingConditions | None = None,
                        rm_lo_Nm: float = 150.0e3, rm_hi_Nm: float = 225.0e3) -> tuple[float, float]:
    """Design bending at the (lower, upper) RM bracket — the dominant-sensitivity band (`D-1`).
    Every operational load scales **linearly** with ``RM_max``."""
    import dataclasses

    cond = cond or SailingConditions()
    lo = operational_load(split, dataclasses.replace(cond, rm_max_Nm=rm_lo_Nm)).design_bending_Nm
    hi = operational_load(split, dataclasses.replace(cond, rm_max_Nm=rm_hi_Nm)).design_bending_Nm
    return (lo, hi)
