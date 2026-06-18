# Plan — Amazon-baseline wingmast (Phase X)

Implements `spec.md`. Reuse map verified against the codebase (geometry / structural / beams /
materials all present). Each phase ends in a runnable `examples/` script + passing test + a
recorded finding with measured wall-clock. **The OML is frozen at Amazon's geometry throughout
(`D-AMZ-1`).**

## X1 — Amazon OML geometry (`R-AMZ-1`, `R-AMZ-6`)

**Build** `src/wingmast_design/geometry/amazon_mast.py`:
- `AMAZON_STATIONS`: the published table (chord, thickness, role) — 750×300 (deck) → 300×120 (top),
  constant 2.5/1; plus round OD 500 (partners) / OD 450 (heel).
- `AmazonMastSpec` (frozen dataclass): total_length 25.63, sail_track 21.94, the station chords/
  thicknesses, entasis params, bury (`D-AMZ-4`), bearing ODs. `chord_at_z`, `thickness_at_z`,
  `ellipse_section(z)` (a 2.5/1 ellipse OML polyline in the project ordering upper-TE→LE→lower-TE),
  `journal_stations()` (partners_z, heel_z), `entasis_offset(z)`.
- Section primitive: a **true ellipse** OML (not CST) — but emit it in the project's `(N,2)`
  ordering so it drops straight into `box_spar_sections` / the loft helpers. (Add an
  `ellipse_coords(chord, thickness, n)` helper; optionally also fit a `CSTAirfoil` for the
  loft path via `fit_cst` so the existing `build_*_solid` loft works unchanged.)
- `build_amazon_mast_solid(spec)`: reuse the `rotating_mast` loft/transition machinery (ruled
  loft; round-stock transition at OD 500/450). If the existing loft assumes `CSTAirfoil`, feed it
  the CST-fitted ellipse so we touch the audited loft path, not a new one.
- **Deliverable:** `examples/55_amazon_mast.py` → build, `check_fit`-style validity, export
  `exports/amazon_mast.{stl,step}`, viz. `just example 55_amazon_mast`.
- **Tests** (`tests/geometry/test_amazon_mast.py`): every station (chord, thickness) within 1 mm
  of `AMAZON_STATIONS`; t/c == 0.40 ± 1e-3 the full length; ellipse section is simple + closed;
  journal_stations ordering; solid is watertight/positive-volume.

## X2 — Reproduce his structure → estimate his mass (`R-AMZ-3`)

**Build** `src/wingmast_design/structural/amazon_sizing.py` (his construction + his rules):
- Section properties of the **carbon box spar** inside the ellipse (≈ rectangular box at the
  2.5/1 section): `box_section_properties(chord, thickness, t_wall) → (A, I_chord, I_normal, perim)`
  — closed-form for a rectangular tube inscribed in the ellipse (box width/height = a fraction of
  chord/thickness per the drawing; the glass LE/TE fairings are non-structural mass, `OUT`-checked).
- Sizing law (Sponberg): at each station, `t_wall = max(` strength wall for M(z) at FoS 2.5 ·RM,
  `0.03·ID` buckling floor, deflection-driven wall `)`; tapered. `M(z)` from `D-AMZ-3` envelope.
- `estimate_amazon_mast_mass(spec, *, rm_Nm, fos, ply, knockdown, bury) → AmazonMassResult`
  (carbon box mass + glass fairing mass, governing constraint per station, total/mast + both).
- **Verify** (Article II/III): build a tapered journal-BC frame (`solve_frame_journal`) on the
  sized section → operational deflection; assemble geometric stiffness → **`linear_buckling` at
  n≥24** lowest 2–3 modes; confirm feasible.
- **Sensitivity band:** sweep bury (2.6–3.8 m), knockdown (0.4–0.6), FoS (2.5), layup (60–80 % UD)
  → low/central/high mass.
