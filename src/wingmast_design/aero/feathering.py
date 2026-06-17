"""Feathering-robustness model — the **decision gate D-2** (`R-AE-4`, parent `R-LOAD-2a/2b`).

This is the project's **largest mass swing**: whether the free-rotating bare mast reliably
weathervanes into the wind (feathered ⇒ drag-dominated ⇒ **OP-2 governs**, light) or can be
caught off-axis (lift-dominated ⇒ **SURV-1f governs**, several-fold heavier).

**Honest framing (the model is a *conditional* sensitivity, not a closed verdict).** The
load-bearing OUTPUTS the model genuinely *derives* are constraints:

  * **`crossover_aoa`** — the off-axis AoA at which the bare-mast lift bending equals OP-2;
    operational governs only while the steady AoA stays below it (~3.7° at the reference);
  * **`breakeven_rm`** / **`breakeven_c_mast`** — the `D-1` righting moment *below* which, and
    the `D-4` bare-mast chord *above* which, the verdict flips to survival-governed.

The **`design_aoa`** the structure is sized to is an **ASSUMED control target** (a requirement
on the feathering system), *not* a model output; and the reported robustness metrics —
**static stability** (pivot forward of the effective AC), the **restoring slope**, the **yaw
damping**, the **Scruton number** — *inform whether that target is achievable* but do **not**
by themselves close the verdict. So the headline "operational governs" is **conditional**:
it holds at the reference inputs (RM 200, c_mast 1.0, AoA ≤ crossover) and the model reports
the boundaries where it stops holding. CFD / unsteady-aeroelastic confirmation is a flagged
follow-up (`D-AE-d`, `OUT-3`).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .survival import RHO_AIR, BareMast, survival_bending

QUARTER_CHORD = 0.25                  # symmetric-section aerodynamic centre (x/c)
LIFT_SLOPE_PER_RAD = 2.0 * math.pi    # thin-airfoil dCl/dα
_REF_RM_Nm = 200.0e3                   # reference RM the supplied OP-2 bending corresponds to


@dataclass(frozen=True)
class FeatheringConfig:
    """Feathering-mechanism design. The defaults encode the reliable-feathering baseline; the
    ``*_assumed`` fields are design TARGETS / requirements, not derived quantities."""

    pivot_xc: float = 0.25                 # rotation axis on the chord
    bare_ac_xc: float = QUARTER_CHORD      # bare-section aerodynamic centre
    vane_ac_shift_xc: float = 0.10         # ASSUMED trailing-vane aft shift of the effective AC
    design_aoa_deg: float = 3.0            # ASSUMED steady control target (a requirement, not output)
    aoa_stop_deg: float = 12.0             # mechanical AoA stop (the fault bound)
    redundant: bool = True                 # active AoA control + passive trailing vane
    structural_damping_ratio: float = 0.02
    mass_per_len_kgm: float = 60.0         # bare-mast mass/length (Scruton)
    section_tc: float = 0.18               # thickness ratio — sets the cross-stream VIV dimension


@dataclass(frozen=True)
class FeatheringVerdict:
    # --- reported robustness metrics (inform feasibility; NOT verdict inputs) ---
    stable: bool
    restoring_margin_xc: float             # (effective AC − pivot)/c; > 0 ⇒ weathervaning
    vane_restoring_slope_Nm_per_deg: float  # dM/dα about the pivot (negative ⇒ restoring)
    yaw_damping_ratio: float
    scruton_feathered: float               # 2mζ/(ρ·(tc·c_mast)²) — feathered cross-stream dim
    # --- assumed design target ---
    design_aoa_deg: float                  # the AoA the structure is sized to (an ASSUMPTION)
    # --- DERIVED constraints (the model's real outputs) ---
    crossover_aoa_deg: float               # AoA where survival lift = OP-2 (operational below it)
    breakeven_rm_Nm: float                 # RM below which survival_fault governs (D-1)
    breakeven_c_mast_m: float              # c_mast above which survival_fault governs (D-4)
    fault_fos: float                       # FoS the SURV-1f fault is carried at (D-2 reduced)
    # --- conditional verdict (at the reference inputs) ---
    governing_case: str                    # operational | survival_fault | locked
    conditions: str                        # the conditions under which 'operational' holds


def restoring_margin_xc(cfg: FeatheringConfig) -> float:
    """(effective AC − pivot)/c. Positive ⇒ pivot forward of the AC ⇒ yaw-restoring."""
    return (cfg.bare_ac_xc + cfg.vane_ac_shift_xc) - cfg.pivot_xc


def is_stable(cfg: FeatheringConfig) -> bool:
    return restoring_margin_xc(cfg) > 0.0


def vane_restoring_slope(cfg: FeatheringConfig, q_Pa: float, mast: BareMast) -> float:
    """dM/dα about the pivot, per **degree** (negative ⇒ restoring). ``M = q·A·dCl/dα·margin``."""
    margin_m = restoring_margin_xc(cfg) * mast.c_mast_m
    slope_per_rad = -q_Pa * mast.area_m2 * LIFT_SLOPE_PER_RAD * margin_m
    return slope_per_rad * math.pi / 180.0


def scruton_number(cfg: FeatheringConfig, mast: BareMast | None = None) -> float:
    """Sc = 2·m·ζ / (ρ·D²), D = the cross-stream dimension exposed in the assessed regime.

    For the **feathered** design regime the section is edge-on, so D = the thickness
    ``section_tc · c_mast`` (NOT the internal stock diameter) — this is the dimension that
    sheds vortices. With the streamlined thickness the baseline Sc is **~60 (robust)**, not the
    ~4 a stock-diameter length scale wrongly implied. (Broadside/locked would use D = c_mast.)
    """
    mast = mast or BareMast()
    d = cfg.section_tc * mast.c_mast_m
    return 2.0 * cfg.mass_per_len_kgm * cfg.structural_damping_ratio / (RHO_AIR * d * d)


def aoa_max_deg(cfg: FeatheringConfig) -> float:
    """The AoA the structure is sized to: the assumed steady control target when stable **and**
    redundant; the mechanical AoA stop when stable but single-channel (a failure can reach it);
    90° (broadside) if statically unstable. (The first is an ASSUMPTION, not a derived value.)"""
    if not is_stable(cfg):
        return 90.0
    return cfg.design_aoa_deg if cfg.redundant else cfg.aoa_stop_deg


def crossover_aoa_deg(mast: BareMast, q_Pa: float, op2_bending_Nm: float) -> float:
    """DERIVED: the off-axis AoA at which bare-mast lift bending equals OP-2 — operational
    governs only while the steady AoA stays below this."""
    cl_cross = op2_bending_Nm / (q_Pa * mast.area_m2 * mast.arm_m)
    return math.degrees(min(cl_cross, 1.2) / LIFT_SLOPE_PER_RAD)


def feathering_verdict(cfg: FeatheringConfig | None = None, *,
                       mast: BareMast | None = None, q_Pa: float = 1621.0,
                       op2_bending_Nm: float = 160.5e3, fault_fos: float = 1.5) -> FeatheringVerdict:
    """Resolve the D-2 gate as a **conditional** verdict. ``op2_bending_Nm`` is OP-2 at the
    reference RM (200 kN·m); the verdict reports the RM/c_mast boundaries where it flips."""
    cfg = cfg or FeatheringConfig()
    mast = mast or BareMast()
    stable = is_stable(cfg)
    aoa_max = aoa_max_deg(cfg)
    crossover = crossover_aoa_deg(mast, q_Pa, op2_bending_Nm)

    # survival bending at the sized AoA (small-angle lift, capped at the fault Cl)
    cl_at_max = min(LIFT_SLOPE_PER_RAD * math.radians(aoa_max), 1.2)
    bending_at_max = survival_bending(q_Pa, cl_at_max, mast)

    # DERIVED breakevens (OP-2 ∝ RM; survival ∝ c_mast ⇒ A_mast):
    #   operational governs iff bending_at_max < OP-2(RM)  and  survival ∝ c_mast < OP-2
    breakeven_rm = _REF_RM_Nm * bending_at_max / op2_bending_Nm
    breakeven_c_mast = mast.c_mast_m * op2_bending_Nm / bending_at_max if bending_at_max > 0 else float("inf")

    if not stable:
        governing = "locked"
    elif bending_at_max < op2_bending_Nm:
        governing = "operational"          # at the reference; conditional on the breakevens below
    else:
        governing = "survival_fault"

    conditions = (
        f"operational governs while: steady AoA ≤ {crossover:.1f}° (design target {aoa_max:.0f}°), "
        f"RM ≥ {breakeven_rm / 1e3:.0f} kN·m (D-1), and c_mast ≤ {breakeven_c_mast:.2f} m (D-4)"
    )

    return FeatheringVerdict(
        stable=stable,
        restoring_margin_xc=restoring_margin_xc(cfg),
        vane_restoring_slope_Nm_per_deg=vane_restoring_slope(cfg, q_Pa, mast),
        yaw_damping_ratio=cfg.structural_damping_ratio,
        scruton_feathered=scruton_number(cfg, mast),
        design_aoa_deg=aoa_max,
        crossover_aoa_deg=crossover,
        breakeven_rm_Nm=breakeven_rm,
        breakeven_c_mast_m=breakeven_c_mast,
        fault_fos=fault_fos,
        governing_case=governing,
        conditions=conditions,
    )
