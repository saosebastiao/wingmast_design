"""The typed design-load collection — the `G-2` deliverable (`R-AE-7`, parent `R-LOAD-1`).

Assembles the operational (`aero/operational.py`) and survival (`aero/survival.py`) envelopes
into one **named, categorised** collection — **OP-1 / OP-2 / SURV-1 / SURV-1f / SURV-2** — that
Phases S and O size against. Each case carries its per-mast design bending + torque, its
**category** (reusing the Phase-0 `load_cases.CaseCategory` — operational serviceability+ultimate
vs survival ultimate-only), the required **reserve** (`R-PERF-1`: R ≥ 2.0 operational / FoS ≥ 3.0
survival; the feathering fault carries a *reduced* FoS), an **eigen-verify** flag (`R-PERF-4`:
n ≥ 24 for the governing/fault/survival cases), and the **governing** flag (from the conditional
D-2 verdict, `aero/feathering.py`).

The magnitudes reproduce `engineering_basis.md` §3–§4. The governing case is OP-2 **at central
inputs** (RM 200, c_mast 1.0) — but it is conditional: see `feathering_verdict` for the RM /
c_mast breakevens where it flips. This is the aero half of each design case; the body-load half
(gravity/heel, `load_cases.StructuralLoadCase`) is applied with it by the Phase-S FEA.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass

from ..load_cases import CaseCategory
from .feathering import FeatheringConfig, feathering_verdict
from .operational import (
    OPERATIONAL_SCENARIOS,
    OperationalScenario,
    SailingConditions,
    op2,
    resolve_operational,
    scenario_torque_Nm,
)
from .survival import BareMast, surv1_feathered, surv1f_fault, surv2_cat5


@dataclass(frozen=True)
class DesignLoadCase:
    """One typed design-load case (the aero half). Lengths in N·m."""

    name: str
    category: CaseCategory
    design_bending_Nm: float          # per-mast design bending (static × DAF / hurricane q × C)
    design_torque_Nm: float           # torque about the rotation axis (operational; ~0 survival)
    reserve_factor: float             # required reserve: R ≥ 2.0 op / FoS ≥ 3.0 survival / reduced fault
    eigen_verify: bool                # n ≥ 24 required (R-PERF-4)
    governs: bool                     # the governing case for the spar (conditional D-2)
    note: str = ""

    @property
    def serviceability_applies(self) -> bool:
        """Deflection/twist limits apply iff operational (Article IV, via `CaseCategory`)."""
        return self.category.serviceability_applies


#: Survival reserve (FoS ≥ 3.0) and operational reserve (R ≥ 2.0) — stamped here so the
#: reserve policy is single-sourced (not per-scenario).
_OP_RESERVE = 2.0
_SURV_RESERVE = 3.0


def design_load_collection(cond: SailingConditions | None = None,
                           mast: BareMast | None = None, *,
                           cfg: FeatheringConfig | None = None,
                           fault_fos: float = 1.5,
                           scenarios: tuple[OperationalScenario, ...] | None = None,
                           ) -> tuple[DesignLoadCase, ...]:
    """The typed design-load collection, governing case flagged. Pass / append to ``scenarios``
    (default `OPERATIONAL_SCENARIOS`) to **add** an operational case — it flows through the whole
    pipeline and a heavier added case can seize the governing flag (`R-AE-7`)."""
    cond = cond or SailingConditions()
    mast = mast or BareMast()
    scenarios = scenarios if scenarios is not None else OPERATIONAL_SCENARIOS

    op_cases = [
        DesignLoadCase(s.name, CaseCategory.OPERATIONAL,
                       resolve_operational(s, cond).design_bending_Nm, scenario_torque_Nm(s, cond),
                       reserve_factor=_OP_RESERVE, eigen_verify=s.eigen_verify, governs=False,
                       note=s.note)
        for s in scenarios
    ]
    s1, sf, s2 = surv1_feathered(mast)[1], surv1f_fault(mast)[1], surv2_cat5(mast)[1]
    surv_cases = [
        DesignLoadCase("SURV-1", CaseCategory.SURVIVAL, s1.bending_Nm, 0.0,
                       reserve_factor=_SURV_RESERVE, eigen_verify=True, governs=False,
                       note="bare mast feathered ~0°; below operational"),
        DesignLoadCase("SURV-1f", CaseCategory.SURVIVAL, sf.bending_Nm, 0.0,
                       reserve_factor=fault_fos, eigen_verify=True, governs=False,
                       note=f"feathering-fault off-axis; reduced FoS {fault_fos} (D-2 reliable-feathering)"),
        DesignLoadCase("SURV-2", CaseCategory.SURVIVAL, s2.bending_Nm, 0.0,
                       reserve_factor=_SURV_RESERVE, eigen_verify=True, governs=False,
                       note="Cat-5 off-axis bound; ultimate sensitivity"),
    ]
    cases = (*op_cases, *surv_cases)

    # The D-2 crossover/breakevens are calibrated against OP-2; keep that wiring. Only the
    # governing FLAG is generalised to max-bending-among-eligible (so an added case can win).
    verdict = feathering_verdict(cfg, mast=mast, op2_bending_Nm=op2(cond).design_bending_Nm,
                                 fault_fos=fault_fos)
    return _flag_governing(cases, verdict.governing_case, scenarios)


def _flag_governing(cases: tuple[DesignLoadCase, ...], verdict: str,
                    scenarios: tuple[OperationalScenario, ...]) -> tuple[DesignLoadCase, ...]:
    """Set the single ``governs`` flag from the conditional D-2 verdict: when operational-governed,
    the heaviest **governs-eligible** operational case wins (magnitude, not position) — so an added
    scenario can seize it; otherwise the feathering fault (`SURV-1f`) governs."""
    if verdict == "operational":
        eligible = {s.name for s in scenarios if s.governs_eligible}
        op = [c for c in cases if c.category is CaseCategory.OPERATIONAL and c.name in eligible]
        winner = max(op, key=lambda c: c.design_bending_Nm).name if op else None
    else:  # survival_fault | locked → the off-axis survival fault is the governing case
        winner = "SURV-1f"
    return tuple(dataclasses.replace(c, governs=(c.name == winner)) for c in cases)


def governing_case(collection: tuple[DesignLoadCase, ...]) -> DesignLoadCase:
    """The single governing case (exactly one is flagged ``governs``)."""
    gov = [c for c in collection if c.governs]
    if len(gov) != 1:
        raise ValueError(f"expected exactly one governing case, got {[c.name for c in gov]}")
    return gov[0]
