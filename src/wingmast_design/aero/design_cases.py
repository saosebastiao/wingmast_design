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

from dataclasses import dataclass

from ..load_cases import CaseCategory
from .feathering import FeatheringConfig, feathering_verdict
from .operational import SailingConditions, op1, op2, operational_torque_Nm
from .survival import BareMast, surv1_feathered, surv1f_fault, surv2_cat5

#: Reference cambered-wingsail operating point for the operational torque (D-4-dependent).
_TORQUE_Q_PA = 74.0
_TORQUE_AREA_M2 = 75.0
_TORQUE_CHORD_M = 3.2


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


def design_load_collection(cond: SailingConditions | None = None,
                           mast: BareMast | None = None, *,
                           cfg: FeatheringConfig | None = None,
                           fault_fos: float = 1.5) -> tuple[DesignLoadCase, ...]:
    """The OP-1/OP-2/SURV-1/SURV-1f/SURV-2 typed collection, with the governing case flagged."""
    cond = cond or SailingConditions()
    mast = mast or BareMast()
    o1, o2 = op1(cond), op2(cond)
    torque = operational_torque_Nm(_TORQUE_Q_PA, _TORQUE_AREA_M2, _TORQUE_CHORD_M, cond)
    s1 = surv1_feathered(mast)[1]      # design = upper drag coeff
    sf = surv1f_fault(mast)[1]
    s2 = surv2_cat5(mast)[1]

    verdict = feathering_verdict(cfg, mast=mast, op2_bending_Nm=o2.design_bending_Nm, fault_fos=fault_fos)
    gov = verdict.governing_case       # "operational" ⇒ OP-2 governs (conditional)

    return (
        DesignLoadCase("OP-1", CaseCategory.OPERATIONAL, o1.design_bending_Nm, torque,
                       reserve_factor=2.0, eigen_verify=False, governs=False,
                       note="50:50 nominal; deflection/twist-governing"),
        DesignLoadCase("OP-2", CaseCategory.OPERATIONAL, o2.design_bending_Nm, torque,
                       reserve_factor=2.0, eigen_verify=True, governs=(gov == "operational"),
                       note="70:30 worst single mast; spar strength + buckling"),
        DesignLoadCase("SURV-1", CaseCategory.SURVIVAL, s1.bending_Nm, 0.0,
                       reserve_factor=3.0, eigen_verify=True, governs=False,
                       note="bare mast feathered ~0°; below operational"),
        DesignLoadCase("SURV-1f", CaseCategory.SURVIVAL, sf.bending_Nm, 0.0,
                       reserve_factor=fault_fos, eigen_verify=True, governs=(gov == "survival_fault"),
                       note=f"feathering-fault off-axis; reduced FoS {fault_fos} (D-2 reliable-feathering)"),
        DesignLoadCase("SURV-2", CaseCategory.SURVIVAL, s2.bending_Nm, 0.0,
                       reserve_factor=3.0, eigen_verify=True, governs=False,
                       note="Cat-5 off-axis bound; ultimate sensitivity"),
    )


def governing_case(collection: tuple[DesignLoadCase, ...]) -> DesignLoadCase:
    """The single governing case (exactly one is flagged ``governs``)."""
    gov = [c for c in collection if c.governs]
    if len(gov) != 1:
        raise ValueError(f"expected exactly one governing case, got {[c.name for c in gov]}")
    return gov[0]
