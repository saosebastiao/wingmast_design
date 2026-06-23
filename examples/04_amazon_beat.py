"""Phase X4 deliverable: optimize the project-method mast to beat Sponberg (`R-AMZ-5`).

FEA-in-the-loop min-mass optimization over the INTERNAL section geometry only (box chord/depth
fractions, FW shell + web walls, spar count ∈ {3,4,5}) — the external Amazon OML stays frozen —
at Amazon's own loads/criteria (strength + orthotropic cap-panel buckling λ ≥ 1.5). Reports two
points: (A) mass-optimal at Amazon's criteria, and (B) stiffness-matched (also deflection ≤
Amazon's), so the win is shown both ways. The full progression X2 → X3 → X4 is the headline.

Run: `just example 04_amazon_beat`   (slow — differential evolution; not in CI)
"""
from __future__ import annotations

import time

from wingmast_design.geometry.amazon_mast import AmazonMastSpec
from wingmast_design.structural.amazon_optimize import optimize_amazon_beat
from wingmast_design.structural.amazon_sizing import estimate_amazon_mast_mass


def main() -> None:
    t0 = time.perf_counter()
    spec = AmazonMastSpec()
    amz = estimate_amazon_mast_mass(spec)
    a_kg, a_defl = amz.mass_per_mast_kg, amz.tip_defl_m

    print("Optimize the project-method Amazon mast to beat Sponberg — internal DVs only, OML frozen")
    print(f"  Sponberg (X2): {a_kg:.0f} kg/mast (both {2*a_kg:.0f}), deflection {a_defl:.2f} m, buckling λ {amz.min_local_buckling_lambda:.2f}\n")

    print("  (A) mass-optimal — Amazon criteria (strength + cap-buckling λ≥1.5, no deflection cap):")
    bestA, runsA = optimize_amazon_beat(spec, amazon_per_mast_kg=a_kg, maxiter=30, seed=1)
    for r in runsA:
        print(f"      n={r.n_cells}: {r.mass_per_mast_kg:5.0f} kg/mast ({r.vs_amazon_pct:+5.1f}%)  "
              f"λ {r.min_panel_buckling_lambda:.2f}  defl {r.tip_defl_m:.2f} m  fit {r.fit_margin_mm:.0f} mm")
    print(f"      BEST(A): {bestA.n_cells} cells → {bestA.mass_per_mast_kg:.0f} kg/mast "
          f"({bestA.vs_amazon_pct:+.1f}%), both {bestA.mass_both_masts_kg:.0f} kg\n")

    print(f"  (B) stiffness-matched — also deflection ≤ Amazon's {a_defl:.2f} m:")
    bestB, runsB = optimize_amazon_beat(spec, amazon_per_mast_kg=a_kg, defl_cap_m=a_defl, maxiter=30, seed=1)
    for r in runsB:
        print(f"      n={r.n_cells}: {r.mass_per_mast_kg:5.0f} kg/mast ({r.vs_amazon_pct:+5.1f}%)  "
              f"λ {r.min_panel_buckling_lambda:.2f}  defl {r.tip_defl_m:.2f} m")
    print(f"      BEST(B): {bestB.n_cells} cells → {bestB.mass_per_mast_kg:.0f} kg/mast "
          f"({bestB.vs_amazon_pct:+.1f}%), both {bestB.mass_both_masts_kg:.0f} kg, defl {bestB.tip_defl_m:.2f} m\n")

    p = bestA.params
    print("  optimal section (A): "
          f"{p.n_cells} spars, box {p.box_frac_chord:.2f}c × {p.box_frac_thick:.2f}t, "
          f"shell {p.t_shell*1e3:.1f} mm, web {p.t_web*1e3:.1f} mm")
    print(f"  PROGRESSION  Sponberg {a_kg:.0f} → my-method first-order ~526 → OPTIMIZED "
          f"{bestA.mass_per_mast_kg:.0f} kg/mast  ({bestA.vs_amazon_pct:+.1f}% vs Sponberg)")
    print(f"DONE in {time.perf_counter() - t0:.0f} s")


if __name__ == "__main__":
    main()
