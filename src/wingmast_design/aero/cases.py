"""Load-case envelope for the wingsail.

FROZEN LEGACY (shell-beam re-scope, 2026-06-16): this module now holds only the frozen
**dinghy `DESIGN_CASES` values** — apparent-wind operating points for the 5 m
demonstration wingsail. (The `LoadCase` *type* is forward and was moved to `aero.loads`;
this module imports it.) The Oyster-595 re-scope retired these values; they are no longer
exported from the `aero` forward API. New work uses the apparent-wind cases Phase A will
define plus the typed **structural** load collection in `wingmast_design.load_cases`.
The only remaining importer of these frozen values is the **bannered-legacy**
`scenario.py` default (retired in Phase A); `examples/02`/`03` import them directly. Do
not build forward (Oyster-595) work on this. See `docs/specs/00-rescope-groundwork/`
(`R-GND-1`).

`DESIGN_CASES` is sized for a 5 m demonstration wingsail on a small sailing dinghy.
"""
from __future__ import annotations

# `LoadCase` (the operating-point type) is forward and lives in `aero.loads`; only the
# concrete dinghy *values* below are frozen legacy. Importing the type from there (not
# the reverse) keeps the forward solver off this frozen module (`R-GND-1`).
from .loads import LoadCase

DESIGN_CASES: tuple[LoadCase, ...] = (
    LoadCase("nominal_trim",   airspeed_mps=10.0, alpha_deg=8.0,  description="10 m/s AWS, trimmed near best L/D"),
    LoadCase("max_aoa",        airspeed_mps=15.0, alpha_deg=12.0, description="Approaching stall at design AWS"),
    LoadCase("design_gust",    airspeed_mps=15.0, alpha_deg=8.0,  safety_factor=1.5, description="Trimmed + 1.5x gust factor"),
    LoadCase("survival",       airspeed_mps=25.0, alpha_deg=6.0,  description="Survival AWS, dumped AoA"),
    LoadCase("feathered",      airspeed_mps=25.0, alpha_deg=0.0,  description="Passively feathered in survival AWS"),
)
