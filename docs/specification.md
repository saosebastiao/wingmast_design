# Specification — Free-Standing Rotating CFRP Wingmast (Oyster-595 Twin Rig)

**Version 1.0.0 · 2026-06-16.** Governed by `docs/constitution.md`; quantitative basis &
derivations in `docs/engineering_basis.md`; source brief `prompts/high_level_idea.md`.
This is the *top-level* specification. Per-feature detailed specs live under
`docs/specs/**` and trace back to this document.

Requirement IDs: **`R-<area>-<n>`** (testable), **`G-<n>`** (goals/non-functional),
**`D-<n>`** (decisions/assumptions), **`OUT`** (out of scope). MUST/SHOULD/MAY per RFC-2119.

---

## 1. Purpose & scope

Produce a parameterized, FEA-in-the-loop, **minimum-mass** design of a **free-standing
(unstayed), fully-rotating carbon-fiber wingmast** for a sailboat, plus the analysis and
optimization harness that sizes it and the exports that justify each milestone. The
wingmast serves as the structural spar **and** the guide rail for a reefable/stowable
**soft wingsail** raised on halyards.

- **In scope:** the rotating CFRP mast structure (stock + journals + transition + wing);
  the aerodynamic load envelope incl. the **tandem two-mast slot-effect interaction**; the
  composite + manufacturing physics for the **filament-wound box-spar / UD-longeron /
  filament-wound-shell** process; the minimum-mass optimization; and the required exports.
- **`OUT-1`** Multi-scale generality (drone-wing → turbine-blade). Single scenario only.
- **`OUT-2`** Structural modelling of the soft-sail membrane, halyards, and rig hardware —
  these are **applied loads/reactions only** (`D-3`).
- **`OUT-3`** Full higher-fidelity aero-structural co-optimization; hull/deck/keel design;
  VPP/route optimization beyond what sets the load split.
- **`OUT-4`** Detailed bearing/mechanism, deck-hardware, and sail-handling engineering
  beyond the load-introduction interface needed to size the spar.

---

## 2. Reference platform & development scenario

**Two distinct wings (terminology — used throughout).** The **wingmast** is the bare rigid,
rotating CFRP structure we design — a *small-chord* streamlined wing (chord `c_mast`, a
fraction of the wingsail chord). The **wingsail** is the wingmast **plus the deployed soft
fabric sail** — the large propulsive surface (NACA-0018, ~3.2 m mean chord, ~75 m²/mast).
**Operational loads arise from the wingsail (sail deployed, RM-limited); survival loads arise
from the bare wingmast (sail furled, feathered).** (basis §4)

`R-SCN-1` The design target is an **Oyster-595-class** yacht (≈19 m LOA, loaded
displacement ≈33 t, upwind sail area ≈180 m², air draft ≈27.6 m); see basis §1.

`R-SCN-2` The rig is **two tandem (fore-and-aft) free-rotating wingmasts**, symmetric
(equal height), each carrying a **tapered NACA-0018 soft wingsail** mounted in an
**aerodynamically balanced** way (sail area distributed fore *and* aft of the rotation
axis).

`R-SCN-3` The two masts **MUST** be independently controllable in angle of attack (to
balance steering and to power/depower) and spaced to benefit from the **slot effect**.
Nominal aero load split **50:50**; worst-case single-mast split **70:30 forward:aft**
(`R-LOAD-3`).

`R-SCN-4 (performance parity)` The tandem soft-wingsail rig **MUST** roughly match the
**upwind driving force of the standard rig** at the design condition. Match target:
equivalent drive force to 180 m² of standard rig, achieved with **~150–180 m² total wing
area** (75–90 m²/mast). See `D-4` (camber) and `R-AERO-2`.

---

## 3. Geometry & parameters

`R-GEO-1` The mast is modelled bottom-to-top as: **heel step** (lower journal, near the
keel) → **stock** (rotating circular section through the hull) → **deck partners** (upper
journal) → **transition zone** (circular → airfoil) → **wing root** → tapered **airfoil
wing** → **wing tip**. The stock rotates 360°+ over a fixed inner stub carrying two journal
bearings (basis §2).

`R-GEO-2 (parameters)` The design is parameterized by at least the following, each with
**bounds and increments** (Constitution: manufacturability + optimisation):

