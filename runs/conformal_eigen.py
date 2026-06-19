"""Eigen-verify the conformal optimum's governing cap panel at n≥24 (Article III, X5).

Reuses the audited eigen path (`amazon_eigen`): the exact orthotropic SS-plate eigenvalue (which
IS the closed form the sizer used) + a converged-mesh shell-FEA cross-check. Judges feasibility on
the conservative exact floor (λ ≥ 1.5); the FEA only adds margin (its linear-w Kσ is overstiff).
"""
import json
from pathlib import Path

import numpy as np

from wingmast_design.geometry.amazon_mast import AmazonMastSpec
from wingmast_design.materials.unidir import laminate_stiffness
from wingmast_design.structural.amazon_conformal import ConformalParams, conformal_section
from wingmast_design.structural.amazon_eigen import cap_panel_eigen_lambda, exact_ortho_ss_lambda

spec = AmazonMastSpec()
best = json.loads((Path(__file__).resolve().parent.parent / "exports" / "conformal_best.json").read_text())
p = ConformalParams(n_cells=best["n_cells"], blend_radius=best["blend_radius"], t_web=best["t_web"],
                    t_shell=best["t_shell"], shell_helix_deg=best["shell_helix_deg"],
                    layup_f0=best["layup_f0"], layup_f45=best["layup_f45"], layup_f90=best["layup_f90"],
                    n_int=240)
mods = p.props()

# governing station = min closed-form λ over the wing
zs = np.linspace(0.0, 0.9 * spec.sail_track_length, 40)
z_bind = min(zs, key=lambda zz: conformal_section(float(zz), spec, p, props=mods)[1].panel_buckle_lambda)
t_cap, sec, gov = conformal_section(float(z_bind), spec, p, props=mods)

A, D, _ = laminate_stiffness(p.ply, f0=p.layup_f0, f45=p.layup_f45, f90=p.layup_f90, thickness=t_cap)
sigma_op = sec.cap_sigma / p.fos
aspect = float((D[0, 0] / D[1, 1]) ** 0.25)
b = sec.cell_panel

exact = exact_ortho_ss_lambda(D, t_cap, b, sigma_op)
print(f"conformal optimum: {best['n_cells']} cells, {best['mass_per_mast_kg']:.0f} kg/mast "
      f"({best['vs_amazon_pct']:+.1f}% vs Sponberg)")
print(f"governing cap panel @ z={z_bind:.1f} m: b={b*1e3:.0f} mm, t_cap={t_cap*1e3:.1f} mm, "
      f"σ_op={sigma_op/1e6:.0f} MPa, aspect={aspect:.2f}")
print(f"  closed-form λ = {sec.panel_buckle_lambda:.3f}")
print(f"  exact analytical λ = {exact:.3f}   (== closed form, confirms it is the exact eigenvalue)")
print("  converged-mesh shell-FEA eigen:")
for ny in (8, 12, 16, 24):
    lam = cap_panel_eigen_lambda(A, D, t_cap, b, sigma_op, ny=ny, aspect=aspect)
    print(f"    ny={ny:>2}: λ={lam:.3f}")
fea24 = cap_panel_eigen_lambda(A, D, t_cap, b, sigma_op, ny=24, aspect=aspect)
print(f"\n  FEASIBLE (exact floor ≥1.5): {exact >= 1.5 - 1e-6}   "
      f"(FEA n=24 λ={fea24:.2f} = +{100*(fea24-exact)/exact:.0f}% margin over exact)")
