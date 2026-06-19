# Glossary — terms, acronyms & symbols

A living reference for the vocabulary used across this project. **Keep it current**: when a
new term, acronym, or symbol enters the docs or code, add a one-line entry here. Authoritative
numbers live in `engineering_basis.md`; requirements in `specification.md`; this is just the
lookup so terms aren't re-derived.

> **The one distinction to get right:** the **wingsail** (mast **+** deployed soft sail, ~3–4 m
> chord) is the *aerodynamic* surface that sets the operational loads; the **wingmast** (the
> bare rigid CFRP structure *alone*, ~0.5–1 m chord) is the *structural* object we optimise.
> They are not the same thing — see both entries below.

---

## 1. The two "wings" (do not conflate)

| Term | Meaning |
|---|---|
| **Wingsail** | The bare mast **+ the deployed soft fabric sail** = the large propulsive airfoil (NACA-0018-ish, ~3.2 m mean chord, ~75 m²/mast). Drives the **operational** loads. The exported aero load *surface*, not a structure we build. |
| **Wingmast** | The bare, rigid, rotating **CFRP structure alone** (sail furled) — a much smaller streamlined section, chord `c_mast` ≈ 0.5–1 m. **This is the object of optimisation** (box spars + longerons + shell). Drives the **survival** loads. |

---

## 2. Wingmast anatomy & geometry

| Term | Meaning |
|---|---|
| **Heel step** | The lowest fitting near the keel; the **lower journal** bearing station. |
| **Stock** | The rotating circular section of the mast that passes through the hull (deck → heel). |
| **Bury** | The stock length between the two journals (deck-partners → heel-step); sets the bearing-couple arm. |
| **Deck partners** | The deck-level fitting at the top of the stock; the **upper journal** bearing station. |
| **Journal (bearing)** | A radial bearing the rotating stock turns in. Two of them (heel + partners); `F_bearing = M_base / bury`. |
| **Transition zone** | The spanwise band where the section morphs circular (stock) → airfoil (wing), `z ∈ [−transition_length, 0]`; smoothstep-faired. |
| **Wing root / tip** | Bottom (`z = 0`) / top (`z = span`) of the exposed airfoil wing. |
| **Stock / OML / outer shell** | Stock = the circular rotating base; **OML** = outer mold line (the faired outer surface); **outer shell** = the filament-wound skin to the OML. |
| **Cell (conformal cell)** | A hollow, filament-wound CFRP **closed-section spar whose caps follow the airfoil contour** (curved — *not* a rectangular box, *not* a round tube). ≥3 run chordwise (LE + centre(s) + TE) and are co-bonded side-by-side to fill the section. **This is the correct term**; "box spar" is a retained misnomer (these are conformal, not boxes). The code API still uses the historical `box_spar*` names (`BoxSparLayout`, `box_spar_sections`). |
| **D-cell** | The **leading-edge** conformal cell: the curved LE skin closed off by a shear web → a "D" in section. The **TE cell** is its mirror; the **interior cell(s)** have curved (airfoil-conforming) top + bottom caps bounded by two webs. |
| **Multi-cell (N-cell) torsion box** | The co-bonded assembly = N conformal **cells** filling the airfoil + UD **longerons** in the corner channels + the FW **outer shell** that fairs it to the OML. "Box" = a *closed torsion-carrying section*, not a rectangle. The project's mast build (vs Sponberg's single box spar + glass fairings). |
| **Conformal** | Of a closed section: shaped to **follow its container's contour** (the OML). Contrast: round → **tube spar**; rectangular → **box spar** (neither is what we build). |
| **Box spar / tube spar** | **(deprecated for our build)** Box spar = rectangular hollow section; tube spar = round hollow section. Our members are neither — see **cell** / **multi-cell torsion box**. Retained only to describe *Sponberg's* single-box mast and in legacy code names. |
| **Longeron** | A unidirectional (0°-ish) load-carrying member laid into the **longeron channel** — the void left between **adjacent cells** by their rounded corners (top + bottom of each shared web). |
| **Blend curve / blend radius** | The rounded corner of a **cell**; its **radius** sets the inter-cell longeron-channel void size (the blend-radius → longeron coupling). |
| **Entasis** | A slight convex spanwise bow of the wing loft-axis (classical column entasis); composes with taper. |
| **Pivot / rotation centre** | The rotation axis the mast turns about (on the chord at `rotation_center_xc`, ~0.25c). Distinct from the aerodynamic **CoM** (below). |
| **Rotational-center foil offset** | The rotation-axis position on the chord — a design parameter, distinct from the aerodynamic centre-of-moment. |
| **Taper / t/c** | Chord narrowing root→tip (taper ratio = tip/root ≈ 0.6); **t/c** = thickness-to-chord ratio (NACA-0018 → 0.18). |
| **Kulfan / CST** | **C**lass-**S**hape **T**ransformation — a parametric airfoil representation (Kulfan 2007); supports arbitrary sections, not just named NACA. |

