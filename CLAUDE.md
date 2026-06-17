# wingmast_design — project conventions

Free-standing (unstayed), **fully-rotating CFRP wingmast** for a sailboat — structural
spar + guide rail for a reefable soft wingsail. Built as **filament-wound hollow box spars
+ co-bonded UD longerons filling the inter-spar channels + a filament-wound outer shell**,
sized **FEA-in-the-loop** for **minimum mass**. Reference platform: **Oyster-595-class**
yacht with **two tandem NACA-0018 wingmasts** (`docs/specification.md`).

> **Re-scoped 2026-06-16** from a single root-clamped shell-beam wingsail to this twin
> rotating-wingmast brief. The physics/optimization/CAD/viz **infrastructure is retained**;
> geometry, aero, boundary conditions, and the manufacturing model are re-targeted. Prior
> plan archived at `docs/archive/plan_shellbeam.md`; absolute masses from that era do not
> transfer (only lever effectiveness + governing physics do).

## Documents (read before structural/sizing work — precedence top-down)

- `docs/constitution.md` — **supreme** governing principles. This file operationalises it.
- `docs/specification.md` — what the system must do (requirements `R-*`/`G-*`/`D-*`).
- `docs/engineering_basis.md` — verified load chain, geometry targets, material data,
  citations, and the dominant sensitivities behind the spec's numbers.
- `docs/plan.md` — **the forward plan ONLY** (Phases 0/G/A/S/M/O/V). No findings here.
- `docs/findings.md` — **append-only** archive of analyses, findings, decisions log. All new
  findings and decisions go HERE, in the established house format.
- `docs/specs/<NN-feature>/` — per-feature detailed specs + plans (spec-driven workflow).
- `docs/respec_research/` — the raw re-scope research/audit dossier (provenance).

## Non-negotiable conventions (from the constitution)

- **Measure, never estimate, wall-clock.** Every FEA/sizing/verification run is timed
  (`time` or Bash timing) and the **measured** duration recorded in the finding. Estimates
  have run ~10× off. Record `ru_maxrss` (self + children) for heavy runs. (Article I)
- **A result counts only if converged AND feasible.** Check both before reporting any mass.
  Within-noise (~2–3 % ftol/basin) differences are not wins. Otherwise it's a *diagnostic* —
  say so. (Article II)
- **Verify buckling at a CONVERGED mesh (n_levels ≥ 24), not the sizing mesh.** The coarse
  eigen is unconservatively overstiff (overshoots low at n≈12, settles to a converged
  cluster floor by n≥24); judge feasibility on that floor over the lowest 2–3 modes
  (eigen-only). The closed-form model is calibrated for the OPERATIONAL envelope but
  **non-conservative for survival** — survival-sized designs MUST be eigen-verified at n≥24.
  (Article III)
- **Survival governs; physics honesty.** Never size to an idealisation that understates
  load (the bare-mast survival case is the full exposed-chord planform, not a slim strut).
  Flag every derived/unpublished input by its sensitivity (the reference RM_max scales all
  operational loads linearly). Serviceability limits (deflection, twist) apply to
  **operational** cases only. (Article IV)
- **Manufacturability is a hard constraint.** Designs must be buildable by the filament-wound
  box-spar process (no true 0° passes; windable angles; integer plies); **the co-bonded
  interface must never be the critical load path.** (Article V)
- **Negative results are findings too** — same rigor, with *why* it lost. (Article VII)
- **Memory-budget parallel runs.** Sum of concurrent heavy-worker peaks ≤ ~half machine RAM;
  never stack independent heavy FEA runs. **Measured:** an IPOPT medium worker peaks **~18
  GiB** → on this 32 GiB machine the safe cap is **n_workers=1** (8-way caused watchdog
  kernel panics). Lightweight read/research agent fan-out is exempt. (Article VIII)
- **Every new analytic gradient gets an FD-validation test** (central diff, rel-err ≤ ~1e-4,
  tiny mesh — follow `tests/beams/test_sensitivity.py`). (Article IX)
