"""Feathering-robustness model — the **decision gate D-2** (`R-AE-4`, parent `R-LOAD-2a/2b`).

This is the project's **largest mass swing**: whether the free-rotating bare mast reliably
weathervanes into the wind (feathered ⇒ drag-dominated ⇒ **OP-2 governs**, light) or can be
caught off-axis (lift-dominated ⇒ **SURV-1f governs**, several-fold heavier). The gate fixes
the credible maximum off-axis angle ``AoA_max`` the structure is sized to, and reports the
robustness metrics that justify it.

**Analytical/engineering baseline** (`D-AE-d`) — CFD / unsteady aeroelastic is a flagged
follow-up (`OUT-3`), not a Phase-A blocker. The model:

  * **static restoring margin** — the pivot must sit *forward* of the bare section's effective
    aerodynamic centre (the trailing vane moves it aft) → a positive yaw-**restoring** moment
    that drives the mast back to 0° (weathervane);
  * **vane restoring slope** ``dM/dα`` about the pivot;
  * **VIV** — the Scruton number (high ⇒ vortex-shedding lock-in resistant);
  * **AoA_max** — bounded by the mechanical AoA stop when stable + redundant; 90° (broadside)
    if statically unstable;
  * **governing verdict** — compares the survival bending at ``AoA_max`` (and the reduced-FoS
    fault) against OP-2.

Defaults encode the **reliable-feathering baseline** (`D-2` chosen stance): pivot 0.25c, a
trailing vane, redundant active+passive control, AoA stops ⇒ operational-governed.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .survival import RHO_AIR, BareMast, survival_bending

QUARTER_CHORD = 0.25         # symmetric-section aerodynamic centre (x/c)
LIFT_SLOPE_PER_RAD = 2.0 * math.pi   # thin-airfoil dCl/dα


@dataclass(frozen=True)
class FeatheringConfig:
    """Feathering-mechanism design (reliable-feathering baseline defaults)."""

    pivot_xc: float = 0.25                 # rotation axis on the chord
    bare_ac_xc: float = QUARTER_CHORD      # bare-section aerodynamic centre
    vane_ac_shift_xc: float = 0.10         # aft shift of the effective AC from a trailing vane
    design_aoa_deg: float = 3.0            # credible STEADY off-axis excursion (reliable control)
    aoa_stop_deg: float = 12.0             # mechanical AoA stop (the fault bound)
    redundant: bool = True                 # active AoA control + passive trailing vane
    structural_damping_ratio: float = 0.02
    mass_per_len_kgm: float = 60.0         # bare-mast mass/length (Scruton)
    diameter_m: float = 0.7                # cross-stream dimension (≈ stock dia) for VIV


@dataclass(frozen=True)
class FeatheringVerdict:
    stable: bool
    restoring_margin_xc: float             # (effective AC − pivot)/c; > 0 ⇒ weathervaning
    aoa_max_deg: float
    crossover_aoa_deg: float               # AoA where survival lift = OP-2 (operational-governed below)
    vane_restoring_slope_Nm_per_deg: float  # dM/dα about the pivot (negative ⇒ restoring)
    yaw_damping_ratio: float
    scruton_number: float
    fault_fos: float                       # FoS the SURV-1f fault is carried at (D-2 reduced)
    governing_case: str                    # operational | survival_fault | locked


def restoring_margin_xc(cfg: FeatheringConfig) -> float:
    """(effective AC − pivot)/c. Positive ⇒ pivot forward of the AC ⇒ yaw-restoring."""
    eff_ac = cfg.bare_ac_xc + cfg.vane_ac_shift_xc
    return eff_ac - cfg.pivot_xc


def is_stable(cfg: FeatheringConfig) -> bool:
    return restoring_margin_xc(cfg) > 0.0


def vane_restoring_slope(cfg: FeatheringConfig, q_Pa: float, mast: BareMast) -> float:
    """dM/dα about the pivot, per **degree** (negative ⇒ restoring). ``M = q·A·c·dCl/dα·margin``."""
    area = mast.area_m2
    margin_m = restoring_margin_xc(cfg) * mast.c_mast_m
    slope_per_rad = -q_Pa * area * LIFT_SLOPE_PER_RAD * margin_m
    return slope_per_rad * math.pi / 180.0


def scruton_number(cfg: FeatheringConfig) -> float:
    """Sc = 2·m·ζ / (ρ·D²) — VIV lock-in resistance (higher is better; ≳ 10–20 is robust)."""
    return 2.0 * cfg.mass_per_len_kgm * cfg.structural_damping_ratio / (RHO_AIR * cfg.diameter_m ** 2)


def aoa_max_deg(cfg: FeatheringConfig) -> float:
    """Credible maximum off-axis AoA the structure is sized to: the small steady excursion
    when stable **and** redundant (reliable control holds it near 0°); the mechanical AoA stop
    when stable but single-channel (a failure can reach the stop); 90° (broadside) if
    statically unstable."""
    if not is_stable(cfg):
        return 90.0
    return cfg.design_aoa_deg if cfg.redundant else cfg.aoa_stop_deg


def crossover_aoa_deg(mast: BareMast, q_Pa: float, op2_bending_Nm: float) -> float:
    """The off-axis AoA at which the bare-mast lift bending equals OP-2 — operational governs
    only while ``AoA_max`` stays below this. A key D-2 robustness margin."""
    cl_cross = op2_bending_Nm / (q_Pa * mast.area_m2 * mast.arm_m)
    return math.degrees(min(cl_cross, 1.2) / LIFT_SLOPE_PER_RAD)


def feathering_verdict(cfg: FeatheringConfig | None = None, *,
                       mast: BareMast | None = None, q_Pa: float = 1621.0,
                       op2_bending_Nm: float = 160.5e3, fault_fos: float = 1.5) -> FeatheringVerdict:
    """Resolve the D-2 gate: AoA_max + the governing-case verdict for a given mechanism.

    ``fault_fos`` is the (reduced) FoS the SURV-1f fault is carried at under the
    reliable-feathering baseline (redundancy lets it be < the 3.0 survival FoS).
    """
    cfg = cfg or FeatheringConfig()
    mast = mast or BareMast()
    stable = is_stable(cfg)
    aoa_max = aoa_max_deg(cfg)
    crossover = crossover_aoa_deg(mast, q_Pa, op2_bending_Nm)

    # survival bending at AoA_max: small-angle lift (Cl ≈ dCl/dα · α, capped at the fault Cl).
    cl_at_max = min(LIFT_SLOPE_PER_RAD * math.radians(aoa_max), 1.2)
    bending_at_max = survival_bending(q_Pa, cl_at_max, mast)

    if not stable:
        governing = "locked"
    elif bending_at_max < op2_bending_Nm:
        governing = "operational"          # OP-2 governs; the off-axis fault is a reduced-FoS check
    else:
        governing = "survival_fault"

    return FeatheringVerdict(
        stable=stable,
        restoring_margin_xc=restoring_margin_xc(cfg),
        aoa_max_deg=aoa_max,
        crossover_aoa_deg=crossover,
        vane_restoring_slope_Nm_per_deg=vane_restoring_slope(cfg, q_Pa, mast),
        yaw_damping_ratio=cfg.structural_damping_ratio,
        scruton_number=scruton_number(cfg),
        fault_fos=fault_fos,
        governing_case=governing,
    )
