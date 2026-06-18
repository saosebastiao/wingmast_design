"""AeroSandbox-backed aerodynamic loads on the wingsail.

The dinghy aerodynamic envelope (`cases.DESIGN_CASES` / `cases.LoadCase`) is
**frozen legacy** (the re-scope retired the dinghy operating points) and is no
longer part of this forward API — import it from `wingmast_design.aero.cases`
directly if you genuinely need the legacy cases. The Oyster-595 structural load
collection lives in `wingmast_design.load_cases` (`R-GND-1`).
"""
from .loads import (
    AeroResult,
    PanelLoads,
    run_case,
    run_case_lifting_line,
    sweep_envelope,
)
from .model import build_airplane, build_asb_wing
from .operational import (
    OPERATIONAL_SCENARIOS,
    CeilingKind,
    HeelingCeiling,
    OperationalLoad,
    OperationalScenario,
    SailingConditions,
    op1,
    op2,
    operational_load,
    operational_torque_Nm,
    resolve_operational,
    rm_sensitivity_band,
    scenario_torque_Nm,
)
from .survival import (
    BareMast,
    Q_CAT3,
    Q_CAT5,
    SurvivalLoad,
    dynamic_pressure,
    locked_broadside,
    surv1_feathered,
    surv1f_fault,
    surv2_cat5,
    survival_bending,
)
from .feathering import (
    FeatheringConfig,
    FeatheringVerdict,
    crossover_aoa_deg,
    feathering_verdict,
    is_stable,
    restoring_margin_xc,
    scruton_number,
)
from .design_cases import (
    DesignLoadCase,
    design_load_collection,
    governing_case,
)
from .load_vectors import (
    AeroBalance,
    DistributedMastLoad,
    nodal_load_vectors,
    operational_mast_load,
)

__all__ = [
    "AeroResult",
    "PanelLoads",
    "build_airplane",
    "build_asb_wing",
    "run_case",
    "run_case_lifting_line",
    "sweep_envelope",
    "OperationalLoad",
    "SailingConditions",
    "op1",
    "op2",
    "operational_load",
    "operational_torque_Nm",
    "rm_sensitivity_band",
    "OPERATIONAL_SCENARIOS",
    "CeilingKind",
    "HeelingCeiling",
    "OperationalScenario",
    "resolve_operational",
    "scenario_torque_Nm",
    "BareMast",
    "Q_CAT3",
    "Q_CAT5",
    "SurvivalLoad",
    "dynamic_pressure",
    "locked_broadside",
    "surv1_feathered",
    "surv1f_fault",
    "surv2_cat5",
    "survival_bending",
    "FeatheringConfig",
    "FeatheringVerdict",
    "crossover_aoa_deg",
    "feathering_verdict",
    "is_stable",
    "restoring_margin_xc",
    "scruton_number",
    "DesignLoadCase",
    "design_load_collection",
    "governing_case",
    "AeroBalance",
    "DistributedMastLoad",
    "nodal_load_vectors",
    "operational_mast_load",
]
