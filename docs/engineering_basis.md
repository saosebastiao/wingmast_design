# Engineering Basis — Oyster-595 Twin Wingmast

**Established 2026-06-16** from a 14-agent research + audit workflow (raw dossier:
`docs/respec_research/respec_basis_audit.json`), with the critical load chain
**independently recomputed by three adversarial verifiers**. This is the quantitative
backing for `docs/specification.md`. Numbers here are the *derivation*; the spec states
them as *requirements*. Per Constitution Article IV every derived input carries its
provenance and sensitivity.

> **Status of the numbers.** All arithmetic reproduced cleanly across three independent
> recomputes. The two substantive corrections the verifiers forced into this basis (vs
> the first-pass synthesis) are called out inline as **[CORRECTION]**. The biggest single
> sensitivity is the reference boat's righting moment, which is **not published** and
> scales every operational load linearly.

---

## 1. Reference platform (Oyster 595, Humphreys design, 2021; CE Cat A)

| Quantity | Value | Provenance |
|---|---|---|
| LOA / LWL / beam | 19.05 / 16.81 / 5.36 m | published |
| Draft (fin) | 2.68 m | published |
| Displacement (light / loaded) | 30,807 / 33,324 kg | published |
| Design-max displacement | ~38,000 kg | **derived** (loaded + payload margin) |
| Ballast | ~9,150–11,500 kg (~30–37 % lightship) | **derived** |
| Air draft above DWL (std rig) | 27.59 m | published |
| Standard rig | fractional sloop, in-mast-furling main + ~105 % genoa | published |
| Upwind sail area (100 % foretriangle) | **180 m²** (catalog w/ furling ≈ 167) | published; use 180 as the drive-force match target |
| **Max righting moment RM_max** | **200 kN·m central (bracket 150–225)** | **derived — see §3, dominant sensitivity** |
| RM at 30° heel (rig-sizing ref) | ~150 kN·m (bracket 106–186) | **derived** (NBS / ISO 12215-9 basis) |

**[CORRECTION] RM_max.** The first-pass synthesis adopted 225 kN·m
(= 38,000 kg × g × GZmax 0.60 m). Two of three verifiers showed that 225 sits at the
**optimistic top** of the credible band — it requires *both* the unpublished design-max
displacement *and* a generous GZmax. Using the **published loaded displacement
(33,324 kg)** with GZmax 0.60 gives ~196 kN·m. **Adopt RM_max ≈ 200 kN·m as the central
design value; carry 225 kN·m as a conservative upper bracket.** Operational loads scale
linearly with this number — pinning the real RM curve from Oyster / the ISO 12215 stability
booklet is open-question #1.

---

## 2. Twin-wingmast geometry targets (assumed concept — to be pinned)

| Parameter | Value | Notes |
|---|---|---|
| Configuration | 2 tandem, fore-and-aft, free-rotating | 50:50 nominal aero split, independent AoA |
| Airfoil (faired mast section) | NACA 0018 (symmetric, t/c 0.18) | rotation axis ~0.25c |
| Exposed wing span (above deck) | 22.0 m | vs 26.8 m std rig — shorter, recovers area via higher drive coefficient |
| Deck above WL | 1.8 m | |
| CE above WL / above partners | 12.5 m / **10.7 m** | 10.7 m is the operational cantilever arm |
| Heeling lever (CE above WL + CLR below WL) | **14.0 m** | CLR 1.5 m below WL |
| Stock length (deck → heel, bury) | ~3.1 m | AeroRig ~1/7-of-above-deck rule; sets bearing-couple loads |
| Reference (root) chord / tip chord | 4.0 m / 2.4 m | taper ratio 0.6 |
| Per-mast **wingsail** area (sail deployed) | 75 m² (150 m² total) | from drive-force match, §5 |
| **Bare-wingmast chord `c_mast`** (sail furled) | fraction of wingsail chord; ~1.0 m placeholder (TBD) | sets survival area A_mast ≈ c_mast·span ≈ 22 m² ≪ 70 m² wingsail (§4) |
| Mast spacing (rotation-axis to axis) | **1.5 chord ≈ 6.0 m** (range 1–2c) | Munk stagger theorem frees streamwise spacing from induced-drag penalty; choose for coupling + helm balance |
| Rotational-center offset | rotation axis at cambered operating CoP, ≈0.25c | keep residual hinge torque small |
| Bearing arrangement | fixed inner stub + two journals (upper @ partners, lower @ heel) | outer wound mast rotates 360°; F_bearing = M_base / bury |

