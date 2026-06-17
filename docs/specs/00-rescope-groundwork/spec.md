# Spec — Re-scope groundwork (Phase 0)

**Status:** draft · **Parent:** `docs/specification.md` `R-LOAD-1`, `G-5` (and the
foundation for `G-3`/`G-4`) · `docs/plan.md` Phase 0 · Constitution Articles **XII**
(single source of truth) and **XIII** (spec-driven).

## Scope

Establish a clean foundation so Phases G/A/S/M/O/V *build on*, not *fight*, the shell-beam
legacy. Three workstreams:

1. **Retire / quarantine** code the re-scope obsoletes, and fix the dangling shell-beam doc
   references — *without* breaking the still-green fast suite.
2. **Promote the single source of truth** (Article XII): a typed structural load-case +
   scenario layer in `src/`, and the assembly/section builders, replacing the literals
   currently duplicated across `runs/`.
3. **Pay down the tooling debt** the audit flagged.

This is a **scaffolding/refactor** phase. It introduces the *types and seams* the later
phases populate; it does **not** itself define the final Oyster-595 load magnitudes,
journal BCs, box-spar sections, or aero (those are Phases A/S — see Open questions).

### Out of scope
- `OUT-1` Final load **magnitudes / heel angle / slam g / DAF** for the twin rig — Phase A
  (`R-LOAD-*`) sets these; Phase 0 only provides the **typed container** they will populate.
- `OUT-2` Journal/bearing BCs, box-spar cross-sections, tandem aero — Phases S/A.
- `OUT-3` Any new analytic gradient or sizing result — Phase 0 ships no new optimum.
- `OUT-4` Deleting the shell-beam `examples/` and `runs/` scripts — they remain as the
  historical measurement record (CLAUDE.md "Layout notes"); they are *decoupled/marked*,
  not removed.

## Requirements

- `R-GND-1 (retire dinghy aero envelope)` — the dinghy airspeed/AoA **envelope of concrete
  cases** (`aero/cases.py::DESIGN_CASES`) **MUST** be removed from the forward path. Because
  it was imported by `aero/__init__.py`, `scenario.py`, and shell-beam examples, "retire"
  means **decouple its forward-path consumers and archive the module**, not a raw delete
  that reds the suite. The `LoadCase` *type* is forward (Phase A populates it) and is moved
  to `aero/loads.py` so the aero **solver** no longer imports the frozen module; the only
  remaining src/ reference to the frozen `DESIGN_CASES` *values* is the **bannered-legacy**
  `scenario.py` default (retired in Phase A — not the forward solver). MUST. (Refines plan 0.2.)
- `R-GND-2 (retire tube-spar sizer)` — `structural/beam.py` (`TubeSparSizing`,
  `size_tube_spar`, the Phase-3 baseline) **MUST** be frozen as historical and removed from
  the structural package's forward `__all__`. MUST. (Refines plan 0.2.)
- `R-GND-3 (truss decision)` — `truss/*` **MUST** be explicitly designated **archived,
  analysis-only** (kept, not retired — it may inform connecting-member work later) and that
  status recorded so no later phase assumes it is on the forward path. MUST. (Plan 0.2;
  CLAUDE.md already marks it archived — this makes it authoritative + discoverable.)
- `R-GND-4 (heal dangling doc refs)` — The dead links to `improvement_backlog.md` and
  `guided_generative_design.md` in `docs/findings.md` and `docs/plan.md` **MUST** be
  resolved (repointed to the new canonical docs or removed). No dangling shell-beam doc
  link remains **in those two files**. The archived `docs/archive/plan_shellbeam.md` keeps
  its original links (to docs that existed when it was the live plan) **by design** — it is
  a frozen historical snapshot, not a maintained doc. MUST. (Plan 0.2.)
