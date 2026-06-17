# Plan — Rotating wingmast geometry (Phase G)

**Parent spec:** `./spec.md`

## Reuse (from the audit verdicts — `docs/plan.md`; confirmed by the Phase-G code survey)

- **Keep (unchanged):** the airfoil **contour ordering** convention (`geometry/airfoil.py`
  `naca_00xx_coords` — `(N,2)` cosine-spaced, upper-TE→LE→lower-TE, closed TE); the
  `ruled=True` loft strategy + the smoothstep transition `_transition_blend(u)=u²(3-2u)` and
  `_airfoil_to_circle_polyline` morph (`geometry/wing.py`); the `WingSpec` skeleton +
  `chord_at_z`/`section_z_fractions`/`spar_radius` machinery; `wingsails.py` named instances
  as the *small/medium demo* family.
- **Refactor / extend:** `geometry/airfoil.py` (add the Kulfan/CST source alongside NACA);
  `geometry/wing.py` `build_wing_solid` + `WingSpec` (add the heel/stock/deck-partners/journal
  zones, the rotational-center foil offset, entasis); `geometry/__init__.py` exports.
- **New (`src/`):** a Kulfan airfoil module; the typed geometry **parameter set** (bounds +
  increments, `R-GG-5`); the **box-spar + longeron-channel + outer-shell** geometry builder;
  the **geometric-fit** validator (`R-GG-4`); a twin-rig **assembly** builder.
- **Do not touch (`OUT-4`):** the legacy `beams/build.py` form-beam frame
  (`build_form_beams`, arc-spaced perimeter beams) — the box-spar geometry supersedes it; it
  stays the frozen shell-beam baseline. The existing param-based `beams.build_assembly` is the
  shell-beam assembly — leave it; the new twin-rig assembly is a distinct builder.

## Steps

1. **Pin the green baseline.** `just test`; record passing count + wall-clock (every step holds
   it). (The Phase-0 venv fix already restored green — `217 passed`.)
2. **G.1 — Kulfan/CST airfoils (`R-GG-1`).** New `geometry/kulfan.py` wrapping ASB's Kulfan
   → the project's `(N,2)` upper-TE→LE→lower-TE closed contour. Provide a NACA-0018 CST fit as
   the reference default; a per-station root→tip CST-weight blend (`R-GEO-3`). Unit-test the
   NACA match tolerance + ordering + blend monotonicity. Keep `naca_00xx_coords` as the
   validation oracle.
3. **G.2 — Rotating-mast geometry stack (`R-GG-2`).** Extend `WingSpec` with named zones
   (heel-step, stock, deck-partners, transition, wing) + Z-extents, the rotational-center
   **foil offset** (distinct from `pivot_frac`), and **entasis** (resolve `D-5`: spanwise
   loft-axis bow vs taper-knot — recommend a separate convex offset of the section centroid so
   it composes with taper). Tag the two **journal stations** on the result for Phase S.
   Reuse `build_wing_solid`'s ruled loft + transition; prepend the stock/heel/deck circular
   sections below the transition. Tests per `R-GG-2` acceptance.
4. **G.3 — Box-spar + longeron + shell geometry (`R-GG-3`).** New `geometry/box_spars.py`:
   given the OML section at a station + the box-spar layout (count, blend-corner radius), emit
   (a) ≥3 convex spar cross-sections with blend-curve corners, (b) the inter-spar longeron
   **channel** sections computed from the blend radius (the blend→void coupling), (c) the outer
   shell to the OML. Build-strategy decision (spec open-q): **section-set + loft** (lighter,
   Phase-S-meshable) over watertight booleans unless volume is needed. Cored shell stays a
   `MAY` flag. Tests per `R-GG-3`.
5. **G.4 — Geometric-fit validator (`R-GG-4`).** New `geometry/fit.py`: per-station
   point-in-polygon / clearance check that spars+longerons ⊂ OML and pairwise non-intersecting
   (touch allowed within `clearance_tol`). Return `(feasible, binding_station_z, signed_margin)`.
   If this term is later made **differentiable** for the optimizer, it gets an FD-validation
   test (Constitution IX) — **flag:** Phase G ships it as a *check* (non-differentiated), so IX
   is N/A here; note it for Phase O.
6. **G.5 — Typed parameter set (`R-GG-5`).** A frozen dataclass in `src/` carrying every
   normative-table parameter with `(lower, upper, increment)` + default; the twin-rig reference
   instance; consumed by the assembly builder. Test: every param has bounds; default ∈ bounds.
7. **G.6 — Twin-rig assembly + example (`R-GG-6`).** A `build_wingmast_assembly(params) ->
   Compound` composing OML + box-spars + longerons + shell + the two masts at `mast_spacing`;
   `examples/<NN>_rotating_wingmast.py` builds it at the Oyster-595 reference params, runs the
   fit validator, and exports STL + STEP to `exports/`. Geometry-fit smoke test (passes on
   reference, **fails** on an inflated member).
8. **Re-run `just test`** → matches/exceeds the step-1 baseline; record wall-clock. Milestone
   export (assembly viz, Article XI) — regeneration command in the finding.

## Deliverable & gate

Runnable `examples/<NN>_rotating_wingmast.py` + STL/STEP export + the geometry-fit smoke test +
the green fast suite + a recorded finding (measured wall-clock). No FEA/eigen this phase
(III N/A); milestone CAD export per XI. Closing the gate **feeds Phases A and S**.

## Risks / dependencies

- **Depends on:** Phase 0 (done — typed scaffolding, green suite). No upstream geometry blocker.
- **Feeds:** Phase A (OML → aero surface), Phase S (box-spar sections + journal stations → FEA
  mesh/BCs). Land the parameter set + assembler cleanly so A/S consume one source.
- **Decision gates:** none block Phase G. Carries `D-4` (`c_mast`) + `D-5` (entasis) as
  parameters; `D-5` is resolved *within* this plan (step 3), `D-4` stays Phase A.
- **Risk:** build123d 0.10.0 has **no** Kulfan/CST primitive (survey) → G.1 hand-wraps ASB
  Kulfan; **no** boolean-intersection helper relied on → G.4 uses polygon clearance math, not
  CAD booleans (also faster/meshable). **Risk:** the airfoil→circle morph assumes star-shaped
  sections w.r.t. the pivot — the rotational-center offset must keep sections star-shaped
  (assert it).
- **Risk:** scope. G.3 (box-spar/longeron/shell) is the largest new surface; if it slips, G.1+
  G.2+G.4 + a *single*-spar placeholder still close a runnable assembly + fit test (note any
  such de-scope explicitly in the finding — Article VII; no silent caps).
