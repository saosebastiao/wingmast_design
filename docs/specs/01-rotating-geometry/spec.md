# Spec — Rotating wingmast geometry (Phase G)

**Status:** draft · **Parent:** `docs/specification.md` `R-GEO-1…5`, `R-CON-1`, goal `G-1` ·
`docs/plan.md` Phase G · numbers from `docs/engineering_basis.md` §1–§2, §7 · Constitution
Articles **V** (manufacturability), **XI** (regenerable CAD), **XIII** (spec-driven).

## Scope

The parameterized **rotating-wingmast CAD model**: the bottom-to-top anatomy (heel-step →
stock → deck-partners → transition → tapered airfoil wing → tip), arbitrary Kulfan/CST
airfoils, the manufacturing geometry (≥3 filament-wound hollow **box spars** + inter-spar
**longeron channels** + filament-wound **outer shell**), and a **geometric-fit** validator —
producing a valid assembly that passes `R-CON-1` and exports to STL/STEP. This **substantially
advances `G-1`**: Phase G ships the **OML twin-mast assembly** (exported) + the **validated
2-D box-spar / longeron / shell section set** + the fit validator; the **walled 3-D
box-spar/longeron/shell solid assembly** that `G-1`'s text names is **deferred to the Phase-S
mesh** (the section set is built to feed it). The headline is therefore *partial* `G-1`
closure, not full.

Phase G builds **geometry only**. It produces the OML + member CAD and the typed parameter
set (bounds + increments) that Phases A (aero load surface) and S (structural mesh / box-spar
mechanics) consume. It does **not** solve aero, apply journal BCs, mesh for FEA, size plies,
or compute winding feasibility (those are Phases A/S/M).

### Out of scope
- `OUT-1` Aerodynamic loads, the tandem slot effect, survival/feathering — Phase A.
- `OUT-2` Journal/bearing **boundary conditions**, FEA mesh, box-spar **mechanics/sizing** —
  Phase S. Phase G models the journal **zones** as geometry (bearing stations), not BCs.
- `OUT-3` Filament-winding **angle feasibility**, integer-ply **thickness**, co-bond
  **allowables**, manufacturing-process **sim** — Phase M. Phase G honours windable *shape*
  (convex spars, blend-curve corners, taper for release) but assigns no wind angles/plies.
- `OUT-4` The legacy shell-beam **form-beam** frame (`beams/build.py` arc-spaced perimeter
  beams) is **not** extended; the box-spar geometry supersedes it for the re-scoped structure.
  Form beams stay only as the frozen shell-beam baseline.
- `OUT-5` `c_mast` (bare-wingmast survival chord) is **carried as a parameter** but its
  pinned value is a Phase-A/`D-4` decision — Phase G ships the placeholder + the geometry
  that consumes it.

## Requirements

- `R-GG-1 (Kulfan/CST airfoils)` — *(parent `R-GEO-4`, `R-GEO-3`)* The airfoil source **MUST**
  support arbitrary **Kulfan/CST** parameters (not only NACA), preserving the project's
  closed-contour ordering — `(N,2)`, cosine-spaced, **upper-TE → LE → lower-TE**, duplicate TE
  dropped before a periodic spline. It **SHOULD** wrap AeroSandbox's Kulfan (already a
  dependency) rather than hand-roll CST. **NACA-0018 MUST be reproducible** as the reference
  default (CST fit to the existing `naca_00xx_coords` within a stated tolerance). Root and tip
  airfoils **MAY** differ with a spanwise CST-weight blend (`R-GEO-3`). MUST.
- `R-GG-2 (rotating-mast geometry stack)` — *(parent `R-GEO-1`, `R-GEO-2`)* The model **MUST**
  represent the full anatomy as distinct, named spanwise **zones** with their own Z-extents:
  **heel-step** (lower journal) → **stock** (rotating circular section, the bury through the
  hull) → **deck-partners** (upper journal) → **transition** (circular→airfoil) → **wing root**
  → tapered **airfoil wing** → **tip**. It **MUST** carry the **rotational-center foil offset**
  — the rotation axis position on the chord (`rotation_center_xc`) — as a parameter; this is
  the geometric rotation axis (the structural inscribed-circle uses the same axis) and is
  **distinct from the aerodynamic center-of-moment**, a Phase-A quantity (`R-GEO-2`). It
  **MUST** support **entasis** (convex spanwise bow of the wing loft-axis above the root,
  `D-5`). The two journal **stations** (heel + partners) are tagged on the geometry for Phase
  S. MUST.