- `R-GND-5 (typed structural load case in src/)` — A typed `StructuralLoadCase` **MUST**
  live in `src/`, carrying at minimum: acceleration/body-load vector(s), gravity, heel
  angle, datum direction, safety factor(s), and a **category** field classifying the case
  **operational (serviceability+ultimate)** vs **survival (ultimate-only)** vs
  **manufacturing**, per `R-LOAD-1`. Serviceability limits **MUST** be expressible as
  applying to operational cases only (Article IV). MUST. **Directly satisfies `R-LOAD-1`.**
- `R-GND-6 (typed Scenario in src/)` — A typed `Scenario` (or extended `DesignParameters`)
  in `src/` **MUST** own the structural load collection + the accel/datum/SF constants
  currently hardcoded in `runs/chain_rebuild.py` (`G0`, `TH`, `ACCELS`, `SF`, `DATUM`), so
  they are defined **once**. MUST. (Article XII; plan 0.3.)
- `R-GND-7 (promote assembly + section builders)` — `build_sections_from_result` and a
  `build_assembly(sized_result) -> Compound`-style entry point **MUST** live in `src/` and
  be consumed by optimizer, eigen verification, and exports alike — replacing the copies in
  `runs/{chain_rebuild,slam_*,export_best,eigen_*}.py`. MUST. (Article XII; plan 0.3.)
- `R-GND-8 (tooling debt)` — The ParaView camera **MUST NOT** be hardcoded to the 5 m span
  (`paraview/_common._wing_side_view`); it **SHOULD** derive its framing from the scenario
  span. The `paraview/README.md` script table **MUST** match the scripts actually present.
  SHOULD/MUST. (Plan 0.4.) **Note:** the `just test` recipe required by 0.4 already exists
  (`justfile:55`) — recorded as done, no action.

## Acceptance

How each requirement is verified. A result counts only if the suite is **green** with
**measured wall-clock** (Constitution I, II). Phase 0 ships no sizing optimum, so "result"
here = green fast suite + the seams demonstrably wired.

- `R-GND-1/2/3` — `just test` (fast suite) stays **green** after the decouple/freeze;
  the archived modules are absent from the forward packages' `__all__`; and an
  **import-graph** test asserts the forward aero solver (`aero.loads`/`model`/`__init__`)
  does not import the frozen `aero.cases`, that the only src/ importer of it is the
  bannered-legacy `scenario.py`, and that `structural.beam`/`truss.*` are fully clean
  (`tests/test_rescope_groundwork.py`).
- `R-GND-4` — A link-check asserts **zero** dangling markdown *links* to
  `improvement_backlog.md` / `guided_generative_design.md` in `docs/{findings,plan}.md`
  (plain-text mentions allowed; the archived `plan_shellbeam.md` is out of scope by design).
- `R-GND-5/6` — A unit test constructs the typed `StructuralLoadCase`/`Scenario`,
  asserts the operational-vs-survival category drives serviceability-limit applicability,
  and asserts the promoted constants equal the former `runs/` literals **bit-for-bit**
  (behaviour-preserving promotion; cf. the P.0 "reproduced bit-exactly" precedent).
- `R-GND-7` — An `examples/` script builds sections + assembly from a (legacy or stub)
  sized result through the **`src/`** entry points and round-trips an STL/STEP export;
  measured wall-clock recorded.
- `R-GND-8` — A render at the medium (22 m) span frames the spar without manual camera
  edits; `README.md` table diffed against `ls paraview/*.py`.

**Deliverable & gate (whole phase):** green fast suite on the re-targeted scaffolding;
typed load/scenario + assembly seams in `src/`; an `examples/` script exercising them; and
a recorded finding in `docs/findings.md` (Articles I, VII, XI). This gate **opens Phases
G/A/S/M** (they consume the `Scenario`/load-case types and the `build_assembly` seam).

## Decisions & assumptions

