# Spec — Structural: journal BCs + box-spar mechanics (Phase S)

**Status:** draft · **Parent:** `docs/specification.md` `R-CON-3`, `R-PERF-1…7`, `R-MFG-4`,
goal `G-3` · `docs/plan.md` Phase S · consumes Phase G geometry + Phase A loads · Constitution
Articles **III** (eigen-verify at n≥24; survival non-conservative for closed-form), **IV**
(survival governs; serviceability operational-only), **IX** (FD-validate every analytic
gradient).

## Scope

The structural subsystem for the **bare rotating wingmast**: **journal/bearing boundary
conditions** (two spanwise-separated radial supports + released pivot rotation + heel thrust —
**not** a root clamp), a **hollow box-spar cross-section** primitive with analytic sensitivities
and local-buckling checks, the **variable-section mast mesh** + retargeted aero-load
projection, **co-bond interface** stiffness + ILSS limits, **helical filament-wound
anisotropy**, and **converged-mesh eigen buckling**. The deliverable solves **OP-2 + SURV-1f**
on the box-spar mast with journal BCs, eigen-verified at n≥24 (`G-3`).

Phase S builds the **structural model + its constraints**, not the optimum. It reuses the
math-validated FEM core (shell/beam_shell/eigen_buckling/geometric_stiffness/frame). Phase O
minimises mass over the design vector this phase exposes; Phase M pins the ply/bondline
allowables.

### Out of scope
- `OUT-1` Mass **optimization** (the sizing loop, multistart, shadow prices) — Phase O. Phase S
  ships a *solve* + the typed constraints/gradients O will drive.
- `OUT-2` As-built ply allowables / co-bond GIC-ILSS coupon values / integer plies — Phase M.
  Phase S uses the basis §6–§7 placeholders, flagged by sensitivity (Article IV).
- `OUT-3` The legacy shell-beam **form-beam** structural path (`beams/shell_model`,
  arc-spaced perimeter beams) — superseded by the box-spar model; not extended (`R-GND`-style
  freeze). The FEM **core** math (`shell`, `beam_shell` assembly, `eigen_buckling`,
  `geometric_stiffness`, `frame`) is reused unchanged.
- `OUT-4` Aeroelastic / divergence / flutter closure for the free-rotating wing — Phase V.
  Phase S applies the Phase-A loads as static (× DAF); it does not re-solve loads-on-deformed.

## Requirements

- `R-S-1 (journal/bearing boundary conditions)` — *(parent `R-CON-3`)* The model **MUST** apply
  **journal BCs**, not a rigid root clamp: two **spanwise-separated radial supports** at the
  deck-partners (upper journal, `z = −transition_length`) and heel-step (lower journal,
  `z = −transition_length − stock_length`) stations; the **pivot-axis rotation released** (the
  mast is free to rotate / weathervane); and the **heel step reacting axial thrust** (gravity
  down the stock). Bearings carry **finite radial stiffness** (spring/penalty), not an infinite
  clamp. The journal **reactions** are recovered and reported (`R-PERF-7`). A journal-supported
  spar buckles differently than a clamped one — the buckling boundary **MUST** be re-verified
  on this BC. MUST.
- `R-S-2 (variable-section mast mesh + load projection)` — *(parent `R-LOAD-4`)* The mesh
  builder **MUST** target the **rotating-mast geometry** (`geometry.RotatingMastSpec` + the
  box-spar `SparSection`s) — the slender variable-section wing + the transition zone + the
  stock — **not** the legacy uniform wingsail. It **MUST** tag the two bearing stations for
  `R-S-1`, and project the Phase-A distributed loads (normal **+ chordwise drag + torsion about
  the pivot** — extend the normal-only `projection`) onto the box-spar + outer-shell surfaces,
  with self-weight/heel body loads. MUST.
