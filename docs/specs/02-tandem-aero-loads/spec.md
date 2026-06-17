# Spec — Tandem aerodynamics & load envelope (Phase A)

**Status:** draft · **Parent:** `docs/specification.md` `R-AERO-2`, `R-SCN-3/4`, `R-LOAD-1…5`,
goal `G-2`, decisions `D-1/D-2/D-4` · `docs/plan.md` Phase A · numbers from
`docs/engineering_basis.md` §3–§5 · Constitution Articles **IV** (survival governs; physics
honesty), **XII** (typed load collection), **XIII** (spec-driven).

## Scope

The aerodynamic **load envelope** the structure is sized to: the operational sailboat load
model (apparent wind, heel, the **righting-moment cap**), the **tandem two-mast slot effect**
and the per-mast load split, the **survival bare-wingmast feathering** envelope, the
**distributed** non-normal loads, **dynamic amplification**, and the **feathering-robustness
study (decision gate D-2)** that fixes the survival design AoA. The deliverable is the typed
**OP-1 / OP-2 / SURV-1 / SURV-1f / SURV-2** design-load collection (`G-2`) that Phases S/O
consume. This is the phase that **resolves the largest mass swing in the project** (D-2).

Phase A produces **loads**, not structure. It does not mesh, apply journal BCs, size plies,
or solve the FEA (Phases S/O); it reproduces the `engineering_basis.md` §3–§4 load chain as
*verified, typed* cases and pins the governing case.

### Out of scope
- `OUT-1` Structural FEA / journal BCs / box-spar mechanics / eigen sizing — Phases S/O.
  (Phase A flags which cases must be eigen-verified at n≥24, but does not run it.)
