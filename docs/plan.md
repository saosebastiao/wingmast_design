# High-Level Plan — Re-scope to the Oyster-595 Twin Wingmast

**Forward plan only** (Constitution Article XIII). Findings/decisions go to
`docs/findings.md`. Governed by `docs/constitution.md`; targets `docs/specification.md`;
numbers from `docs/engineering_basis.md`. The prior shell-beam plan is archived at
`docs/archive/plan_shellbeam.md`.

This plan takes the repo from its shell-beam research state to **spec compliance** (`G-1…G-5`).
Detailed per-phase specs + plans will be authored in the next session under `docs/specs/<NN-feature>/`.

---

## Where we are (2026-06-16)

The repo is a mature **FEA-in-the-loop laminate sizing system** for a *single, root-clamped,
free-flying* shell-beam wingsail. The re-scope keeps the physics/optimization/CAD/viz
**infrastructure** and re-targets the geometry, aero, boundary conditions, and manufacturing
model to a *twin, journal-mounted, free-rotating* wingmast built from filament-wound box
spars. The audit (`docs/respec_research/`) verdicts:

| Verdict | Count | What |
|---|---|---|
| **Keep** | 28 | FEM core (`shell`, `beam_shell`, `buckling`, `eigen_buckling`, `frame`, `geometric_stiffness`); materials (`unidir`, `failure`); NLP scaffolding (`design_vector`, `constraints`); `viz/vtu`; export & multistart runners; ParaView `shell_fea`; tests |
| **Refactor** | 20 | sizer (`laminate_sizing`, `sensitivity`, `fea_model`, `cross_section`, `sections`, `build`, `splines`, `body_loads`, `shell_model`); aero `model`; geometry `airfoil`/`wing`; `mesh`, `projection`; `scenario` |
| **Retire** | 3 | `aero/cases.py` (dinghy envelope), `structural/beam.py`, the old `plan.md` (done) |
| **Uncertain** | 11 | `truss/*` (stress-line/frame-field — orthogonal to the fixed box-spar concept); `tip_coupling`, `fidelity`, `fea.py` (tet solver); missing `improvement_backlog.md` / `guided_generative_design.md` |

**Durable knowledge preserved** (do not re-derive): the design-vector layout & constraint
formulation, the adjoint sensitivity engine + SensCache, KS aggregation, multistart &
warm-start conventions, the eigen-mesh-convergence behaviour (n≈12 overshoot → n≥24 floor),
the closed-form-vs-eigen calibration, build123d loft conventions (`ruled=True`), and the
material/Tsai-Wu defaults. Absolute masses (1021.6 kg op / 1575.3 kg survival) are for the
22 m demo wing and **do not transfer** — only lever *effectiveness* and governing-physics
conclusions carry over.

---

## Critical path & decision gates

```
Phase 0 (groundwork) ─┬─► Phase G (geometry) ─┐
                      ├─► Phase A (aero) ──────┼─► Phase O (optimization) ─► Phase V (verify+exports)
                      └─► Phase S (structural) ┘        ▲
                              Phase M (materials/mfg) ──┘
```

- **Gate D-2 (feathering robustness)** — resolve *before* committing spar mass: the survival
  design AoA / off-axis load (drag-dominated if feathering is robust → operational governs;
  off-axis transient if not → survival governs by several-fold; locked-broadside is worst).
  Sits at the Phase A → Phase O boundary; largest mass swing in the project
  (`docs/specification.md` D-2, R-LOAD-2).
- **Gate D-1 (RM curve)** and **D-4 (sail-area/camber)** — pin before any *absolute* mass
  claim; methodology proceeds without them.

Phases G/A/S/M are largely parallelizable after Phase 0; Phase O integrates them; Phase V
closes the loop. Each phase ends in a runnable `examples/` script + a passing smoke test +
a recorded finding (Constitution Articles I, VII, XI).

---

## Phase 0 — Re-scope groundwork

**Goal:** clean foundation so later phases build, not fight, the legacy.

- **0.1** Adopt the spec-driven layout: `docs/{constitution,specification,engineering_basis,plan}.md`
  (done); create `docs/specs/` for per-feature detailed specs; add a re-scope marker
  finding to `docs/findings.md`.
- **0.2** Retire dead code behind the re-scope: archive/remove `aero/cases.py` dinghy
  envelope and `structural/beam.py`; decide `truss/*` (recommend **archive as analysis-only**,
  not retire — it MAY place `notes.md` item-5 connecting beams later). Resolve the missing
  `improvement_backlog.md` / `guided_generative_design.md` references (content now lives in
  the new spec/basis).
- **0.3** Promote the **single source of truth** (Article XII): a typed `StructuralLoadCase`
  + `Scenario` in `src/` (heel angle, slam g, gravity, per-case classification
  serviceability/ultimate), and `build_assembly(sized_result) -> Compound`, consumed by
  optimizer, eigen verification, and exports alike — replacing the duplicated literals in
  `runs/`. Promote `build_sections_from_result` + accel/datum/SF constants out of `runs/`
  into `src/`.