- **Warm-start sweeps.** Start from the nearest prior optimum (`x0=`); fine meshes from
  resampled coarse solutions; pad absent design-vector blocks equivalence-preservingly.
  (Article X)
- **Milestones export regenerable CAD + analyses.** New headline / validated lever /
  re-baseline ⇒ exported (or example-regenerable) CAD (STL/STEP via the sized-export path)
  + FEA fields (`exports/*.vtu`) + screenshots (`just shot`). The three standing exports are
  **assembly viz, manufacturing-process sim/viz, stress/strain viz.** `exports/` is
  gitignored: regenerability is the requirement; the finding records the command. (Article XI)
- **Single source of truth, run through `just`.** Load cases / scenario / material systems /
  assembly build are typed in `src/`, never duplicated in `runs/`. Run Python through `just`
  (`just py`, `just example NN`, `just test`) so `PYTHONPYCACHEPREFIX` keeps bytecode out of
  the tree. Tooling interpreter: `.venv/bin/python`. (Article XII)
- **Spec-driven workflow.** constitution → specification → plan → `docs/specs/**` detailed
  spec+plan → implementation. Plans hold no findings; findings hold no forward plan.
  (Article XIII; see the `spec-workflow` skill.)

## Legacy / re-scope status

- **Legacy sizers are frozen.** `beams/sizing.py`, `beams/shell_sizing.py` are historical
  baselines; new features go to the laminate path (`laminate_sizing.py` + `sensitivity.py`).
- **Retired by the re-scope:** `aero/cases.py` (dinghy envelope) and `structural/beam.py`.
  `truss/*` is archived as analysis-only (orthogonal to the fixed box-spar concept).
- **Reuse verdicts** for every module: `docs/plan.md` "Where we are" + `docs/respec_research/`.

## Project skills (in .claude/skills/)

- `spec-workflow` — the constitution/spec/plan/detailed-spec/implement flow; where files
  live; requirement-ID conventions; how to start a feature.
- `wingmast-domain` — durable reference: terminology, axis conventions, the load-case
  collection (OP-1/OP-2/SURV-1/SURV-2/MFG-1), governing case, key parameters.
- `sizing-run` — how to launch/monitor/report long sizing runs.
- `record-finding` — the findings.md + decisions-log recording workflow.
- `justfile-tasks` — project task runner recipes and how to extend them.

Reviewer subagent `physics-reviewer` (`.claude/agents/`) checks structural/aero/laminate/
sizing changes against the constitution before they're called done.

## Pending upgrade

- **Python 3.14 when build123d > 0.10.0 releases.** On 3.13; 3.14 blocked solely by
  build123d 0.10.0 (`requires-python <3.14`, OCP `<7.9`); cp314 OCP wheels exist and
  build123d's dev branch supports `<3.15` + OCP 7.9. On a new build123d release: bump
  `requires-python` to `>=3.14,<3.15`, `.python-version` to 3.14, `uv lock && uv sync`, run
  the full suite, commit. 3.14 carries the real interpreter gains.

## Layout notes

- `examples/` numbered scripts are the measurement record; not run in CI (no CI — local
  suite only). Many examples are shell-beam-era and will be refactored per the plan.
- `tests/` is the fast unit suite (`just test` / `uv run pytest`); `sizing`-marked tests are
  the slow split (`just test` excludes them).
- `src/wingmast_design/` packages: `geometry/` (build123d OML, airfoil), `aero/`
  (AeroSandbox loads), `materials/` (UD ply + CLT + failure), `structural/` (FEM: shell,
  beam_shell, buckling, eigen_buckling, frame), `beams/` (sizer: laminate_sizing,
  sensitivity, design_vector, constraints, cross_section), `viz/` (VTU / ocp_vscode),
  `truss/` (archived analysis-only). New per-plan: rotating-mast geometry, tandem aero,
  journal BCs, box-spar sections, manufacturing/winding.
- Geometry viewer: examples call `show_in_viewer(part)` → OCP CAD Viewer (port 3939); no-op
  if not running. ParaView 6.x via `just view` / `just shot` (`paraview/*.py`).
