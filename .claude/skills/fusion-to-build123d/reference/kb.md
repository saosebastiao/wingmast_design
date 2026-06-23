# Fusion 360 -> build123d translation knowledge base

A practitioner's reference for translating Autodesk Fusion 360 designs (and Fusion Python API scripts) into idiomatic **build123d** code. Every API name below has been confirmed against primary documentation (help.autodesk.com Fusion 360 API Reference / User's Manual; build123d.readthedocs.io; gumyr/build123d source). Hallucinated names flagged during verification have been corrected and are called out explicitly. Confidence is encoded in the fidelity column and in the per-row notes.

> **The one-sentence summary:** A Fusion design is a *recorded, recomputable parametric history graph over a named B-rep, in centimeter/radian internal units*; a build123d design is *a linear Python program that builds an OCCT B-rep once, in millimeters/degrees, with no history, no constraint solver, and no persistent entity names.* Translation = flatten the timeline into ordered statements, lift parameters to Python variables, replace the solver with explicit coordinate math, replace named-entity references with re-evaluated geometric selectors, and convert cm->mm / rad->deg.

---

## 1. Fusion 360 design-as-program mental model

A Fusion design is **not** a script you write top-to-bottom; it is a **parametric history graph** that the kernel records and recomputes. The Python API (`adsk.*`) merely drives that same recorder. Four nested ideas:

### 1.1 Object model (the runtime)
Three packages:
- **`adsk.core`** — `Application`, `UserInterface`, math (`Point3D`, `Vector3D`, `Matrix3D`), `ValueInput`, `UnitsManager`, `ObjectCollection`, base collections.
- **`adsk.fusion`** — the modeling model: `Design`, `Component`, `Occurrence`, `BRepBody`, `Sketch`, the feature collections, `Timeline`.
- **`adsk.cam`** — manufacturing (out of scope here).

Entry points are **not** `__main__`:
- A **script** defines `def run(context):` and dies when it returns.
- An **add-in** adds `def stop(context):` (the unload/cleanup hook) and persists for the whole Fusion session; you register event handlers in `run` and remove them in `stop`. *(Verified: `def run(context):` is the universal entry point for both; `def stop(context):` is add-in-specific.)*

Singleton root and the canonical descent:
```python
import adsk.core, adsk.fusion
app = adsk.core.Application.get()
ui  = app.userInterface
design = adsk.fusion.Design.cast(app.activeProduct)   # None-guard in real code
root   = design.rootComponent                          # read-only
```
Hierarchy: **Application -> Document -> Product(s) -> Design -> rootComponent**. Every design has exactly one `rootComponent`.

### 1.2 Timeline (the defining trait)
- `design.designType` is `adsk.fusion.DesignTypes.ParametricDesignType` or `DirectDesignType`. **Parametric records a `Timeline`; switching to Direct destroys the timeline and all history** — one-way, history-destroying. (This is a whole-design setting, equivalent to the UI "Capture Design History" toggle.)
- `design.timeline` exposes (verified verbatim): `count`, `item(i)`, `markerPosition` (0..count, 0 = beginning), `moveToBeginning`/`moveToEnd`/`moveToNextStep`/`moveToPreviousStep`/`play`, `deleteAllAfterMarker`, `timelineGroups`.
- Each feature has `.timelineObject` with `rollTo(rollBefore: bool) -> bool`.
- Editing an upstream node/parameter triggers **recompute** of all downstream nodes. **The graph is the source of truth; the geometry is its output.**

### 1.3 Sketches + constraint solver (2D intent)
- `sketch = component.sketches.add(planarEntity[, occurrenceForCreation])` where `planarEntity` is a `ConstructionPlane` (e.g. `xYConstructionPlane`) **or** a planar `BRepFace`.
- Geometry via `sketch.sketchCurves.sketchLines` / `sketchArcs` / `sketchCircles` / ... and `sketch.sketchPoints`. Point args accept `Point3D` **or** `SketchPoint` (the latter links parametrically).
- A **numerical constraint solver** enforces `sketch.geometricConstraints` (`addCoincident`, `addTangent`, `addParallel`, `addPerpendicular`, `addHorizontal`, `addVertical`, `addConcentric`, `addEqual`, `addMidPoint`, `addSymmetry`, ...) and `sketch.sketchDimensions` (driving dimensions: `addDistanceDimension`, `addRadialDimension`, `addAngularDimension`; each has `isDriving`). `sketch.isFullyConstrained` reports determinacy.
- **Profiles are auto-computed, read-only closed regions:** `sketch.profiles.item(0)`. You never author a `Profile`; features consume it. The solver auto-detects all closed regions (including nested islands) and indexes them.

### 1.4 Features, parameters, units
- Uniform **createInput -> configure -> add** pattern off `component.features.<xxxFeatures>`:
  ```python
  inp = component.features.extrudeFeatures.createInput(profile, operation)
  inp.setOneSideExtent(extentDef, direction)   # or setSymmetricExtent(dist, isFullLength, taper)
  ext = component.features.extrudeFeatures.add(inp)
  ```
  `add()` produces **both** geometry and a timeline node. Arity diverges by feature: loft is `createInput(operation)` then `loftInput.loftSections.add(profile)`; combine puts the boolean on `cInput.operation`.
