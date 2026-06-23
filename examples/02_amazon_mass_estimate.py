"""Phase X2 deliverable: estimate Project Amazon's as-built mast mass (`R-AMZ-3`).

Reproduces Amazon as Sponberg built and sized it (carbon box spar + glass fairings, design =
2.5×RM, wall = max(strength, his t/ID≥0.03 floor), tapered) and integrates the mass his papers
never published — cross-validated against his "12.7 mm box" drawing annotation, with a sensitivity
band and an FEA deflection check + closed-form local-buckling margin.

Run: `just example 02_amazon_mass_estimate`
"""
from __future__ import annotations

import time

from wingmast_design.geometry.amazon_mast import (
    AMAZON_DESIGN_MOMENT_NM,
    AMAZON_RM_NM,
    AmazonMastSpec,
)
from wingmast_design.structural.amazon_sizing import (
    AmazonSizingParams,
    amazon_mass_band,
    estimate_amazon_mast_mass,
    size_wall_at_z,
)


def main() -> None:
    t0 = time.perf_counter()
    spec = AmazonMastSpec()

    print("Project Amazon mast mass estimate — Sponberg's construction + his sizing rules")
    print(f"  load: RM_max {AMAZON_RM_NM/1e3:.0f} kN·m × FoS 2.5 = design {AMAZON_DESIGN_MOMENT_NM/1e3:.0f} kN·m/mast")
    print("  wall = max(strength, Sponberg t/0.03·panel buckling floor), tapered:")
    params = AmazonSizingParams()
    for z in (0.0, 7.31, 14.63, 21.0):
        t, gov = size_wall_at_z(z, spec, params)
        print(f"    z={z:5.2f} m  t_wall {t*1e3:5.1f} mm  ({gov})")

    r = estimate_amazon_mast_mass(spec)
    print("\n  === MASS ESTIMATE (central) ===")
    print(f"    carbon box (wing) {r.carbon_box_kg:6.0f} kg")
    print(f"    round stock       {r.stock_kg:6.0f} kg")
    print(f"    glass fairings    {r.fairing_kg:6.0f} kg")
    print(f"    PER MAST          {r.mass_per_mast_kg:6.0f} kg")
    print(f"    BOTH MASTS        {r.mass_both_masts_kg:6.0f} kg")
    print(f"    root wall {r.root_wall_mm:.1f} mm  (validates vs Sponberg's ~12.7 mm box annotation)")
    print(f"    governing: {', '.join(f'{k} {v*100:.0f}%' for k, v in r.governing_fracs.items())}")
    print(f"    FEA tip deflection {r.tip_defl_m:.2f} m ({r.tip_defl_pct_height:.0f}% of height) at RM_max "
          f"(intentionally flexible — not a sizing constraint in his method)")
    print(f"    local buckling λ {r.min_local_buckling_lambda:.2f} at operating load (t/ID floor reserve)")

    print("\n  === SENSITIVITY BAND (both masts) ===")
    band = amazon_mass_band(spec)
    for k in ("low", "central", "high"):
        b = band[k]
        print(f"    {k:>7}: {b.mass_both_masts_kg:5.0f} kg  "
              f"(per mast {b.mass_per_mast_kg:4.0f}, root wall {b.root_wall_mm:.1f} mm, λ {b.min_local_buckling_lambda:.2f})")
    lo, hi = band["low"].mass_both_masts_kg, band["high"].mass_both_masts_kg
    print(f"\n  ESTIMATE: Amazon's two masts ≈ {band['central'].mass_both_masts_kg:.0f} kg "
          f"(band {lo:.0f}–{hi:.0f} kg); ~{band['central'].mass_per_mast_kg:.0f} kg/mast.")
    print(f"DONE in {time.perf_counter() - t0:.1f} s")


if __name__ == "__main__":
    main()