---

## 3. Load cases & load concepts

| Term | Meaning |
|---|---|
| **RM** | **R**ighting **M**oment — the heeling moment the hull can resist before capsizing. `RM_max` ≈ 200 kN·m (Oyster-595; the dominant linear sensitivity, `D-1`). |
| **RM-limited** | The load is capped by the **boat's stability**: the sail can make more force than the hull can resist, so the boat heels/depowers to the RM ceiling. The steady load = `split·RM_max`, **independent of wind speed**. Normal upwind-in-a-breeze case. |
| **q-limited** | The load is capped by the **wind**: `q·area·C_lift` (scales with wind²), used when the wind *can't* drive the rig to the RM ceiling (e.g. reaching). Always ≤ the RM cap. |
| **Coupled ceiling** | `heeling = min(split·RM, split·aero_capacity)` — the RM ceiling **always** applies; the q term only binds below it (the honest model; Article IV). |
| **Split** | The per-mast share of the rig load: **50:50** nominal (`OP-1`), **70:30** forward:aft worst-single-mast (`OP-2`). |
| **DAF** | **D**ynamic **A**mplification **F**actor — gust/seaway multiplier on the static load (≥1.5 operational). |
| **Operational / survival** | Operational = sailing (wingsail deployed; serviceability **and** ultimate). Survival = hurricane (sail furled, bare mast feathered; **ultimate only**). |
| **Serviceability vs ultimate** | Serviceability = deflection/twist limits (operational cases only, Article IV). Ultimate = strength/buckling (all cases). |
| **Governing case** | The load case that sizes the spar (the heaviest binding one). `OP-2` governs at central inputs (conditional on `D-2`). |
| **OP-1 / OP-2** | Operational: RM-limited 50:50 (~115 kN·m, deflection/twist) / worst single mast 70:30 (~160 kN·m, **governs**). |
| **SURV-1 / SURV-1f / SURV-2** | Survival: bare mast feathered ~0° (~8–39 kN·m) / **feathering-fault** off-axis (~390–470 kN·m, reduced-FoS check) / Cat-5 off-axis bound (~730–880 kN·m). |
| **MFG-1** | Manufacturing "case": hoop-wind prestress + bondline constraints (not a bending case). |
| **CE / CLR / heeling lever** | **C**entre of **E**ffort (aero force height) / **C**entre of **L**ateral **R**esistance (hull, below WL) / heeling lever = CE-above-WL + CLR-below-WL (≈14 m). |
| **Operational arm** | The cantilever bending arm (CE above the partners, ≈10.7 m). |

---

## 4. Aerodynamics & feathering

