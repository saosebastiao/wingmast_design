---
name: fusion-to-build123d
description: Use when converting a Fusion 360 design (or a Fusion 360 Python API script) into idiomatic build123d code — translating sketches, timeline features, parameters, constraints, components and assemblies, and resolving API / capability impedance mismatches (parametric timeline → linear script, persistent named entity references → geometric selectors, constraint solver → explicit coordinates, cm/radians → mm/degrees). Consult before hand-translating any Fusion model to build123d.
---

# Fusion 360 → build123d translation

> **The whole problem in one sentence.** A Fusion design is a *recorded, recomputable
> parametric history graph over a **named** B-rep, in **centimetre/radian** internal units*;
> a build123d design is *a linear Python program that builds an OCCT B-rep **once**, in
> **mm/degree** units, with **no history, no constraint solver, and no persistent entity
> names***. Translating = **flatten** the timeline into ordered statements · **lift** Fusion
> user-parameters to Python variables · **replace** the solver with explicit coordinate math ·
> **replace** named-entity references with re-evaluated geometric selectors · **convert**
> cm→mm / rad→deg.

**Authoritative bundled reference — read before translating anything non-trivial:**
- `reference/kb.md` — verified concept models (§1 Fusion, §2 build123d incl. the builder-vs-algebra rule §2.2), the **46-row concept/API mapping table (§3)**, **impedance catalog (§4)**, **7-step playbook with before/after code (§5)**, **gotchas (§6)**, ~60 cited primary-doc URLs (§7). Every API name was adversarially verified against the docs; corrections are flagged inline.
- `reference/mapping_table.csv` — §3 as machine-readable rows (`fusion_concept,fusion_api,build123d_idiom,build123d_api,fidelity,notes`). **Treat as the allow-list: never emit a build123d name that is not in here or kb.md.**
- `reference/fidelity_check.py` — runnable validator (build123d 0.10.0, already in the repo venv). Use it as the objective "done" gate.

Examples in kb.md §5 were executed against **build123d 0.10.0 in this repo's `.venv`** and produce the stated geometry; joint and hole signatures were introspected from that venv.

## Step 0 — decide the path (gate before any code)

- If the part uses **T-spline / sculpt / freeform / sheet-metal / direct-edit (`BaseFeature`) / mesh** bodies, OR you only need the *final geometry* (not editable parametrics) → **`import_step` the body and mark it frozen. Stop.** These are not history-reconstructible (kb.md §4.7). Do not attempt to re-author features.
- Otherwise → **code-to-code** translation via the playbook below.

## The 7-step playbook (full before/after code in kb.md §5)

1. **Lift parameters** → a single source of truth: module-level constants or a frozen `@dataclass`, **cm→mm**, keeping unit intent as `n * MM`. Cross-parameter Fusion expressions (`width = length/4`) become eager Python expressions (dependency *graph* lost, relationship preserved).
2. **Choose authoring mode** (builder vs algebra — table below; kb.md §2.2).
3. **Translate sketches: solver → explicit geometry.** Read the *solved* coordinates (cm→mm); replace constraints with explicit coords / Python math; replace tangency with `TangentArc`/`RadiusArc`/`JernArc`/`SagittaArc`/`DoubleTangentArc`. `sketch.profiles.item(0)` → the `BuildSketch` result or `make_face()`.
4. **Flatten the timeline** → one ordered build123d statement per feature node. Map `FeatureOperations` → `Mode` (Join→`ADD`, Cut→`SUBTRACT`, Intersect→`INTERSECT`; NewBody/NewComponent → a *separate* `Part`/`Compound`, **not** a mode). Angles **rad→deg**.
5. **Translate entity refs → robust selectors** (see hard rule). Inside builders use `Select.LAST`/`Select.NEW` for the just-created geometry.
6. **Reconstruct assembly:** each `Component` → a `Part`/function; each `Occurrence` → a placed child (`transform2` is **cm** → `Location`, ×10); reuse via `copy.copy()` then place; joints → build123d joint classes + `connect_to`.
7. **Verify** with `reference/fidelity_check.py` before calling it done.

## Hard rules — these prevent the two high-severity failures (and the silent ones)

