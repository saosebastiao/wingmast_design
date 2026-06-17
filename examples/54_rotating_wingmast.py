"""Phase G deliverable: the parameterized twin rotating-wingmast assembly + fit + export.

Builds the Oyster-595 twin-rig reference geometry from the typed parameter set
(`R-GG-5`), reports the box-spar / longeron section set + the geometric-fit verdict
(`R-GG-4`), and exports the tandem assembly to STL + STEP (`R-GG-6`, Article XI).

Run: `just example 54_rotating_wingmast`
"""
from __future__ import annotations

import time
from pathlib import Path

from build123d import export_step, export_stl

from wingmast_design.geometry import (
    GEOMETRY_PARAMS,
    MastGeometryParameters,
    assembly_fit,
    assembly_root_section,
    build_wingmast_assembly,
    longeron_void_area,
)


def main() -> None:
    t0 = time.perf_counter()
    params = MastGeometryParameters.reference()
    spec = params.to_mast_spec()
    layout = params.to_box_layout()

    print("Twin rotating-wingmast — Oyster-595 reference parameters")
    print(f"  span {spec.span} m · chord {spec.root_chord}→{spec.tip_chord} m · "
          f"rotation axis {spec.rotation_center_xc:.2f}c · mast spacing {params.mast_spacing} m")
    print(f"  parameters in-bounds: {not params.out_of_bounds()} "
          f"({len(GEOMETRY_PARAMS)} parameters, each with (lower, upper, increment))")
    upper, lower = spec.journal_stations
    print(f"  journals: deck-partners z={upper:.2f} m, heel-step z={lower:.2f} m "
          f"(bury {upper - lower:.2f} m)")

    # Box-spar / longeron section set at the root (R-GG-3)
    sec = assembly_root_section(params)
    print(f"  box spars: {len(sec.cells)} cells, {len(sec.channels)} longeron channels; "
          f"channel void {longeron_void_area(layout.blend_radius) * 1e4:.1f} cm² "
          f"(blend radius {layout.blend_radius * 1e3:.0f} mm)")

    # Geometric fit (R-GG-4)
    fit = assembly_fit(params)
    print(f"  geometric fit: {'FEASIBLE' if fit.feasible else 'INFEASIBLE'} "
          f"(margin {fit.margin * 1e3:.0f} mm, binding '{fit.binding_reason}' at z={fit.binding_z:.1f} m)")
    assert fit.feasible, "reference geometry must satisfy R-CON-1"

    # Assembly + export (R-GG-6)
    asm = build_wingmast_assembly(params)
    out = Path(__file__).resolve().parent.parent / "exports"
    out.mkdir(exist_ok=True)
    export_stl(asm, str(out / "twin_wingmast.stl"))
    export_step(asm, str(out / "twin_wingmast.step"))
    print(f"  wrote {out}/twin_wingmast.{{stl,step}} ({len(asm.children)} masts)")
    print(f"DONE in {time.perf_counter() - t0:.1f} s")


if __name__ == "__main__":
    main()