| Term | Meaning |
|---|---|
| **q** | Dynamic pressure = ½ρV² (Pa). Hurricane: Cat 3 ≈ 1621 Pa (100 kt), Cat 5 ≈ 3042 Pa (137 kt). |
| **AoA** | **A**ngle **o**f **A**ttack — the section's incidence to the (apparent) wind. |
| **AC** | **A**erodynamic **C**entre — the chord point about which the pitching moment is ~constant (~0.25c for a symmetric section). |
| **CoM / CoP** | Centre of moment / centre of pressure (aerodynamic) — distinct from the mechanical **pivot**. |
| **Feathering** | Letting the free-rotating bare mast weathervane to ~0° AoA in survival, so it sees drag (small) not lift (large). The top mass lever (`D-2`). |
| **Weathervane** | The self-aligning behaviour when the pivot is **forward** of the AC → a yaw-restoring moment that drives AoA → 0. |
| **Crossover AoA** | The off-axis AoA at which the bare-mast lift bending equals OP-2 (~3.7°); operational governs only below it. |
| **Breakeven RM / c_mast** | The `RM` below (~161 kN·m) / `c_mast` above (~1.24 m) which the governing case flips operational → survival. |
| **Slot effect** | The lift enhancement from two tandem masts spaced ~1–2 chord (Munk stagger). |
| **Tandem** | Two masts fore-and-aft on the boat centreline, independently AoA-controlled. |
| **Camber** | Asymmetry that raises lift; the soft sail develops **operating camber** when sheeted (CL ≈ 1.45), so the symmetric NACA-0018 is the *faired mast* section, not the operating section (`D-4`). |
| **VIV** | **V**ortex-**I**nduced **V**ibration — lock-in resonance from vortex shedding. Resisted by a high **Scruton number**. |
| **Sc / St** | **Sc**ruton number `2mζ/ρD²` (VIV resistance; ≳10–20 robust) / **St**rouhal number (shedding frequency `fD/V`). |
| **Cd / Cl / Cm** | Drag / lift / (pitching-)moment coefficients. |
| **Re** | **Re**ynolds number — the viscous/inertial ratio `ρVc/μ` (sets the flow regime / drag). |
| **KJ** | **K**utta–**J**oukowski — the per-panel lift law `F = ρ Γ (V×dl)` used by the lifting-line solver. |
| **ASB / LL / VLM / VPP** | **A**ero**S**and**B**ox (the aero library) / **L**ifting **L**ine / **V**ortex **L**attice **M**ethod / **V**elocity **P**rediction **P**rogram. |
| **AWS / TWA** | **A**pparent **W**ind **S**peed / **T**rue **W**ind **A**ngle. |

---

## 5. Structures, materials & manufacturing

| Term | Meaning |
|---|---|
| **CFRP / UD** | **C**arbon-**F**ibre-**R**einforced **P**olymer / **U**ni**D**irectional ply (fibres one way). Default: T700/epoxy. |
| **CLT** | **C**lassical **L**aminate **T**heory — the A/B/D-matrix stiffness model for a stacked laminate. |
| **Tsai-Wu / max-strain** | Composite failure criteria (interaction polynomial / per-strain-component); reserve `R = 1/utilisation`. |
| **OML** | **O**uter **M**old **L**ine — the faired outer aerodynamic surface. |
| **FEA / FEM** | **F**inite **E**lement **A**nalysis / **M**ethod — the structural solver. |
| **Buckling / eigen / λ** | Linear buckling: `(K + λ·Kσ)φ = 0`; **λ** (eigenvalue) = the load multiplier at buckling (need λ ≥ 1.5, verified at n ≥ 24). |
| **Filament winding** | Wrapping resin-wet tow helically over a mandrel; **no true 0° passes**; min helical ≈5–15°. |
| **Mandrel** | The form the shell/spar is wound onto (slight taper or collapsible for release). |
| **Co-bond / co-cure** | Joining a cured part to an uncured one (co-bond) / curing two parts together (co-cure); the bonded interface must **not** be the critical load path. |
| **ILSS / GIC** | **I**nter**L**aminar **S**hear **S**trength / mode-I critical strain-energy-release-rate (bondline allowables). |
| **Vf** | Fibre **V**olume **f**raction (≈0.60; down-rated for wet-wound). |
| **Sandwich / core** | A skin = face / core / face (e.g. PVC foam) for bending stiffness at low mass. |
| **Knockdown** | A multiplicative strength/stiffness reduction (process, wet-wind, crimp, wrinkle). |
| **SF / FoS / R** | **S**afety **F**actor / **F**actor **o**f **S**afety / reserve factor `R = 1/utilisation` (R ≥ 2.0 op, FoS ≥ 3.0 survival). |
| **STL / STEP / VTU** | Faceted mesh CAD / CAD-exchange CAD / VTK-unstructured-grid (FEA-field visualisation) file formats. |
| **CAD / OCC / build123d** | Computer-aided design / OpenCascade (the geometry kernel) / the Python CAD library used. |

---

## 6. Optimisation & numerics

