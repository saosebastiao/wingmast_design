# Spec — Amazon-baseline wingmast (calibration → reproduce → beat) (Phase X)

**Status:** draft · **Parent:** `docs/specification.md` `R-GEO-1…5`, `R-PERF-1…7`, `R-LOAD-1…5`,
`R-MFG-1…4`, `R-CON-1…3`, `R-OPT-1…3`, `R-EXP-1…4`, goals `G-1`/`G-3` · prior art
`docs/respec_research/sponberg_amazon_prior_art.md` · Constitution Articles **I** (measure
wall-clock), **II** (converged AND feasible), **III** (eigen-verify n≥24), **IV** (physics
honesty; serviceability operational-only; flag derived inputs by sensitivity), **V**
(manufacturability; bonded interface never the critical path), **IX** (FD-validate gradients),
**X** (warm-start), **XI** (regenerable CAD + analyses).

## Scope

Re-baseline the geometry onto **Eric Sponberg's *Project Amazon* wingmast** (the closest built,
professionally-engineered free-standing rotating carbon wingmast — prior-art dossier) and use it
as a **calibration benchmark**:

1. **(X1) Reproduce his OML in CAD** — a parametric `amazon_mast` geometry from the published
   station table (2.5/1 ellipse, 750×300 mm at deck → 300×120 mm at top, modified entasis,
   25.63 m mast / 21.94 m sail track, rounding to round OD 500 / OD 450 at the two bearings).
2. **(X2) Estimate his as-built mast mass** by reproducing **his own structure and sizing rules**
   (carbon box spar + bonded glass LE/TE fairings; design = 2.5 × RM_max = 627 kN·m; 60–80 % UD
   laminate at ~½ knockdown; wall = the governing max of strength, his `t/ID ≥ 0.03` buckling
   floor, and operational deflection; tapered) → the **mass number his papers never published**,
   eigen-verified at n≥24, with a sensitivity band.
3. **(X3) Rebuild the identical OML with *this project's* manufacturing concept** — 3 **and** 4
   filament-wound box spars + co-bonded UD channel longerons + a filament-wound outer shell —
   sized to the same loads/criteria; manufacturable (`check_fit`).
4. **(X4) Optimize the internal structure to beat him** — FEA-in-the-loop min-mass over
   **internal** design variables only, at **Amazon's own loads**, targeting mass below the X2
   estimate; report the margin, governing constraints, and shadow prices; eigen-verified.

This is an **apples-to-apples** benchmark: identical external envelope and identical loads;
the only thing that varies between Sponberg's mast and ours is the **internal structure +
manufacturing method + optimization**.

### Out of scope (`OUT-*`)
- `OUT-1` **Any change to the external OML** (section t/c, chord, taper, entasis, planform) —
  **frozen** at Amazon's published geometry for all of X1–X4 (`D-AMZ-1`, user directive). External
  geometry becomes a design variable only *after* these goals are met, in a later phase.
- `OUT-2` Re-targeting to the Oyster-595 loads (RM 200 kN·m, FoS 3.0) — deferred (`D-AMZ-2`);
  X1–X4 run entirely at Amazon's own loads.
- `OUT-3` As-built ply allowables / co-bond coupon values — use basis §6–§7 + Sponberg's
  ~½-knockdown placeholder, flagged by sensitivity (Article IV).
- `OUT-4` The legacy NACA-0018 `RotatingMastSpec` reference geometry — kept frozen, not deleted;
  the pipeline re-points at `amazon_mast` as the new baseline.

## Requirements

- `R-AMZ-1` (OML fidelity) — A new `geometry/amazon_mast.py` MUST reproduce Amazon's outer mould
  line from the published station table to **≤ 1 mm** on chord and thickness at every station
  (2.5/1 ellipse held constant; modified-entasis taper; round OD 500 / 450 transitions at the
  partners and heel). Refines `R-GEO-1/2/3`.
- `R-AMZ-2` (frozen envelope) — The external OML MUST be held **fixed** across X1–X4: no
  external-geometry design variable (t/c, chord, taper, entasis, planform) appears in any X2–X4
  sizing/optimization. Operationalizes `D-AMZ-1` / `OUT-1`.
- `R-AMZ-3` (his-mass estimate) — A structural model MUST estimate Amazon's **as-built mast mass**
  (both masts) by reproducing Sponberg's construction (carbon box spar + glass fairings) and
  sizing rules (design = FoS 2.5 × RM_max; 60–80 % UD at ~½ knockdown; wall = max(strength,
  `t/ID ≥ 0.03`, operational deflection); tapered). The result MUST be **converged AND feasible**,
  **eigen-verified at n≥24** (lowest 2–3 modes), reported with **measured wall-clock** and a
  **sensitivity band** over the flagged derived inputs (bury length, knockdown, FoS, deflection
  allowance). Refines `R-PERF-1…7`, `R-LOAD-1…5`.
