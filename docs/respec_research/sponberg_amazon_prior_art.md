# Prior art baseline — Eric Sponberg free-standing rotating wingmasts (*Project Amazon*)

**Status:** reference / provenance (not a spec). Captured 2026-06-17 from primary sources at the
user's request ("use the design of these masts as a baseline"). All numbers below are from
**Sponberg's own primary documents** unless tagged otherwise; secondary web sources are marked.

*Project Amazon* is the closest published prior art to this project: a yacht carrying **two
free-standing, rotating, carbon-fibre wing masts**, engineered by a naval architect (Eric W.
Sponberg) who had by then designed ~50–60 free-standing masts and wrote the only practical
design paper on them. Its **structure, loads, bearings, and taper transfer directly**; its
**aerodynamic section does not** — on Amazon the *mast is the wing* (soft sails on a luff track
behind a 750 mm elliptical spar), whereas here the bare wingmast sits *inside* a large deployable
soft wingsail, so our mast section is set by the soft sail, not by mast aero.

## Sources (all self-hosted by Sponberg, primary unless noted)

| Tag | Document | URL |
|---|---|---|
| **PBB** | "Project Amazon and the Unstayed Rig," *Professional BoatBuilder* No. 55, Oct/Nov 1998, pp. 44–57 | ericwsponberg.com/wp-content/uploads/Project-Amazon-PBB.pdf |
| **SNAME** | "Project Amazon: An Open Class 60 Sailboat for Single-Handed Round-the-World Racing," *Marine Technology* Vol. 37 No. 2, Spring 2000, pp. 65–78 (SNAME) | ericwsponberg.com/wp-content/uploads/Project-Amazon-SNAME.pdf |
| **D&E** | "Design and Engineering Aspects of Free-Standing Masts and Wingmasts," 6th Chesapeake Sailing Yacht Symposium 1983 + **2011 author's addendum** (his updated rules) | ericwsponberg.com/wp-content/uploads/design-engineering-masts.pdf |
| **SOTA** | "Free-Standing Masts — Some Thoughts on the State of the Art" | ericwsponberg.com/wp-content/uploads/state-of-the-art-on-free-standing-masts.pdf |
| web | OceanNavigator "Rig developments / Unstayed rig for Around Alone"; SYDI project page | oceannavigator.com; ericwsponberg.com/boat-designs/project-amazon/ |

Both **PBB and SNAME agree to the digit** on the mast geometry and loads (the SNAME drawing
Fig. 17/18 reproduces the PBB drawing). The secondary OceanNavigator claim of a "3:1" section is
**wrong and explicitly contradicted by Sponberg**: *"A ratio of 3.0/1 would be too narrow"* — Amazon
is **2.5/1**.

## The boat

Open Class 60 **aluminium cat-ketch**, designed by Sponberg for owner/builder Sebastian Reidl for
the 1998–99 Around Alone (ex-BOC) singlehanded round-the-world race. Hull built Cape Town;
masts by **Ted Van Dusen / Composite Engineering, Concord MA**. Concept 1992, built 1996–97.
(Reidl retired in Leg 1, Oct 1998, citing keel-tank fuel contamination; boat later for sale in St
Martin.)

| Particular | Value (SNAME Fig. 16) |
|---|---|
| LOA / LWL | 18.28 m / 18.153 m |
| Beam / draft | 5.728 m / 4.50 m |
| Displacement (design) | 14.915 t — **built ~30 % heavy; race-ready 19.475 t** |
| Sail area (main+mizzen) | 125.3 + 125.7 m² (high-aspect elliptical, two masts) |
| Keel | aluminium **swing keel ±30°**, 21 %-thick GA(W) section, faired trim tab, ~1 t fuel inside |
| Range of stability / RA@90° (final) | 134.8° / 1.5224 m |

