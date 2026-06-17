---
name: wingmast-domain
description: Use as the durable reference for wingmast domain facts — terminology (stock, journals, heel step, deck partners, transition zone), the axis/contour conventions, the load-case collection (OP-1/OP-2/SURV-1/SURV-2/MFG-1) and which case governs, the design parameters, and the manufacturing concept. Consult before geometry, aero, structural, or sizing work so these aren't re-derived.
---

# Wingmast domain reference

Authoritative numbers: `docs/engineering_basis.md`. Requirements: `docs/specification.md`.
This is the quick lookup so you don't re-derive them.

## Anatomy (bottom → top)

**heel step** (lowest, near keel; lower journal) → **stock** (rotating circular section
through the hull) → **deck partners** (top of stock; upper journal) → **transition zone**
(circular → airfoil) → **wing root** → tapered **airfoil wing** → **wing tip**.
The stock rotates 360°+ over a fixed inner stub carrying two **journal bearings**;
`F_bearing = M_base / bury`. **Rotational center** (rotation axis) is distinct from the
**center of moment** (aerodynamic) — the offset between them is a design parameter.

## Configuration

Two **tandem** (fore-and-aft) free-rotating wingmasts, NACA-0018 **soft wingsails**,
independently AoA-controlled, spaced **1.5 chord ≈ 6 m** (range 1–2c) for the slot effect.
Object of optimization = the **mast** (soft sail + halyards = applied loads only).

**Two wings (don't conflate):** the **wingsail** = bare mast **+ deployed soft sail** = the
large propulsive surface (~3.2 m chord, ~75 m²/mast) → drives the OPERATIONAL loads. The
**wingmast** = the bare rigid CFRP structure alone (chord `c_mast` ≪ wingsail) → drives the
SURVIVAL loads (sail furled, feathered).

## Axis & contour conventions (preserve)

- Axes: **chord +X, span +Z, airfoil normal +Y**; rotation axis at X=0,Y=0; Z=0 at wing root;
  transition `z ∈ [-transition_length, 0]`; stock below.
- Airfoil contour: `(N,2)` cosine-spaced, traversed **upper-TE → LE → lower-TE**, duplicate TE
  point dropped before closing a periodic spline. Any Kulfan source preserves this ordering.
- build123d loft uses **`ruled=True`** (BSpline-smooth loft overshoots across the
  airfoil→circle morph). Transition blend = smoothstep `f(u)=u²(3-2u)`.

## Load-case collection (size each mast to OP-2 + SURV-1)

| ID | Case | Category | Design base bending / mast | Governs |
|---|---|---|---|---|
| OP-1 | RM-limited heeling, 50:50 | operational | ~115–129 kN·m | deflection/twist |
| **OP-2** | Worst single mast, 70:30 | operational | ~160–180 kN·m | **spar (governs)** |
| SURV-1 | Bare **wingmast**, furled, Cat 3, feathered ~0° | survival | ~10–40 kN·m | below operational |
| SURV-1f | Feathering-fault, off-axis Cl 1.0–1.2 (bare-mast area) | survival (fault) | ~390–470 kN·m | fault check |
| SURV-2 | Bare wingmast, Cat 5 (off-axis bound) | survival bound | ~730–880 kN·m | ultimate sensitivity |
| MFG-1 | Hoop-wind prestress + bondline | manufacturing | constraint set | interfaces |

**Operational (OP-2) GOVERNS the spar** under the design assumption of reliable feathering
(corrected 2026-06-16). Survival is the **bare wingmast** (small area `A_mast = c_mast·span`,
**not** the wingsail chord) feathered to ~0° → drag-dominated ~10–40 kN·m, well below OP-2.
`SURV-1f` (feathering fault: off-axis lift ~390–470 kN·m; locked-broadside worse) is a
fault-tolerance check, not the primary driver. Size SURV to a justified max off-axis AoA,
**eigen-verify at n≥24**, and maximise feathering robustness (pivot fwd of AC, yaw damping,
AoA stops, redundant active+vane) — the top mass lever (`docs/specification.md` D-2 /
R-LOAD-2).

## Targets

Tip deflection ≤ 2 % span (0.44 m, operational only); tip twist ≤ 5° (operational only);
buckling eigen λ ≥ 1.5 (n≥24, lowest 2–3 modes); strength R ≥ 2.0 op / FoS ≥ 3.0 survival;
bondline util < 1. Objective: min total spar+skin mass (both masts).

## Design parameters (each with bounds + increments)

Rotational base diameter · airfoil shape+chord (Kulfan/CST; NACA-0018 ref) · rotational-center
foil offset · taper · entasis · sectional thickness/ply counts (integer plies) · blend-curve
params (→ longeron-channel size) · mast spacing · box-spar layout (≥3 chordwise spars).

## Manufacturing concept

≥3 filament-wound hollow box spars (convex, blend-curve corners, slight taper for release)
→ co-bonded into the airfoil → UD tow laid into inter-spar **longeron channels** and
VARTM-infused (longeron + glue + gap filler) = the new mandrel → **filament-wound outer
shell** fairs it. No true 0° passes; min helical ~5–15°; integer plies + first-layer hoop
floor; **bonded interface never the critical load path**. Material: T700/epoxy (Vf 0.60),
down-rated for wet-wound (`docs/engineering_basis.md` §6–§7).

## Reference platform (Oyster 595)

LOA 19.05 m, loaded disp ~33 t, upwind sail area 180 m² (drive-force match target), air
draft 27.6 m. **RM_max ≈ 200 kN·m central (bracket 150–225) — derived/unpublished, the
dominant linear sensitivity on all operational loads.** Twin-rig: 22 m exposed span, root
chord 4 m, taper 0.6, CE 10.7 m above partners, ~150 m² total wing area (assumes cambered
operating section — a plain symmetric 0018 gives no area saving; `D-4`).
