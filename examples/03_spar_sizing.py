"""Size the tapered CFRP rotation-spar tube for the medium (22 m) wingsail against the full load envelope.

Runs the LL aero envelope then calls structural.size_tube_spar to find the
minimum-mass tapered hollow-tube spar that satisfies axial stress and tip
deflection limits under all DESIGN_CASES, and prints mass + critical dimensions.
"""
from __future__ import annotations

from wingmast_design.aero import DESIGN_CASES, build_airplane, sweep_envelope
from wingmast_design.geometry import medium_wingsail
from wingmast_design.materials import T700_EPOXY
from wingmast_design.structural import size_tube_spar


def main() -> None:
    spec = medium_wingsail
    airplane = build_airplane(spec)
    envelope = sweep_envelope(airplane, DESIGN_CASES)
    sizing = size_tube_spar(spec, envelope, material=T700_EPOXY)

    print(f"Material:           {sizing.material.name}")
    print(f"Root diameter:      {sizing.diameter_root_m * 1000:.1f} mm")
    print(f"Tip  diameter:      {sizing.diameter_tip_m * 1000:.1f} mm")
    print(f"Root wall thk:      {sizing.wall_root_m * 1000:.2f} mm")
    print(f"Tip  wall thk:      {sizing.wall_tip_m * 1000:.2f} mm")
    print(f"Max axial stress:   {sizing.max_stress_Pa / 1e6:.1f} MPa")
    print(f"Max tip deflection: {sizing.max_tip_deflection_m * 1000:.1f} mm")
    print(f"Governing case:     {sizing.governing_case}")
    print(f"Spar mass:          {sizing.mass_spar_kg:.2f} kg")
    print(f"Stub mass:          {sizing.mass_stub_kg:.2f} kg")
    print(f"Total:              {sizing.mass_total_kg:.2f} kg")


if __name__ == "__main__":
    main()
