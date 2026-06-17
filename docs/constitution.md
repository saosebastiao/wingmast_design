# wingmast_design — Project Constitution

**Version 1.0.0 · Ratified 2026-06-16 · Supersedes the implicit conventions of the
shell-beam build-out (archived in `docs/archive/plan_shellbeam.md`).**

This is the supreme governing document of the project. It states the principles that
every specification, plan, analysis, sizing run, and line of code must honour.
`CLAUDE.md` *operationalises* this constitution (file paths, commands, machine limits);
where the two ever conflict, the constitution wins and `CLAUDE.md` is corrected.
Detailed specs and plans (`docs/specs/**`) inherit and may tighten — never relax —
these principles. Amendment procedure is in §Governance.

---

## Mission

Design a **free-standing (unstayed), fully-rotating CFRP wingmast** for a sailboat,
**minimum-mass** subject to strength, stiffness, twist, buckling, and manufacturability
constraints, **sized FEA-in-the-loop** against a verified collection of operational and
survival load cases. The reference platform is an **Oyster-595-class** yacht carrying
**two tandem wingmasts** with NACA-0018 soft wingsails (`docs/specification.md`). The
mast is built by a specific process — **filament-wound hollow box spars + co-bonded
UD longerons filling the inter-spar channels + a filament-wound outer shell** — and the
design must be buildable by that process. Every important milestone yields exported,
regenerable CAD plus the analyses that justify it.

---

## Principles

### Article I — Measure, never estimate (wall-clock)

Every FEA / sizing / verification run **MUST** be timed (`time`, or captured Bash
duration) and the **measured** wall-clock recorded in the finding. Estimates in this
project have run ~10× off. A claim about how long something takes, or how much memory it
uses, is not admissible unless it was measured. Record `ru_maxrss` (self + children) for
heavy runs.

### Article II — A result counts only if converged AND feasible

No mass, deflection, twist, or margin may be reported as a *result* unless the run both
**converged** (optimizer success, iterations < maxiter) **and** is **feasible** (all
constraints satisfied, checked explicitly). Otherwise it is a **diagnostic** and must be
labelled as such. Differences within the **~2–3 % ftol/basin noise floor** are not wins
or losses — never claim them as such.

### Article III — Verify buckling at a converged mesh

The sizing-mesh linear-buckling eigenvalue is unconservatively overstiff and **MUST NOT**
be trusted for feasibility. Buckling feasibility is judged on the **converged cluster
floor at n_levels ≥ 24**, over the lowest **2–3 modes** (eigen-only). The closed-form
buckling model is well-calibrated to the converged eigen for the **operational** envelope
but **non-conservative for survival/slam** — survival-sized designs **MUST** be
eigen-verified at n ≥ 24 before any mass or feasibility is claimed.

### Article IV — Physics honesty; survival governs; flag non-conservatism

The model must behave like the real structure, and known non-conservatisms must be
written down, not buried.
- **Never size to an idealisation that understates load.** (Lesson of the re-scope: a
  bare-mast survival moment computed on a slim "strut" planform understated the real
  full-wing-chord load ~3×. Survival **governs** this spar; size to the honest exposed
  geometry, eigen-verified.)
- **Every quantitative input carries its provenance and sensitivity.** Derived /
  unpublished numbers (e.g. the reference boat's righting moment, which scales every
  operational load linearly) **MUST** be flagged as the dominant sensitivities and be
  the first things pinned down.
- Load-case classification is explicit: **serviceability** (deflection, twist) limits
  apply to **operational** cases only; **ultimate/survival** cases are governed by
  strength + buckling + eigen, with deflection demoted to a linear-FEA validity guardrail.

### Article V — Manufacturability is a first-class constraint

A design that cannot be built by the prescribed process is infeasible, not merely
suboptimal. The model **MUST** encode the process realities: filament-winding angle
limits (no true 0° longitudinal passes; non-geodesic slippage bound), box-spar /
mandrel windability and release, integer-ply discretisation, and the longeron-channel
geometry. **The co-bonded / secondary-bonded interface MUST NEVER be the critical load
path** — it is checked at interlaminar/bondline allowables (≈ an order of magnitude below
in-laminate strength) with a process-measured knockdown.

### Article VI — Minimum mass, doubly weighted aloft

The objective is **minimum total CFRP mass** of the two wingmast spars and skins. Mass
aloft trades directly against the boat's righting moment and is therefore *doubly*
valuable; the optimiser and every lever are judged on mass against the established
baseline, never on intuition.