Note the keel is a **21 %-thick aerofoil explicitly chosen for stiffness** (SNAME p.71: "thicker
sections bend/twist less, stall less in waves, larger I and section modulus") — the *same*
deep-section argument that applies to our mast.

## The masts — geometry (PBB + SNAME, identical)

**Basic wing section: a 2.5/1 ellipse, 750 mm chord × 300 mm thickness at the largest section
→ constant t/c = 0.40 the full wing length.** Symmetric fore/aft and side/side. Sections are
**chord × thickness in mm**:

| Station | Role | Chord × thick [mm] | t/c |
|---|---|---|---|
| 6 (masthead) | top | 300 × 120 | 0.40 |
| 5 | | 437.5 × 175 | 0.40 |
| 4 | | 550 × 220 | 0.40 |
| 3 | | 637.5 × 255 | 0.40 |
| 2 | | 700 × 280 | 0.40 |
| 1 | | 737.5 × 295 | 0.40 |
| 0 | **at deck (max section)** | **750 × 300** | 0.40 |
| — | deck partners (bearing) | **500 mm OD round** | rotates |
| — | heel (bearing) | **450 mm OD round** | rotates |

- **Total mast length 25.63 m** (~84–85 ft); **sail-track length 21.94 m** (≈ our 22 m exposed span).
- **Taper = modified entasis** (SYDI standard): max section at the deck partners; fatter at
  mid-height than a straight taper ("stronger, stiffer, lighter"; Greek-column principle, also
  resists column buckling). Above the gooseneck a straight length then a math-formula taper,
  gentle then steeper toward the top. Below deck: round, straight taper 500→450 mm for the
  bearings/deck opening.
- **Section ratio band across Sponberg's wingmasts:** 2.5/1 (t/c 0.40, *narrowest he'll go*) →
  2.0/1 (0.50) → 1.25/1 (0.80, almost round). **3.0/1 (t/c 0.33) "too narrow."** The ellipse is
  chosen because its LE radius keeps flow attached and it is trivial to compute I/SM; "fatter
  sections are more forgiving, stall later, and buckle sideways less."

## The masts — construction & bearings (SNAME p.75; PBB p.52–54)

- **Primary structure = prepreg carbon-fibre box spar** (approximately rectangular), the primary
  load path, with **prepreg fibreglass (S/E-glass) leading- and trailing-edge fairings** bonded on
  to make the ellipse. Honeycomb/foam-cored sandwich shells; built over female tooling (one box
  half-mould + one LE/TE mould, cycled 4×). Rounds to OD 500 / 450 at the bearing stations.
- **Bearings (maps directly to our journal-BC model):**
  - **Deck partners:** stainless-steel **roller bearing** (radial).
  - **Heel:** **combination roller + thrust bearing** (radial **+ axial** — carries mast weight).
  - Both masts near-identical → interchangeable. Reefs/outhauls run in 19–25 mm PVC conduits
    through the deck bearing to below.
- **Wall thickness:** "**⅛″–½″ (3.2–12.7 mm) in most instances**"; box wall ~12.7 mm + ~5 mm
  skins on Amazon (drawing annotations). **Rule: t/OD ≥ 0.03.**
- **Mast mass: not published** in either paper (Amazon's build weights were never properly logged;
  boat ran ~30 % heavy). The web "~3 kg/m" figure is a *small-mast* generic — does not scale to an
  85-ft Open-60 mast; treat as unknown.

## Design loads & Sponberg's method (the transferable engineering)

From the Amazon drawings **and** his D&E methodology paper (with 2011 updates):

1. **Load = the boat's maximum righting moment.** "The maximum possible bending moment the mast
   can ever carry equals the maximum righting moment of the boat" (a free-floating boat can't load
   the mast past its own RM). Amazon: **RM_max = 185,000 ft·lbf ≈ 251 kN·m**.
2. **Moment distribution (design envelope):** spread **RM_max constant between partners and
   gooseneck**, then **taper linearly to zero at the masthead and to zero at the heel** (trapezoid).
   Simplified headline: **zero at top → max at the deck partners → zero at the heel.**
