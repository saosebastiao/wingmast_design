# Prior-art papers

Source documents behind the project's design decisions. Cite by filename from `docs/findings.md`
and the dossiers in `docs/respec_research/`.

## Eric Sponberg — free-standing rotating wing masts

The provenance for the **Project Amazon baseline** (`docs/respec_research/sponberg_amazon_prior_art.md`
and the Phase X1–X4 findings). All self-hosted by the author at `ericwsponberg.com`; retrieved
2026-06-17. *Project Amazon* is the closest built prior art to this project — an Open-60 cat-ketch
with two free-standing, rotating carbon wingmasts. Sponberg wrote the only practical design paper on
free-standing masts and had engineered ~50–60 of them.

| File | Document | Role |
|---|---|---|
| `sponberg_project_amazon_PBB_1998.pdf` | "Project Amazon and the Unstayed Rig," *Professional BoatBuilder* No. 55, Oct/Nov 1998, pp. 44–57 | **primary** — mast station table (2.5:1 ellipse, 750×300→300×120), loads (RM × 2.5), construction |
| `sponberg_project_amazon_SNAME_2000.pdf` | "Project Amazon: An Open Class 60 Sailboat…," SNAME *Marine Technology* 37(2), Spring 2000, pp. 65–78 | **primary** — fuller scantlings, bearings (deck roller + heel roller/thrust), layup, weight history; agrees with PBB to the digit |
| `sponberg_design_engineering_freestanding_masts_1983.pdf` | "Design and Engineering Aspects of Free-Standing Masts and Wingmasts," 6th Chesapeake Sailing Yacht Symposium 1983, **+ 2011 author's addendum** | **primary method** — load = RM, FoS 3.0, t/ID ≥ 0.03, ~½ knockdown, deflection-at-operational |
| `sponberg_state_of_the_art_freestanding_masts.pdf` | "Free-Standing Masts — Some Thoughts on the State of the Art" | methodology / rationale (text-extractable) |
| `sponberg_wing_masts.pdf` | "Wing Masts" | wing-mast section design |
| `sponberg_engineered_to_stand_alone.pdf` | "Engineered to Stand Alone" | free-standing rig overview |
| `sponberg_wobegon_daze_wingmast_rig.pdf` | "New Wingmast Rig for *Wobegon Daze*" | wingmast retrofit case study |

## Other

| File | Document |
|---|---|
| `kulfan_2007.pdf` | Kulfan, "A Universal Parametric Geometry Representation Method — CST" (the airfoil parameterization used in `geometry/kulfan.py`) |

> These are third-party copyrighted documents kept locally for engineering reference/provenance.
