"""Phase X3 deliverable: rebuild the Amazon OML with THIS project's method (`R-AMZ-4`).

Same frozen 2.5:1 ellipse, same Amazon loads/criteria — but built the project way (3 and 4
filament-wound box spars + co-bonded UD channel longerons + filament-wound shell). Confirms
manufacturability (`check_fit`) and reports the first-order mass of each vs the X2 his-construction
estimate. (X4 then optimizes the internal distribution to minimise mass.)

Run: `just example 57_amazon_myway_build`
"""
from __future__ import annotations

import time

from wingmast_design.geometry.amazon_mast import AmazonMastSpec
from wingmast_design.structural.amazon_myway import (
    MyWayParams,
    estimate_myway_mass,
    myway_fit,
    myway_section,
)
from wingmast_design.structural.amazon_sizing import estimate_amazon_mast_mass


def main() -> None:
    t0 = time.perf_counter()
    spec = AmazonMastSpec()
    amz = estimate_amazon_mast_mass(spec)

    print("Rebuild Amazon's OML with the project method — 3 vs 4 box spars + UD longerons + FW shell")
    print(f"  baseline (Sponberg's single box + glass fairings, X2): {amz.mass_per_mast_kg:.0f} kg/mast")
    E_cap, E_shell = MyWayParams().moduli()
    print(f"  laminates: 0° cap {E_cap/1e9:.0f} GPa, helical FW shell {E_shell/1e9:.0f} GPa\n")

    best = None
    for n in (3, 4):
        p = MyWayParams(n_spars=n)
        fit = myway_fit(spec, p)
        t_root, _, gov = myway_section(0.0, spec, p)
        r = estimate_myway_mass(spec, p, amazon_per_mast_kg=amz.mass_per_mast_kg)
        print(f"  --- {n} box spars ---")
        print(f"    manufacturable: {'YES' if fit.feasible else 'NO'} "
              f"(check_fit margin {fit.margin*1e3:.0f} mm)")
        print(f"    root cap wall {t_root*1e3:.1f} mm ({gov}) — vs Amazon's 13.5 mm buckling-floor")
        print(f"    mass {r.mass_per_mast_kg:.0f} kg/mast ({r.mass_both_masts_kg:.0f} kg both)  "
              f"= wing {r.wing_kg:.0f} + stock {r.stock_kg:.0f}")
        print(f"    feasible: {r.feasible} (cap util {r.max_cap_util:.2f}, shell util {r.max_shell_util:.2f}); "
              f"governing { {k: round(v, 2) for k, v in r.governing_fracs.items()} }")
        print(f"    vs Amazon: {r.vs_amazon_pct:+.1f}%\n")
        assert fit.feasible, f"R-AMZ-4: {n}-spar build must be manufacturable"
        if r.feasible and (best is None or r.mass_per_mast_kg < best[1]):
            best = (n, r.mass_per_mast_kg, r.vs_amazon_pct)

    assert best is not None, "at least one spar count must be feasible"
    n_b, m_b, pct_b = best
    print(f"  BEST first-order: {n_b} box spars → {m_b:.0f} kg/mast ({pct_b:+.1f}% vs Sponberg), "
          f"both masts {2*m_b:.0f} kg.")
    print("  (X4 optimizes the wall/cap/shell/longeron distribution to push further.)")
    print(f"DONE in {time.perf_counter() - t0:.1f} s")


if __name__ == "__main__":
    main()
