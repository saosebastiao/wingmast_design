# Plan — Re-scope groundwork (Phase 0)

**Parent spec:** `./spec.md`

## Reuse (from the audit verdicts — `docs/plan.md`)

- **Keep:** the FEM core, materials, NLP scaffolding, `viz/vtu`, export/multistart runners,
  ParaView `shell_fea`, tests — untouched by Phase 0 except the camera seam (`R-GND-8`).
- **Refactor:** `scenario.py` (drop the dinghy `LoadCase` dependency; add/host the typed
  structural load collection — `R-GND-5/6`); `paraview/_common.py` (span-derived camera —
  `R-GND-8`). Promote `build_sections_from_result` + the `runs/` constants/builders into
  `src/` (`R-GND-6/7`).
- **New (`src/`):** `StructuralLoadCase` type + a structural load-case collection module;
  a `build_assembly(sized_result) -> Compound` entry point; the promoted
  `build_sections_from_result`.
- **Retire (decouple + archive, not delete):** `aero/cases.py` (`R-GND-1`),
  `structural/beam.py` (`R-GND-2`); designate `truss/*` archived-analysis-only (`R-GND-3`).

## Steps

1. **Inventory & pin the green baseline.** Run `just test`; record the passing count +
   measured wall-clock as the before-state (every later step must hold this green).
2. **`R-GND-5/6` — typed structural layer (do this first; it unblocks the decouple).**
   Add `StructuralLoadCase` (accel vector(s), gravity, heel, datum, SF, `category` ∈
   {operational, survival, manufacturing}) and a collection in `src/`. Host the
   `runs/chain_rebuild.py` literals (`G0`, `TH`, `ACCELS`, `SF`, `DATUM`) here **byte-
   identically** (`D-GND-b`). Decide `Scenario`-extends-`DesignParameters` vs new sibling.
3. **`R-GND-7` — promote builders.** Move `build_sections_from_result` and add
   `build_assembly(...)` into `src/`; re-point at least one `runs/` consumer (or a new
   example) at the `src/` entry points. Keep signatures behaviour-preserving.
4. **`R-GND-1/2` — decouple + archive legacy.** Remove `aero.cases` from
   `aero/__init__.__all__` and `scenario.py`'s import (it now uses the typed structural
   layer); remove `structural.beam` from `structural/__init__.__all__`. Move both modules to
   an archived location (or mark frozen with a header pointing at the spec). Shell-beam
   `examples/0{2,3}`, `22` that imported them are pinned to the archived path or marked
   legacy (`OUT-4`) — **not** deleted.
5. **`R-GND-3` — truss designation.** Add the authoritative "archived, analysis-only"
   marker (module docstring/`__init__` note) so discovery matches CLAUDE.md.
6. **`R-GND-4` — heal doc links.** Repoint/remove the `improvement_backlog.md` /
   `guided_generative_design.md` references in `docs/findings.md` and `docs/plan.md` to the
   canonical `constitution`/`specification`/`engineering_basis` docs.
7. **`R-GND-8` — tooling debt.** Make `_wing_side_view` derive camera framing from the
   scenario span (no 5 m literal); reconcile `paraview/README.md`'s script table with
   `ls paraview/*.py`.
8. **Tests.** Add a unit test for the typed load-case category→serviceability gating and the
   bit-exact constant promotion (`R-GND-5/6`); a forward-path import-guard smoke test
   asserting `aero.cases`/`structural.beam`/`truss.*` are absent from forward `__all__`
   (`R-GND-1/2/3`); a doc link-check (`R-GND-4`). No new analytic gradient is introduced, so
   **no FD-validation test is required** this phase (Constitution IX is N/A here — flag if
   step 3 ends up adding a differentiated term).
9. **Re-run `just test`** → must match/exceed the step-1 green baseline; record wall-clock.

## Deliverable & gate

Runnable `examples/<NN_name>.py` that builds sections + assembly via the new `src/` entry
points and round-trips an STL/STEP export; the green fast suite; and a recorded finding
(measured wall-clock) in `docs/findings.md`. No buckling eigen / milestone export is due
(Phase 0 ships no structural optimum — III/XI N/A this phase). Closing this gate **opens
Phases G/A/S/M**.

## Risks / dependencies

- **Depends on:** nothing upstream — Phase 0 is the critical-path root.
- **Blocks:** Phases G/A/S/M consume the `Scenario`/`StructuralLoadCase` types and the
  `build_assembly` seam, so land this cleanly before fanning them out.
- **Decision gates:** none resolved here. The typed load cases are intentionally
  value-empty until **D-2** (feathering/survival AoA), **D-1** (RM curve), **D-4** (camber)
  land in Phase A (`spec OUT-1`).
- **Risk:** decoupling `scenario.py` from the dinghy `LoadCase` could red shell-beam
  examples. Mitigation: pin them to the archived path (`OUT-4`) — they are the historical
  record, not CI-gated, but should still import.
- **Risk:** "byte-identical" constant promotion drift. Mitigation: the bit-exact assertion
  test (step 8) is the guard, per the P.0 reproduction precedent.