**[CORRECTION] span/AR descriptor.** 75 m²/mast at *mean* chord 3.2 m ⇒ ~23 m aero span,
AR ~7 (the first-pass "18.75 m span, AR 4–5" used the *root* chord). Cosmetic; does not
affect loads. Note the 23 m aero span slightly exceeds the 22 m structural exposed span —
reconcile when the planform is pinned.

---

## 3. Operational load chain (per mast)

Equilibrium ceiling: **steady aero heeling moment cannot exceed the hull's max righting
moment.** This caps usable sail force regardless of wind.

```
RM_max (whole boat)                         = 200 kN·m   [central; 225 upper bracket]
 → 50:50 split per mast                      = 100 kN·m
 → transverse aero force / mast (÷14.0 m lever) = 7.14 kN  (both masts 14.3 kN)
 → base/partners bending (×10.7 m arm)       = 76.5 kN·m static
 → × DAF 1.5 (Nordic Boat Standard gust/seaway) = 115 kN·m   ← OP-1 design / mast
```

At the 225 upper bracket the same chain gives **86.0 → 129 kN·m** (the numbers all three
verifiers reproduced exactly). **OP-1 design band: ~115 kN·m (RM 200) to 129 kN·m
(RM 225).**

**Worst single mast (OP-2).** In true tandem (spacing ≥ 1c) the **leading** rig carries
the larger, steadier load; the trailing rig is shadowed. Adopt a **70:30** forward:aft
split (low-Re tandem-wing CL evidence). 0.70 × RM gives **~160 kN·m (RM 200) to 180 kN·m
(RM 225)** design. Absolute single-mast bound (100 % share, still capped by whole-boat RM)
≈ 229–258 kN·m. **Each spar is sized to the OP-2 case, not the 50:50 nominal.**

**Operational torque (balanced wing):** T = q·A·c·|Cm_axis|, q ≈ 74 Pa, Cm_axis ≈ −0.16
⇒ ~4.3 kN·m static, ~6–9 kN·m design. Sets the ±45° torsion plies / twist stiffness and
the rotation-bearing torque.

---

## 4. Survival load chain (bare wingmast, furled, hurricane) — **operational normally governs**

**Two distinct wings (the key distinction).** The **wingsail** = the bare mast *plus the
deployed soft fabric sail* — the large propulsive surface (NACA-0018, ~3.2 m mean chord,
~75 m²/mast) that drives the boat and is RM-limited (§3). The **wingmast** = the bare rigid
rotating CFRP structure *alone* — a *much smaller* streamlined wing (chord `c_mast` ≈ a
fraction of the wingsail chord; placeholder ~1.0 m → bare planform A_mast ≈ c_mast·span ≈
22 m², ≪ 70 m² wingsail; `c_mast` TBD, §2). **Operational loads come from the wingsail
(deployed); survival loads come from the bare wingmast (sail furled).**

In survival the soft sail is **furled/stowed** and the bare wingmast is **feathered into the
wind** (~0° AoA) by an active-AoA-control and/or trailing-wind-vane mechanism (design
baseline; assumed reliable, with redundancy). So survival is a *small-area, drag-dominated*
case:

```
q(100 kt, Cat 3) = ½·1.225·(100·0.5144)² = 1621 Pa;   q(137 kt, Cat 5) = 3042 Pa
bare-wingmast planform A_mast ≈ c_mast·span ≈ 1.0·22 ≈ 22 m²  (≪ 70 m² wingsail);  arm ≈ 11 m

(design)      FEATHERED ~0° AoA, Cd ≈ 0.02–0.10:
    M = q·Cd·A_mast·arm = 1621·(0.02–0.10)·22·11 ≈  8–39 kN·m   ← far below operational
(reference)   OPERATIONAL OP-2:                      ~160–180 kN·m   ← GOVERNS the spar
(fault check) FEATHERING FAILS, off-axis Cl ≈ 1.0–1.2:
    M = q·Cl·A_mast·arm ≈ 390–470 kN·m (Cat 3; 3-s gust ×1.69 ⇒ ~660–790); Cat 5 ~730–880
(fault)       LOCKED BROADSIDE, Cd ≈ 1.5:            ≈ 590 kN·m (Cat 3)
```