- **`FeatureOperations` enum** (verified — members carry the `FeatureOperation` suffix): `JoinFeatureOperation`, `CutFeatureOperation`, `IntersectFeatureOperation`, `NewBodyFeatureOperation`, `NewComponentFeatureOperation`. (The bare forms `Cut`/`Intersect`/`NewBody` do **not** exist as standalone identifiers.)
- Numerics are `adsk.core.ValueInput`: `createByReal(x)` (raw, **internal units**) or `createByString('25 mm')` (unit-bearing expression; a bare `createByString('25')` is interpreted in the document's *display* units).
- Parameters: `ModelParameter` (auto-created, has `createdBy` + `role`, e.g. role `"Depth"` on an extrude) and `UserParameter` (`design.userParameters.add(name, value: ValueInput, units, comment)`). `design.allParameters` is everything. `.value` is a double in internal units (setting it **resets** the expression); `.expression` is a unit-aware string that may reference other parameters (a live dependency graph).
- **Internal/database units are CENTIMETERS** for length (area cm², volume cm³), **RADIANS** for angle, kg, s — regardless of display units (`design.unitsManager`, with `convert`, `evaluateExpression`, `formatInternalValue`). **This is the dominant translation gotcha.**

### 1.5 Topology & assembly
- B-rep hierarchy: `BRepBody -> BRepLump -> BRepShell -> BRepFace -> BRepLoop -> BRepCoEdge/BRepEdge -> BRepVertex`, plus flattened `body.faces/edges/vertices/shells/lumps`. (Fusion enforces exactly one lump per body.)
- **Topology vs geometry:** `BRepFace.geometry` -> unbounded `Surface`; `BRepEdge.geometry` -> `Curve3D` (e.g. `Line3D`/`Arc3D`). Evaluators (`BRepFace.evaluator` -> `SurfaceEvaluator`, `BRepEdge.evaluator` -> `CurveEvaluator3D`, with `getNormalAtParameter`/`getPointAtParameter`) map param<->3D space. Fusion advises preferring B-rep-object evaluators over geometry-object evaluators (they account for the rest of the body).
- Construction geometry uses the same throwaway-input pattern: `constructionPlanes.createInput()` -> one `setBy*` -> `add(input)`.
- **Component vs Occurrence vs Proxy:**
  - `Component` = a geometry/feature/parameter *definition* (`component.bRepBodies`, not repositionable).
  - `Occurrence` = a placed *instance* with `occurrence.component` and `occurrence.transform2` (a `Matrix3D` in **cm**).
  - `Proxy` = an instance-aware entity identity: `entity.createForAssemblyContext(occurrence)` -> proxy with `.nativeObject` (the underlying entity) and `.assemblyContext` (the **top-level** occurrence in the path); paths look like `Comp:1/RedFace`.
- **Persistent entity references:** the durable, saveable token is `entity.entityToken` (a string) resolved via `Design.findEntityByToken()`. `BRepFace.tempId`/`BRepEdge.tempId` are **NOT persistent** — valid only while the document is open *and* the body is unmodified. (Verification correction: earlier drafts mislabeled `tempId`/proxy paths as the persistence mechanism; the real persistent reference is `entityToken`/`findEntityByToken`, while proxy paths only disambiguate *instances*.)
- Assembly via `component.occurrences` (direct children; `allOccurrences` for the flat recursive list) and `component.joints` / `component.jointOrigins`.

### 1.6 Export
- `design.exportManager`: build an options object (`createSTEPExportOptions(filename[, geometry])`, `createIGESExportOptions`, `createSATExportOptions`, `createSTLExportOptions`, `createOBJExportOptions`, `createC3MFExportOptions`, `createFusionArchiveExportOptions`) — this *writes nothing* — then `exportManager.execute(options)`. (`execute` is on the **ExportManager**, not on the options object.)
- STEP/IGES/SAT/SMT carry only B-rep (no timeline/sketches/constraints/joints; STEP additionally carries partial colors/labels). Only the native `.f3d`/`.f3z` archive round-trips the editable design.
- Imported/history-less bodies in a parametric design must be wrapped in a `BaseFeature`: `baseFeatures.add()` -> `startEdit()` -> `bRepBodies.add(body, targetBaseFeature)` -> `finishEdit()`. (`targetBaseFeature` is required in parametric mode, ignored in direct mode.)

---

## 2. build123d idiomatic mental model

build123d is a thin Pythonic wrapper over OpenCASCADE (via the **OCP** binding — the same kernel CadQuery uses; build123d is "derived from portions of CadQuery, extensively refactored"). "Parametric" means **the Python source is the parameter set**: re-run the script with different variable values. There is **no recompute graph, no timeline, no constraint solver, and no persistent entity names.** Idiomatic build123d is three skills: the topology data model, picking one of two equivalent authoring modes, and re-selecting geometry by property every run.

### 2.1 Topology (the data model)
- Rooted hierarchy of `Shape` subclasses: **`Vertex`(0D) -> `Edge`(1D) -> `Wire` -> `Face`(2D) -> `Shell` -> `Solid`(3D) -> `Compound`**. Each wraps an OCCT `TopoDS_*` in `.wrapped`. `Shape` is an anytree `NodeMixin`, so shapes carry `.parent`/`.children`/`.descendants`.
- `Compound` subclasses tag dimensionality: **`Curve`(1D), `Sketch`(2D), `Part`(3D)** — these are the result types of the builders/algebra. `class Part(Compound)`.
- Everything is a **first-class Python value**: `r = Rectangle(w, h); print(r.area)`. Query with `.volume`, `.area`, `.center()`, `.bounding_box()`, `.geom_type` (a `GeomType` enum). Evaluation methods live directly on `Edge`/`Face`: `position_at`, `location_at`, `normal_at`, `tangent_at`, `param_at`, `arc_center`, `geom_adaptor()` (the OCCT-level handle). There is **no separate evaluator object** as in Fusion.

### 2.2 Builder mode vs Algebra mode — the decision rule

They are **equivalent over the same kernel**; pick per situation.

**Builder mode** — stateful context managers, beginner-friendly, tracks pending state:
- `with BuildPart() / BuildSketch() / BuildLine()` accumulate a "running total." Objects add themselves **on instantiation**, combined per their `Mode` (`ADD` default, `SUBTRACT`, `INTERSECT`, `REPLACE`, `PRIVATE`). `Hole`/`CounterBoreHole`/`CounterSinkHole` default to `SUBTRACT`.
- **Pending cascade:** a `BuildLine` exiting inside a `BuildSketch` hands up wires; a `BuildSketch` exiting inside a `BuildPart` hands up `pending_faces`. `extrude()`/`revolve()`/`loft()`/`sweep()` consume pending faces when called with no profile argument.
- **Position BEFORE creating** (a `.moved()` after creation is a no-op on the running total). Use `Locations`/`Pos`/`Rot` contexts.
- Result is read off the builder: `ex.part` (BuildPart), `bs.sketch` (BuildSketch), `bl.line` / `bl.wires()` (BuildLine).

**Algebra mode** — stateless, equation-like, preferred for programmatic generation:
- Objects combined with `+` (fuse), `-` (cut), `&` (intersect); `+=`/`-=`/`&=` idiomatic. Results are `Compound`s typed `Part`/`Sketch`/`Curve`.
- Objects have **no location parameter** — place with `*` (left-to-right in the accumulated LOCAL frame, **non-commutative**): `Plane.XZ * Pos(1, 2, 3) * Rot(0, 100, 45) * Box(1, 2, 3)`.
- **Operations are free functions taking the target explicitly:** `extrude(Circle(r), amount=h)`.
- Rule: algebra cannot be used *inside* a builder context, but algebra objects can be `add`ed into builders.

**Decision rule (use this):**

| Choose | When |
|---|---|
| **Builder mode** | Hand-translating a short/medium linear Fusion timeline; you want the pending-faces cascade (sketch -> extrude with no profile arg); you like `Select.LAST`/`Select.NEW` scoping to the last op; readability for humans. |
| **Algebra mode** | Generating geometry programmatically (loops, comprehensions, data-driven counts); you want explicit `*`-placement that mirrors Fusion's explicit `Matrix3D`/`transform2` model; composing functions/returning shapes from helpers; unit-testing intermediate shapes. |
| **Mixed** | Author sub-parts in algebra, `add()` them into a `BuildPart` for the final assembly — legal and common. |

For Fusion translation specifically, **algebra mode is often the more faithful target** because Fusion's `Move`/`Occurrence` model is explicit-transform, which maps cleanly onto `Location * shape`. Builder mode is more faithful for the *create-then-cut-then-fillet* timeline rhythm.

### 2.3 Locations / planes / workplanes (placement is arithmetic)
- `Location` = translation + rotation. `Pos` (position-only) and `Rot`/`Rotation` (rotation-only) are subclasses. `*` composes **left-to-right in the accumulated LOCAL frame and is non-commutative**: `loc * Rot(...) * Pos(...)` ≠ `loc * Pos(...) * Rot(...)`.
- `Plane` is a coordinate system (origin + x/y/z_dir). Constants: `Plane.XY/XZ/YZ/YX/ZX/ZY` plus `front/back/left/right/top/bottom/isometric`. `Plane(face)` ("sketch on this face"; must be planar). Constructor `Plane(origin, x_dir=, z_dir=)` (give x_dir + z_dir **or** x_dir + y_dir, not all three; `z_dir` is the normal). Methods: `Plane.XY.offset(25)` (along normal), `plane.rotated((0,0,30))` (about the plane's own origin). `Plane(loc) *`, `Plane(face.location) *`, and `loc *` are equivalent.
  - build123d is unconditionally **Z-up, right-handed** (`Plane.XY` normal = +Z; `Plane.XZ` has x_dir=+X, y_dir=+Z, normal=-Y). Fusion's default modeling orientation is also Z-up (it was historically Y-up and is user-settable); both are right-handed. If a Fusion document was authored Y-up, imported geometry is rotated 90° about X.
- Workplanes are passed to builders: `BuildSketch(Plane.XZ)`, `BuildSketch(face)`, or `BuildSketch(*part.faces())` (every face). build123d sketches in a local XY frame, then relocates onto the given workplane.
- Multiple-placement contexts (they nest and multiply out): `Locations`, `GridLocations(x_spacing, y_spacing, x_count, y_count)`, `PolarLocations(radius, count, start_angle=0.0, angular_range=360.0, rotate=True)`, `HexLocations`.

### 2.4 Selectors (the replacement for "click a face"/named refs)
- Plural selectors `.vertices()/.edges()/.wires()/.faces()/.shells()/.solids()` return a **`ShapeList`** (a `list` subclass) **re-evaluated from scratch every run**.
- Refine by **stable geometric property**: `filter_by(GeomType.CIRCLE | Axis | Plane | lambda)`, `sort_by(Axis.Z | SortBy.RADIUS/AREA/...)`, `group_by(...)`, `filter_by_position`, then index `[0]/[-1]/[-2:]`. Operators: `|` = filter_by, `>`/`<` = sort_by, `>>`/`<<` = group_by-end, `[]` = index. Inside builders, `Select.LAST`/`Select.NEW` scope to the last operation.
- **Idiomatic:** select from high in topology, then filter — `fillet(part.faces().sort_by(Axis.Z)[-1].edges().filter_by(GeomType.CIRCLE), radius=1)`. Never rely on raw `[n]` indices into the full list (order is not guaranteed stable).

### 2.5 Operations, joints, assemblies, IO
- **Free functions** (algebra) / context-aware (builder): `extrude, revolve, loft, sweep, fillet, chamfer, offset, thicken, mirror, split, scale, project, make_face, add`. Default modes differ: extrude/revolve/etc. `ADD`; offset/split/scale `REPLACE`. **There is no method named "shell"** — hollow via `offset(..., amount=-t, openings=face)` or `thicken`.
- **Joints** (`build123d.joints`): `RigidJoint, RevoluteJoint, LinearJoint, CylindricalJoint, BallJoint` — **NO `PinSlotJoint`, NO planar joint.** Bind via the constructor's `to_part`/`joint_location`, reach via `part.joints["label"]`, wire with `a.connect_to(b, **kwargs)` (self fixed, other moves; the moving side becomes a `RigidJoint`). Kwargs by type: `RevoluteJoint` -> `angle`; `LinearJoint` -> `position` (+optional `angle`); `CylindricalJoint` -> `position`, `angle`; `BallJoint` -> `angles`; `RigidJoint` -> `angles`/`angle`/`position`.
- **Assemblies are just `Compound` trees** — no dedicated class: `Compound(label="asm", children=[a, b])`, set `.parent`. Labels are non-unique; each child carries a `Location`/`color`. Reuse a definition across instances with `copy.copy()` (shallow — children share the underlying OCCT TShape but carry independent `Location`s; `~550 KB` vs `~52 MB` for deepcopy in the docs' example) then place each copy.
- **IO:** `import_step(path) -> Compound` (reads colors+labels), `import_stl(path) -> Face` (mesh), `import_brep(path) -> Shape` (topology only); `export_step(shape, path, unit=Unit.MM, ...)`, `export_stl(shape, path, tolerance=, angular_tolerance=)`, `export_gltf`, `Mesher` (3MF), `ExportDXF`/`import_dxf`, `ExportSVG`/`import_svg`. **No IGES or SAT support** (Fusion's IGES/SAT have no build123d path; use STEP). **No `.f3d`/`.f3z`.**
- **Default/scale convention:** model is effectively unitless with the scalar constants `MM=1, CM=10*MM, M=1000*MM, IN=25.4*MM, FT=12*IN, THOU=IN/1000`; the **export default is `Unit.MM`**. Most constructors take **degrees**. Idiomatic to write dimensions as `80 * MM` to keep unit intent in-code.

---

## 3. Comprehensive concept / API mapping table

Fidelity legend: **direct** (1:1 semantic, only units/lifecycle differ) · **approximate** (maps with caveats / lost metadata) · **lossy** (significant semantic loss; translate *intent*) · **none** (no equivalent; use a workaround/bridge). All corrections from verification are applied.

| Fusion concept | Fusion API | build123d idiom | build123d API | Fidelity | Notes / corrections |
|---|---|---|---|---|---|
| Script/add-in entry point | `def run(context):` / `def stop(context):` | Plain Python module body (re-executed top-to-bottom) | `if __name__ == "__main__":` (optional) | approximate | `run` is the entry for both scripts and add-ins; `stop` is the **add-in** unload hook. build123d has no handler/lifecycle/add-in concept. |
| Application/Document/Product/Design root | `adsk.core.Application.get()`; `adsk.fusion.Design.cast(app.activeProduct)`; `design.rootComponent` | No app singleton; the built part is the root | `BuildPart()` -> `Part` / `Compound` | none | No document/product/application layer; geometry exists as Python objects. The `Part` (a `Compound`) is the de-facto root. |
| Parametric timeline (recompute graph) | `design.timeline` (`count`/`item`/`markerPosition`/`play`/`moveToEnd`/`deleteAllAfterMarker`); `Feature.timelineObject.rollTo(rollBefore)` | Linear script order; re-running the script IS the recompute | (no equivalent) | none | **Central paradigm gap.** No marker/rollback object. Flatten timeline into ordered statements. |
| Parametric vs Direct design mode | `design.designType = adsk.fusion.DesignTypes.ParametricDesignType \| DirectDesignType` | Always effectively history-free; the script is the parametric layer | (no equivalent) | none | No in-model history toggle; editability lives in source. |
| User parameter (unit-bearing expression) | `design.userParameters.add(name, value: ValueInput, units, comment)`; `param.expression` | Module-level Python variable / dataclass field | `length = 80 * MM` | approximate | Keep unit intent via `* MM`/`* IN`. **What is lost is the expression dependency graph** (cross-parameter symbolic recompute), not the unit. |
| Model parameter (auto, role-tagged) | `ModelParameter` (`createdBy`, `role` e.g. `"Depth"`) | The literal/variable passed into the op | `extrude(amount=thickness)` | approximate | No separate parameter object; the value is just the argument. |
| Numeric value input | `adsk.core.ValueInput.createByReal(cm)` / `createByString('25 mm')` | Python float (mm) or `n * MM` | `25.0` / `25 * MM` | approximate | `createByReal` is in **cm**; `* 10` to reach mm. `createByString` expressions de-parameterize to a literal float (build123d has no expression engine). |
| Internal units (length=cm, angle=rad) | `design.unitsManager` (`convert`/`evaluateExpression`); database cm/radians | Unitless model, `MM=1` scale; export defaults `Unit.MM`; angles in degrees | `MM/CM/M/IN/FT/THOU`; enum `Unit.MM/CM/...` | approximate | **HIGH-RISK:** ×10 cm->mm; ×(180/π) rad->deg. A missed conversion is a silent 10× / 57.3× scale error. `Unit` (export enum) ≠ the scalar constants. |
| Create a sketch on a plane/face | `component.sketches.add(planarEntity[, occurrenceForCreation])` | Open a `BuildSketch` on a workplane or face | `with BuildSketch(Plane.XY): ...` / `BuildSketch(part.faces().sort_by(Axis.Z)[-1])` | direct | Construction plane -> `Plane` constant; planar `BRepFace` -> `Plane(face)` or pass the `Face` directly (must be planar). |
| Sketch line/arc/circle geometry | `sketch.sketchCurves.sketchLines.addByTwoPoints` / `sketchArcs.addByCenterStartSweep(center, start, sweepAngle)` / `sketchCircles.addByCenterRadius` | 1D objects in `BuildLine`, or 2D primitives directly | `Line, Polyline, CenterArc, ThreePointArc, RadiusArc, Spline, Bezier`; `Circle, Rectangle, Ellipse, RegularPolygon` | direct | Coords cm->mm; arc `sweepAngle` **radians -> degrees**. Fusion `addByCenterStartSweep` has no radius arg (implied by start point); a build123d `CenterArc` takes explicit center/radius/start_angle/arc_size — convert, or use `RadiusArc`/`ThreePointArc`. |
| Geometric constraints (coincident/tangent/parallel/...) | `sketch.geometricConstraints.addCoincident/addTangent/addParallel/addPerpendicular/addHorizontal/...` | **No solver:** bake relationships into explicit coordinates / Python math; tangent-aware constructors only for tangency | `TangentArc, SagittaArc, JernArc, DoubleTangentArc`; coords computed in Python | lossy | **HIGH loss.** Read SOLVED coordinates at translation time. Tangency -> special arcs; everything else (coincident/parallel/perp/equal/concentric/symmetric/midpoint) -> computed coords / shared `Vertex`. Relationships do not self-correct on later edits. |
| Dimensional/driving constraints | `sketch.sketchDimensions.addDistanceDimension/addRadialDimension/addAngularDimension`; `isDriving` | Distances are just numeric args / Python expressions | `Rectangle(width, height)`; `Circle(radius)` | lossy | **Corrected:** `Rectangle` takes `(width, height, rotation=0, align, mode)` — there is **no `length` parameter**. Driven-vs-driving distinction and the dimension network are lost. |
| Auto-computed profile (closed region) | `sketch.profiles.item(0)` | The `Sketch` result itself / make a face from closed wires | `make_face()` (consumes `BuildSketch` pending **edges**); the BuildSketch result | approximate | build123d builds faces from closed loops on demand via `make_face()` (edges must form a single closed wire) rather than exposing an indexed `profiles` collection. |
| Extrude feature | `extrudeFeatures.createInput(profile, operation)`; `setOneSideExtent`/`setSymmetricExtent`; `add()` | `extrude()` consuming pending faces or explicit profile | `extrude(to_extrude=None, amount=, both=, taper=, until=, dir=, target=, clean=, mode=)` | direct | `FeatureOperations` -> `Mode` (Join->ADD, Cut->SUBTRACT, Intersect->INTERSECT). "To entity" -> `until=` (an `Until` enum). Symmetric -> `both=True`. |
| Revolve feature | `revolveFeatures.createInput(profile, axis, operation)`; `setAngleExtent(isSymmetric, ValueInput)` | `revolve()` about an `Axis` | `revolve(profiles=None, axis=Axis((0,0,0),(0,0,1)), revolution_arc=360.0, clean=, mode=)` | direct | Fusion angle set after createInput, in **radians**; build123d `revolution_arc` in **degrees**. Default axis is Z (`Axis.Z` equivalent). |
| Sweep feature | `sweepFeatures.createInput(profile, path, operation)` | `sweep()` along a `BuildLine`/`Wire` path | `sweep(sections=None, path=None, multisection=, is_frenet=, transition=, normal=, binormal=, clean=, mode=)` | direct | Path from a `BuildLine`/`Wire`. Fusion guideRail/twistAngle have no direct sweep arg; build123d folds lofted multi-profile sweeps into `multisection=True`. |
| Loft feature | `loftFeatures.createInput(operation)`; `loftInput.loftSections.add(profile)`; `loftInput.centerLineOrRails` (`addRail`/`setCenterLine`) | `loft()` through ordered sections | `loft(sections=None, ruled=False, clean=, mode=)` | approximate | Sections map directly. **build123d `loft()` has NO rail/centerline parameter** — only the boolean `ruled`. Guided/multi-rail lofts cannot be reproduced 1:1. |
| Fillet feature | `filletFeatures.createInput()`; `filletInput.addConstantRadiusEdgeSet(edges, ValueInput, isTangentChain)` (or `addVariableRadiusEdgeSet`); `filletFeatures.add(input)` | `fillet()` on selected edges (a `ShapeList`) | `fillet(objects, radius)` | approximate | **Corrected:** edges are added via `addConstantRadiusEdgeSet(...)`, not "edgeSetInputs.add". `fillet` takes a **single float radius** per call; variable/chord-length fillets are richer in Fusion. |
| Chamfer feature | `chamferFeatures.createInput2()`; `input.chamferEdgeSets.addEqualDistanceChamferEdgeSet/addTwoDistancesChamferEdgeSet/addDistanceAndAngleChamferEdgeSet(...)`; `chamferFeatures.add(input)` | `chamfer()` on selected edges | `chamfer(objects, length, length2=None, angle=None, reference=None)` | direct | **Corrected:** the modern path is `createInput2()` -> `chamferEdgeSets`. (The old `createInput(edges, isTangentChain)` + `setToEqualDistance` was **retired Dec 2020**; do not pair `createInput` with `chamferEdgeSets`.) Equal-distance -> `length`; two-distance -> `length`+`length2`; distance-angle -> `length`+`angle`. |
| Shell feature (hollow body) | `shellFeatures.createInput(entities, isTangentChain)`; thickness via `insideThickness`/`outsideThickness` | `offset` with openings, or `thicken` a face | `offset(objects, amount=-t, openings=faces, kind=Kind.ARC)`; `thicken(to_thicken, amount=t)` | approximate | **No "shell" method.** Negative `amount` insets; `openings` = faces to remove. Fusion's asymmetric inside/outside and per-face thickness are not replicated by a single-amount offset. |
| Hole feature | `holeFeatures.createSimpleInput/createCounterboreInput/createCountersinkInput`; `setPositionBySketchPoint`; `setToSimpleHole/setToTappedHole/setToClearanceHole` | `Hole`-family objects (default `Mode.SUBTRACT`) at `Locations` | `Hole(radius)`, `CounterBoreHole(...)`, `CounterSinkHole(radius, counter_sink_radius, depth=None, counter_sink_angle=82, mode=Mode.SUBTRACT)`; `with PolarLocations(...)` | approximate | Note Fusion's lowercase compound `createCounterboreInput`/`createCountersinkInput`. build123d holes are static cut geometry with no thread/clearance/standard-size table metadata. |
| Thread feature | `threadFeatures.createInput(inputCylindricalFaces, threadInfo)`; `createThreadInfo` | `bd_warehouse` thread classes, or a manual helical sweep | `bd_warehouse.thread.IsoThread / Thread / TrapezoidalThread / AcmeThread / MetricTrapezoidalThread / PlasticBottleThread` | partial | **Corrected (was "none"):** the official `bd_warehouse` collection provides real swept-solid thread classes. No cosmetic-thread mode and no `ThreadInfo` standards-table-on-a-selected-face workflow — you instantiate with explicit params and position it. |
| Combine (boolean) feature | `combineFeatures.createInput(targetBody, tools)`; `cInput.operation` | Boolean operators (algebra) or `mode=` (builder) | `a + b` / `a - b` / `a & b`; `Mode.ADD/SUBTRACT/INTERSECT` | direct | Direct match to Join/Cut/Intersect. Fusion's `keepToolBodies`/`isNewComponent` options have no analog. |
| Boolean operation enum | `FeatureOperations.JoinFeatureOperation/CutFeatureOperation/IntersectFeatureOperation/NewBodyFeatureOperation/NewComponentFeatureOperation` | `Mode` enum (or `+`,`-`,`&` / a new Part) | `Mode.ADD/SUBTRACT/INTERSECT/REPLACE/PRIVATE` | approximate | **Corrected:** members carry the `FeatureOperation` suffix. NewBody/NewComponent are **not** boolean modes -> create a separate `Part`/`Compound`. (`REPLACE`/`PRIVATE` are *not* equivalents of NewBody/NewComponent.) |
| Rectangular pattern | `rectangularPatternFeatures.createInput(inputEntities, directionOneEntity, quantityOne, distanceOne, patternDistanceType)`; then `setDirectionTwo(...)` | `GridLocations` context (builder) or loop placing copies | `with GridLocations(x_spacing, y_spacing, x_count, y_count): ...` | approximate | One `createInput` = 1-D; 2-D needs `setDirectionTwo`. **Spacing semantics:** `SpacingPatternDistanceType` = center-to-center (maps 1:1, no conversion). `ExtentPatternDistanceType` = total span -> convert `spacing = extent / (count - 1)`. |
| Circular pattern | `circularPatternFeatures.createInput(inputEntities, axis)` | `PolarLocations` context | `with PolarLocations(radius, count, start_angle=0.0, angular_range=360.0, rotate=True): ...` | approximate | `rotate=True` aligns copies to the arc (Fusion default). PolarLocations places objects as they are *constructed*; Fusion patterns an *existing* feature. |
| Mirror feature | `mirrorFeatures.createInput(inputEntities, mirrorPlane)` | `mirror()` about a `Plane` | `mirror(objects=None, about=Plane.XZ, mode=Mode.ADD)` | direct | Mirror plane (planar face/construction plane) -> build123d `Plane` (via `Plane(face)` if a face). |
| Move/Copy feature | `moveFeatures.createInput2(inputEntities)` then `MoveFeatureInput.defineAsFreeMove(transform: Matrix3D)` (or `defineAsTranslateXYZ`/`defineAsRotate`/`defineAsPointToPoint`); `moveFeatures.add(input)` | Place with `Location`/`*` or `.moved()`/`.located()`/`.locate()` | `loc * shape`; `shape.moved(Location)`; `shape.located(Location)`; `shape.locate(Location)` | direct | **Corrected:** `createInput2` takes only the entity collection; the `Matrix3D` goes to `defineAsFreeMove` (orthogonal matrix; no scale/mirror). `Matrix3D` (cm) -> `Location` (×10). `.moved()` = relative copy; `.located()` = absolute copy; `.locate()` = absolute in-place. A Fusion free-move (relative) maps best to `.moved()` / `loc * shape`. |
| Split body / split face | `splitBodyFeatures.createInput(splitBodies, splittingTool, isSplittingToolExtended)` | `split()` by a plane/face keeping a side; **body tool -> boolean cut** | `split(objects=None, bisect_by=Plane.XZ, keep=Keep.TOP, mode=Mode.REPLACE)` | approximate | **Corrected note:** `split()` only bisects by `Plane`/`Face`/`Shell`. A *body* as the splitting tool -> use boolean subtraction (`Part - Part`). `isSplittingToolExtended` (auto-extend finite tool) has no `split()` equivalent. `Keep` = TOP/BOTTOM/BOTH/ALL/INSIDE/OUTSIDE. |
| Offset (faces/surface) feature | `offsetFeatures.createInput(entities, distance, operation, isChainSelection)` | `offset()` free function | `offset(objects=None, amount=0, openings=None, kind=Kind.ARC, side=Side.BOTH, closed=True, mode=Mode.REPLACE)` | approximate | Fusion args are `entities`/`operation` (not `faces`/`op`). build123d `offset` is overloaded (1D inset, surface offset, solid shell), so broader than Fusion's faces->surface feature. |
| Construction plane | `constructionPlanes.createInput()` + `setByOffset`/`setByThreePoints`/`setByAngle` + `add()` | `Plane` object/constant | `Plane.XY.offset(25)`; `Plane(face)`; `Plane(origin, x_dir=, z_dir=)`; `plane.rotated(...)` | direct | `setByOffset` -> `Plane.offset`. `setByThreePoints` -> derive directions yourself (origin=p1, x_dir=p2-p1, z_dir=(p2-p1).cross(p3-p1)); **no 3-point constructor**. `setByAngle` -> `Plane.rotated` (rotates about the plane's own origin — move origin onto the axis first if needed). |
| Construction axis | `constructionAxes.createInput()` + `setByLine`/`setByEdge`/`setByTwoPoints` (+ others) + `add()` | `Axis` object/constant | `Axis.X/Y/Z`; `Axis((0,0,0),(0,0,1))`; `edge.to_axis()` | direct | Used for revolve axis, sorting, rotation. build123d `Axis` is a value object, not a timeline feature. |
| Construction point | `constructionPoints.createInput()` + `setByPoint`/`setByCenter` + `add()` | `Vector`/`Vertex`/`Pos` | `Vector(x,y,z)`; `Vertex(x,y,z)`; `Pos(x,y,z)` | approximate | **Corrected (was "direct"):** Fusion construction point is a persistent parametric feature; build123d targets are transient value objects (`Vertex` is the closest topological analog; `Pos` when a datum frame is intended). |
| Base origin planes | `component.xYConstructionPlane`/`xZConstructionPlane`/`yZConstructionPlane` | `Plane` constants | `Plane.XY` / `Plane.XZ` / `Plane.YZ` | direct | Naming-style difference only (lowerCamelCase `xZConstructionPlane` vs `Plane.XZ`). Both right-handed/Z-up; a Y-up Fusion document rotates imported geometry 90° about X. |
| B-rep topology traversal | `body.faces/edges/vertices/shells/lumps`; `face.loops`; `edge.startVertex/endVertex` | Selector methods returning `ShapeList` | `.faces() .edges() .vertices() .wires() .shells() .solids()` | direct | Both expose flattened collections. Asymmetries: no build123d `lumps()`; build123d adds `solids()`/`wires()` and the filter/sort operators; `compounds()` is an empty stub. |
| Geometry vs topology (underlying surface/curve) | `BRepFace.geometry` (Surface) / `BRepEdge.geometry` (Curve3D); `.evaluator` (SurfaceEvaluator/CurveEvaluator3D) | `.geom_type` enum + per-shape evaluation methods + `geom_adaptor()` | `face.geom_type` (`GeomType.PLANE`...); `edge.geom_type` (`GeomType.LINE`...); `normal_at`/`tangent_at`/`position_at`/`geom_adaptor()` | approximate | `geom_type` classifies; the closer analog to Fusion `.geometry` is `geom_adaptor()`. build123d spreads evaluation over `Edge`/`Face` methods rather than a dedicated evaluator object. |
| Named/tracked entity reference | `entity.entityToken` + `Design.findEntityByToken()` (persistent); proxy paths (`Comp:1/RedFace`, instance-scoped); `tempId` (session-only) | Runtime geometric selector recipe (re-evaluated each run) | `.faces().sort_by(Axis.Z)[-1]`; `.edges().filter_by(GeomType.CIRCLE)` | lossy | **Corrected:** the persistent token is `entityToken`/`findEntityByToken` (not `tempId`, which is session-only; not proxy paths, which only disambiguate instances). **The topological-naming gap** — translate the *intent* (which face/edge by property), never a raw index. |
| Component (geometry definition) | `Component`; `component.bRepBodies` | A `Part` / sub-`Compound` (bodies -> `part.solids()`/children) | `Part` / `Compound(label=, children=[...])` | approximate | No definition/instance separation; `Part` is a `Compound` subclass. |
| Occurrence (placed instance + transform) | `Occurrence.component`; `Occurrence.transform2` (`Matrix3D`, cm) | `Compound` child placed via `Location`; reuse via `copy.copy()` + place | `child2 = copy.copy(child); child2.move(Location(...)); Compound(children=[child2, ...])` | approximate | **Corrected:** `transform2` is in **cm** (×10). Shallow `copy.copy()` children share geometry (definition/instance-like) with independent Locations; the bare claim "not a definition/instance split" understates this. |
| Proxy (instance-aware entity) | `entity.createForAssemblyContext(occurrence)`; `proxy.nativeObject`/`assemblyContext` (top-level occurrence) | Resolve to concrete located geometry per placement | (no equivalent) | none | No instance-aware identity/back-reference; select on the placed concrete shape. (Shared geometry exists via `copy.copy()`, but without the proxy identity link.) |
| Joints | `component.joints`/`jointOrigins`; rigid/revolute/slider/cylindrical/ball/**planar**/**pin-slot** | build123d joint classes + `connect_to` | `RigidJoint, RevoluteJoint, LinearJoint, CylindricalJoint, BallJoint`; `a.connect_to(b, angle=/position=/angles=)` | approximate | **NO `PinSlotJoint`, NO planar joint.** Slider -> `LinearJoint`; cylindrical -> `CylindricalJoint`; revolute -> `RevoluteJoint`; rigid -> `RigidJoint`; ball -> `BallJoint`. Pin-slot -> `LinearJoint`(+angle) or `CylindricalJoint` (note lost 2nd constraint). `connect_to` is directional (self fixed; moving side becomes a `RigidJoint`). |
| Assembly structure / browser tree | `rootComponent.occurrences` (direct children; `allOccurrences` recursive) | `Compound` tree (anytree) | `Compound(label=, children=[...])`; `.parent`; `show_topology()` | approximate | No dedicated assembly class; labels non-unique; no component/occurrence (definition/instance) distinction carried. |
| Export STEP | `exportManager.createSTEPExportOptions(path[, geometry])`; `exportManager.execute(opts)` | `export_step` / `import_step` | `export_step(shape, path, unit=Unit.MM, ...)`; `import_step(path) -> Compound` | direct | B-rep + STEP colors/labels on **export**; timeline/sketches/constraints/joints do NOT transfer. (import_step returns a `Compound`; color/label restoration on import is undocumented.) The universal interop bridge. |
| Export IGES / SAT | `createIGESExportOptions` / `createSATExportOptions` | (no build123d path) | (no equivalent) | none | **Corrected:** build123d has **no IGES/SAT** import/export. Use STEP, or convert externally at the OCCT level. |
| Export STL/OBJ/3MF (mesh) | `createSTLExportOptions(...)`; `surfaceDeviation` (cm, linear), `normalDeviation` (rad, angular), `meshRefinement` | `export_stl` / `Mesher`; `import_stl` returns a `Face` | `export_stl(shape, path, tolerance=, angular_tolerance=)`; `Mesher(unit=Unit.MM)`; `import_stl(path) -> Face` | approximate | Fusion `surfaceDeviation` (cm, linear) -> `tolerance`; `normalDeviation` (rad) -> `angular_tolerance`. Imported STL is a mesh `Face`, not an editable solid. |
| Native editable archive | `createFusionArchiveExportOptions(...)` (`.f3d`; `.f3z` for referenced assemblies) | The Python `.py` script itself is the editable source | (no equivalent) | none | Only path that round-trips Fusion intent. build123d's analog is keeping/sharing the `.py`. |
| Imported/direct-edit body in a parametric design | `BaseFeature` (`baseFeatures.add` -> `startEdit` -> `bRepBodies.add(body, targetBaseFeature)` -> `finishEdit`) | `import_step` the frozen body; treat as non-parametric | `import_step(path) -> Compound`; then select faces/edges | approximate | The STEP/BREP bridge for T-spline/sculpt/sheet-metal/direct-edit bodies — not history-reconstructible. build123d has no parametric/non-parametric flag; everything is history-free. |

---

## 4. Impedance-mismatch catalog

Each: what it is · severity · concrete resolution.

### 4.1 Timeline / recompute graph vs re-executed linear script — **severity: medium**
Fusion records every action as an editable, recomputable `Timeline` node; editing an upstream value recomputes downstream. build123d has no recompute graph, no timeline, no rollback. There is nothing for `markerPosition`/`deleteAllAfterMarker`/`timelineGroups` to map to.
**Resolution:** Walk the timeline in order (`for i in range(timeline.count): node = timeline.item(i)`) and emit one build123d statement per node — re-running the script IS the recompute. Lift Fusion user parameters to module-level Python variables (or a `@dataclass`) so the result stays adjustable. Timeline grouping/rollback is dropped; document that mid-history editing is now done by editing source.

### 4.2 Persistent named/tracked entity references vs runtime selectors (topological naming) — **severity: high**
Fusion addresses "this face/edge" by a durable token (`entityToken` + `findEntityByToken`) and disambiguates instances via proxy paths. build123d has **no durable token**: every selection is re-evaluated from scratch, and list order is explicitly not guaranteed stable. **This is the central failure mode.**
**Resolution:** Never translate a named ref to `part.edges()[n]`. At translation time, read the captured entity's `geom_type`/position/normal/area and author a robust property recipe — select from higher topology first, then filter:
```python
top = part.faces().sort_by(Axis.Z)[-1]
fillet(top.edges().filter_by(GeomType.CIRCLE), radius=1)
```
Where a selector is genuinely ambiguous, flag for human review rather than guess.

### 4.3 Constraint-solved sketches vs explicit coordinates — **severity: high**
Fusion sketches are governed by a numerical solver (`addCoincident`/`addTangent`/`addParallel` + driving `SketchDimensions`) that propagates edits and reports `isFullyConstrained`. build123d has no solver; geometry is placed by explicit coordinates / Python math, with tangency only via special constructors.
**Resolution:** Read the **solved** coordinates from the Fusion API and emit explicit build123d geometry. Where the original used tangency, use `TangentArc`/`SagittaArc`/`JernArc`/`DoubleTangentArc`. Re-derive coordinates from the lifted Python parameters via algebra so the relationship is encoded in formulas (compute the tangent point in Python). Document that under-constrained / driven-dimension intent is lost.

### 4.4 Internal units cm/radians vs default mm/degrees — **severity: medium (high consequence if missed)**
All Fusion API numerics are **cm** for length (cm²/cm³ for area/volume) and **radians** for angle, regardless of display units. build123d defaults to mm and most constructors take degrees. A missed conversion produces a valid-looking model that is silently 10× (or 57.3×) wrong.
**Resolution:** Centralize conversion in one helper and unit-test it:
```python
import math
def cm_to_mm(x): return x * 10.0
def rad_to_deg(a): return math.degrees(a)
```
Prefer reading user-facing intent via `UnitsManager.evaluateExpression` / the parameter `expression` rather than raw `createByReal` values. Write build123d dimensions as `n * MM` to keep intent visible.

### 4.5 Components/Occurrences/Proxies vs single Compound+Location tree — **severity: medium**
Fusion separates `Component` (definition, unplaced) from `Occurrence` (placed instance with `transform2`), and `Proxy` gives instance-aware face/edge identity. build123d has only a `Compound` tree with placed `Location`s; no definition/instance split, no proxy.
**Resolution:** Map each `Component` to a build123d `Part`/sub-`Compound`; map each `Occurrence` to a placed child via that occurrence's `transform2` converted to a `Location` (cm->mm). For repeated components, `copy.copy()` (shallow — shared geometry, independent Location) then place. Resolve proxies to concrete located geometry per placement — never assume one selector addresses "the face on instance 2."

### 4.6 Joints: full Fusion joint set vs build123d's five classes — **severity: medium**
Fusion offers rigid/revolute/slider/cylindrical/ball/**planar**/**pin-slot**. build123d has exactly `RigidJoint`/`RevoluteJoint`/`LinearJoint`/`CylindricalJoint`/`BallJoint` — no pin-slot, no planar — and `connect_to` is directional pairwise wiring (self fixed; the moving side becomes a `RigidJoint`).
**Resolution:** slider->`LinearJoint`, cylindrical->`CylindricalJoint`, revolute->`RevoluteJoint`, rigid->`RigidJoint`, ball->`BallJoint`. Pin-slot -> `LinearJoint`(+`angle`) or `CylindricalJoint`, noting the lost second constraint. Planar/pin-slot -> flag for manual review. Preserve `connect_to` direction; use the type-specific kwargs (`angle`/`position`/`angles`).

### 4.7 Direct-edit / T-spline / sculpt / sheet-metal vs reconstructible B-rep ops — **severity: high**
T-spline/freeform/sculpt and sheet-metal rules are barely exposed even in Fusion's own API and are not history-faithfully reconstructible; `BaseFeature` direct-edit bodies and imported meshes have no parametric recipe; meshes are not B-reps.
**Resolution:** Do not attempt feature re-authoring. Export the resulting body from Fusion to **STEP** and bring it in via `import_step` (returns a `Compound` you can still select faces/edges on); import meshes via `import_stl`/`Mesher` (result is a mesh `Face`). Use this STEP/BREP bridge as the universal fallback for any Fusion feature lacking an idiomatic build123d operation, and clearly mark such parts as imported-and-frozen.

### 4.8 Builder running-total semantics vs declarative `add()` — **severity: medium**
In Fusion, `createInput`->`add()` explicitly creates a feature regardless of order. In build123d builder mode, objects add themselves **on instantiation** combined per `Mode`, post-creation `.moved()` is a no-op on the running total, default modes vary (`Hole`->SUBTRACT, offset/split->REPLACE), and operations consume pending faces only when called with no profile.
**Resolution:** Set placement BEFORE creation using `Locations`/`Pos`/`Rot` contexts (or use algebra mode with explicit `*` placement, which is more faithful to Fusion's explicit-transform model). Explicitly pass `mode=` matching the `FeatureOperation`; don't assume `ADD`. Verify each op consumes the intended pending faces or receives an explicit profile.

### 4.9 Export asymmetry / fidelity — **severity: medium**
Fusion can export a fully editable native archive (`.f3d`/`.f3z`) but neutral STEP/IGES/SAT carry only dead B-rep (STEP + partial colors/labels). build123d's `import_step` yields a non-parametric `Compound`, supports STEP but **not IGES/SAT**, and has no `.f3d`/`.f3z`. No neutral path round-trips intent in either direction.
**Resolution:** Choose by need — **code-to-code** translation when parametric intent must survive (most effort); **STEP -> import_step** when only final geometry is needed (trivial, intent lost). Treat STEP/BREP as a one-way geometry bridge and keep the build123d `.py` as the editable source of truth. Note colors/labels survive STEP export but appearance/layers are often distorted across translators.

---

## 5. Idiomatic-translation PLAYBOOK

Ordered procedure to translate a Fusion design into idiomatic build123d.

### Step 0 — Decide the path
If the Fusion part uses T-spline/sculpt/sheet-metal/freeform/direct-edit, or you only need final geometry: **export STEP, `import_step`, stop** (mark it frozen). Otherwise proceed to code-to-code translation.

### Step 1 — Lift parameters to a single source of truth
Walk `design.allParameters` / `design.userParameters`. Emit module-level constants or a frozen `@dataclass`, converting cm->mm and keeping unit intent:
```python
from dataclasses import dataclass
from build123d import *

@dataclass(frozen=True)
class Params:
    length: float = 80 * MM      # Fusion userParameter "length" = 8 cm
    width:  float = 60 * MM
    thickness: float = 10 * MM
    bolt_circle_r: float = 40 * MM
    bolt_count: int = 6
P = Params()
```
Cross-parameter Fusion expressions (`width = length/4`) become eager Python expressions (`width = P.length/4`) — the dependency *graph* is lost but the relationship is preserved in source.

### Step 2 — Choose the authoring mode
Use the decision rule in §2.2. Default to **builder mode** for a hand-translated linear timeline; switch to **algebra mode** for data-driven generation or when you want explicit `*`-placement mirroring Fusion's `transform2`.

### Step 3 — Translate sketches: solver -> explicit geometry
For each Fusion sketch: read the **solved** coordinates (cm->mm). Replace constraints with explicit coordinates/Python math; replace tangency with `TangentArc`/`RadiusArc`/etc. Replace `sketch.profiles.item(0)` with the `BuildSketch` result (or `make_face()` on a `BuildLine`).

### Step 4 — Flatten the timeline into ordered operations
Iterate `timeline.item(i)` and emit one statement per feature, in order. Map `FeatureOperations` -> `Mode`. **Set placement before creation** (builder) or via `*` (algebra). Angles rad->deg.

### Step 5 — Translate entity references to robust selectors
Replace every `entityToken`/named reference with a geometric selector recipe (§4.2): select from high topology, filter by `GeomType`/`Axis`/position, sort, then index `[-1]`/`[0]`. Inside builders, use `Select.LAST` to grab the just-created faces/edges.

### Step 6 — Reconstruct assembly: Components/Occurrences/Joints -> Compound + Joints
Each `Component` -> a `Part`/function returning a part. Each `Occurrence` -> a placed child (`transform2` cm->mm -> `Location`). Bind `RigidJoint`/`RevoluteJoint`/... inside each `BuildPart`, gather into a `Compound`, and wire with `connect_to`.

### Step 7 — Verify
Re-run the script. Compare `volume`/`bounding_box`/`center` and key face counts against the Fusion model (or against a STEP export of it). A 10× bounding box = a missed unit conversion. Export STEP from both and diff.

---

### 5.1 Extrude-from-sketch

**Fusion API:**
```python
import adsk.core, adsk.fusion
app = adsk.core.Application.get()
design = adsk.fusion.Design.cast(app.activeProduct)
root = design.rootComponent

sk = root.sketches.add(root.xYConstructionPlane)
sk.sketchCurves.sketchLines.addCenterPointRectangle(
    adsk.core.Point3D.create(0, 0, 0),
    adsk.core.Point3D.create(4, 3, 0))          # cm -> 40 x 30 mm half-extents
prof = sk.profiles.item(0)

extrudes = root.features.extrudeFeatures
ext_in = extrudes.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
ext_in.setDistanceExtent(False, adsk.core.ValueInput.createByReal(1.0))  # 1 cm = 10 mm
extrudes.add(ext_in)
```
**Idiomatic build123d (builder):**
```python
from build123d import *
length, width, thickness = 80 * MM, 60 * MM, 10 * MM
with BuildPart() as part:
    with BuildSketch(Plane.XY):
        Rectangle(length, width)              # centered by default
    extrude(amount=thickness)                 # consumes the pending face; Mode.ADD
```
**Idiomatic build123d (algebra):**
```python
from build123d import *
length, width, thickness = 80 * MM, 60 * MM, 10 * MM
part = extrude(Rectangle(length, width), amount=thickness)
```

### 5.2 Revolve

**Fusion API:**
```python
import math
sk = root.sketches.add(root.xZConstructionPlane)
# ... draw the profile to revolve, on one side of the axis ...
prof = sk.profiles.item(0)
axis = root.zConstructionAxis            # construction axis

revolves = root.features.revolveFeatures
rev_in = revolves.createInput(prof, axis,
                              adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
rev_in.setAngleExtent(False, adsk.core.ValueInput.createByReal(2 * math.pi))  # radians
revolves.add(rev_in)
```
**Idiomatic build123d (builder):**
```python
from build123d import *
with BuildPart() as part:
    with BuildSketch(Plane.XZ):
        with BuildLine():
            Polyline((10, 0), (30, 0), (30, 5), (20, 20), (10, 20), close=True)
        make_face()
    revolve(axis=Axis.Z, revolution_arc=360.0)   # degrees, not radians
```
**Idiomatic build123d (algebra):**
```python
from build123d import *
section = Plane.XZ * make_face(Polyline((10,0),(30,0),(30,5),(20,20),(10,20), close=True).edges())
part = revolve(section, axis=Axis.Z, revolution_arc=360.0)
```

### 5.3 Fillet on selected edges

**Fusion API:**
```python
body = root.bRepBodies.item(0)
edges = adsk.core.ObjectCollection.create()
# pick the top face's circular edges by walking topology (illustrative)
for f in body.faces:
    if f.geometry.surfaceType == adsk.core.SurfaceTypes.PlaneSurfaceType:
        for e in f.edges:
            edges.add(e)

fillets = root.features.filletFeatures
fil_in = fillets.createInput()
fil_in.addConstantRadiusEdgeSet(edges, adsk.core.ValueInput.createByReal(0.2), True)  # 2 mm
fillets.add(fil_in)
```
**Idiomatic build123d (builder) — select by property, never by index:**
```python
from build123d import *
with BuildPart() as part:
    Box(80, 60, 10)
    # round the four vertical edges
    fillet(part.edges().filter_by(Axis.Z), radius=2)
    # or: the circular edges of the top face only
    # fillet(part.faces().sort_by(Axis.Z)[-1].edges().filter_by(GeomType.CIRCLE), radius=2)
```
**Idiomatic build123d (algebra):**
```python
from build123d import *
part = Box(80, 60, 10)
part = fillet(part.edges().filter_by(Axis.Z), radius=2)
```

### 5.4 Boolean cut

**Fusion API:**
```python
target = root.bRepBodies.item(0)
tools  = adsk.core.ObjectCollection.create()
tools.add(root.bRepBodies.item(1))

combines = root.features.combineFeatures
comb_in = combines.createInput(target, tools)
comb_in.operation = adsk.fusion.FeatureOperations.CutFeatureOperation
combines.add(comb_in)
```
**Idiomatic build123d (builder):**
```python
from build123d import *
with BuildPart() as part:
    Box(80, 60, 10)
    with Locations((0, 0, 0)):
        Cylinder(radius=15, height=20, mode=Mode.SUBTRACT)   # cut
```
**Idiomatic build123d (algebra):**
```python
from build123d import *
part = Box(80, 60, 10) - Cylinder(radius=15, height=20)
```

### 5.5 Circular pattern

**Fusion API:**
```python
inputs = adsk.core.ObjectCollection.create()
inputs.add(some_hole_feature)             # the seed feature to pattern
axis = root.zConstructionAxis

cpat = root.features.circularPatternFeatures
cp_in = cpat.createInput(inputs, axis)
cp_in.quantity = adsk.core.ValueInput.createByReal(6)
cp_in.totalAngle = adsk.core.ValueInput.createByString('360 deg')
cpat.add(cp_in)
```
**Idiomatic build123d (builder) — PolarLocations places copies as they are created:**
```python
from build123d import *
with BuildPart() as part:
    Cylinder(radius=50, height=10)
    with Locations(part.faces().sort_by(Axis.Z)[-1]):       # work on the top face
        with PolarLocations(radius=40, count=6):            # bolt circle
            Hole(radius=4)                                  # default Mode.SUBTRACT
```
**Idiomatic build123d (algebra):**
```python
from build123d import *
part = Cylinder(radius=50, height=10)
plane = Plane(part.faces().sort_by(Axis.Z).last)
part -= plane * PolarLocations(radius=40, count=6) * Hole(radius=4, depth=10)
```

### 5.6 Assembly with a joint

**Fusion API (sketch):**
```python
# Two components placed as occurrences, joined with a revolute joint.
occ_base = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
occ_arm  = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
# ... build geometry in each component, create JointGeometry / JointOrigin ...
joints = root.joints
jin = joints.createInput(jointGeoBase, jointGeoArm)
jin.setAsRevoluteJointMotion(adsk.fusion.JointDirections.ZAxisJointDirection)
joints.add(jin)
```
**Idiomatic build123d — bind joints inside each part, gather into a Compound, wire with `connect_to`:**
```python
from build123d import *

# --- base part with a RigidJoint anchor for the hinge ---
with BuildPart() as base_builder:
    Box(60 * MM, 40 * MM, 10 * MM)
    RigidJoint(
        "hinge_attachment",
        joint_location=Location((25 * MM, 0, 10 * MM), (0, 0, 0)),
    )
base = base_builder.part

# --- arm part with a RigidJoint that will mate to the revolute axis ---
with BuildPart() as arm_builder:
    Box(50 * MM, 12 * MM, 6 * MM, align=(Align.MIN, Align.CENTER, Align.CENTER))
    RevoluteJoint(
        "pivot",
        axis=Axis((0, 0, 0), (0, 0, 1)),
        angular_range=(0, 180),
    )
arm = arm_builder.part

# --- assemble: connect_to is directional (self fixed, other moves) ---
base.joints["hinge_attachment"].connect_to(arm.joints["pivot"], angle=45)

assembly = Compound(label="hinge_assembly", children=[base, arm])
# export_step(assembly, "assembly.step")   # B-rep + labels; joints are NOT exported
```
Notes: `RigidJoint`/`RevoluteJoint` are created **inside** the `BuildPart` context so they attach to that part; reach them via `part.joints["label"]`; `connect_to(other, angle=...)` keeps `self` fixed and repositions `other`, and the moving side is treated as a `RigidJoint` mate. For a slider use `LinearJoint(..., axis=, linear_range=)` and `connect_to(..., position=...)`; pin-slot has no class — approximate with `LinearJoint`(+`angle`) or `CylindricalJoint`.

---

## 6. Gotchas & failure modes

1. **Units: the silent 10× / 57.3× error (highest practical risk).** Every length from the Fusion API is **cm**; every angle is **radians**. build123d defaults to mm and degrees. `ValueInput.createByReal(2)` is **2 cm = 20 mm**. `setAngleExtent(..., createByReal(math.pi))` is 180°, but `revolve(revolution_arc=math.pi)` would be **3.14°**. Centralize and unit-test conversions; verify by comparing bounding boxes.

2. **Topological-naming fragility.** Selectors are re-evaluated every run and list order is not guaranteed stable. `part.edges()[3]` is a time bomb — adding any earlier feature can reshuffle indices. Always filter/sort by stable geometric property and select from high topology first. `tempId` is NOT persistent (session + unmodified-body only); the durable Fusion token is `entityToken` — but it has no build123d analog, so translate the *intent*, not the token.

3. **Constraint loss.** No solver in build123d. Coincident/parallel/perpendicular/equal/concentric/symmetric/midpoint have **no** primitive — they collapse to computed coordinates or shared vertices. Only tangency survives, via `TangentArc`/`SagittaArc`/`JernArc`/`DoubleTangentArc`. Driven-vs-driving dimensions and `isFullyConstrained` are gone. Read solved coordinates; re-encode intent as Python formulas.

4. **Unsupported features — use the STEP bridge.** T-spline/freeform/sculpt, sheet-metal rules, and direct-edit `BaseFeature` bodies are not history-reconstructible (often barely exposed in Fusion's own API). Do **not** re-author them; `export STEP -> import_step` and mark the part frozen. Meshes (`import_stl`) come in as a `Face`, not an editable solid.

5. **No "shell" method.** Hollowing is `offset(..., amount=-t, openings=face)` or `thicken`. A naive search for `shell(...)` will fail. Fusion's asymmetric inside/outside and per-face thickness are not reproduced by a single-amount offset.

6. **Builder running-total surprises.** Objects combine **on instantiation**; `.moved()` after the fact is a no-op on the running total. Default modes differ (`Hole`->SUBTRACT, offset/split/scale->REPLACE). Position *before* creating, and pass `mode=` explicitly. If `extrude()` mysteriously does nothing or consumes the wrong thing, check what's in `pending_faces`.

7. **`Rectangle` has no `length` parameter.** It is `Rectangle(width, height, rotation=0, align=, mode=)`. (Hallucinated-name correction.)

8. **Chamfer uses `createInput2()` + `chamferEdgeSets`.** The old Fusion `chamferFeatures.createInput(edges, isTangentChain)` + `setTo*` path was **retired Dec 2020**; do not mix `createInput` with `chamferEdgeSets`. `MoveFeatures.createInput2(entities)` takes **only** the entities — the `Matrix3D` goes to `defineAsFreeMove`. (Hallucinated-signature corrections.)

9. **No `PinSlotJoint`, no planar joint, no IGES/SAT, no `.f3d`/`.f3z`.** Map pin-slot/slider/planar onto the five real joint classes (noting lost constraints) and bridge geometry through STEP only.

10. **Loft guidance loss.** build123d `loft()` has only a boolean `ruled` flag — no rails, no centerline. Multi-rail / centerline-guided Fusion lofts cannot be reproduced 1:1; verify the result or re-model.

11. **`connect_to` is directional and mutates placement.** `a.connect_to(b)` keeps `a` fixed and moves `b`; the moving side becomes a `RigidJoint` mate. Preserve the Fusion join direction or the assembly will be positioned around the wrong part.

12. **Handedness / orientation.** Both systems are right-handed and (by default) Z-up. A Fusion document authored Y-up imports rotated 90° about X. `Plane.XZ` in build123d has normal -Y (a right-handed frame) — note this when reasoning about sketch face orientation.

---

## 7. References

Fusion 360 API (help.autodesk.com / cloudhelp ENU):
- Python Add-in Template: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/PythonTemplate_UM.htm
- Writing/Debugging (Creating a Script or Add-In): https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/WritingDebugging_UM.htm
- Components and Proxies (User's Manual): https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/ComponentsProxies_UM.htm
- Units (User's Manual): https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Units_UM.htm
- B-Rep Geometry (User's Manual): https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/BRepGeometry_UM.htm
- Timeline: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Timeline.htm
- TimelineObject.rollTo: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/TimelineObject_rollTo.htm
- UnitsManager / convert: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/UnitsManager.htm , https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/UnitsManager_convert.htm
- ValueInput / createByReal: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/ValueInput.htm , https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/ValueInput_createByReal.htm
- UserParameters.add: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/UserParameters_add.htm
- Parameter / ModelParameter: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Parameter.htm , https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/ModelParameter.htm
- Sketches.add: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Sketches_add.htm
- SketchArcs.addByCenterStartSweep: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/SketchArcs_addByCenterStartSweep.htm
- GeometricConstraints: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/GeometricConstraints.htm
- SketchDimensions / SketchDimension: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/SketchDimensions.htm , https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/SketchDimension.htm
- Sketch.profiles / Profiles.item: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Sketch_profiles.htm , https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Profiles_item.htm
- ExtrudeFeatures.createInput / setSymmetricExtent: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/ExtrudeFeatures_createInput.htm , https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/ExtrudeFeatureInput_setSymmetricExtent.htm
- FeatureOperations enum: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/FeatureOperations.htm
- SimpleRevolveFeatureSample: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/SimpleRevolveFeatureSample_Sample.htm
- SweepFeatures.createInput: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/SweepFeatures_createInput.htm
- LoftFeatureInput.loftSections: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/LoftFeatureInput_loftSections.htm
- ConstantRadiusFillet sample: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/ConstantRadiusFillet_Sample.htm
- ChamferFeatures.createInput (retirement note) / EqualDistanceChamfer sample: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/ChamferFeatures_createInput.htm , https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/EqualDistanceChamferFeature_Sample.htm
- HoleFeatures: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/HoleFeatures.htm
- ThreadFeatures.createInput: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/ThreadFeatures_createInput.htm
- CombineFeatures.createInput / CombineFeatureInput.operation: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/CombineFeatures_createInput.htm , https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/CombineFeatureInput_operation.htm
- RectangularPatternFeature sample: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/RectangularPatternFeatureSample_Sample.htm
- CircularPatternFeatures.createInput: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/CircularPatternFeatures_createInput.htm
- MirrorFeatures.createInput: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/MirrorFeatures_createInput.htm
- MoveFeatures.createInput2 / MoveFeatureInput.defineAsFreeMove / Matrix3D: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/MoveFeatures_createInput2.htm , https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/MoveFeatureInput_defineAsFreeMove.htm , https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Matrix3D.htm
- SplitBodyFeatures.createInput: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/SplitBodyFeatures_createInput.htm
- OffsetFeatures.createInput: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/OffsetFeatures_createInput.htm
- ConstructionPlaneInput (setByOffset/setByThreePoints/setByAngle): https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/ConstructionPlaneInput.htm
- ConstructionPoints / ConstructionPointInput: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/ConstructionPoints_createInput.htm , https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/ConstructionPointInput_setByPoint.htm
- Component.xYConstructionPlane: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Component_xYConstructionPlane.htm
- Construction Plane sample: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/ConstructionPlaneSample_Sample.htm
- BRepBody / BRepFace / BRepEdge: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/BRepBody.htm , https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/BRepFace.htm , https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/BRepEdge.htm
- BRepFace.tempId: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/BRepFace_tempId.htm
- Component / Component.bRepBodies: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Component.htm , https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Component_bRepBodies.htm
- Occurrence / Occurrence.transform2: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Occurrence.htm , https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Occurrence_transform2.htm
- ExportManager / createSTEPExportOptions: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/ExportManager.htm , https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/ExportManager_createSTEPExportOptions.htm
- STLExportOptions (surfaceDeviation/normalDeviation/meshRefinement): https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/STLExportOptions_surfaceDeviation.htm , https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/STLExportOptions_normalDeviation.htm
- BaseFeature / BRepBodies.add: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/BaseFeature.htm , https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/BRepBodies_add.htm
- Autodesk dev blog — toggle/capture design history (designType): https://blog.autodesk.io/fusion-api-toggle-capture-design-history/

build123d (build123d.readthedocs.io):
- Introduction: https://build123d.readthedocs.io/en/latest/introduction.html
- Key concepts: https://build123d.readthedocs.io/en/stable/key_concepts.html
- Key concepts (algebra): https://build123d.readthedocs.io/en/latest/key_concepts_algebra.html
- BuildPart / BuildSketch: https://build123d.readthedocs.io/en/stable/build_part.html , https://build123d.readthedocs.io/en/stable/build_sketch.html
- Objects: https://build123d.readthedocs.io/en/latest/objects.html
- Operations: https://build123d.readthedocs.io/en/latest/operations.html
- Builder API reference (GridLocations/PolarLocations): https://build123d.readthedocs.io/en/latest/builder_api_reference.html
- Direct API reference: https://build123d.readthedocs.io/en/latest/direct_api_reference.html
- Topology / selection: https://build123d.readthedocs.io/en/latest/topology_selection.html
- Selector tutorial: https://build123d.readthedocs.io/en/latest/tutorial_selectors.html
- Location arithmetic: https://build123d.readthedocs.io/en/latest/location_arithmetic.html
- Joints: https://build123d.readthedocs.io/en/latest/joints.html
- Joint tutorial (hinge assembly): https://build123d.readthedocs.io/en/latest/tutorial_joints.html
- Assemblies: https://build123d.readthedocs.io/en/latest/assemblies.html
- Import/Export (units, STEP/STL/glTF; no IGES/SAT/f3d): https://build123d.readthedocs.io/en/stable/import_export.html
- Introductory examples (builder/algebra, PolarLocations + holes): https://build123d.readthedocs.io/en/latest/introductory_examples.html
- External tools (bd_warehouse): https://build123d.readthedocs.io/en/latest/external.html
- bd_warehouse threads: https://bd-warehouse.readthedocs.io/en/latest/_modules/thread.html
- Build enums (Mode/Keep) source: https://build123d.readthedocs.io/en/v0.10.0/_modules/build_enums.html

---

## 8. Open questions / to-verify (not fully confirmed against primary docs in this pass)

1. **`import_step` colour/label restoration is undocumented.** `export_step` is confirmed to write colours+labels, but whether `import_step` reconstructs them onto the `Compound`'s children (`.color`/`.label`) was not confirmed on a primary page. Verify before relying on round-tripped appearance.
2. **Fusion `JointInput` motion-setter names** (e.g. `setAsRevoluteJointMotion`, `JointDirections` members) used in the §5.6 *Fusion-side* snippet were not individually confirmed against a primary page. The build123d side of that example is venv-verified; the Fusion side should be checked against the `Joints`/`JointInput` reference before treating it as copy-paste accurate.
3. **`GridLocations` spacing vs Fusion `ExtentPatternDistanceType`** off-by-one (`extent = spacing*(count-1)`) was reasoned, not read from a worked Fusion example. Confirm if exactness matters.
4. **`bd_warehouse`** (threads, §3 thread row) is a separate non-core package; its install/version compatibility with the project's pinned **build123d 0.10.x** was not checked. Confirm before recommending it for threaded features here.
5. **build123d `sweep()` guide-rail support.** Fusion sweeps with `guideRail`/`twistAngle` have no confirmed 1:1 `sweep()` argument; `multisection=True` covers lofted sweeps, but rail-guided constant-section sweeps may need manual reconstruction — needs a targeted test.
6. **`loft(ruled=False)` vs Fusion's default smooth/tangent loft** transition fidelity was not measured — relevant to this project's NACA airfoil lofts. Verify against a STEP export if surface fidelity matters. (Note: the `wingmast-domain` skill records that this repo's own lofts use `ruled=True` because the BSpline-smooth loft overshoots across the airfoil→circle morph.)
- gumyr/build123d (source, cheat sheet): https://github.com/gumyr/build123d , https://github.com/gumyr/build123d/blob/dev/docs/cheat_sheet.rst