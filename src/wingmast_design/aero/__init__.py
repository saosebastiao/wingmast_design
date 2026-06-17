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

__all__ = [
    "AeroResult",
    "PanelLoads",
    "build_airplane",
    "build_asb_wing",
    "run_case",
    "run_case_lifting_line",
    "sweep_envelope",
]