| Parameter | Notes |
|---|---|
| Rotational base diameter | stock diameter at the journals |
| Airfoil shape + chord | NACA-0018 reference; **arbitrary Kulfan/CST** airfoils supported (`R-GEO-4`) |
| Rotational-center foil offset | rotation axis position vs the section, distinct from CoM (basis §2) |
| Taper parameters | base→tip chord and thickness/ply taper |
| Entasis | convex spanwise bow (clarify vs taper-knot profile — `D-5`) |
| Sectional thickness / ply counts | per region; **integer plies** at build (`R-MFG-3`) |
| Blend-curve parameters | box-spar corner radii → imply longeron-channel size & longeron params (`R-GEO-5`) |
| Mast spacing | rotation-axis to axis, 1–2 chord (basis §2) |
| Box-spar layout | ≥3 chordwise box spars (LE curve, center section(s), TE curve) |
| **Bare-wingmast chord `c_mast`** | furled bare-mast section chord — a *fraction* of the wingsail chord; sets the survival area `A_mast` (`R-LOAD-2`) |

Concrete numeric bounds + increments for every parameter are populated in the Phase G
detailed spec (`docs/specs/01-rotating-geometry/`), seeded from basis §2 (e.g. root chord
4.0 m, taper 0.6, mast spacing 6–8 m). The brief's "all parameters have bounds and
increments" is satisfied there, not by inventing precision here.

`R-GEO-3` Root airfoil and tip airfoil **MAY** differ, with a spanwise blend.

`R-GEO-4` The airfoil source **MUST** support arbitrary **Kulfan/CST** parameters (not
only named NACA sections), preserving the project's closed-contour ordering convention;
NACA-0018 is the reference default. (`prompts/notes.md` item 1; `docs/prior_art/kulfan_2007.pdf`.)

`R-GEO-5 (manufacturing geometry)` The geometry **MUST** represent the prescribed build:
≥3 **filament-wound hollow box spars** (convex, blend-curve corners, slight taper for
mandrel release) co-bonded into the airfoil; the **inter-spar longeron channels** formed
by the rounded corners; and the **filament-wound outer shell** that fairs the assembly.
A structural core (inner shell + core + outer shell) is **MAY**, used only if stiffness
forces it (labour cost — avoid unless necessary).

---

## 4. Load cases (the design collection)

`R-LOAD-1` Sizing runs against a **typed load-case collection in `src/`** (Constitution
Article XII), classified **operational** (serviceability + ultimate) vs **survival**
(ultimate only). Magnitudes and derivations: basis §3–§4. Headline values (per mast,
design = static × DAF):

| ID | Case | Category | Design base bending / mast | Governs |
|---|---|---|---|---|
| **OP-1** | RM-limited heeling, 50:50 | operational | ~115 kN·m (RM 200) … 129 (RM 225) | deflection/twist |
| **OP-2** | Worst single mast, 70:30 | operational | ~160 … 180 kN·m | **spar strength + buckling (governs)** |
| SURV-1 | Bare **wingmast** (sail furled), Cat 3, feathered ~0° (`R-LOAD-2`) | survival | feathered ~10–40 kN·m | below operational |
| SURV-1f | Feathering-fault, off-axis Cl 1.0–1.2 (bare-mast area) | survival (fault) | ~390–470 kN·m | fault-tolerance check |
| SURV-2 | Bare wingmast, Cat 5 (off-axis bound) | survival (bound) | ~730–880 kN·m | ultimate sensitivity |
| **MFG-1** | Hoop-wind prestress + bondline | manufacturing | constraint set (not a bending case) | interfaces |

`R-LOAD-1b (torsion)` Operational **torque about the rotation axis** ≈ 6–9 kN·m design
(balanced wing, basis §3) — sizes the ±45° torsion plies, the twist constraint (`R-PERF-3`),
and the rotation-bearing torque; survival torque is small (feathered). Each case carries
bending **and** torsion.

`R-LOAD-2 (survival — bare wingmast, feathered)` SURV-1 is the **bare wingmast** (soft sail
furled), feathered to ~0° AoA, computed on the **bare-wingmast planform** `A_mast = c_mast ·
span` (the small structural section — **NOT** the larger wingsail chord), drag-dominated
(Cd ≈ 0.02–0.10) ⇒ design load **~10–40 kN·m, below operational** (basis §4). Under reliable
feathering, **OP-2 governs the spar.** `SURV-1f` is the **feathering-fault** check
(mechanism jam / power loss / vane failure): off-axis Cl ≈ 1.0–1.2 on `A_mast` ⇒ ~390–470
kN·m (Cat 3); a locked-broadside mast is worse still. The optimistic pure-0° value **MUST
NOT** be the *sole* design point unless robust, redundant feathering is *demonstrated*; the
SURV-1f design AoA and the FoS it must carry come from the Phase A study (`D-2`). Any
governing or fault case is **eigen-verified at n ≥ 24** (Articles III–IV).

