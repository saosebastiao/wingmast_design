"""Phase-A.7 — the typed design-load collection / `G-2` deliverable (`R-AE-7`, parent `R-LOAD-1`)."""
from __future__ import annotations

import dataclasses

from wingmast_design.aero.design_cases import (
    DesignLoadCase,
    design_load_collection,
    governing_case,
)
from wingmast_design.aero.operational import SailingConditions
from wingmast_design.aero.survival import BareMast
from wingmast_design.load_cases import CaseCategory


def test_collection_has_the_five_typed_cases():
    coll = design_load_collection()
    assert [c.name for c in coll] == ["OP-1", "OP-2", "SURV-1", "SURV-1f", "SURV-2"]
    assert all(isinstance(c, DesignLoadCase) for c in coll)
    by = {c.name: c for c in coll}
    assert by["OP-1"].category is CaseCategory.OPERATIONAL
    assert by["SURV-1f"].category is CaseCategory.SURVIVAL


def test_magnitudes_reproduce_the_basis_bands():
    by = {c.name: c for c in design_load_collection()}
    assert abs(by["OP-1"].design_bending_Nm - 115e3) < 2e3
    assert abs(by["OP-2"].design_bending_Nm - 160e3) < 2e3
    assert 38e3 < by["SURV-1"].design_bending_Nm < 40e3
    assert 466e3 < by["SURV-1f"].design_bending_Nm < 476e3
    assert 730e3 < by["SURV-2"].design_bending_Nm < 890e3


def test_op2_governs_at_central_inputs():
    coll = design_load_collection()
    g = governing_case(coll)
    assert g.name == "OP-2"
    assert g.governs and g.category is CaseCategory.OPERATIONAL


def test_serviceability_gate_is_operational_only():
    for c in design_load_collection():
        assert c.serviceability_applies == (c.category is CaseCategory.OPERATIONAL)


def test_reserves_and_eigen_flags():
    by = {c.name: c for c in design_load_collection()}
    assert by["OP-2"].reserve_factor == 2.0          # R ≥ 2.0 operational
    assert by["SURV-1"].reserve_factor == 3.0        # FoS ≥ 3.0 survival
    assert by["SURV-1f"].reserve_factor == 1.5       # reduced FoS for the feathering fault (D-2)
    assert by["OP-2"].eigen_verify and by["SURV-1"].eigen_verify
    assert not by["OP-1"].eigen_verify               # deflection-governed, not buckling-critical


def test_governing_flag_is_conditional_on_d1_d4():
    """The governing case tracks the conditional D-2 verdict: low RM or large c_mast flips it."""
    lo_rm = design_load_collection(dataclasses.replace(SailingConditions(), rm_max_Nm=150e3))
    assert governing_case(lo_rm).name == "SURV-1f"   # survival-governed at the lower RM bracket
    big_mast = design_load_collection(mast=BareMast(c_mast_m=1.4))
    assert governing_case(big_mast).name == "SURV-1f"


def test_exactly_one_governing_case():
    import pytest

    coll = design_load_collection()
    assert sum(c.governs for c in coll) == 1
    # a degenerate collection with no governing case is rejected
    with pytest.raises(ValueError):
        governing_case(tuple(dataclasses.replace(c, governs=False) for c in coll))


# --- the headline guarantee: ADD an operational scenario and it propagates -----------

def test_added_scenario_seizes_governing():
    """Append one OperationalScenario → it flows into the collection AND can become the governing
    case (governing is by magnitude, not hardcoded OP-2). This is the 'repeatable' guarantee."""
    from wingmast_design.aero.operational import (
        OPERATIONAL_SCENARIOS,
        HeelingCeiling,
        OperationalScenario,
    )

    op3 = OperationalScenario("OP-3", split=0.85, ceiling=HeelingCeiling.rm_capped(),
                              eigen_verify=True, governs_eligible=True, note="heavy split")
    coll = design_load_collection(scenarios=(*OPERATIONAL_SCENARIOS, op3))
    names = [c.name for c in coll]
    assert "OP-3" in names                                   # propagated into the collection
    g = governing_case(coll)
    assert g.name == "OP-3"                                  # the heavier added case seized governing
    by = {c.name: c for c in coll}
    assert g.design_bending_Nm > by["OP-2"].design_bending_Nm


def test_added_q_limited_case_below_op2_does_not_govern():
    """A q-limited reaching case capped below OP-2 is present but does NOT falsely govern."""
    from wingmast_design.aero.operational import (
        OPERATIONAL_SCENARIOS,
        HeelingCeiling,
        OperationalScenario,
    )

    reach = OperationalScenario("OP-reach", split=0.60,
                                ceiling=HeelingCeiling.q_limited(q_Pa=220.0, area_m2=45.0, cl_drive=1.1),
                                note="reaching, q-limited")
    coll = design_load_collection(scenarios=(*OPERATIONAL_SCENARIOS, reach))
    assert "OP-reach" in [c.name for c in coll]
    assert governing_case(coll).name == "OP-2"               # OP-2 still governs


def test_non_eligible_scenario_never_governs():
    """A heavy scenario flagged governs_eligible=False is sized for but cannot be the governing case."""
    from wingmast_design.aero.operational import (
        OPERATIONAL_SCENARIOS,
        HeelingCeiling,
        OperationalScenario,
    )

    heavy = OperationalScenario("OP-X", split=0.95, ceiling=HeelingCeiling.rm_capped(),
                                governs_eligible=False, note="heavy but not eligible")
    coll = design_load_collection(scenarios=(*OPERATIONAL_SCENARIOS, heavy))
    assert governing_case(coll).name == "OP-2"               # OP-X heavier but not eligible