- `R-GG-3 (box-spar + longeron-channel + shell geometry)` — *(parent `R-GEO-5`)* The geometry
  **MUST** represent the prescribed build: **≥3 convex box spars** (LE curve section, ≥1
  center section, TE curve section) with **blend-curve corner radii**; the **inter-spar
  longeron channels** whose cross-section is **computed from the blend params** (corner radius
  → void size — the blend-radius→longeron coupling); and the **outer shell** to the OML.
  **Phase-G fidelity (honest scope):** the spars are modelled as a **chordwise partition** of
  the OML section — simple, convex, filleted-corner *cells* (solid bands sampled off the OML
  surfaces; the spar **wall** and the longeron **void** are placeholder *areas*, not modelled
  cavities), and the outer-shell polyline **coincides with the OML** (no wall inset). The
  **walled hollow tubes + inset shell surface + the slight taper-for-release** (manufacturing
  shape) are part of the **deferred Phase-S/M** build, not Phase G. A 3-part **cored** shell is
  **MAY** (only if Phase-S stiffness forces it). MUST.
- `R-GG-4 (geometric-fit constraint)` — *(parent `R-CON-1`)* A validator **MUST** confirm, at
  every spanwise station, that box spars + longerons + shell **fit within the faired OML** and
  members **may touch but MUST NOT intersect** (within a clearance tolerance). It returns a
  boolean feasibility + the **binding station and signed margin**. MUST.
- `R-GG-5 (parameter bounds + increments)` — *(parent `R-GEO-2`)* **Every** design parameter
  **MUST** carry an explicit **(lower, upper, increment)**, seeded from basis §2, as the typed
  geometry parameter set in `src/`. This is where the spec's "all parameters have bounds and
  increments" is satisfied (`docs/specification.md` §3). The table below is normative. MUST.
- `R-GG-6 (deliverable: assembly + export + fit smoke test)` — *(parent `G-1`, Article XI)* A
  runnable `examples/` script **MUST** build the full parameterized rotating-mast assembly at
  the Oyster-595 twin-rig reference parameters and export **STL + STEP**; a **geometry-fit
  smoke test** asserts `R-GG-4` passes on the reference design and **fails** on a deliberately
  over-thick member (the validator actually bites). MUST.

### Normative parameter set (`R-GG-5`)

Seeded from `docs/engineering_basis.md` §2 (assumed concept — values marked *TBD* await the
cited decision; bounds/increments are engineering ranges, not yet optimised). Per mast.

**The chords below are the BARE WINGMAST (the rigid structure we optimise, ~0.5–1.0 m), NOT
the ~3–4 m wingsail.** The wingsail (mast + deployed soft sail) is the **aerodynamic** surface
that sets the operational loads (Phase A) — it is an *aero* parameter (~3–4 m chord, basis §2),
not part of this structural geometry. The mast `root_chord` here **is** the swept bare-mast
chord (it subsumes the former separate `c_mast`); the survival aero (`aero/survival.py`) uses
the same mast chord for `A_mast`. (Corrected 2026-06-17 — the geometry was initially built at
the wingsail chord.)

| Parameter | Default | (lower, upper) | increment | Source / note |
|---|---|---|---|---|
| Exposed mast span (above partners) | 22.0 m | (18.0, 26.0) | 0.5 m | basis §2 (= wingsail span) |
| **Mast** root chord | 1.0 m | (0.5, 1.0) | 0.05 m | bare-mast chord, swept DV (`D-4`); **not** the 4 m wingsail |
| **Mast** tip chord | 0.6 m | (0.3, 0.7) | 0.05 m | taper ~0.6 |
| Taper ratio (tip/root) | ~0.60 | (0.4, 0.9) | 0.05 | **derived** from root/tip chord — not an independent DV / not in `GEOMETRY_PARAMS` |
| Airfoil t/c (ref) | 0.18 | (0.15, 0.30) | 0.01 | NACA-0018 ref; CST weights are the true DV (t/c may grow for structural depth) |
| Rotational-center foil offset (x/c) | 0.25 | (0.20, 0.35) | 0.01 | basis §2 (axis ~0.25c) |
| Entasis (max convex bow / span) | 0.0 | (0.0, 0.03) | 0.005 | `D-5` **resolved**: sin-bow of the loft axis, composes with taper |
| Stock (base) diameter | inscribed @ root (~0.16 m) | (0.08, 0.20) m | 0.01 m | ≤ inscribed circle at the mast root |
| Stock length (deck→heel bury) | 3.1 m | (2.5, 4.0) | 0.1 m | basis §2; **hull-set**, not chord-set |
| Transition length (circle→airfoil) | 0.9 m | (0.5, 1.5) | 0.1 m | existing `WingSpec` |
| Mast spacing (axis-to-axis) | 6.0 m | (4.0, 8.0) | 0.25 m | basis §2; **aero-set** (~1.5·wingsail c) |
| Box-spar count | 3 | (3, 5) | 1 | `R-GEO-5` (LE + center(s) + TE) |
| Box-spar blend-corner radius | 0.015 m | (0.008, 0.030) | 0.002 m | mast-scale → longeron-channel void |
| Box-spar wall (geometry placeholder) | 0.004 m | (0.002, 0.010) | 0.001 m | true value sized in Phase O |
| Outer-shell wall (geometry placeholder) | 0.003 m | (0.002, 0.008) | 0.001 m | true value sized in Phase O |