- **Deliverable:** `examples/56_amazon_mass_estimate.py` (prints the mass table + governing
  constraint + band + eigen λ; exports the stress/deflection `*.vtu`). **Finding:** Amazon mast
  mass estimate, converged+feasible, measured wall-clock.
- **Tests:** `box_section_properties` vs hand calc; FD-validate any analytic gradient added
  (Article IX, `tests/.../test_amazon_sizing.py`, central diff rel-err ≤ 1e-4); mass monotone in
  RM and in wall.

## X3 — Rebuild the OML, this project's way (`R-AMZ-4`)

- Map the **frozen Amazon ellipse** through `box_spar_sections` with `n_spars ∈ {3, 4}` (the
  existing chordwise partition) + UD longeron channels + FW shell. Reuse `check_fit` retargeted to
  the Amazon section set (it is OML-agnostic — it takes a spec + layout).
- Adapter so `amazon_mast` sections feed the partition/`check_fit`/sizer the same way
  `RotatingMastSpec` does (a thin `to_box_layout`-style bridge; **no** geometry DVs exposed).
- Size each (3- and 4-spar) build with `size_beam_shell_laminate` at Amazon's loads/criteria
  (internal DVs only: wall/ply bands, layup, spar radii). Co-bond ILSS check < 1.
- **Deliverable:** `examples/57_amazon_myway_build.py` (3- and 4-spar fit + sized mass + export);
  **Finding:** the two masses vs the X2 (his-construction) estimate. **Tests:** `check_fit`
  feasible both counts; manufacturability gates (windable, integer plies, no true 0°).

## X4 — Optimize to beat him (`R-AMZ-5`)

- Run `size_beam_shell_laminate_multistart` (warm-started from X3, Article X) min-mass over the
  internal design vector at Amazon's loads; pick the lighter of {3,4} spars.
- **Eigen-verify** the optimum at n≥24; capture **shadow prices** (`shadow_prices_from_specs`).
- **Headline:** optimized mass vs X2 estimate = the % we beat Sponberg by (or a rigorous negative
  finding with *why*, Article VII).
- **Deliverable:** `examples/58_amazon_beat.py`; export sized CAD + stress/strain `*.vtu` +
  `just shot`; **Finding:** the margin, governing constraints, shadow prices, measured wall-clock.

## Cross-cutting
- **Memory budget (Article VIII):** X2/X4 heavy runs `n_workers=1` (18 GiB/worker on 32 GiB).
- **Warm-start (Article X):** X4 from X3; fine meshes from resampled coarse.
- **Single source of truth (Article XII):** loads/criteria typed once (an `AMAZON_CASE` constant);
  run through `just`.
- **Records:** each phase → `docs/findings.md` (append-only) + decisions-log row; `R-AMZ`
  requirement marked in the spec when met.

## Sequence & status
- [x] X1 geometry + export + tests — `amazon_mast.py`, 0.000 mm station fidelity, valid solid, 7 tests (2026-06-17)
- [x] X2 mass estimate — **two masts ≈ 1290 kg (band 1020–1625)**; root wall 13.5 mm validates vs his 12.7 mm box; buckling-floor-governed; 7 tests (2026-06-17). Eigen-verify deferred to X3/X4 (meshed model).
- [x] X3 3- & 4-spar rebuild + fit + sized mass — **3 spars 526 kg/mast (−18.5 % vs his 646)** (buckling-rigorous), both manufacturable; composite section; 5 tests (2026-06-17)
- [x] X4 optimize — **−8.8 % stiffness-matched (589) / −27.6 % mass-optimal (467) kg/mast**, 3 spars, orthotropic cap-panel buckling λ=1.5; 4 tests (2026-06-17).
- [x] X4 eigen closure — governing cap panel eigen-verified: **exact analytical λ=1.50** (confirms closed form) + converged-mesh shell-FEA (overstiff +23 %, Article III); buckling-feasible. `amazon_eigen.py`, 3 tests (2026-06-17).