`R-LOAD-2a (feathering robustness)` The design SHOULD maximise weathervane reliability —
pivot forward of the bare-section aerodynamic center (positive yaw restoring moment), aero
balance, yaw damping, mechanical AoA stops, VIV-lock-in detuning, and **redundant feathering**
(active AoA control + passive trailing vane) — to keep SURV-1 in the feathered regime.

`R-LOAD-2b (feathering-robustness reporting — gate D-2)` From the Phase A study, report: the
credible maximum off-axis AoA (`AoA_max`), the vane restoring-moment-vs-AoA slope, the yaw
damping ratio, and the VIV lock-in susceptibility (Scruton number). The structure is sized
to `AoA_max`; whether `SURV-1f` governs follows from it.

`R-LOAD-3` The per-mast load split derives from the tandem aero model (`R-AERO-2`); each
spar is sized to **OP-2 (70:30)**, not the 50:50 nominal.

`R-LOAD-4` Aerodynamic loads **MUST** be distributed along the span as normal force,
**chordwise/tangential drag, and torsion about the rotation axis** (not normal-only), and
fed to the structural model. Self-weight + inertial (heel) body loads are included for
operational cases.

`R-LOAD-5 (dynamic amplification)` A gust/seaway DAF (≥1.5 operational; the survival case
folds gust into q and FoS) applies; the slender free-standing mast's **vortex-shedding /
dynamic amplification** is assessed rather than assumed covered by a single scalar (basis
open-q #5, #9).

---

## 5. Design constraints

`R-CON-1 (geometric fit)` Assembly members **MAY** touch but **MUST NOT** intersect;
nothing exceeds the outer-shell envelope. Box spars + longerons + shell fit within the
faired OML at every station.

`R-CON-2 (manufacturability)` Every design **MUST** be buildable by the prescribed process
(Constitution Article V):
- `R-MFG-1` Filament-winding angle feasibility: **no true 0° longitudinal passes**;
  helical angles within the windable set for the local mandrel; non-geodesic slippage
  bound respected (basis §7).
- `R-MFG-2` Box-spar windability/release: convex sections, blend-curve corners, taper or
  collapsible-mandrel feasibility.
- `R-MFG-3` **Integer-ply discretisation** at a known band thickness, with a mandatory
  first-layer hoop floor; FEA re-verify after rounding.
- `R-MFG-4 (interfaces)` Co-bond vs co-cure declared per joint; **bonded/secondary
  interfaces checked at knocked-down interlaminar/bondline allowables and MUST NOT be the
  critical load path.**

`R-CON-3 (boundary conditions)` The structural model **MUST** apply **journal/bearing**
boundary conditions (two spanwise-separated radial supports at heel-step and partners;
released pivot-axis rotation; the heel step reacting thrust) — **not** a rigid root clamp.

---

## 6. Performance constraints & reportable metrics

For every qualifying design, report and constrain (thresholds: basis §8; serviceability
limits apply to **operational** cases only):

| Metric | Constraint | Report |
|---|---|---|
| `R-PERF-1` Strength / survival | no failure under any load case; Tsai-Wu/max-strain reserve R ≥ 2.0 (op) / FoS ≥ 3.0 (survival), where R = 1/utilisation | governing case, margin |
| `R-PERF-2` Stiffness | tip deflection ≤ 2 % exposed span (0.44 m) — operational | mm |
| `R-PERF-3` Twist | tip twist ≤ 5.0° — operational | degrees |
| `R-PERF-4` Buckling | eigen λ ≥ 1.5 (lowest 2–3 modes), verified n ≥ 24, **per load case**; survival judged solely on the converged eigen | λ_cr, mode, case |
| `R-PERF-5` Mass | minimise (objective) — CFRP spars + longerons + shell; hardware excluded, reported separately | kg (per mast + total) |
| `R-PERF-6` Center of mass | report | m (height above heel) |
| `R-PERF-7` Bearing/interface | journal reactions, bondline util < 1 | kN, util |

`R-PERF-8` A mass is reportable only if **converged AND feasible** with measured
wall-clock (Constitution Articles I–II); within-noise (~2–3 %) differences are not wins.

---

## 7. Optimization problem

`R-OPT-1` **Minimise** total CFRP mass of both wingmast spars + skins, **subject to** all
§5 design constraints and §6 performance constraints, over the §3 parameters within their
bounds.

`R-OPT-2` Method: gradient-based NLP (SLSQP, escalating to **IPOPT** for the larger
box-spar + longeron + wind-angle design vector and on SLSQP stalls), with **FD-validated
analytic gradients** (Article IX), **KS aggregation** of max-based constraints for
smoothness, **multistart**, and **warm-started** sweeps (Article X).

`R-OPT-3` The harness proposes parameters → applies design constraints → if feasible,
simulates performance → ratchets the best feasible mass as the new threshold; it computes
**parameter sensitivities / shadow prices** to direct the next lever (the brief's
"intelligently chooses parameters" / sensitivity-model intent).

---

## 8. Required deliverables (per qualifying design above a performance threshold)

`R-EXP-1` **Assembly visualization** (CAD: STL/STEP via the sized-export path; OCP viewer).

`R-EXP-2` **Manufacturing-process simulation/visualization** — the build sequence
(box-spars → filled longeron channels = new mandrel → filament-wound outer shell), tow-path
/ winding-angle fields. *(Green-field; see plan Phase M/G.)*

`R-EXP-3` **Stress/strain visualization** — FEA fields (`exports/*.vtu`) + ParaView
screenshots for the governing cases.

`R-EXP-4` Each milestone records, in `docs/findings.md`, the command that regenerates all
of the above (Constitution Article XI).

---

## 9. Success criteria (acceptance for "spec-compliant v1")

`G-1` *(Articles V, XI)* A parameterized rotating-wingmast CAD model exists with the §3
parameters + bounds, producing a valid box-spar / longeron / shell assembly that passes
`R-CON-1` geometric fit.

`G-2` *(Articles IV, XII)* The aero subsystem produces the §4 load envelope **including the
tandem slot-effect load split** and the bare-wingmast feathered/fault survival loads,
distributed per `R-LOAD-4`.

`G-3` *(Articles III, IV, V)* The structural subsystem solves all load cases with **journal
BCs** (`R-CON-3`), composite laminate mechanics, co-bond interfaces, and **converged-mesh
eigen buckling**.

`G-4` *(Articles I, II, VI, X, XI)* The optimizer returns a **converged, feasible,
minimum-mass** design for the twin rig against the full load collection, with
shadow-price-directed lever analysis, measured wall-clock, and the three required exports —
for a stated set of pinned inputs (`D-1`, `D-2`).

`G-5` *(Articles V, IX, XI, XII)* Every analytic gradient has an FD-validation test; the fast
unit suite is green; manufacturability constraints (`R-MFG-*`) are enforced so the headline
is an **as-buildable** mass, not an idealised one.

---

## 10. Key decisions & assumptions (with sensitivity)

`D-1` Reference RM_max = **200 kN·m central** (bracket 150–225); **derived/unpublished —
dominant linear sensitivity** on all operational loads. *Action:* pin from the real
stability curve (basis open-q #1).

`D-2 (top lever — feathering, not a binary lock/free fork)` The survival load, and hence
whether **survival or operational governs the spar**, is set by **feathering robustness**,
not by a lock-vs-free choice (basis §4; corrected 2026-06-16). A *reliably feathering* mast
sits in the low-drag regime (operational governs); imperfect feathering drives the off-axis
transient bound (survival governs by several-fold); a *locked* mast only helps if held
head-to-wind and is the **worst** case if locked broadside. *Action:* the first trade study
(plan Phase A gate) is an aeroelastic/vane-dynamics + CFD study to (i) establish the credible
maximum off-axis AoA the structure must survive and (ii) design the feathering mechanism
(pivot-vs-AC margin, damping, AoA stops) to minimise it. This is the largest mass lever in
the project.

`D-3` Structural object = the **mast only**; soft sail + halyards = applied loads
(`OUT-2`).

`D-4 (camber)` 150 m² parity assumes the soft wingsail develops **operating camber when
sheeted** (CL ≈ 1.45); NACA-0018 is the *faired mast section*, not the operating section.
A plain symmetric section gives no area saving → otherwise budget ~180–190 m². *Action:*
confirm via the tandem aero model (basis §5).

`D-5` "Entasis" is treated as a convex-bow term; reconcile with the taper-knot profile
when the geometry parametrization is built.

`D-6` Material = project default T700/epoxy (Vf 0.60), **down-rated for wet-wound**;
co-bond knockdowns set from process coupons (basis §6–§7).

`D-7` Keel-stepped (two-bearing couple) assumed; deck-stepped would add the +50 % step
penalty and change the base arm (basis open-q #6).

> Decisions `D-1`, `D-2`, `D-4` and basis open-questions §9 are the agenda for the next
> (detailed-spec) session and gate the absolute mass numbers — not the methodology.