## Acceptance

A result counts only with a green fast suite + measured wall-clock for the example
(Constitution I, II). Geometry phase ships valid CAD, not a sizing optimum.

- `R-GG-1` — a unit test fits CST weights to NACA-0018 and asserts the contour matches
  `naca_00xx_coords(0.18)` within a stated max-deviation tolerance; asserts the ordering
  convention (first/last at TE, LE at the min-x index) and closed-contour periodicity; asserts
  a root≠tip blend produces a monotone intermediate section.
- `R-GG-2` — a test asserts each zone's Z-extent is contiguous and ordered
  (heel < stock < partners < transition < root=0 < tip), the journal stations are tagged at
  the right Z, and the rotational-center offset shifts the section vs the pivot as specified;
  entasis=0 reproduces the straight loft.
- `R-GG-3` — a test builds the box-spar + longeron + shell section set at the root and asserts
  ≥3 convex spars, blend-radius→channel-void coupling (larger blend ⇒ larger longeron void),
  and that the outer shell encloses them.
- `R-GG-4 / R-GG-6` — the geometry-fit smoke test: `R-GG-4` **passes** on the reference design
  and **fails** when a spar wall/blend is inflated past the OML (the validator bites); the
  example builds the assembly and writes STL + STEP to `exports/` (regenerable; Article XI).
- `R-GG-5` — a test asserts every parameter in the normative table exposes (lower, upper,
  increment) with default within bounds, and that the reference assembly is built from it.

**Deliverable & gate (whole phase):** green fast suite; the typed parameter set + the
parameterized assembly builder in `src/`; a runnable example exporting the twin-rig STL/STEP;
the geometry-fit smoke test; a recorded finding (measured wall-clock; Articles I, VII, XI).
Closing this gate **feeds Phase A** (OML for the aero surface) and **Phase S** (box-spar
sections + journal stations for the structural mesh).

## Decisions & assumptions

- `D-GG-a (Kulfan via AeroSandbox)` — use ASB's Kulfan implementation (already a dependency)
  as the CST engine, wrapped to the project's contour ordering; do not hand-roll CST. Tightens
  Article V (single airfoil source) + avoids a re-derivation. *Sensitivity:* none on loads;
  airfoil shape is a downstream aero/area lever (`D-4`).
- `D-GG-b (≥3 box spars, default 3)` — LE-curve + one center + TE-curve, blend-curve corners;
  bounds [3,5]. The blend-corner radius is the **coupling parameter** (corner radius → longeron
  channel void → Phase-S longeron area). Tightens `R-GEO-5`/Article V.
- `D-GG-c (cored shell is MAY)` — build the single filament-wound shell by default; the 3-part
  cored shell is built only if Phase-S stiffness demands it (labour cost — basis §7). Honours
  the spec's "avoid unless necessary".
- `D-GG-d (geometry placeholders for wall/ply)` — spar/shell wall thicknesses are **geometry
  placeholders** here; the true values + integer plies are sized in Phases O/M. Phase G must
  not present a wall as a sized result (Article V honesty).
- `D-GG-e (compose, don't mutate the legacy WingSpec)` — reuse the audited `ruled=True` loft +
  smoothstep transition + airfoil ordering (all *keep*) via a behaviour-preserving `contour=`
  param on `wing.py`, and add a **new** `RotatingMastSpec` (zones, Kulfan airfoil, offset,
  entasis, box-spar layout) by **composition** — not by mutating the frozen demo `WingSpec`
  (mirrors the Phase-0 new-module discipline). Behaviour-preserving for the legacy NACA path
  (the legacy transition/wingsail tests stay green).

## Resolved during implementation (2026-06-16; see `docs/findings.md`)
- `D-5 (entasis)` — **RESOLVED:** entasis is a **separate sin-bow offset** of the wing
  loft-axis (section origin) above the root, peaking mid-span, 0 at root/tip and below the
  root (the stock/rotation axis stays straight) — **composes with** the chord taper rather
  than being expressed via taper knots. *(Implication: the bowed wing is offset from the
  straight rotation axis; on 360° rotation it sweeps — acceptable static geometry.)*
- `Build strategy` — **RESOLVED:** the box-spar geometry is **section-set + loft** (not
  watertight booleans) — lighter, OCC-boolean-free, and Phase-S-meshable.

## Open questions
- `c_mast` value (survival area) — `D-4`/Phase-A; Phase G carries the placeholder (`OUT-5`).
- Stock/journal exact dimensions (stock length 3.1 m, bury, bearing widths) — seeded from
  basis §2; refine when Phase S sets the bearing-couple model (`R-CON-3`).
- The **walled 3-D box-spar/longeron/shell** solid assembly (hollow tubes + inset shell +
  taper-for-release) — deferred to the Phase-S mesh; Phase G ships the 2-D section set it
  feeds (`R-GG-3` honest-scope note).
