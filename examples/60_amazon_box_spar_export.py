"""Wall-accurate CAD assembly of the Amazon-baseline mast (`R-AMZ-6`, Article XI).

A layered, separable-parts assembly (not solid bands): each part is a real solid you can see
and isolate —

  * **outer FW shell** — a hollow tube of wall ``T_SHELL`` following the OML;
  * **3 box spars** — hollow boxes (wall ``T_BOX``) inset inside the shell, the bending structure;
  * **2 UD longerons** — solid fills in the inter-spar channels;
  * **bearing stock** — the round OD500→OD450 section below the deck.

The box spars are inset by the shell thickness so the shell wraps them with no overlap (the
co-bond interface). Walls are uniform representative values of the optimized schedule (the real
sizer tapers them per station); set T_BOX/T_SHELL to taste. Exports a coloured STEP + STL.

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
    offset,
)

from wingmast_design.beams.cross_section import resample_closed_polyline
from wingmast_design.geometry.amazon_mast import AmazonMastSpec, ellipse_coords
from wingmast_design.geometry.box_spars import BoxSparLayout, box_spar_sections

N_PTS, N_STATIONS = 64, 10
T_BOX, T_SHELL = 0.004, 0.003          # representative box-spar / shell walls [m]


def _face(poly: np.ndarray):
    pts = [(float(x), float(y)) for x, y in poly[:-1]]
    with BuildSketch() as sk:
        with BuildLine():
            Polyline(*pts, close=True)
        make_face()
    return sk.sketch


def _loft(faces):
    with BuildPart() as part:
        for f in faces:
            add(f)
        loft(ruled=True)
    return part.part


def _centered_ellipse(chord: float, thick: float, n: int = 130) -> np.ndarray:
    """Project-ordered ellipse (upper-TE→LE→lower-TE) of given chord×thick, centred at origin."""
    e = ellipse_coords(n // 2)                # unit-chord 2.5:1 ellipse, t/c 0.40
    out = e.copy()
    out[:, 0] = (e[:, 0] - 0.5) * chord        # centre on x, scale to chord
    out[:, 1] = e[:, 1] / 0.40 * (thick / chord) * chord   # rescale y to the requested thickness
    return out


def _hollow(outer_polys, t_wall, zs):
    outer = _loft([Plane(origin=(0, 0, float(z))) * _face(p) for z, p in zip(zs, outer_polys)])
    inner = _loft([Plane(origin=(0, 0, float(z))) * offset(_face(p), amount=-t_wall)
                   for z, p in zip(zs, outer_polys)])
    return outer - inner


def main() -> None:
    t0 = time.perf_counter()
    spec = AmazonMastSpec()
    layout = BoxSparLayout(n_spars=3, blend_radius=0.02)
    zs = np.linspace(0.0, spec.sail_track_length, N_STATIONS)

    print("Wall-accurate Amazon mast assembly — shell + 3 box spars + 2 longerons + stock")

    # --- outer shell: OML → inset by T_SHELL (the box-spar envelope) ---
    oml = [spec.section_oml(float(z), n_pts=2 * (N_PTS // 2)) for z in zs]
    env = [_centered_ellipse(spec.chord_at_z(float(z)) - 2 * T_SHELL,
                             spec.thickness_at_z(float(z)) - 2 * T_SHELL, N_PTS) for z in zs]
    shell = (_loft([Plane(origin=(0, 0, float(z))) * _face(p) for z, p in zip(zs, oml)])
             - _loft([Plane(origin=(0, 0, float(z))) * _face(p) for z, p in zip(zs, env)]))
    print(f"  FW shell:    valid {shell.is_valid}, wall material {shell.volume:.3f} m³")

    # --- box spars: partition the (inset) envelope, hollow each ---
    spars, longerons = [], []
    cells_by_z = [box_spar_sections(e, layout) for e in env]
    for k in range(layout.n_spars):
        polys = [resample_closed_polyline(np.asarray(c.cells[k], float), N_PTS) for c in cells_by_z]
        s = _hollow(polys, T_BOX, zs)
        spars.append(s)
        print(f"  box spar {k}: valid {s.is_valid}, wall material {s.volume:.3f} m³")

    # --- UD longerons: solid fills in the inter-spar channels ---
    n_ch = len(cells_by_z[0].channels)
    for j in range(n_ch):
        polys = [resample_closed_polyline(np.asarray(c.channels[j].polyline, float), 24)
                 for c in cells_by_z]
        lg = _loft([Plane(origin=(0, 0, float(z))) * _face(p) for z, p in zip(zs, polys)])
        longerons.append(lg)
        print(f"  longeron {j}: valid {lg.is_valid}, volume {lg.volume:.4f} m³")

    # --- bearing stock (round, below deck) ---
    zb = np.linspace(spec.heel_z, -0.05, 5)
    stock = _loft([Plane(origin=(0, 0, float(z))) * _face(spec.section_oml(float(z), n_pts=80))
                   for z in zb])
    print(f"  stock:       valid {stock.is_valid}, volume {stock.volume:.3f} m³")

    # --- colour + assemble ---
    spar_cols = [Color(0.85, 0.2, 0.2), Color(0.2, 0.55, 0.9), Color(0.3, 0.8, 0.3)]
    for i, (s, c) in enumerate(zip(spars, spar_cols)):
        s.color, s.label = c, f"box_spar_{i}"
    for i, lg in enumerate(longerons):
        lg.color, lg.label = Color(0.95, 0.75, 0.1), f"longeron_{i}"
    shell.color, shell.label = Color(0.6, 0.6, 0.65, 0.35), "fw_shell"
    stock.color, stock.label = Color(0.45, 0.45, 0.5), "bearing_stock"
    asm = Compound(children=[*spars, *longerons, shell, stock])

    out = Path(__file__).resolve().parent.parent / "exports"
    out.mkdir(exist_ok=True)
    export_step(asm, str(out / "amazon_assembly.step"))
    export_stl(asm, str(out / "amazon_assembly.stl"))
    export_stl(Compound(children=[*spars, *longerons]), str(out / "amazon_structure_only.stl"))
    print(f"  wrote exports/amazon_assembly.{{step,stl}} (+ amazon_structure_only.stl); "
          f"{len(asm.solids())} solids")

    _render_section(spec, layout, out)
    print(f"DONE in {time.perf_counter() - t0:.1f} s")


def _render_section(spec: AmazonMastSpec, layout: BoxSparLayout, out: Path) -> None:
    """Wall-accurate root cross-section showing the separable parts (clearer than a 3-D render of
    a 22-m-slender solid; the 3-D itself is the exported STEP)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path as MPath

    def _inner_poly(poly, t, n=80):
        w = offset(_face(poly), amount=-t).faces()[0].outer_wire()
        return np.array([((w @ (i / n)).X, (w @ (i / n)).Y) for i in range(n + 1)])

    def _ring(outer, inner, fc, alpha=1.0):
        verts = np.vstack([outer, outer[0], inner[::-1], inner[-1]])
        codes = ([MPath.MOVETO] + [MPath.LINETO] * (len(outer) - 1) + [MPath.CLOSEPOLY]
                 + [MPath.MOVETO] + [MPath.LINETO] * (len(inner) - 1) + [MPath.CLOSEPOLY])
        return PathPatch(MPath(verts, codes), fc=fc, ec="k", lw=0.7, alpha=alpha)

    fig, ax = plt.subplots(figsize=(11, 5.5))
    oml = spec.section_oml(0.0, n_pts=200)
    env = _centered_ellipse(spec.chord_at_z(0.0) - 2 * T_SHELL, spec.thickness_at_z(0.0) - 2 * T_SHELL)
    ax.add_patch(_ring(oml, env, (0.62, 0.62, 0.7), 0.45))
    ax.plot([], [], "s", color=(0.62, 0.62, 0.7), label=f"FW shell ({T_SHELL*1e3:.0f} mm wall)")
    sec = box_spar_sections(env, layout)
    cols = [(0.85, 0.2, 0.2), (0.2, 0.55, 0.9), (0.3, 0.78, 0.3)]
    names = ["box spar — LE", "box spar — mid", "box spar — TE"]
    for k, c in enumerate(sec.cells):
        o = resample_closed_polyline(np.asarray(c, float), 100)
        ax.add_patch(_ring(o, _inner_poly(o, T_BOX), cols[k], 0.9))
        ax.plot([], [], "s", color=cols[k], label=f"{names[k]} ({T_BOX*1e3:.0f} mm wall)")
    for ch in sec.channels:
        p = np.asarray(ch.polyline, float)
        ax.fill(p[:, 0], p[:, 1], color=(0.96, 0.75, 0.1), ec="k", lw=0.5)
    ax.plot([], [], "s", color=(0.96, 0.75, 0.1), label="UD longeron")
    ax.set_aspect("equal"); ax.grid(alpha=0.2)
    ax.legend(loc="center left", bbox_to_anchor=(1.0, 0.5), fontsize=10)
    ax.set_title("Amazon-baseline wingmast — wall-accurate cross-section (root, 750×300 mm)\n"
                 "3 hollow box spars + 2 UD longerons inside the FW shell", fontsize=11, weight="bold")
    ax.set_xlabel("chord X [m]"); ax.set_ylabel("normal Y [m]")
    fig.tight_layout()
    fig.savefig(str(out / "amazon_assembly_section.png"), dpi=140, bbox_inches="tight")
    print("  rendered exports/amazon_assembly_section.png")


if __name__ == "__main__":
    main()