- `R-S-3 (box-spar cross-section + local buckling)` — *(parent `R-GEO-5`, `R-PERF-4`)* A
  **hollow box-spar section** primitive **MUST** exist (web height, cap width, wall thickness →
  A, I, J), with **element stiffness** in those terms and **analytic** `dA/d·`, `dI/d·`
  derivatives (FD-validated, Article IX). It **MUST** carry **web-shear** and
  **cap-compression local-buckling** constraints (closed-form, KS-aggregated, with FD-validated
  gradients) alongside the global eigen (`R-S-6`). A **multi-spar topology** builder consumes
  the `box_spars.SparSection` (≥3 spars + the longeron channels) — replacing the single
  arc-spaced-perimeter-beam model. MUST.
- `R-S-4 (co-bond / co-cure interfaces)` — *(parent `R-MFG-4`)* Co-bonded interfaces (spar↔spar,
  spar↔shell, longeron↔channel) **MUST** be modelled with **finite interface stiffness** (not a
  rigid weld) and checked against **knocked-down bondline shear/peel (ILSS)** allowables; the
  bonded interface **MUST NOT** be the critical load path (Article V). Bearing + interface
  **stress recovery** is reported (`R-PERF-7`, util < 1). Extend the existing stiff-massless-bond
  primitive toward a cohesive/finite-stiffness interface. MUST.
- `R-S-5 (filament-wound helical anisotropy)` — *(parent `R-MFG-1`)* The shell/spar laminate
  stiffness **MUST** accept a **continuous helical wind-angle** field θ(z) (mapped → per-element
  `Qbar`/A/D), not only the 0/±45/90 area fractions the current CLT takes. No true 0° passes;
  the windable-angle set is honoured (the wound shell is ±θ helical). MUST.
- `R-S-6 (converged-mesh eigen verification)` — *(parent `R-PERF-4`, Article III)* Global linear
  buckling **MUST** be eigen-verified at a **converged mesh (n ≥ 24)** over the lowest 2–3 modes,
  **per load case**, on the journal-BC geometry — the closed-form/local checks are calibrated for
  the operational envelope and **non-conservative for survival**, so the **survival** cases are
  judged **solely on the converged eigen** (λ ≥ 1.5). MUST.
- `R-S-7 (deliverable: solve OP-2 + SURV-1f, eigen-verified)` — *(parent `G-3`)* A runnable
  `examples/` script **MUST** solve the box-spar mast with journal BCs under **OP-2** (governing
  operational) and **SURV-1f** (the feathering-fault survival case), recover stress / journal
  reactions / interface utils, run the n≥24 eigen, and report the `R-PERF-1…7` metrics with
  **measured wall-clock** (Articles I, II). MUST.

## Acceptance

A structural result counts only if the solve **converged** and the design is **feasible**
(`R-PERF-8`), with measured wall-clock. Phase S ships a *solve* + tests, not a mass optimum.

- `R-S-1` — a test asserts the two journal stations are supported (radial), the pivot rotation
  DOF is free (a torque about the pivot produces rotation, not reaction), the heel reacts axial
  thrust, and a free-free check fails (no rigid-body modes only once both journals + thrust are
  applied); journal reactions sum to the applied transverse load (equilibrium). The buckling
  boundary is re-verified (eigen on the journal BC differs from the clamped one).
- `R-S-2` — the mesh is built from `RotatingMastSpec` at the mast scale; bearing stations are
  tagged at the right z; a load-conservation test: the projected normal+drag+torsion integrate
  to the case totals (force/torque conserving, like the legacy normal projection).
- `R-S-3` — a `BoxSection` reproduces A/I/J for a known box; **FD validates** `dA/d·`, `dI/d·`
  (central diff, rel-err ≤ ~1e-4, tiny mesh — `tests/beams/test_sensitivity.py` pattern); the
  web-shear + cap-compression utils bite when the wall is thinned; KS providers + their
  gradients FD-pass.
- `R-S-4` — the interface stiffness is finite (not rigid); an ILSS util is computed and bites
  when the bond is overstressed; a test asserts the bonded interface is **not** the binding
  constraint at the reference design (Article V).
- `R-S-5` — a helical θ(z) maps to per-element A/D and reproduces the symmetric ±45 result when
  θ = 45°; an off-axis θ shifts the stiffness as expected; gradients (if differentiated) FD-pass.