| Term | Meaning |
|---|---|
| **DV / design vector** | The optimisation **D**esign **V**ariables (ply thicknesses, radii, fractions, …) as a named-block vector. |
| **SLSQP / IPOPT** | **S**equential **L**east-**SQ**uares **P**rogramming / **I**nterior-**P**oint **OPT**imizer — the NLP solvers. |
| **KS aggregation** | **K**reisselmeier–**S**teinhauser smooth-max — aggregates many constraints into one differentiable scalar. |
| **Adjoint / SensCache** | The adjoint method for cheap gradients (`λᵀ ∂K/∂x`); SensCache memoises the per-element ∂K builds. |
| **FD** | **F**inite **D**ifference — used to validate every analytic gradient (central diff, rel-err ≤ ~1e-4). |
| **KKT / shadow price** | **K**arush–**K**uhn–**T**ucker optimality multipliers; the **shadow price** = kg-per-unit cost of a binding constraint (lever analysis). |
| **Multistart / warm-start** | Multiple optimiser starts to escape local minima / seeding a run from the nearest prior optimum. |
| **MILP** | **M**ixed-**I**nteger **L**inear **P**rogram (e.g. discrete ply-count selection). |
| **Converged + feasible** | A result counts only if the optimiser converged **and** all constraints hold (Article II); otherwise it's a *diagnostic*. |
| **ru_maxrss** | Peak resident memory (bytes on macOS) — recorded for heavy runs (memory-budget rule). |

---

## 7. Project conventions

| Term | Meaning |
|---|---|
| **Phases 0 / G / A / S / M / O / V** | The forward plan: groundwork / **G**eometry / **A**ero / **S**tructural / **M**aterials-mfg / **O**ptimisation / **V**erification (`plan.md`). |
| **R-\<area\>-\<n\>** | A testable **R**equirement (e.g. `R-GEO-5`, `R-AE-4`). Area codes: GEO, AERO/AE, LOAD, CON, SCN, PERF, MFG, OPT, EXP, GND (groundwork), GG (phase-G detail). |
| **G-\<n\>** | A top-level **G**oal / success criterion (`G-1`…`G-5`). |
| **D-\<n\>** | A **D**ecision / assumption with provenance + sensitivity (`D-1` RM curve, `D-2` feathering, `D-4` camber). |
| **OUT-\<n\>** | An explicit **out-of-scope** exclusion in a spec. |
| **MUST / SHOULD / MAY** | RFC-2119 requirement strength. |
| **Articles I–XIII** | The Constitution's governing principles (`constitution.md`); referenced by Roman numeral. |
| **Doc precedence** | constitution → specification → engineering_basis → plan → `specs/**` detailed → findings (top-down). |
| **Findings / decisions log** | `findings.md` — the append-only record of analyses + decisions (no forward plan); plans hold no findings. |

---

## 8. Reference platform

| Term | Meaning |
|---|---|
| **Oyster-595** | The reference yacht (≈19 m **LOA**, ~33 t displacement, ~180 m² upwind sail area, 27.6 m air draft). |
| **LOA** | **L**ength **O**ver**A**ll. |
| **Cat 3 / Cat 5** | Saffir-Simpson hurricane **Cat**egories (~100 kt / ~137 kt) — the survival wind speeds. |
| **c_mast / A_mast** | Bare-wingmast chord (≈0.5–1 m, `D-4`) / its planform area `c_mast·span` (≈22 m²) — sets the survival load. |
| **Project Amazon** | Eric Sponberg's Open-60 cat-ketch with **twin free-standing rotating carbon wingmasts** (1998) — the closest published prior art. Baseline: 2.5/1 ellipse (t/c 0.40), entasis taper, carbon box spar + glass fairings, deck-roller + heel-roller/thrust bearings, design = FoS×RM_max, t/ID ≥ 0.03. Dossier: `docs/respec_research/sponberg_amazon_prior_art.md`. |
| **Sponberg method** | Free-standing mast sizing: load = boat **RM_max** (constant partners→gooseneck, tapered to zero at both ends), design = FoS (3.0) × RM_max, ~½ knockdown on ideal laminate, deflection checked at **operational** (F4–5) load not max RM, local-buckling floor **t/ID ≥ 0.03** for a 50–80 % UD laminate. |