- `R-AMZ-4` (this-project rebuild) — The same frozen OML MUST be rebuilt with the project
  manufacturing concept — **3 and 4** filament-wound box spars + co-bonded UD channel longerons +
  filament-wound shell — each **manufacturable** (`check_fit` feasible; windable angles; integer
  plies; no true 0°) and sized to the same loads. The **bonded interface MUST NOT be the critical
  load path** (Article V). Refines `R-MFG-1…4`, `R-CON-1…3`.
- `R-AMZ-5` (beat him) — An FEA-in-the-loop min-mass optimization over **internal** design
  variables only (ply/wall schedule, layup fractions, internal layout, spar count ∈ {3,4}), at
  **Amazon's loads**, MUST produce a **converged AND feasible, eigen-verified** design and report
  its mass vs the X2 estimate (the headline margin), governing constraints, and shadow prices.
  Refines `R-OPT-1…3`, goal `G-3`.
- `R-AMZ-6` (regenerable) — X1/X2/X3/X4 milestones MUST export regenerable CAD + FEA fields +
  screenshots per Article XI, with the regeneration command recorded in the finding. Refines
  `R-EXP-1…4`.

## Acceptance

| Req | Verified by |
|---|---|
| R-AMZ-1 | unit test asserting each station's (chord, thickness) ≤ 1 mm vs the published table; example builds + exports STL/STEP; `just shot` render. |
| R-AMZ-2 | the X2–X4 design vectors contain **no** external-geometry entry (test/inspection); the OML solid is byte-identical across the phases. |
| R-AMZ-3 | a sizing run on the carbon-box-spar Amazon model: reported mass (both masts) **converged + feasible**, **eigen λ at n≥24** ≥ his implied margin, with measured wall-clock + a low/central/high band. |
| R-AMZ-4 | `check_fit` feasible for the 3- and 4-spar builds; co-bond utilization < 1 (interface not critical); both sized masses reported. |
| R-AMZ-5 | optimized mass **< X2 estimate** (or, if not, a rigorous negative finding with *why*); eigen-verified n≥24; shadow prices + governing constraints recorded. |
| R-AMZ-6 | `exports/*.stl|step|vtu` + screenshots regenerable by the recorded `just example …` command. |

## Decisions & assumptions

- `D-AMZ-1` — **External OML frozen at Amazon's published geometry** for X1–X4 (user directive,
  2026-06-17). We beat Sponberg by internal structure + manufacturing + optimization, **not** by
  reshaping the wing. Tightens (never relaxes) the design space. External geometry re-opens only
  after X1–X4 are achieved.
- `D-AMZ-2` — **Loads = Amazon's own:** RM_max = 185,000 ft·lbf = **251 kN·m**, **FoS 2.5**,
  design moment/mast = **627 kN·m**, his criteria throughout (apples-to-apples). Sensitivity:
  RM scales all loads linearly. Oyster re-targeting deferred (`OUT-2`).
- `D-AMZ-3` — **Moment model:** Sponberg's design envelope — RM_max spread **constant from
  partners to gooseneck**, tapered linearly to zero at the masthead and at the heel. Headline:
  zero-top / max-at-partners / zero-heel. (Used for X2 to match his method; X3/X4 may also drive
  the distributed-aero model as a cross-check.)
- `D-AMZ-4` — **Below-deck bury** (partners→heel; **unpublished**) estimated from Sponberg's
  **10–15 % of mast length** rule → **2.6–3.8 m**; central **3.2 m**, swept for sensitivity.
- `D-AMZ-5` — **Deflection** sized to Sponberg's *operational* allowance, not the project's strict
  2 %: he measured ~0.9 m fore-aft / ~0.46 m athwartships at 25 kt full sail (~2–4 % of height), so
  Amazon is expected **strength/buckling-governed**, not deflection-governed. Deflection enters X2
  as a generous operational check; the strict R-PERF-2 (2 %) is **not** imposed on the *Amazon*
  estimate (it would over-size vs his real mast). Flagged.
- `D-AMZ-6` — **Material:** ~1996 prepreg carbon UD (T800-class, `materials.T800_EPOXY`) with
  Sponberg's **~½ knockdown** on ideal properties; layup **70 % UD / 15 % ±45 / 15 % 90** central
  (band 60–80 % UD). Sensitivity: laminate modulus/strength scales mass.
- `D-AMZ-7` — **Spar count ∈ {3, 4}** swept in X3/X4; lighter feasible reported (the count is the
  one *internal* topology DV that is discrete).

## Open questions
- Amazon's **actual mast mass** is unpublished — the X2 estimate is the only available figure;
  cross-check against Sponberg's general "~½ ideal properties" + the `t/OD ≥ 0.03` wall and the
  drawing's "5 mm skins / 12.7 mm box" annotations (record the reconciliation in `findings.md`).
- Whether the **glass LE/TE fairings** carry meaningful bending (Sponberg: "box spar is the
  primary structural element") — assume fairings are non-structural mass in X2 unless the section
  property check says otherwise; record.
