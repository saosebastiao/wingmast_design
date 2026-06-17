# Plan — Tandem aerodynamics & load envelope (Phase A)

**Parent spec:** `./spec.md`

## Reuse (from the audit verdicts + the Phase-A code survey)

- **Keep (unchanged):** `aero/loads.py` — the **Kutta-Joukowski plumbing** (`_compute_panel_loads`,
  `PanelLoads`, `AeroResult` + its `roll/pitch/yaw` moments + `dynamic_pressure_Pa`,
  `run_case`/`run_case_lifting_line`/`sweep_envelope`), the `LoadCase` operating-point type, and
  `distributed_normal_force`. The frame contract `R_GEOM_FROM_AERO` (`structural/projection.py`).
- **Refactor:** `aero/model.py` — generalise `build_asb_wing`/`build_airplane` to consume the
  new `geometry.RotatingMastSpec` + **CST airfoils** (today: `WingSpec` + NACA-only), and add a
  **tandem two-wing `Airplane`** factory (ASB `Airplane` already supports multi-wing — the
  survey confirms; no solver bump). `structural/projection.py` — **extend** with chordwise-drag
  + torsion distribution (keep the normal-force path + frame change).
- **New (`src/`):** the operational **apparent-wind / heel / RM-cap** model; the **tandem
  slot-effect** split; the **survival feathering** envelope (analytical, drag-based); the
  **feathering-robustness (D-2)** model; the **DAF + VIV** assessment; and the **typed
  design-load collection** builder that emits OP/SURV cases (composing with the Phase-0
  `load_cases.StructuralLoadCase`).
- **Do not touch:** the frozen dinghy `aero.cases` (`R-GND-1`); Phase A defines its cases
  programmatically from the apparent-wind model, not as frozen literals.

## Steps

1. **Pin the green baseline.** `just test`; record count + wall-clock (currently 256 passed).
2. **A.1 — operational load model (`R-AE-1`).** New `aero/sailing.py` (or `aero/operational.py`):
   apparent-wind triangle + heel attitude + the **RM-cap** chain `RM_max → split → ÷lever →
   ×arm → ×DAF`. Unit-test it reproduces basis §3 to the digit (OP-1 ≈ 115 kN·m @ RM 200, 129 @
   225). Cambered operating polar (CL ≈ 1.45) as the operational lift input (`D-AE-e`).
3. **A.2 — tandem slot effect (`R-AE-2`).** Refactor `aero/model.py` to build a **2-wing
   `Airplane`** (fore + aft at `mast_spacing`) from `RotatingMastSpec`/CST; run LiftingLine to
   quantify the slot enhancement vs spacing (1–2 c) and the per-mast split; expose 50:50 (OP-1)
   / 70:30 (OP-2). Validate the split against the basis 70:30 adoption + a spacing sweep.
4. **A.3 — survival feathering envelope (`R-AE-3`).** New `aero/survival.py`: analytical
   `q·C·A_mast·arm` across feathered (Cd 0.02–0.10) / off-axis-fault (Cl 1.0–1.2) /
   locked-broadside (Cd 1.5) at Cat-3/Cat-5 q; on the **bare-mast planform** (`c_mast·span`),
   not the wingsail chord. Test reproduces SURV-1 ≈ 8–39, SURV-1f ≈ 390–470 kN·m; flag the
   governing/fault cases for n≥24 eigen (Phase S). **NOT** the ASB lifting-line (`D-AE-c`).
5. **A.4 — feathering-robustness / D-2 (`R-AE-4`).** New `aero/feathering.py`: the weathervane
   restoring-moment model (pivot forward of the bare-section AC → positive yaw-restoring),
   yaw-damping ratio, AoA stops, **VIV Scruton/Strouhal** detuning, redundancy. Produces
   `AoA_max`, the vane slope, damping ratio, Scruton, the feathering-fault FoS, **and the
   governing-case verdict** (operational vs survival vs locked). Analytical baseline; CFD flagged
   (`OUT-3`). This is the `D-2` resolution — record in `findings.md`, update the spec `D-2` row.
6. **A.5 — distributed non-normal loads (`R-AE-5`).** Extend `structural/projection.py` (+
   `beams/fea_model.py`) with **chordwise-drag** + **torsion-about-pivot** spanwise
   distributions (mirror `distributed_normal_force`'s force-conserving lumping; keep the frame
   change). FD/conservation test: distributions integrate to the case totals. Torque ≈ 6–9 kN·m.
7. **A.6 — dynamic amplification (`R-AE-6`).** Apply DAF ≥ 1.5 (operational); add a
   Strouhal-shedding-vs-mode + Scruton lock-in check returning a margin. (Shares the Scruton
   machinery with A.5/A.4.)
8. **A.7 — typed design-load collection (`R-AE-7`).** New `aero/design_cases.py`: a
   `DesignLoadCase` (aero load: per-mast bending + torsion + spanwise distribution at design q;
   + the body-load **category** + SF/DAF) and a builder emitting **OP-1/OP-2/SURV-1/SURV-1f/
   SURV-2**, composing with `load_cases.StructuralLoadCase`. Names the governing case.
9. **Example + tests.** `examples/<NN>_aero_envelope.py`: build the tandem model, run the
   feathering study, emit + print the typed collection (with the governing case + the RM-band
   sensitivity), measured wall-clock. A test asserts the collection reproduces the basis bands.
10. **Re-run `just test`** → matches/exceeds the step-1 baseline; record wall-clock + the D-2
    finding.

## Deliverable & gate

Runnable `examples/<NN>_aero_envelope.py` emitting the typed OP/SURV collection + the D-2
verdict; green fast suite; a recorded finding (measured wall-clock; the resolved `D-2` AoA_max
+ governing case). No FEA/eigen this phase (Phase A flags cases for Phase-S eigen). Closing the
gate **resolves D-2** and **feeds Phases S and O**.

## Risks / dependencies

- **Depends on:** Phase G (geometry — the OML/CST + `mast_spacing` + `c_mast` parameter); Phase
  0 (the typed `StructuralLoadCase` layer). Both done.
- **Feeds:** Phase O (the cases to minimise mass against — OP-2 governs), Phase S (the
  distributed loads + the eigen-verify list).
- **Decision gates:** **D-2 is resolved here** (the phase's headline). `D-1` (RM curve) and
  `D-4` (camber/`c_mast`) stay parameterised — the methodology + governing-case verdict do not
  need their final values; only an *absolute* mass headline does (flag in the finding).
- **Risk:** AeroSandbox LiftingLine is **invalid feathered/stalled** → survival is analytical
  (`D-AE-c`); do not run ASB at high AoA. **Risk:** no native **ground-plane** in ASB → A.1
  bounds the root-image effect or post-processes a mirror image (a `plan.md`-step choice; record
  what was done). **Risk:** the feathering study is the project's largest uncertainty — keep the
  analytical model's assumptions explicit and the `AoA_max` flagged by method (Article IV); if
  it must escalate to CFD, that is a scoped follow-up, recorded, not silently skipped.
