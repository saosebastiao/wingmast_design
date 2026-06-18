"""Export the Amazon-baseline mast WITH its box-spar internal structure (`R-AMZ-6`, Article XI).

The X1 export (`amazon_mast.{stl,step}`) is only the OML. This lofts the **3-box-spar +
longeron-channel + outer-shell** partition (the optimized project-method build) into 3-D solids so
the internal structure is visible: the three filament-wound box spars, the two inter-spar longeron
channels between them, and the faired outer shell (the OML).

Run: `just example 60_amazon_box_spar_export`
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
from build123d import (
    BuildLine,
    BuildPart,
    BuildSketch,
    Color,
    Compound,
    Plane,
    Polyline,
    add,
    export_step,
    export_stl,
    loft,
    make_face,
)

from wingmast_design.beams.cross_section import resample_closed_polyline
from wingmast_design.geometry.amazon_mast import AmazonMastSpec, build_amazon_mast_solid
from wingmast_design.geometry.box_spars import BoxSparLayout, box_spar_sections

N_PTS = 60          # resampled vertices per cell (consistent vertex count → clean ruled loft)
N_STATIONS = 10     # spanwise loft sections over the wing


def _face(poly: np.ndarray):
    pts = [(float(x), float(y)) for x, y in poly[:-1]]
    with BuildSketch() as sk:
        with BuildLine():
            Polyline(*pts, close=True)
        make_face()
    return sk.sketch


def _loft_cell(spec: AmazonMastSpec, layout: BoxSparLayout, k: int, zs: np.ndarray):
    """Loft box-spar cell index ``k`` across the wing stations into a solid."""
    faces = []
    for z in reversed(zs):
        cell = box_spar_sections(spec.section_oml(float(z)), layout).cells[k]
        rs = resample_closed_polyline(np.asarray(cell, float), N_PTS)
        faces.append(Plane(origin=(0.0, 0.0, float(z))) * _face(rs))
    with BuildPart() as part:
        for f in faces:
            add(f)
        loft(ruled=True)
    return part.part


def main() -> None:
    t0 = time.perf_counter()
    spec = AmazonMastSpec()
    # the optimized build: 3 box spars (the rest of the section — walls/helix — is structural,
    # not OML; the partition topology is what the export shows)
    layout = BoxSparLayout(n_spars=3, blend_radius=0.02, spar_wall=0.006, shell_wall=0.003)
    zs = np.linspace(0.0, spec.sail_track_length, N_STATIONS)

    print("Amazon mast WITH box spars — 3 filament-wound box spars + 2 longeron channels + shell")
    spars = []
    for k in range(layout.n_spars):
        s = _loft_cell(spec, layout, k, zs)
        spars.append(s)
        print(f"  box spar {k}: valid={s.is_valid}, volume {s.volume:.3f} m³")
    oml = build_amazon_mast_solid(spec)
    print(f"  OML shell: valid={oml.is_valid}, volume {oml.volume:.3f} m³")

    # colour for clarity, assemble as one compound
    palette = [Color(0.85, 0.2, 0.2), Color(0.2, 0.6, 0.85), Color(0.3, 0.8, 0.3)]
    for i, (s, c) in enumerate(zip(spars, palette)):
        s.color = c
        s.label = f"box_spar_{i}"
    oml.color = Color(0.7, 0.7, 0.7, 0.25)
    oml.label = "oml_shell"
    asm = Compound(children=[*spars, oml])

    out = Path(__file__).resolve().parent.parent / "exports"
    out.mkdir(exist_ok=True)
    export_step(asm, str(out / "amazon_box_spars.step"))
    export_stl(asm, str(out / "amazon_box_spars.stl"))
    # also the bare box-spar cluster (no shell) — clearer for inspecting the internal structure
    export_stl(Compound(children=spars), str(out / "amazon_box_spars_only.stl"))
    print(f"  wrote exports/amazon_box_spars.{{step,stl}} + amazon_box_spars_only.stl")
    print(f"DONE in {time.perf_counter() - t0:.1f} s")


if __name__ == "__main__":
    main()
