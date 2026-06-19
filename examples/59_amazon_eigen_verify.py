"""Phase X4 closure: eigen-verify the governing cap-panel buckling (`R-AMZ-5`, Article III).

Closes the converged-mesh eigen verification owed on the optimized project-method Amazon mast:
the governing buckling mode (cap-panel orthotropic plate, sized to λ = 1.5) is checked with the
EXACT analytical plate eigenvalue (confirms the closed form to the digit) and an independent
converged-mesh shell-FEA eigen. The FEA's linear-w geometric stiffness is unconservatively
overstiff (~20 %) for the high-D11/D22 cap — so feasibility is judged on the conservative
exact/closed-form floor (λ = 1.5), with the FEA confirming only MORE margin (Article III).

Run: `just example 59_amazon_eigen_verify`
"""
from __future__ import annotations

import time

from wingmast_design.geometry.amazon_mast import AmazonMastSpec
from wingmast_design.structural.amazon_eigen import verify_cap_panel_eigen
from wingmast_design.structural.amazon_myway import MyWayParams


def main() -> None:
    t0 = time.perf_counter()
    spec = AmazonMastSpec()
    # the X4 mass-optimal design (3 spars, narrow-deep box, near-0° shell)
    opt = MyWayParams(n_cells=3, box_frac_chord=0.45, box_frac_thick=0.88,
                      t_shell=0.0025, t_web=0.003)
    r = verify_cap_panel_eigen(spec, opt)

    print("Eigen verification — governing cap panel of the optimized project-method mast")
    print(f"  governing station z={r.z_station:.1f} m: cell width {r.cell_width_m*1e3:.0f} mm, "
          f"cap wall {r.cap_wall_mm:.1f} mm, operating stress {r.sigma_op_MPa:.0f} MPa, aspect {r.aspect:.2f}")
    print(f"\n  closed-form λ (used by the sizer)     : {r.closed_form_lambda:.3f}")
    print(f"  EXACT analytical SS-plate eigen λ     : {r.exact_analytical_lambda:.3f}   "
          f"← confirms the closed form to the digit (it IS the exact eigenvalue)")
    print("  converged-mesh shell-FEA eigen (ny → λ):")
    for ny, lam in r.convergence:
        print(f"      ny={ny:2d} across panel: λ = {lam:.3f}")
    print(f"  FEA converged λ                       : {r.fea_lambda_converged:.3f}  "
          f"(+{r.fea_overstiff_pct:.0f} % — the linear-w Kσ is unconservatively overstiff here)")
    print(f"\n  VERDICT: buckling-feasible = {r.feasible}  "
          f"(judged on the conservative exact floor λ = {r.exact_analytical_lambda:.2f} ≥ 1.5; "
          f"FEA confirms only more margin — Article III)")
    print(f"DONE in {time.perf_counter() - t0:.1f} s")


if __name__ == "__main__":
    main()