3. **Factor of safety:** Amazon used **2.5** (→ operating ≤ 40 % of breaking, since composite fibres
   begin failing at ~50 % of ultimate). **By 2011 Sponberg moved to FoS = 3.0** as standard practice
   — i.e. our basis's FoS ≥ 3.0 *is* his mature value; Amazon's 2.5 was the earlier figure.
   Design moment/mast (Amazon) = 2.5 × 251 = **462,500 ft·lbf ≈ 627 kN·m**.
   *(Both papers print "140,963 kg-m" for this — a units slip: 462,500 ft·lbf × 0.3048 with lb
   mislabelled kg. Correct is 627 kN·m / 63,940 kgf·m.)*
4. **Section-shape (local) buckling rule:** for a cantilever mast laminate **50–80 % unidirectional**,
   the minimum solid-laminate wall to prevent section buckling is **t/ID ≥ 0.03** (any height, any
   diameter). His concrete anti-buckling floor.
5. **Laminate:** **60–80 % UD axial**, remainder split between 90° hoop and ±45° bias; thicker at
   base, tapering to the top; built over a male mandrel (controlled inner surface).
6. **Material knockdown:** "the ideal laminate properties I tabulated are optimistic — **use about
   half**." (Independent confirmation of our ~0.5 knockdown.)
7. **Deflection is checked at OPERATIONAL load, not max RM:** double-integrate M/(E·I) along the
   tapered mast (section + wall both taper), normalised so heel and partners don't move, **at a
   Force 4–5 sailing load — NOT at max righting moment.** (Independent confirmation of our
   serviceability-operational-only rule.)
8. **Wing section properties:** compute actual I and SM of the wing shape directly (CAD
   mass-properties) — which we already do.

## Cross-check vs this project (what validates, what to revise)

| Item | Sponberg / Amazon prior art | Our current basis | Verdict |
|---|---|---|---|
| Mast **t/c** | 0.40 (Amazon); range **0.40–0.80** | **0.18** (NACA-0018, basis L49) | **REVISE** — 0.18 is thinner than any free-standing mast he builds; our own first-order wants t/c ≳ 0.57, mid-band. |
| Load basis | design = FoS × RM_max | RM_max ≈ 200 kN·m dominant | ✅ same philosophy |
| **FoS** | **3.0** (mature); 2.5 (Amazon era) | FoS ≥ 3.0 survival (cites Sponberg) | ✅ matches his current value |
| Material knockdown | "~half of ideal" | 0.5 knockdown (E1 135→67.5) | ✅ confirmed |
| Deflection datum | **operational/F4-5, not max RM** | serviceability = operational only (Art. IV) | ✅ confirmed independently |
| Local-buckling floor | **t/ID ≥ 0.03** | (first-order found buckling governs) | **ADOPT** as a buildable buckling-constraint floor |
| Moment shape | const partners→gooseneck, taper to ends | distributed aero → max at base | cross-check envelope; ours is the actual aero, his is a conservative design envelope |
| Supports | 2 bearings: deck roller + heel roller/thrust | journal BCs (partners + heel, axial at one) | ✅ built confirmation of the architecture |
| Section ratio cap | 3.0/1 "too narrow" (t/c 0.33 floor) | — | aero-driven on his masts; **ours is freer** (soft sail carries aero ⇒ can go deeper than 0.40) |
| Span | 21.9 m track / 25.6 m mast | 22 m exposed | ✅ near-identical scale |
| Per-mast RM | 251 kN·m (full boat RM each mast) | 200 boat / 160 OP-2 per mast | our loads are *not* high vs this prior art |

## Open items / still unknown
- **Mast mass** — unpublished in both primary papers (the one number we most want for a mass
  baseline). Would require Composite Engineering build records or a reconstruction from the
  laminate schedule (not in the papers).
- Exact **layup schedule by station** (ply counts) — described in method (60–80 % UD + off-axis)
  but the per-station ply table for Amazon is not in the papers.
