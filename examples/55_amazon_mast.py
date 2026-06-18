"""Phase X1 deliverable: the Project-Amazon baseline wingmast OML (`R-AMZ-1`, `R-AMZ-6`).

Reproduces Eric Sponberg's *Project Amazon* free-standing rotating wingmast OML from his
published station table (2.5:1 ellipse, 750×300 mm at the deck → 300×120 mm at the masthead,
modified-entasis taper, round OD500/OD450 bearing stock), checks each station against the
published dimensions, reports the two journal stations, and exports STL + STEP (Article XI).

Run: `just example 55_amazon_mast`
"""
from __future__ import annotations

import time
from pathlib import Path

from build123d import export_step, export_stl

from wingmast_design.geometry import (
    AMAZON_DESIGN_MOMENT_NM,
    AMAZON_FOS,
    AMAZON_RM_NM,
    AMAZON_STATIONS_MM,
    AMAZON_TC,
    AmazonMastSpec,
    build_amazon_mast_solid,
)
from wingmast_design.viz import show_in_viewer


def main() -> None:
    t0 = time.perf_counter()
    spec = AmazonMastSpec()

    print("Project Amazon baseline wingmast — Sponberg PBB No.55 1998 / SNAME 37(2) 2000")
    print(f"  total mast {spec.total_length:.3f} m · sail track {spec.sail_track_length:.3f} m · "
          f"constant 2.5:1 ellipse (t/c {AMAZON_TC})")
    print(f"  loads (his own): RM_max {AMAZON_RM_NM/1e3:.0f} kN·m · FoS {AMAZON_FOS} · "
          f"design moment {AMAZON_DESIGN_MOMENT_NM/1e3:.0f} kN·m/mast")

    # Station-table fidelity (R-AMZ-1): each station within 1 mm of the published table.
    print("  station fidelity (chord×thick mm, vs published):")
    worst = 0.0
    for i, (cmm, tmm) in enumerate(AMAZON_STATIONS_MM):
        z = spec._station_fracs[i] * spec.sail_track_length
        c, t = spec.chord_at_z(z) * 1e3, spec.thickness_at_z(z) * 1e3
        worst = max(worst, abs(c - cmm), abs(t - tmm))
        print(f"    st{i} z={z:5.2f}m  {c:6.1f}×{t:5.1f}  (pub {cmm:6.1f}×{tmm:5.1f})  t/c {t/c:.3f}")
    print(f"  worst station error: {worst:.3f} mm (R-AMZ-1 requires ≤ 1 mm)")
    assert worst <= 1.0, "R-AMZ-1: station OML must match the published table within 1 mm"

    upper, lower = spec.journal_stations
    print(f"  journals: deck-partners z={upper:.2f} m (OD {spec.deck_od*1e3:.0f}), "
          f"heel z={lower:.2f} m (OD {spec.heel_od*1e3:.0f}); bury {spec.bury:.2f} m "
          f"({100*spec.bury/spec.total_length:.1f}% of mast)")

    # Build + export (R-AMZ-6, Article XI)
    solid = build_amazon_mast_solid(spec)
    assert solid.is_valid, "lofted Amazon mast solid must be valid"
    print(f"  solid: valid={solid.is_valid}, OML volume {solid.volume:.3f} m³")

    out = Path(__file__).resolve().parent.parent / "exports"
    out.mkdir(exist_ok=True)
    export_stl(solid, str(out / "amazon_mast.stl"))
    export_step(solid, str(out / "amazon_mast.step"))
    print(f"  wrote {out}/amazon_mast.{{stl,step}}")
    show_in_viewer(solid, names=["amazon_mast"])
    print(f"DONE in {time.perf_counter() - t0:.1f} s")


if __name__ == "__main__":
    main()
