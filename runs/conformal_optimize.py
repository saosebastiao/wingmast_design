"""Optimize the as-built conformal multi-cell torsion box vs Sponberg (X5)."""
import json
import time
from dataclasses import replace
from pathlib import Path

from wingmast_design.geometry.amazon_mast import AmazonMastSpec
from wingmast_design.structural.amazon_conformal import (
    ConformalParams,
    estimate_conformal_mass,
    optimize_conformal_beat,
)
from wingmast_design.structural.amazon_sizing import estimate_amazon_mast_mass

spec = AmazonMastSpec()
amz = estimate_amazon_mast_mass(spec).mass_per_mast_kg
print(f"Sponberg (X2) per-mast: {amz:.0f} kg\n")

# search on a coarse station grid (mass integral converges by ~70), serial (macOS fork is flaky)
t0 = time.perf_counter()
base = ConformalParams(n_int=70)
best, runs = optimize_conformal_beat(spec, amazon_per_mast_kg=amz, cell_counts=(3, 4, 5),
                                     base=base, seed=1, maxiter=40, popsize=12, workers=1)
# re-evaluate the winner at full resolution so the reported mass + cap schedule are converged
best_p = replace(best.params, n_int=240)
best_full = estimate_conformal_mass(spec, best_p, amazon_per_mast_kg=amz)
best = replace(best, params=best_p, result=best_full, mass_per_mast_kg=best_full.mass_per_mast_kg,
               vs_amazon_pct=best_full.vs_amazon_pct or 0.0,
               min_buckle_lambda=best_full.min_buckle_lambda)
dt = time.perf_counter() - t0

for r in runs:
    p = r.params
    print(f"  n={r.n_cells}: {r.mass_per_mast_kg:5.0f} kg/mast ({r.vs_amazon_pct:+5.1f}% vs Sponberg)  "
          f"λ={r.min_buckle_lambda:.2f}  tip={r.tip_defl_m:.2f}m  feas={r.result.feasible}  "
          f"[blend={p.blend_radius*1e3:.0f} tweb={p.t_web*1e3:.1f} tshell={p.t_shell*1e3:.1f} "
          f"helix={p.shell_helix_deg:.1f}° f0={p.layup_f0:.2f}]  "
          f"(DE nit={r.de_nit} success={r.de_success} bounds={r.at_bounds}/5)")

p = best.params
print(f"\nBEST: {best.n_cells} cells → {best.mass_per_mast_kg:.0f} kg/mast "
      f"({best.vs_amazon_pct:+.1f}% vs Sponberg), λ={best.min_buckle_lambda:.2f}, "
      f"root cap {best.result.root_cap_mm:.1f} mm, tip {best.tip_defl_m:.2f} m")
print("  governing: " + ", ".join(f"{k}:{v:.2f}" for k, v in best.result.governing_fracs.items() if v > 0))
print(f"\nwall-clock: {dt:.1f} s")

# persist the winner for the CAD to consume (sized walls == CAD)
out = Path(__file__).resolve().parent.parent / "exports" / "conformal_best.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps({
    "n_cells": best.n_cells, "blend_radius": p.blend_radius, "t_web": p.t_web,
    "t_shell": p.t_shell, "shell_helix_deg": p.shell_helix_deg,
    "layup_f0": p.layup_f0, "layup_f45": p.layup_f45, "layup_f90": p.layup_f90,
    "mass_per_mast_kg": best.mass_per_mast_kg, "vs_amazon_pct": best.vs_amazon_pct,
    "cap_schedule": best.result.cap_schedule,
}, indent=2))
print(f"wrote {out}")
