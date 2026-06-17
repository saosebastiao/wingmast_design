# Plan — Structural: journal BCs + box-spar mechanics (Phase S)

**Parent spec:** `./spec.md`

## Reuse (from the audit verdicts + the Phase-S code survey)

- **Keep (unchanged — math-validated):** `structural/shell.py` (DKT+CST shell K, laminate
  element, stress recovery), `structural/beam_shell.py` (the combined beam+shell assembly +
  `fixed_nodes` solve), `structural/frame.py` (`BeamSection`, beam element stiffness),
  `structural/eigen_buckling.py` (`linear_buckling`), `structural/geometric_stiffness.py`
  (`assemble_geometric_stiffness`), `structural/buckling.py` (closed-form util checks),
  `materials/unidir.py` (`laminate_stiffness`, the A/D path — `tri_element_stiffness_laminate`
  already accepts arbitrary per-tri A/D), `materials/failure.py` (Tsai-Wu/max-strain).
- **Refactor:** `structural/projection.py` (+ a new mast projector) — variable-section + add
  chordwise-drag + torsion (today normal-only); `structural/mesh.py` / a new mast-mesh builder
  off `RotatingMastSpec` + `box_spars.SparSection` (today uniform-wing + root clamp).
- **New (`src/`):** the **journal-BC** assembly (finite-stiffness radial springs + released
  pivot + heel thrust); a **`BoxSection`** primitive (web/cap/wall → A,I,J + analytic
  derivatives) + web-shear/cap-compression **local-buckling** constraints + KS providers; the
  **box-spar topology** mesh (spars + longerons as beams, wound shell as skin); the **co-bond
  interface** (finite stiffness + ILSS check); the **helical θ(z) → A/D** wrapper.
- **Freeze (`OUT-3`):** the legacy form-beam `beams/shell_model` arc-spaced model — superseded.

## Steps

1. **Pin the green baseline.** `just test` (currently 289 passed); record count + wall-clock.
2. **S.1 — journal BCs (highest priority).** New `structural/journal_bc.py`: augment the
   stiffness with **radial penalty springs** at the two bearing nodes (cross-axis translations),
   leave the pivot-axis rotation free, react axial thrust at the heel. Provide
   `apply_journal_bcs(K, nodes, partners_z, heel_z, k_radial, ...)`. Tests per `R-S-1`
   (supported radially, pivot free, thrust reacted, reaction equilibrium, buckling boundary
   differs from clamp). Reuse the existing solve once K is augmented.
3. **S.3 — box-spar section.** New `structural/box_section.py` (or extend `frame.BeamSection`):
   `BoxSection(web_height, cap_width, wall)` → A, Iy, Iz, J + **analytic** `dA/d·`, `dI/d·`;
   web-shear + cap-compression local-buckling utils + KS providers. **FD-validate** every
   derivative (Article IX; `tests/beams/test_sensitivity.py` pattern) **before** anything
   consumes it.
4. **S.2 — mast mesh + projection.** New `structural/mast_mesh.py`: build the spanwise beam
   grid (box spars at the `SparSection` web positions, longerons in the channels) + the skin
   shell from `RotatingMastSpec`; tag the two bearing stations. Extend `projection.py` with
   chordwise-drag + torsion distribution (mirror the force-conserving normal lumping). Load-
   conservation test (`R-S-2`).
5. **S.5 — helical anisotropy.** New `materials` wrapper `helical_laminate(ply, theta_deg(z),
   thickness)` → A/D for the wound shell (reuses `transformed_Qbar`); θ=45° reproduces the ±45
   result. Feed per-element A/D to `tri_element_stiffness_laminate` (already accepts it).
6. **S.4 — co-bond interface.** Extend the stiff-bond primitive (`beams/tip_coupling` clique)
   to a **finite-stiffness** connector + an **ILSS** shear/peel util from the recovered
   interface force; assert it is not the binding constraint at the reference (`R-S-4`).
7. **S.6 — eigen verification.** Wire `assemble_geometric_stiffness` + `linear_buckling` for the
   box-spar mast at **n ≥ 24**; survival judged solely on the converged eigen (`D-S-c`).
8. **S.7 — the deliverable solve.** `examples/<NN>_mast_structural.py`: solve **OP-2 + SURV-1f**
   on the box-spar mast with journal BCs, recover stress/journal-reactions/interface-utils, run
   the n≥24 eigen, report `R-PERF-1…7` with measured wall-clock. Smoke test + recorded finding.
9. **Re-run `just test`** → matches/exceeds the step-1 baseline; record wall-clock; eigen-verify
   the survival case at n≥24 (Article III); milestone export if a headline (Article XI).

## Deliverable & gate

Runnable `examples/<NN>_mast_structural.py` solving OP-2 + SURV-1f with journal BCs + box spars,
eigen-verified at n≥24 + the `R-PERF` metrics; green fast suite; FD-validation tests for every
new analytic gradient (Article IX); a recorded finding (measured wall-clock; converged +
feasible per case). Closing the gate **feeds Phase O** (the design vector + gradients) and
**Phase M** (allowables).

## Risks / dependencies

- **Depends on:** Phase G (the box-spar `SparSection` geometry at mast scale) + Phase A (the
  typed OP-2 / SURV-1f loads). Both on `main`.
- **Feeds:** Phase O (minimise mass over this model + its analytic gradients), Phase M (pin ply
  + bondline allowables), Phase V (aeroelastic closure on the structural model).
- **Biggest risks (survey):** (1) **journal-BC formulation** — new; the buckling boundary must
  be re-verified vs the clamp (`D-S-a` mitigates with a physical finite-stiffness model).
  (2) **box-spar section + local buckling + analytic gradients** — new from scratch; FD-validate
  first (step 3). (3) **survival non-conservatism** — judge SURV-1f on the n≥24 eigen, not the
  closed form (`D-S-c`; the prior project's slam lesson). (4) **variable-section mesh
  convergence** — re-check the n≥24 rule on the transition zone. (5) **slender mast (AR ~25)** —
  buckling/stiffness may dominate in a thin section carrying ~160 kN·m; the topology (`D-S-b`)
  may need the longerons/shell as real load path, surfaced once the solve runs.
- **Decision gates:** none block Phase S; `D-1`/`D-4` (RM, c_mast) stay parameterised (they
  scale the loads + the geometry, not the structural method). The journal **bearing stiffness**
  value is a flagged input (`D-S-a`).
