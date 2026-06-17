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

import math
from dataclasses import dataclass
from enum import Enum

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


# ---------------------------------------------------------------------------
# Extensible operational-scenario framework (`R-AE-1/2`). ADD an operational case by appending
# one `OperationalScenario` to `OPERATIONAL_SCENARIOS` (or pass `scenarios=` to
# `design_cases.design_load_collection`); the whole pipeline — bending, torque, category,
# reserve, eigen flag, and the GOVERNING-case selection — re-runs over it uniformly, and a
# heavier added case can seize the governing flag. Two heeling ceilings are first-class:
# RM-capped (equilibrium) and q-limited (wind-limited), COUPLED by `heeling = min(RM-share,
# aero-capacity)` so the righting-moment ceiling always binds (Article IV: never understate).
# ---------------------------------------------------------------------------


class CeilingKind(Enum):
    RM_CAPPED = "rm_capped"      # equilibrium ceiling: aero capacity unbounded, RM binds
    Q_LIMITED = "q_limited"      # wind-limited: capacity = q·area·cl_drive·heeling_lever


@dataclass(frozen=True)
class HeelingCeiling:
    """What caps the steady rig heeling moment for a scenario — a tagged union (not a callable)
    so the registry stays pure, inspectable data. New ceiling physics = a new `CeilingKind`."""

    kind: CeilingKind
    q_Pa: float = 0.0
    area_m2: float = 0.0
    cl_drive: float = 0.0

    @classmethod
    def rm_capped(cls) -> "HeelingCeiling":
        return cls(CeilingKind.RM_CAPPED)

    @classmethod
    def q_limited(cls, q_Pa: float, area_m2: float, cl_drive: float) -> "HeelingCeiling":
        return cls(CeilingKind.Q_LIMITED, q_Pa, area_m2, cl_drive)

    def aero_heeling_capacity_Nm(self, cond: SailingConditions) -> float:
        """Rig-level aero heeling moment the wind can produce (`math.inf` for RM_CAPPED — the
        righting moment is the binding ceiling there)."""
        if self.kind is CeilingKind.RM_CAPPED:
            return math.inf
        return self.q_Pa * self.area_m2 * self.cl_drive * cond.heeling_lever_m


@dataclass(frozen=True)
class OperationalScenario:
    """One operational operating point — THE registry entry. Add a new scenario by appending
    one of these. Category is always OPERATIONAL (stamped by the collection builder)."""

    name: str
    split: float                              # per-mast fore/aft load fraction
    ceiling: HeelingCeiling
    daf: float | None = None                  # override cond.daf; None → fall back
    cm_axis: float = -0.16                    # section moment coeff for this camber point (torque)
    torque_q_Pa: float = 74.0                 # torque operating point (D-4-dependent)
    torque_area_m2: float = 75.0
    torque_chord_m: float = 3.2
    eigen_verify: bool = True                 # n≥24 (`R-PERF-4`)
    governs_eligible: bool = True             # may be flagged the governing case
    note: str = ""


def resolve_operational(scen: OperationalScenario, cond: SailingConditions | None = None) -> OperationalLoad:
    """Resolve a scenario to its per-mast load. The steady heeling is the COUPLED ceiling
    ``min(split·RM_max, split·aero_capacity)`` — equilibrium always caps (Article IV); the
    q-limited ceiling only binds when the wind cannot drive the rig to the righting moment."""
    cond = cond or SailingConditions()
    rm_share = scen.split * cond.rm_max_Nm
    aero_share = scen.split * scen.ceiling.aero_heeling_capacity_Nm(cond)
    heeling = min(rm_share, aero_share)
    transverse = heeling / cond.heeling_lever_m
    base_static = transverse * cond.operational_arm_m
    daf = scen.daf if scen.daf is not None else cond.daf
    return OperationalLoad(
        name=scen.name, split=scen.split, heeling_moment_Nm=heeling,
        transverse_force_N=transverse, base_bending_static_Nm=base_static,
        design_bending_Nm=base_static * daf,
    )


def scenario_torque_Nm(scen: OperationalScenario, cond: SailingConditions | None = None) -> float:
    """Operational torque for a scenario's camber/operating point (`R-AE-5`) — per-scenario so a
    reaching/cambered point carries its own cm_axis + cambered area."""
    cond = cond or SailingConditions()
    daf = scen.daf if scen.daf is not None else cond.daf
    return scen.torque_q_Pa * scen.torque_area_m2 * scen.torque_chord_m * abs(scen.cm_axis) * daf


#: The standard operational scenarios. **APPEND** a new `OperationalScenario` here to add an
#: operational case — it flows through the whole pipeline. (OP-1/OP-2 reproduce basis §3.)
OPERATIONAL_SCENARIOS: tuple[OperationalScenario, ...] = (
    OperationalScenario("OP-1", split=SPLIT_NOMINAL, ceiling=HeelingCeiling.rm_capped(),
                        eigen_verify=False, governs_eligible=False,
                        note="50:50 nominal; deflection/twist-governing"),
    OperationalScenario("OP-2", split=SPLIT_WORST, ceiling=HeelingCeiling.rm_capped(),
                        eigen_verify=True, governs_eligible=True,
                        note="70:30 worst single mast; spar strength + buckling"),
)
_BY_NAME = {s.name: s for s in OPERATIONAL_SCENARIOS}


def op1(cond: SailingConditions | None = None) -> OperationalLoad:
    """OP-1: the 50:50 nominal operational case (deflection/twist-governing) — registry lookup."""
    return resolve_operational(_BY_NAME["OP-1"], cond)


def op2(cond: SailingConditions | None = None) -> OperationalLoad:
    """OP-2: the 70:30 worst-single-mast case — **governs the spar** (registry lookup)."""
    return resolve_operational(_BY_NAME["OP-2"], cond)


def operational_torque_Nm(q_Pa: float, area_m2: float, chord_m: float,
                          cond: SailingConditions | None = None, *, daf: bool = True) -> float:
    """Operational torque about the rotation axis: ``T = q·A·c·|Cm_axis|``. Sizes the ±45°
    torsion plies / twist / rotation bearing.

    The **absolute** value is `D-4`-dependent (the cambered operating area + chord, set in A.5).
    At the basis reference (q≈74 Pa, A≈75 m², c≈3.2 m) it gives **~2.84 kN·m static → ~4.3 kN·m
    design** (×DAF). Note the basis §3 line labels ~4.3 as "static" — that is actually the
    *design* (post-DAF) value; and its "~6–9 kN·m design" band needs a larger A·c (~363, ~1.5×)
    or a gust q≈104–156 Pa, to be reconciled when A.5 pins the distributed-torsion planform.
    """
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