- `D-GND-a (retire ≠ delete)` — Legacy modules are **decoupled + archived/frozen**, not
  deleted, preserving the historical measurement record (CLAUDE.md "Layout notes"). Tightens
  Article XII (one forward source) without losing provenance (Article VII). *Sensitivity:*
  none on mass; reduces risk of silently reviving a shell-beam assumption.
- `D-GND-b (promotion is behaviour-preserving)` — Constants/builders move to `src/`
  **byte-identically**; any value change is a *separate* Phase-A/S decision, recorded in
  findings. Tightens Article XII; mirrors the P.0 bit-exact-reproduction discipline.
- `D-GND-c (category field is the serviceability gate)` — `StructuralLoadCase.category`
  is the single switch that makes deflection/twist limits apply to **operational only**
  (Article IV), so a survival case can never be sized to a serviceability idealisation.

## Resolved during implementation (2026-06-16; see `docs/findings.md`)
- `D-GND-d (new sibling module, not extend)` — **RESOLVED:** the typed layer is a new
  top-level module `src/wingmast_design/load_cases.py` (`CaseCategory`, `StructuralLoadCase`,
  the single-source constants), **not** an extension of `DesignParameters` — the latter is
  shell-beam-`Phase-4-5`-scoped legacy that Phases G/A re-target, so entangling the forward
  load types with it would be churn. `runs/chain_rebuild.py` imports the constants from here
  (single source). Satisfies `R-GND-6`.
- `D-GND-e (build_assembly deferral)` — **RESOLVED:** a `build_assembly` already exists
  (`beams/build.py`, **parameter**-based CAD). The plan's `build_assembly(sized_result) ->
  Compound` (a *sized-result* CAD assembly) is **deferred to Phase G/V**: the box-spar
  assembly geometry it would build does not exist until Phase G, so authoring a shell-beam
  sized-result assembly now is churn the re-scope discards. `R-GND-7` is therefore scoped to
  promoting the genuinely-duplicated **FEA** `build_sections_from_result` (done) + the
  constants (done); the example round-trips the existing param-based `build_assembly` export.
- `D-GND-g (adversarial-review fixes)` — A 22-agent adversarial review (6 dimensions →
  refute each finding) confirmed 6 low/medium honesty/completeness defects (0 high), all
  fixed in-phase: (1) the `build_sections_from_result` docstring's provenance was corrected
  (its sole prior definition was `chain_rebuild.py`; the other `runs/` scripts imported, not
  re-implemented, it); (2) the `LoadCase` *type* was moved to `aero/loads.py` so the forward
  aero solver no longer imports the frozen `aero.cases` (the import-graph test now guards
  this); (3) five more `runs/` scripts (`slam`, `export_best`, `survival_mesh_eigen`,
  `survival_mode_id`, `brazier_diag`) that still re-derived `G0`/`TH` were rewired to the
  single source so `R-GND-6`'s "defined once" is now literally true (a runs-wide test
  guards it); (4) the `R-GND-1`/`R-GND-4` acceptance prose was narrowed to what is actually
  achievable/tested (the legacy `scenario.py` `DESIGN_CASES` residual and the archived
  `plan_shellbeam.md` links are documented, in-scope-by-design exceptions).
- `D-GND-f (pre-existing breakage surfaced)` — **RESOLVED:** the "green baseline" `R-GND`
  assumed did **not** exist — `just test` was red (45 collection errors) because the `.venv`
  carried stale `wing_design`-era console-script shebangs from the re-scope directory rename.
  Recreating the venv from the committed lock (`rm -rf .venv && uv sync`) fixed it; baseline
  is **203 passed / 31 deselected / 27.75 s**. Recorded as a finding.

## Open questions
- The **values** the typed load cases hold (OP-2 70:30 split, SURV-1/1f AoA, heel, slam g,
  DAF) are unresolved until Phases A/S and gate **D-2** — Phase 0 provides the empty typed
  container, deliberately not the numbers. (Record resolutions in `docs/findings.md`;
  update `R-LOAD-*` rows.)