- **UNITS (silent 10× / 57.3× bug, kb.md §6.1).** *Every* Fusion API length is **cm**, *every* angle is **radians**, regardless of the document's display units. `ValueInput.createByReal(2)` = 2 cm = **20 mm**. Centralise conversion in one helper, unit-test it, write build123d dims as `n * MM`. A missed conversion yields a valid-*looking* model that is silently wrong.
- **SELECTORS — never index raw (topological naming, kb.md §4.2).** build123d has no persistent entity names and **list order is not guaranteed stable**, so `part.edges()[3]` is a time bomb. Translate the *intent*: select from high topology first, then filter by stable geometric property — e.g. `fillet(part.faces().sort_by(Axis.Z)[-1].edges().filter_by(GeomType.CIRCLE), radius=1)`. If a selection is genuinely ambiguous, emit `# TODO: REVIEW ambiguous selector` and ask a human — do **not** guess.
- **NO INVENTED API NAMES.** Only emit names present in `mapping_table.csv` / kb.md. Verified hallucination traps: **no `shell()` method** → `offset(..., amount=-t, openings=face)` or `thicken`; **`Rectangle(width, height, ...)` has no `length`**; **no `PinSlotJoint`, no planar joint, no IGES/SAT, no `.f3d`/`.f3z`**; chamfer in Fusion uses `createInput2()` + `chamferEdgeSets` (old `createInput` path retired Dec 2020); `FeatureOperations` members carry the `FeatureOperation` suffix (`CutFeatureOperation`, not `Cut`). When you meet an unmapped feature, **fail loudly with a kb.md §4 pointer** — never improvise a name.
- **MODE IS EXPLICIT.** build123d builder objects combine *on instantiation* per their `Mode` (defaults vary: `Hole`→SUBTRACT, `offset`/`split`/`scale`→REPLACE, most ops→ADD). Pass `mode=` matching the `FeatureOperation`; position **before** creating (a `.moved()` afterwards is a no-op on the running total).
- **CUT DIRECTION (verified trap).** When boring a hole from a face with `extrude(..., mode=Mode.SUBTRACT)`, extrude must go **into** the body — i.e. a *negative* `amount` along the (outward) face normal. A positive amount extrudes away from the solid and silently **removes nothing**. (Or use the `Hole` family, which bores inward by default.) This bites every Fusion "cut to depth from this face".
- **JOINTS — direction matters (verified).** Call `connect_to` on the **fixed** joint and pass the **moving** joint's DOF kwargs: `fixed.connect_to(mover, angle=…/position=…/angles=…)`. The reverse (`mover.connect_to(fixed, angle=…)`) runs without error but **silently ignores the kwarg**. `connect_to` keeps `self` fixed and repositions `other`; the moving side becomes a `RigidJoint` mate. Map slider→`LinearJoint`, cylindrical→`CylindricalJoint`, pin-slot→`LinearJoint`(+`angle`) or `CylindricalJoint` (note the lost 2nd constraint); planar → flag for review.

## Builder vs Algebra (kb.md §2.2 — they are equivalent over the same kernel)

| Choose | When |
|---|---|
| **Builder** (`with BuildPart()/BuildSketch()/BuildLine()`) | A short/medium **linear timeline** translated by hand; you want the pending-faces cascade (sketch → `extrude()` with no profile arg) and `Select.LAST` scoping; human readability. |
| **Algebra** (`+ - &`, place with `* Pos()*Rot()`/`Plane`) | **Programmatic** generation (loops/comprehensions/data-driven counts); explicit `*`-placement that mirrors Fusion's `transform2`/occurrence model; composing helper functions. **Often the more faithful target for Fusion.** |
| **Mixed** | Author sub-parts in algebra, `add()` them into a `BuildPart`. Legal and common. |

## Verify before "done"

```bash
# export your translated build123d result to STEP, then diff it against the Fusion STEP:
.venv/bin/python .claude/skills/fusion-to-build123d/reference/fidelity_check.py mine.step fusion.step
```
It compares volume / bounding-box / centre / solid & face counts and flags a ~10× (cm→mm) or ~57.3× (rad→deg) discrepancy. **Non-zero exit = not done.** Caveat: it catches *gross* geometry errors, not "filleted the wrong edge" — pair it with a visual check and the selector review.

## Current phase & what is *not* yet built

This is the **"skill + knowledge base" phase**. The fuller automation is designed in kb.md's architecture but **not yet built**: a Fusion add-in `fusion-intent-exporter` (emits `intent.json` + STEP + STL — timeline order, lifted params in raw cm/rad, *solved* sketch coords, per-reference selector fingerprints, `reconstructible` flags), a `fusion2b123d` converter package, and a packaged `b123d-fidelity-check`. **Today's workflow:** export STEP from Fusion (and share the timeline / parameters / a screenshot or the `.py` script), translate guided by this skill + kb.md, validate with `fidelity_check.py`. If you want the automated pipeline built, say so — the design is ready in kb.md.

## Known caveats needing human review (kb.md §4)

Ambiguous selectors · constraint loss (build123d has no solver — coords are a frozen snapshot) · loft **rails/centerline** (build123d `loft()` has only `ruled`) · guided sweeps · pin-slot/planar joints · T-spline/sheet-metal/freeform → STEP-and-freeze · STEP colour/label round-trip is undocumented. Surface these in a translation report rather than hiding them.