**[CORRECTION — user, 2026-06-16].** This supersedes *both* earlier survival numbers. The
first-pass 450 kN·m used an arbitrary slim strut; the verifiers' "corrected" ~1,300 kN·m used
the **full wingsail chord** — but the bare *wingmast* is neither: it is the small rigid
structural section with the **sail furled**. With the correct small area **and** feathering
(Cd, not Cl), the design survival load is **~10–40 kN·m — far below operational**, so
**OP-2 (~160–180 kN·m) governs the spar.** The off-axis figures (~390–470 kN·m) are a
**feathering-FAULT check** (mechanism jam / power loss / vane failure), *not* the primary
design point; whether they must be carried at full FoS is a design decision, mitigated by
**redundant feathering** (active control + passive vane). A *locked* mast is not a win
either — locked broadside is the worst regime. Eigen-verify any governing case at n ≥ 24
(Articles III–IV).

**Net:** under the design assumption of reliable feathering, **survival does NOT govern —
the project is operational-governed.** The items to pin are feathering reliability and the
required feathering-fault FoS (open-q #2, #5), and `c_mast` (which sets A_mast).

---

## 5. Performance parity — sail area & the camber caveat

Drive-force match at equal q: A_wing = A_std · (Cx_std / Cx_wing). The adopted **150 m²
total** (vs 180 m² sloop) implies a ~1.20× drive-coefficient uplift for the wing rig —
within the documented 15–40 % wingsail advantage.

**[CORRECTION] camber dependency.** A *plain symmetric* NACA-0018 maxes at CL ≈ 1.1–1.2,
≈ the same as a good soft sail — giving **no area saving** (would need ~180–190 m²).
Reaching 150 m² requires the wing to operate at **CL ≈ 1.45**, i.e. with **effective
camber**. This is physically consistent: a *soft* wingsail draped on the mast **develops
camber when sheeted** to one side, so the symmetric NACA-0018 is the *faired mast section*,
not the operating section. The spec must state this explicitly. **Treat 150–180 m² total
as the credible range**; confirm via the tandem aero model at design Re and the actual
t/c = 0.18 cambered operating section (open question #3).

---

## 6. Material system (UD carbon / epoxy)

Project defaults (preserve; flag as "typical — replace with supplier/as-wound data"):

| System | E1 | E2 | G12 | ν12 | Xt | Xc | Yt | Yc | S12 | ρ (kg/m³) |
|---|---|---|---|---|---|---|---|---|---|---|
| T700/epoxy (Vf 0.60) | 135 | 8.5 | 4.5 | 0.32 | 2200 | 1200 | 60 | 200 | 80 | 1550 |
| T800/epoxy (Vf 0.60) | 165 | 8.5 | 5.0 | 0.32 | 2900 | 1500 | 60 | 210 | 90 | 1580 |
(GPa unless noted.)

**Wet-wound knockdown:** filament-wound/infused laminates run higher void / lower Vf
(~50–58 %) than prepreg — down-rate allowables accordingly. No cured-ply thickness constant
exists in code today; winding sizing counts **integer bands of a known band thickness**
(add it). Off-axis transverse/shear strengths are 25–50× below longitudinal, so every
off-axis or interlaminar path is a potential design driver.

---

## 7. Manufacturing constraints (filament winding + co-bond)

- **No true 0° axial passes** (the head reverses at the poles): spar caps are pre-laid
  UD tow/tape under the wound ±helical and 90° hoop layers.
- **Non-geodesic winding stability:** slippage λ = |k_g/k_n| ≤ μ ≈ 0.2–0.5. Practical
  **min helical angle ~5–15°** (long sections) up to **~15–20° unwindable** at short/blunt
  ends.
- **Mandrel:** slight taper for release, or a collapsible mandrel for straight sections.
- **Longerons:** dry UD tow laid into the inter-spar channels and **VARTM-infused** in
  place — strengthening longeron + glue + air-gap filler that fairs the box-spar assembly
  into the new "mandrel" for the outer shell.
- **Co-cure vs co-bond:** a co-cured (monolithic) joint keeps in-laminate allowables; a
  **co-bonded / secondary-bonded** joint reverts to interlaminar/bondline allowables
  (lap-shear ~20–40 MPa, ILSS ~30–120 MPa) — ~1 order of magnitude lower. Set GIC/ILSS from
  DCB/ENF coupons on the *actual* process; model with cohesive-zone elements or require
  interlaminar util < 1 with the knockdown. **The bonded interface must never be the
  critical load path** (Constitution Article V).

---

## 8. Sizing targets (acceptance thresholds)

| Metric | Target | Applies to | Basis |
|---|---|---|---|
| Objective | min total spar+skin mass (both masts) | — | Article VI |
| Tip deflection | ≤ 2 % exposed span = 0.44 m | **operational only** | project convention; serviceability, not survival |
| Tip twist | ≤ 5.0° | **operational only** | project convention; AoA fidelity |
| Buckling reserve | eigen λ ≥ 1.5 on lowest 2–3 modes, **verified n ≥ 24** | all | Article III |
| Strength FoS — operational | Tsai-Wu / max-strain R ≥ 2.0 | operational | project convention |
| Strength FoS — survival/ultimate | FoS ≥ 3.0 (bracket 2.5–4.0) | survival | Sponberg free-standing-spar ≈ 3.0 on max-RM; wind-blade γ_f·γ_m = 3.3–4.0 converge; DNV-ST-0412 Cat I RF 4.5/3.1 conservative alt |
| Bondline/interlaminar | util < 1 at knocked-down allowables | all interfaces | Article V |
| Wall/diameter floor | ≥ 3–4 % of local diameter | all | local-shell-buckling sanity, superseded by n≥24 eigen |

**Caveat (verifiers):** FoS 3.0 is only as good as the load it multiplies — apply it to the
**justified** survival load for the design feathering regime (§4 regime a–b), eigen-verified
at n ≥ 24, never to an optimistic 0°-drag idealisation if feathering cannot be guaranteed.

---

## 9. Open questions / dominant sensitivities (ordered)

1. **Obtain the real Oyster-595 RM curve** (RM_max, RM30, GZmax angle) — replaces the
   derived 200/225 kN·m that drives every operational load linearly.
2. **Feathering robustness & the credible max off-axis AoA** (§4) — the design lever that
   sets whether survival (regime b, several-fold above operational) or operational (regime a)
   governs the spar. Pin via CFD + vane/aeroelastic dynamics; design the pivot-vs-AC margin,
   yaw damping, AoA stops, and VIV detuning to drive the design load toward regime (a).
   Locking is *not* a clean win (locked-broadside is the worst regime). Largest mass swing in
   the project.
3. **Pin the twin-rig planform** — per-mast area / CE height / mean chord / CLR depth; and
   the symmetric-section-vs-cambered-operating-point reconciliation for the 150 m² claim.
4. **Compute the soft-wingsail Cm_ac and cambered CoP** (XFOIL / AeroSandbox at design Re)
   to firm up the balance axis, residual hinge torque, and the rotational-center offset.
5. **Off-axis Cl of an imperfectly weathervaned bare wing in a hurricane** (CFD / wind
   tunnel on the actual fat section, incl. post-stall galloping/VIV) — biggest single driver
   of the governing survival moment.
6. **Keel-stepped vs deck-stepped** + actual bury — sets the base arm, the NBS +50 %
   deck-step penalty, and the journal-bearing couple loads.
7. **Aft-mast unsteady / buffet spectrum** in the leading rig's wake — the aft mast may be
   fatigue- rather than peak-load-driven.
8. **Bondline GIC/ILSS** from coupons on the actual skin-to-spar process; co-cure vs
   co-bond decision for the shell-to-spar joint.
9. **Slam / wave-impact g-level** for a real vessel (the prior project's slam case is a
   research-level open problem; converged slam buckling did not plateau).
10. **VPP sweep across TWA** — the 50:50/70:30 split and the 1–2c optimal spacing are
    upwind/level values; downwind shadowing and heel move both.

These map onto the plan's early phases and are the agenda for the next (detailed-spec)
session.