- `R-S-6 / R-S-7` — the example solves OP-2 + SURV-1f, eigen-verified at **n ≥ 24** (λ ≥ 1.5 over
  the lowest 2–3 modes); reports strength R, deflection, twist (operational only), buckling λ,
  mass, CoM, journal reactions, interface utils; measured wall-clock recorded; a finding logged.

**Deliverable & gate (whole phase):** green fast suite; the journal-BC + box-spar structural
model + its typed constraints/gradients in `src/`; the OP-2 + SURV-1f solve example,
eigen-verified at n≥24; a recorded finding (Articles I–IV, IX). Closing the gate **feeds Phase
O** (the model + design vector + analytic gradients to minimise mass over) and **Phase M** (the
ply/bondline allowables to pin).

## Decisions & assumptions

- `D-S-a (journal BCs = finite-stiffness radial springs)` — model each journal as a
  **finite-stiffness radial support** (penalty springs on the 2 cross-axis translations at the
  bearing nodes), the pivot-axis **rotation free**, the heel reacting **axial thrust** — a
  *physical* bearing model (a journal has real radial stiffness), the **simplest** addition
  (augment K at the bearing DOFs; reuses the existing solver), and it composes with eigen. Not
  Lagrange multipliers (saddle-point system) nor a rigid clamp (un-physical + the audit's
  buckling-boundary concern). Bearing stiffness is a flagged input (sensitivity, Article IV).
- `D-S-b (box spars as beam elements + a shell skin)` — model each box spar (and the longerons)
  as a spanwise **beam element** carrying the `BoxSection` A/I/J, and the filament-wound outer
  shell as the **DKT+CST skin shell** — i.e. reuse the audited `beam_shell` assembly with a
  box section in place of the circular one, **not** a full 3-D shell mesh of every cell wall
  (tractable, differentiable, and the established sizing topology). Local cell-wall buckling is a
  **closed-form** constraint (`R-S-3`), the global mode is the eigen (`R-S-6`).
- `D-S-c (survival judged on the converged eigen)` — the closed-form/local-buckling checks are
  calibrated for the operational envelope and **non-conservative for survival** (the prior
  project measured closed-form util 1.001 while eigen λ 0.81 under slam); so **SURV-1f**
  feasibility is decided by the n≥24 eigen, not the closed form (Article III).
- `D-S-d (placeholder allowables, flagged)` — ply strengths (T700/epoxy, basis §6) + bondline
  ILSS/GIC (basis §7) are **placeholders** pending Phase-M coupons; every derived input is
  flagged by sensitivity; no result is presented as as-built (Article IV/V).
- `D-S-e (reuse the FEM core; freeze the shell-beam path)` — keep `shell`/`beam_shell`/
  `eigen_buckling`/`geometric_stiffness`/`frame`/`buckling` unchanged (math-validated); the
  legacy form-beam `beams/shell_model` arc-spaced model is **frozen** (superseded by the
  box-spar topology), mirroring the Phase-0 legacy-quarantine discipline.

## Open questions / risks
- **Journal bearing stiffness value** — the radial/axial spring constants (a real bearing +
  hull-mount compliance). Seeded as a high-but-finite placeholder; its sensitivity on the
  buckling boundary is checked (`R-S-1` re-verify). A `plan.md` build choice.
- **Box-spar local-buckling fidelity** — closed-form web-shear/cap-compression (calibrated by a
  one-off eigen, like the prior panel-buckling calibration) vs an in-loop local eigen. Start
  closed-form + calibrate; flag if survival forces the in-loop check.
- **Transition-zone mesh convergence** — the n≥24 rule was established for the uniform wing; the
  variable-section + transition mesh refinement strategy is re-checked (`R-S-6`).
- **Helical θ(z) → A/D gradient** — if θ(z) becomes a Phase-O design variable, its analytic
  derivative through `Qbar` needs an FD-validation test (Article IX) — flagged for Phase O.
- **Does the slender mast (AR ~25) need the longerons + shell as load path, or do the box spars
  dominate?** — a Phase-S/O finding once the solve runs; informs the `D-S-b` topology.