- **0.4** Tooling debt the audit flagged: add a `just test` recipe (none exists); retune the
  ParaView camera off the 5 m hardcode; prune the stale `paraview/README.md`.

**Deliverable:** green suite on the re-targeted scaffolding; spec-driven docs in place.
**Principles:** XII, XIII.

## Phase G — Geometry (rotating wingmast parametric CAD)

**Goal:** the `R-GEO-*` parametric model. *Refactor* `geometry/airfoil.py`, `wing.py`;
*keep* the loft conventions and `wingsails.py`.

- **G.1 Kulfan/CST airfoils** (`R-GEO-4`): wrap aerosandbox Kulfan; per-station blend
  (root≠tip); preserve the closed-contour ordering. (`notes.md` items 1–2.)
- **G.2 Rotating-mast geometry** (`R-GEO-1`): heel-step, stock, deck-partners, two journal
  bearing zones, transition zone (circular→airfoil), rotational-center **foil offset** as a
  distinct parameter (`R-GEO-2`), entasis (`D-5`).
- **G.3 Box-spar + longeron-channel CAD** (`R-GEO-5`): ≥3 convex box spars with blend-curve
  corners; compute the inter-spar **longeron channel** cross-sections from the blend params
  (blend radius → void size → longeron strength/mass coupling); the filament-wound outer
  shell; optional 3-part cored shell.
- **G.4 Geometric-fit constraint** (`R-CON-1`): members touch-not-intersect; envelope fit.

**Deliverable:** parameterized assembly example + STL/STEP export; geometry-fit smoke test.
**Gaps closed:** all geometry/CAD gaps. **Principles:** V, XI.

## Phase A — Aerodynamics (load envelope + tandem slot effect)

**Goal:** `R-AERO/R-LOAD-*`. *Keep* `aero/loads.py` KJ plumbing; *refactor* `aero/model.py`.

- **A.1 Sailboat load model:** apparent-wind triangle, heel attitude, the **righting-moment
  cap** on usable sail force, deck/sea ground-plane image at the root.
- **A.2 Tandem two-mast slot effect** (`R-SCN-3`, decision Q2 = "model the interaction"):
  a 2-wing ASB Airplane (or tandem-interaction correction) to choose spacing (1–2c), quantify
  lift enhancement, and produce the **per-mast load split** (50:50 nominal, 70:30 worst) for
  `OP-1`/`OP-2`.
- **A.3 Survival load + feathering dynamics** (`R-LOAD-2/2a`): the bare-mast load across the
  feathering regimes (feathered drag → off-axis transient lift → locked-broadside) on the
  **full exposed-chord planform** at hurricane q (Cat 3 / Cat 5); a vane/aeroelastic-dynamics
  + CFD model to establish the credible max off-axis AoA and design the feathering mechanism
  (pivot-vs-AC margin, yaw damping, AoA stops, VIV detuning). Not the slim-strut idealisation.
- **A.4 Distributed non-normal loads** (`R-LOAD-4`): distribute drag + torsion-about-pivot
  along the span; self-weight/heel body loads.
- **A.5 Dynamic amplification** (`R-LOAD-5`): gust DAF + a vortex-shedding/lock-in assessment
  for the slender free-standing mast.
- **A.6 Decision gate D-2** — feed A.3 into the feathering-robustness study that fixes the
  SURV-1 design AoA and hence whether survival or operational governs.

**Deliverable:** aero-envelope example producing the typed `OP-1/OP-2/SURV-1/SURV-2` cases.
**Gaps closed:** all aero gaps. **Principles:** IV, XII.

## Phase S — Structural (rotating BCs, box spars, interfaces)

**Goal:** `R-CON-3` + box-spar mechanics + co-bond. *Keep* `shell`, `beam_shell`,
`buckling`, `eigen_buckling`, `geometric_stiffness`; *refactor* `fea_model`, `mesh`,
`projection`, `cross_section`, `sections`.

- **S.1 Journal/bearing BCs** (highest priority): per-DOF supports — two spanwise-separated
  radial reactions (heel + partners), released pivot-axis rotation, heel thrust; finite
  bearing stiffness (spring/Lagrange) instead of the rigid clamp. A journal-supported spar
  buckles differently — re-verify the buckling boundary.
- **S.2 Transition-zone / variable-section mesh:** retarget `mesh.py`/`projection.py` off the
  uniform-wing assumption; tag bearing stations; retarget aero-load projection to the
  box-spar + outer-shell surface.
- **S.3 Box-spar cross-section + local buckling:** a hollow box/airfoil-conforming section
  primitive (web height, cap width, wall thickness) with element stiffness + analytic
  dA/dt, dI/dwidth; web-shear and cap-compression local-buckling constraints + KS providers
  + FD-validated gradients (Article IX). Multi-spar topology builder (replace the single
  arc-spaced-perimeter-beams model).
- **S.4 Co-bond / co-cure interfaces** (`R-MFG-4`): interface stiffness + bondline shear/peel
  (ILSS) limit (extend the existing "stiff massless bond" primitive toward cohesive-zone);
  bearing/interface stress recovery.
