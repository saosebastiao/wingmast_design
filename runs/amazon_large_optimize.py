"""Large optimization of the project-method Amazon mast (X4+), with the validated balanced-helical
shell assumptions and an expanded design vector.

DV (6): box_frac_chord, box_frac_thick, t_shell, t_web, shell_helix_deg, cap_f0.
Sweeps spar counts {3,4,5,6} × two scenarios (mass-optimal at Amazon's criteria; stiffness-matched
to Amazon's deflection) with a large parallel differential-evolution budget, then eigen-verifies the
winner. The shell is a balanced ±helix laminate (helix angle is now a DV).

Run: `just py runs/amazon_large_optimize.py`  (slow — large DE; not in CI)
"""
from __future__ import annotations

import time

from wingmast_design.geometry.amazon_mast import AmazonMastSpec
from wingmast_design.structural.amazon_eigen import verify_cap_panel_eigen
from wingmast_design.structural.amazon_optimize import optimize_myway
from wingmast_design.structural.amazon_sizing import estimate_amazon_mast_mass

SPARS = (3, 4, 5, 6)
MAXITER, POPSIZE, WORKERS = 120, 18, -1


def _run(spec, n, amz_kg, defl_cap, tag):
    t0 = time.perf_counter()
    r = optimize_myway(spec, n, amz_kg, seed=1, defl_cap_m=defl_cap,
                       maxiter=MAXITER, popsize=POPSIZE, workers=WORKERS)
    p = r.params
    print(f"  [{tag}] n={n}: {r.mass_per_mast_kg:5.0f} kg/mast ({r.vs_amazon_pct:+5.1f}%)  "
          f"λ {r.min_panel_buckling_lambda:.2f}  defl {r.tip_defl_m:.2f} m  "
          f"box {p.box_frac_chord:.2f}c×{p.box_frac_thick:.2f}t shell {p.t_shell*1e3:.1f}mm "
          f"helix ±{p.shell_helix_deg:.0f}° cap_f0 {p.layup_f0:.2f}  feasible {r.result.feasible}  "
          f"({time.perf_counter()-t0:.0f}s)", flush=True)
    return r


def main() -> None:
    t0 = time.perf_counter()
    spec = AmazonMastSpec()
    amz = estimate_amazon_mast_mass(spec)
    amz_kg, amz_defl = amz.mass_per_mast_kg, amz.tip_defl_m
    print(f"Sponberg baseline (X2): {amz_kg:.0f} kg/mast, deflection {amz_defl:.2f} m")
    print(f"Large DE: spars {SPARS}, maxiter {MAXITER}, popsize {POPSIZE}, workers {WORKERS}, "
          f"6 DVs (incl. helix angle + cap layup)\n")

    print("(A) mass-optimal — Amazon criteria (strength + cap-buckling λ≥1.5, no deflection cap):")
    runsA = [_run(spec, n, amz_kg, None, "A") for n in SPARS]
    bestA = min((r for r in runsA if r.result.feasible), key=lambda r: r.mass_per_mast_kg)
    print(f"  → BEST(A): {bestA.n_cells} spars, {bestA.mass_per_mast_kg:.0f} kg/mast "
          f"({bestA.vs_amazon_pct:+.1f}%), both {bestA.mass_both_masts_kg:.0f} kg\n")

    print(f"(B) stiffness-matched — also deflection ≤ {amz_defl:.2f} m:")
    runsB = [_run(spec, n, amz_kg, amz_defl, "B") for n in SPARS]
    bestB = min((r for r in runsB if r.result.feasible), key=lambda r: r.mass_per_mast_kg)
    print(f"  → BEST(B): {bestB.n_cells} spars, {bestB.mass_per_mast_kg:.0f} kg/mast "
          f"({bestB.vs_amazon_pct:+.1f}%), both {bestB.mass_both_masts_kg:.0f} kg, defl {bestB.tip_defl_m:.2f} m\n")

    print("Eigen-verifying the mass-optimal winner (governing cap panel)...")
    ev = verify_cap_panel_eigen(spec, bestA.params)
    print(f"  exact λ {ev.exact_analytical_lambda:.2f}, converged FEA λ {ev.fea_lambda_converged:.2f} "
          f"(+{ev.fea_overstiff_pct:.0f}% overstiff), feasible {ev.feasible}")

    p = bestA.params
    print(f"\nOPTIMAL SECTION (A): {p.n_cells} cells, box {p.box_frac_chord:.2f}c × "
          f"{p.box_frac_thick:.2f}t, shell {p.t_shell*1e3:.1f} mm at ±{p.shell_helix_deg:.0f}° helix, "
          f"web {p.t_web*1e3:.1f} mm, cap layup {p.layup_f0:.0%} 0°.")
    print(f"HEADLINE: Sponberg {amz_kg:.0f} → optimized {bestA.mass_per_mast_kg:.0f} kg/mast "
          f"({bestA.vs_amazon_pct:+.1f}%, mass-optimal) / {bestB.mass_per_mast_kg:.0f} kg "
          f"({bestB.vs_amazon_pct:+.1f}%, stiffness-matched).")
    print(f"DONE in {time.perf_counter()-t0:.0f} s")


if __name__ == "__main__":
    main()