- `OUT-2` Ply layup / integer plies / co-bond — Phase M.
- `OUT-3` **High-fidelity CFD / unsteady aeroelastic** feathering simulation — Phase A ships
  the **analytical/engineering** feathering-robustness model (`R-AE-4`); CFD is a flagged
  higher-fidelity follow-up (`docs/engineering_basis.md` §9 open-q #5), not a Phase-A blocker.
- `OUT-4` Pinning `D-1` (the real stability/RM curve) and `D-4` (camber/`c_mast` final
  values) — Phase A carries them as parameters with the basis central values + sensitivity;
  the methodology proceeds without the final numbers (`docs/plan.md` decision gates).

## Requirements

- `R-AE-1 (operational sailboat load model)` — *(parent `R-LOAD-1`, `R-SCN-4`, basis §3)* The
  operational aero load **MUST** derive from the **apparent-wind triangle** + heel attitude,
  with the **righting-moment cap** binding: the steady aero heeling moment **MUST NOT** exceed
  `RM_max` (whole-boat) — this caps usable sail force regardless of wind. It produces the
  per-mast transverse force → base/partners bending via the operational arm. The operating
  section is **cambered** (CL ≈ 1.45 for the §5 area; `D-4`), not the plain symmetric NACA-0018
  faired-mast section. The deck/sea **ground-plane image** at the root **SHOULD** be modelled
  (or its lift/bending effect bounded). MUST.
- `R-AE-2 (tandem slot effect + per-mast split)` — *(parent `R-AERO-2`, `R-SCN-3`, `R-LOAD-3`)*
  The two-mast interaction **MUST** be modelled (a 2-wing AeroSandbox `Airplane` LiftingLine,
  or a justified tandem-interaction correction) to (a) quantify the slot-effect lift
  enhancement vs **spacing 1–2 c**, and (b) produce the **per-mast load split**: **50:50
  nominal (OP-1)** and **70:30 forward:aft worst (OP-2)**. **Each spar is sized to OP-2.** MUST.
- `R-AE-3 (survival bare-wingmast feathering envelope)` — *(parent `R-LOAD-2`, basis §4)* The
  survival load **MUST** be computed on the **bare-wingmast planform** `A_mast = c_mast · span`
  (the small structural section, **NOT** the wingsail chord) at hurricane q (Cat 3 = 1621 Pa,
  Cat 5 = 3042 Pa), across the feathering regimes:
  **SURV-1** feathered ~0° (Cd 0.02–0.10 ⇒ ~8–39 kN·m, **below operational**),
  **SURV-1f** feathering-fault off-axis (Cl 1.0–1.2 ⇒ ~390–470 kN·m Cat 3),
  **SURV-2** Cat-5 off-axis bound (~730–880 kN·m). Survival loads are **drag/bluff-body
  analytical** (`q·C·A·arm`), **not** the ASB lifting-line (which is invalid feathered/stalled).
  Any **governing or fault** case is flagged for **eigen verification at n≥24** (Articles
  III–IV). The optimistic pure-0° value **MUST NOT** be the *sole* design point unless `R-AE-4`
  demonstrates robust feathering. MUST.
- `R-AE-4 (decision gate D-2 — feathering robustness / survival AoA)` — *(parent `R-LOAD-2a/2b`,
  `D-2`)* Phase A **MUST** produce the feathering-robustness assessment that fixes **`AoA_max`**
  (the credible maximum off-axis AoA the structure is sized to) and hence **whether SURV-1f
  governs**. It **MUST** report: `AoA_max`, the **vane restoring-moment-vs-AoA slope** (pivot
  forward of the bare-section aerodynamic centre ⇒ positive yaw-restoring), the **yaw damping
  ratio**, the **VIV lock-in susceptibility** (Scruton number), and the **required
  feathering-fault FoS**. The design **SHOULD** maximise feathering reliability (pivot-vs-AC
  margin, aero balance, yaw damping, AoA stops, VIV detuning, **redundant** active + passive
  vane). **This gate sets the governing case** — operational-governed (drag-dominated, robust
  feathering) vs survival-governed (off-axis transient, several-fold heavier) vs
  locked-broadside (worst). MUST. **Largest mass swing in the project.**
- `R-AE-5 (distributed non-normal loads)` — *(parent `R-LOAD-4`)* Aero loads **MUST** be
  distributed along the span as **normal force, chordwise/tangential drag, AND torsion about
  the rotation axis** (not normal-only — today's `distributed_normal_force` is normal-only),
  plus self-weight + inertial (heel) body loads for operational cases, in a form the Phase-S
  structural model consumes. Operational torque ≈ **6–9 kN·m design** (basis §3, Cm_axis ≈
  −0.16) sizes the ±45° plies / twist / rotation-bearing. MUST.
- `R-AE-6 (dynamic amplification)` — *(parent `R-LOAD-5`)* A gust/seaway **DAF ≥ 1.5** applies
  to operational cases (survival folds gust into q + FoS); the slender free-standing mast's
  **vortex-shedding / lock-in** **MUST** be assessed (Strouhal shedding vs structural modes,
  Scruton number) rather than assumed covered by the single DAF scalar. MUST.
- `R-AE-7 (typed design-load collection — deliverable)` — *(parent `R-LOAD-1`, `G-2`)* Phase A
  **MUST** emit the typed **OP-1 / OP-2 / SURV-1 / SURV-1f / SURV-2** design-load collection in
  `src/` — each carrying its aero load (per-mast bending + torsion + distributed spanwise) at
  the design q, its **category** (operational serviceability+ultimate / survival ultimate-only),
  and its **SF/DAF** — reproducing the basis §3–§4 chain and **naming the governing case**. It
  composes with the Phase-0 `StructuralLoadCase` body-load layer (`load_cases.py`). This is the
  `G-2` deliverable Phases S/O size against. MUST.

### Load-chain reference (`engineering_basis.md` §3–§4; per mast, design = static × DAF)

| Case | Category | Source planform | q | C | Design bending | Note |
|---|---|---|---|---|---|---|
| **OP-1** | operational | wingsail (RM-capped) | ~74 Pa | — (RM-limited) | **~115–129 kN·m** | 50:50; deflection/twist |
| **OP-2** | operational | wingsail, worst mast | ~74 Pa | — (0.70·RM) | **~160–180 kN·m** | 70:30; **GOVERNS spar** |
| SURV-1 | survival | bare mast `A_mast` | 1621 Pa | Cd 0.02–0.10 | ~8–39 kN·m | feathered; below op |
| SURV-1f | survival (fault) | bare mast `A_mast` | 1621 Pa | Cl 1.0–1.2 | ~390–470 kN·m | feathering-fault; D-2 |
| SURV-2 | survival (bound) | bare mast `A_mast` | 3042 Pa | Cl off-axis | ~730–880 kN·m | Cat-5 sensitivity |
| (locked) | survival (worst) | bare mast `A_mast` | 1621 Pa | Cd 1.5 | ~590 kN·m | locked broadside |
| torque | all | — | — | Cm −0.16 | ~6–9 kN·m | ±45° plies / bearing |

## Acceptance

A load case counts only if its derivation reproduces the basis chain and is **honest about
provenance** (Article IV: every derived input flagged by sensitivity). Phase A ships verified
loads + measured example wall-clock — no FEA mass this phase.

- `R-AE-1` — a test reproduces the basis §3 operational chain: RM_max 200 → 50:50 100 kN·m →
  ÷14.0 m → ×10.7 m → ×DAF 1.5 = **OP-1 ≈ 115 kN·m** (and 129 at RM 225), to the digit.
- `R-AE-2` — the tandem model returns a slot-effect enhancement vs spacing and the 50:50 /
  70:30 split; **OP-2 ≈ 160–180 kN·m** = 0.70 × the RM-capped per-rig moment.
- `R-AE-3` — the survival builder reproduces **SURV-1 ≈ 8–39 kN·m** (feathered) and
  **SURV-1f ≈ 390–470 kN·m** (fault, Cat 3) on `A_mast` at the stated q/C; SURV-1 < OP-2.
- `R-AE-4` — the feathering study returns a numeric `AoA_max`, vane slope, yaw damping, Scruton,
  and the feathering-fault FoS; and **states the governing case** for a given robustness input.
- `R-AE-5` — drag + torsion distributions exist and integrate to the case totals (force/torque
  conservation, like the existing normal-force projection); torque ≈ 6–9 kN·m design.
- `R-AE-6` — DAF applied; a Strouhal/Scruton lock-in check returns a margin (or flags it).
- `R-AE-7` — an `examples/` script builds the tandem model and **emits the typed OP/SURV
  collection**, naming the governing case; a test asserts the collection's categories +
  magnitudes match the basis bands; measured wall-clock recorded.

**Deliverable & gate (whole phase):** green fast suite; the tandem aero model + the typed
design-load collection in `src/`; the feathering-robustness (D-2) study with a reported
`AoA_max` + governing-case verdict; a runnable example; a recorded finding (Articles I, IV,
VII). Closing this gate **resolves D-2** (records the verdict in `findings.md` + updates the
spec's `D-2` row) and **feeds Phase O** (the cases to size against) and **Phase S** (the
distributed loads + which cases to eigen-verify).

## Decisions & assumptions (with sensitivity — Article IV)

- `D-AE-a (RM_max = 200 kN·m central)` — `D-1`; the **dominant linear sensitivity** on ALL
  operational loads (every OP-* scales linearly with RM). Bracket 150–225; *Action:* pin from
  the real stability curve. Phase A parameterises it; the headline carries the central value +
  the ±sensitivity band.
- `D-AE-b (operational governs, under reliable feathering)` — survival = the **bare wingmast**
  (sail furled) feathered ⇒ drag-dominated, below OP-2; so **OP-2 (70:30) governs the spar**
  (basis §4 correction, 2026-06-16). This holds **iff** `R-AE-4` demonstrates robust feathering;
  if not, SURV-1f governs by several-fold. The whole project's mass hinges on this — `D-2`.
- `D-AE-c (survival is analytical, not ASB)` — feathered/stalled/bluff-body survival loads use
  `q·C·A·arm` with tabulated Cd/Cl, **not** the lifting-line solver (invalid at high AoA). ASB
  is used only for the **attached-flow operational** tandem case.
- `D-AE-d (feathering study is analytical baseline)` — `R-AE-4` ships a weathervane /
  yaw-damping / Scruton engineering model (pivot-vs-AC restoring moment, AoA stops, VIV
  detuning, redundancy); **CFD/unsteady aeroelastic is a flagged follow-up** (`OUT-3`), not a
  Phase-A blocker. The reported `AoA_max` carries its method + uncertainty.
- `D-AE-e (cambered operating section)` — the symmetric NACA-0018 is the *faired mast*; the
  *operating* section is **cambered** (soft sail sheeted, CL ≈ 1.45) to hit the §5 area (`D-4`).
  Operational lift uses the cambered polar; the bare-mast survival uses the symmetric section.

## Open questions / decision gates
- **`D-2` (the gate)** — `AoA_max` + the required feathering-fault FoS + whether SURV-1f
  governs. Resolved *within* this phase (`R-AE-4`); the verdict + its robustness assumptions
  recorded in `docs/findings.md`, and the spec's `D-2` row updated.
- **`D-1`** — the real RM/stability curve (replaces the 200 kN·m central). Dominant sensitivity;
  pin before any *absolute* mass headline (methodology proceeds without it).
- **`D-4`** — the cambered operating CL / sail area (150–180 m²) and the final **`c_mast`**
  (sets `A_mast`). Phase A carries placeholders + the sensitivity.
- Ground-plane image fidelity (root deck/sea reflection) — modelled or bounded? A `plan.md`
  build choice; AeroSandbox LiftingLine has no native ground plane.