- **S.5 Filament-wound anisotropy mapping:** continuous helical wind-angle field → per-tri
  Qbar/A/D (today CLT takes only 0/±45/90 fractions).
- **S.6 Converged eigen verification** (Article III): standard n≥24 eigen check wired for the
  new geometry and the survival cases.

**Deliverable:** structural example solving `OP-2` + `SURV-1` with journal BCs + box spars,
eigen-verified. **Gaps closed:** all structural-FEM gaps. **Principles:** III, IV, IX.

## Phase M — Materials & Manufacturing

**Goal:** `R-MFG-*` + the process deliverable `R-EXP-2`. *Keep* `materials/*`.

- **M.1 Helical layup + failure:** arbitrary ±θ band layup primitive; **max-strain**
  criterion (spec-required) alongside Tsai-Wu; a defined cured band thickness.
- **M.2 Integer-ply discretisation** (`R-MFG-3`): round to integer plies + first-layer hoop
  floor; FEA re-verify (bump-and-reverify).
- **M.3 Windable-angle feasibility** (`R-MFG-1/2`): per-region windable angle sets;
  geodesic/non-geodesic feasibility on the box mandrel; wound-vs-RTM Vf knockdown.
- **M.4 Co-bond knockdowns** (`R-MFG-4`): GIC/ILSS allowables (process-coupon-set);
  co-cure-vs-co-bond modelling.
- **M.5 As-built mass:** wound Vf, turnaround overlaps, joints, bondlines, hardware — report
  ideal vs as-built separately (no idealised headline — Article V).
- **M.6 Manufacturing-process sim/viz** (`R-EXP-2`): the build-sequence + tow-path/winding-angle
  fields as a VTU/animation (green-field; line-cell VTU variant).

**Deliverable:** as-buildable layup + the process visualization export. **Principles:** V, XI.

## Phase O — Optimization (re-target the sizer)

**Goal:** `R-OPT-*`, `G-4`. *Refactor* `laminate_sizing.py`, `sensitivity.py`; *keep*
`design_vector.py`, `constraints.py`, multistart.

- **O.1 New design vector** (Article X-compatible named blocks): box-spar wall/cap/web,
  per-channel longeron count/area, outer-shell bands, helical wind angles — with
  equivalence-preserving warm-start padding.
- **O.2 Analytic gradients + FD tests** for every new section/constraint/body-load term
  (Article IX); retarget the adjoint + SensCache.
- **O.3 IPOPT** for the larger DV (>150 likely) + KS smoothing; wire **IPOPT shadow-price**
  extraction (today SLSQP-only) so the lever methodology survives.
- **O.4 Twin-rig sizing** against the full typed load collection (size each mast to OP-2 +
  SURV-1); ratchet best-feasible mass; sensitivity/shadow-price-directed lever search
  (`R-OPT-3`).

**Deliverable:** converged + feasible minimum-mass twin-rig design, measured wall-clock,
shadow prices. **Principles:** I, II, VI, IX, X.

## Phase V — Verification, aeroelastic closure & exports

**Goal:** `G-3`/`G-5` closure + `R-EXP-*`.

- **V.1** Re-mesh the as-designed assembly; re-solve every case; **eigen-verify at n≥24**
  (esp. SURV-1); converged-mesh feasibility before any headline.
- **V.2** Aeroelastic closure for the **free-rotating** wing: loads-on-deformed-shape
  fixed-point + a **divergence/flutter** check (never executed in the prior project; critical
  for a free-rotating wingmast).
- **V.3** The three exports per qualifying design (`R-EXP-1/2/3`) + milestone CAD/STEP +
  regeneration commands in the finding.

**Deliverable:** spec-compliant v1 wingmast with documented load envelope, margins, and the
full export set. **Principles:** III, IV, XI.

---

## What the next session picks up

1. Resolve the decision gates — **D-2 feathering robustness / survival AoA** (top), then D-1
   (RM curve) and D-4 (camber) — via the basis open-questions (`docs/engineering_basis.md` §9).
2. Author the **Phase 0 + Phase G detailed specs** under `docs/specs/` (the critical-path
   start), then fan out G/A/S/M in parallel.
3. Stand up the Claude config the plan needs as each phase lands (see the config notes in
   `CLAUDE.md` / `.claude/skills/spec-workflow`).
4. **Operationalize** (flagged by the 2026-06-16 consistency review; deferred from this
   high-level pass) in the detailed specs: explicit phase **entry/exit gates** recorded in
   findings; the Article VI **objective dual-weighting** of mass-aloft (formula + α
   sensitivity) in the Phase O spec; provisional numeric values for **ply-band thickness**
   (`R-MFG-3`) and **bondline allowables** (`R-MFG-4`) from process coupons; named `src/`
   module paths for the typed load cases / assembly (Phase 0.3); and a milestone-export
   smoke test + an eigen-convergence test (Articles XI, III). None block the high-level set.