### Article VII — Negative results are findings too

A lever that does not pay, a constraint that does not bind, a mesh that diverges — each
is recorded with the **same rigor** as a win (mechanism, numbers, wall-clock, *why* it
lost). The findings archive is append-only; nothing measured is discarded.

### Article VIII — Memory-budget parallel runs

The sum of concurrent worker peak footprints **MUST** be ≤ ~half of machine RAM; never
stack independent heavy FEA runs to coincident peaks. (Measured: an IPOPT medium worker
peaks ~18 GiB → safe cap on the 32 GiB machine is n_workers = 1; 8-way oversubscription
caused watchdog kernel panics.) Lightweight read/research agent fan-out is exempt; heavy
solver processes are not.

### Article IX — Every analytic gradient is FD-validated

Any new analytic gradient (sensitivity, constraint Jacobian) ships with a
central-difference validation test (rel-err ≤ ~1e-4, tiny mesh) following the
`tests/beams/test_sensitivity.py` pattern. An unvalidated gradient is not trusted in the
loop.

### Article X — Warm-start everything

Sweep and refinement points start from the nearest prior optimum (`x0=`); fine meshes
start from resampled coarse solutions. Seeds are padded equivalence-preservingly so the
incumbent guard can never be lost.

### Article XI — Milestones export regenerable CAD + analyses

Any milestone (new headline mass, validated lever, re-baseline) **MUST** produce exported
— or trivially regenerable via an example — CAD (STL/STEP through the sized-export path)
plus the supporting analysis artifacts (FEA fields to `exports/*.vtu`, screenshots).
`exports/` is gitignored: **regenerability** is the requirement, and the finding records
the command that regenerates it. The three standing deliverables per qualifying design
are **assembly visualization, manufacturing-process simulation/visualization, and
stress/strain visualization**.

### Article XII — Single source of truth, run through `just`

Load cases, the design scenario, material systems, and the assembly build **live as typed
definitions in `src/`** — never as duplicated literals in `runs/` scripts. All Python runs
go through `just` (`just py`, `just example NN`) so `PYTHONPYCACHEPREFIX` keeps bytecode
out of the tree; the tooling interpreter is `.venv/bin/python`.

### Article XIII — Spec-driven workflow

Work flows **constitution → specification → high-level plan → per-feature detailed
spec + plan → implementation**, each artifact tracing to the one above it. Forward plans
live in `docs/plan.md` and `docs/specs/**`; **findings and decisions are recorded in the
append-only `docs/findings.md`** in the house format — *plans hold no findings, findings
hold no forward plan.* No implementation of a non-trivial capability begins before its
detailed spec exists and is consistent with this constitution.

---

## Governing physics & scope (boundaries, not derivations)

- **Object of optimization:** the rotating CFRP mast (stock + transition + wing). The
  soft wingsail, halyards, and rig hardware enter as **applied aerodynamic and reaction
  loads only**, not as optimised structure.
- **Scope:** the Oyster-595 twin-wingmast scenario only. The multi-scale "drone-wing →
  turbine-blade" ambition of the prior project is **retired**; the parametric model stays
  clean but size-range generality is not a goal.
- **Aerodynamics:** modelled to (a) generate the structural load envelope and (b) model
  the **tandem two-mast slot-effect interaction** well enough to choose mast spacing,
  quantify the lift enhancement, and partition load between the masts. Higher-fidelity
  aero-structural co-optimisation is out of scope for now.

Quantitative requirements (load magnitudes, target thresholds) live in
`docs/specification.md`; their derivation and citations live in
`docs/engineering_basis.md`. The constitution fixes *how* we decide, not the numbers.

---

## Governance

- **Precedence:** Constitution > specification > plan > detailed specs > code comments >
  habit. `CLAUDE.md` is the operational layer beneath the constitution.
- **Amendment:** changes to this document are made by editing it, bumping the semantic
  version (MAJOR = principle removed/redefined; MINOR = principle added; PATCH =
  clarification), and appending a decisions-log row in `docs/findings.md` stating the
  change and its rationale. Superseded principles are struck through, not deleted, when
  the history matters.
- **Compliance:** every plan phase and every finding states which principles it exercises
  or is gated by. A reviewer (human or agent) checks new work against these articles
  before it is called done.
- **Living scope:** the reference platform and the prescribed manufacturing concept are
  fixed by the brief and are not casually re-litigated; if the brief changes, the
  specification and this §Mission are amended together.
