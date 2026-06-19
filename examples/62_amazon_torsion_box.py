"""Conformal multi-cell torsion-box assembly of the Amazon-baseline mast (`R-AMZ-6`, Article XI).

The definitive assembly viz. The members are **conformal cells** (a tube spar is round, a box
spar is rectangular — these are neither): each cell's caps lie ON the airfoil ellipse (curved),
so the section reads as the mast it is. The build (project glossary terms):

  * **N conformal cells** filling the chord — the **D-cell** (curved LE skin + web), interior
    cell(s) (curved top+bottom caps between two webs), and the TE cell — each a hollow,
    filament-wound CFRP closed section, co-bonded side-by-side;
  * **UD longerons** nestled in the inter-cell **corner channels** (the voids the cells' blended
    corners leave under the shell, top + bottom of each shared web);
  * the **filament-wound outer shell** fairing the assembly to the OML;
  * the **round bearing stock** (OD500→OD450) below the deck partners.

Together = a **multi-cell (N-cell) torsion box**. Walls here are a *representative* taper (clearly
labelled) — the sized schedule comes from the as-built re-size (flagged separately).

Writes one **STL per part** into ``exports/torsion_box/`` (so ParaView can colour them as a real
CAD assembly — ``paraview/torsion_box.py``), a coloured STEP, and a clean conformal cross-section.

Run: `just example 62_amazon_torsion_box`
"""
from __future__ import annotations

import json
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
from wingmast_design.geometry.cells import CellLayout, cell_sections

# ---- build parameters. If the as-built re-size has been run (exports/conformal_best.json from
# `just py runs/conformal_optimize.py`), the cell count / blend / walls / cap schedule are taken
# from it so the CAD walls ARE the sized walls; otherwise a representative taper is used. --------
N_ST = 13                      # spanwise stations (loft sections) over the wing
N_PTS = 96                     # points per cell outline
RHO = 1600.0                   # CFRP density [kg/m³]

_SIZED = None
_sized_path = Path(__file__).resolve().parent.parent / "exports" / "conformal_best.json"
if _sized_path.exists():
    _SIZED = json.loads(_sized_path.read_text())

if _SIZED:                                                  # sized (as-built re-size)
    N_CELLS = int(_SIZED["n_cells"])
    BLEND = float(_SIZED["blend_radius"])
    T_SHELL = float(_SIZED["t_shell"])
    T_WEB = float(_SIZED["t_web"])
    _CAP_Z = np.array([z for z, _ in _SIZED["cap_schedule"]])
    _CAP_T = np.array([t for _, t in _SIZED["cap_schedule"]])
    T_CAP_ROOT, T_CAP_TIP = float(_CAP_T[0]), float(_CAP_T[-1])
else:                                                       # representative fallback
    N_CELLS = 3
    BLEND = 0.030
    T_SHELL = 0.003
    T_WEB = 0.004
    _CAP_Z = _CAP_T = np.empty(0)
    T_CAP_ROOT, T_CAP_TIP = 0.009, 0.0025

_LE_RGB, _TE_RGB = (0.20, 0.55, 0.85), (0.86, 0.45, 0.20)
_MID_RGB = [(0.32, 0.72, 0.45), (0.70, 0.35, 0.75), (0.40, 0.75, 0.78), (0.90, 0.62, 0.25)]
GOLD = (0.95, 0.78, 0.15)
SHELL_RGB = (0.62, 0.64, 0.70)
STOCK_RGB = (0.42, 0.42, 0.50)


def _cell_style(k: int, n: int) -> tuple[str, tuple, str]:
    """(stl_name, rgb, legend) — position-aware: cell 0 = LE (D-cell), cell n-1 = TE, rest mid."""
    if k == 0:
        return "cell_LE_Dcell", _LE_RGB, "cell — LE (D-cell)"
    if k == n - 1:
        return "cell_TE", _TE_RGB, "cell — TE"
    return f"cell_mid{k}", _MID_RGB[(k - 1) % len(_MID_RGB)], f"cell — mid {k}"


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


def _centered_ellipse(chord: float, thick: float, n: int = 140) -> np.ndarray:
    """Project-ordered ellipse (upper-TE→LE→lower-TE) of given chord×thick, centred at origin."""
    e = ellipse_coords(n // 2)
    out = e.copy()
    out[:, 0] = (e[:, 0] - 0.5) * chord
    out[:, 1] = e[:, 1] / 0.40 * (thick / chord) * chord
    return out


def _hollow(outer_polys, t_wall_per_z, zs):
    outer = _loft([Plane(origin=(0, 0, float(z))) * _face(p) for z, p in zip(zs, outer_polys)])
    inner = _loft([Plane(origin=(0, 0, float(z))) * offset(_face(p), amount=-float(t))
                   for z, p, t in zip(zs, outer_polys, t_wall_per_z)])
    return outer - inner


def _cap_wall(z: float, span: float) -> float:
    if _CAP_T.size:                              # the SIZED schedule (CAD walls == sizer)
        return float(np.interp(z, _CAP_Z, _CAP_T))
    f = min(max(z / span, 0.0), 1.0)             # representative taper
    return T_CAP_ROOT + f * (T_CAP_TIP - T_CAP_ROOT)


def main() -> None:
    t0 = time.perf_counter()
    spec = AmazonMastSpec()
    span = spec.sail_track_length
    layout = CellLayout(n_cells=N_CELLS, blend_radius=BLEND)
    zs = np.linspace(0.0, span, N_ST)

    print(f"Conformal multi-cell torsion box — {N_CELLS} cells (D-cell + {N_CELLS-2} interior + TE)"
          " + corner longerons + FW shell + stock")

    # --- per-station geometry: inset envelope (shell inner) → conformal cells + webs ----------
    chords = [spec.chord_at_z(float(z)) for z in zs]
    thicks = [spec.thickness_at_z(float(z)) for z in zs]
    env = [_centered_ellipse(c - 2 * T_SHELL, t - 2 * T_SHELL) for c, t in zip(chords, thicks)]
    secs = [cell_sections(e, layout) for e in env]
    caps = [_cap_wall(float(z), span) for z in zs]

    # --- N conformal cells (each hollowed: curved caps = t_cap(z), webs = T_WEB) --------------
    cells = []
    for k in range(N_CELLS):
        polys = [resample_closed_polyline(np.asarray(s.cells[k], float), N_PTS) for s in secs]
        # cap wall governs the offset; webs are thicker but a single inward offset reads cleanly
        s = _hollow(polys, caps, zs)
        cells.append(s)
    print(f"  cells:     valid {all(s.is_valid for s in cells)}, "
          f"{sum(s.volume for s in cells) * RHO:6.0f} kg  (caps {T_CAP_ROOT*1e3:.0f}→{T_CAP_TIP*1e3:.1f} mm)")

    # --- UD longerons: the TRUE inter-cell channel gaps (from cells.cell_sections), the void the
    # blend fillets leave between two cells and the shell, lofted top + bottom of each web ---------
    longerons = []
    for wi in range(N_CELLS - 1):
        for attr in ("top_poly", "bottom_poly"):
            polys = [getattr(s.channels[wi], attr) for s in secs]
            if any(len(p) < 3 for p in polys):
                continue                                 # degenerate at some station — skip
            # 20 pts: enough for the curved-triangle gap; more collapses OCC's thin-sliver loft
            faces = [Plane(origin=(0, 0, float(z))) * _face(resample_closed_polyline(np.asarray(p, float), 20))
                     for z, p in zip(zs, polys)]
            longerons.append(_loft(faces))
    print(f"  longerons: valid {all(s.is_valid for s in longerons)}, "
          f"{sum(s.volume for s in longerons) * RHO:6.0f} kg  ({len(longerons)} corner channels)")

    # --- FW outer shell (OML → inset envelope) -----------------------------------------------
    oml = [spec.section_oml(float(z), n_pts=2 * (N_PTS // 2)) for z in zs]
    shell = (_loft([Plane(origin=(0, 0, float(z))) * _face(p) for z, p in zip(zs, oml)])
             - _loft([Plane(origin=(0, 0, float(z))) * _face(p) for z, p in zip(zs, env)]))
    print(f"  shell:     valid {shell.is_valid}, {shell.volume * RHO:6.0f} kg  ({T_SHELL*1e3:.0f} mm wall)")

    # --- round bearing stock (below deck partners) -------------------------------------------
    zb = np.linspace(spec.heel_z, -0.04, 6)
    stock = _loft([Plane(origin=(0, 0, float(z))) * _face(spec.section_oml(float(z), n_pts=80))
                   for z in zb])
    print(f"  stock:     valid {stock.is_valid}, {stock.volume * RHO:6.0f} kg")

    struct = sum(s.volume for s in cells) + sum(s.volume for s in longerons) + shell.volume
    if _SIZED:
        print(f"\n  structural mass/mast = {struct * RHO:.0f} kg (wing, SIZED walls from the as-built "
              f"re-size; sizer wing ≈ {_SIZED['mass_per_mast_kg'] - 111:.0f} kg + {111} kg stock = "
              f"{_SIZED['mass_per_mast_kg']:.0f} kg/mast, {_SIZED['vs_amazon_pct']:+.1f}% vs Sponberg).")
        print("  NB: the CAD hollows each cell with a single (cap) wall, so its webs are thicker than "
              "the sizer's t_web → CAD wing runs ~10% over the sizer; the cap SCHEDULE matches exactly.")
    else:
        print(f"\n  structural mass/mast = {struct * RHO:.0f} kg (representative walls; run "
              "`just py runs/conformal_optimize.py` for the sized schedule).")

    # --- colour, label, export (per-part STL for ParaView + a coloured STEP) -------------------
    out = Path(__file__).resolve().parent.parent / "exports"
    pdir = out / "torsion_box"
    pdir.mkdir(parents=True, exist_ok=True)
    manifest = []
    for k, s in enumerate(cells):
        name, rgb, _ = _cell_style(k, N_CELLS)
        s.color, s.label = Color(*rgb), name
        export_stl(s, str(pdir / f"{name}.stl"))
        manifest.append((name, rgb, 1.0))
    for i, lg in enumerate(longerons):
        lg.color, lg.label = Color(*GOLD), f"longeron_{i}"
        export_stl(lg, str(pdir / f"longeron_{i}.stl"))
        manifest.append((f"longeron_{i}", GOLD, 1.0))
    shell.color, shell.label = Color(*SHELL_RGB, 0.3), "fw_shell"
    stock.color, stock.label = Color(*STOCK_RGB), "bearing_stock"
    export_stl(shell, str(pdir / "fw_shell.stl"))
    export_stl(stock, str(pdir / "bearing_stock.stl"))
    manifest += [("fw_shell", SHELL_RGB, 0.3), ("bearing_stock", STOCK_RGB, 1.0)]

    asm = Compound(children=[*cells, *longerons, shell, stock])
    export_step(asm, str(out / "amazon_torsion_box.step"))
    _write_manifest(pdir, manifest)
    print(f"  wrote {len(manifest)} part STLs → exports/torsion_box/ + amazon_torsion_box.step "
          f"({len(asm.solids())} solids)")

    _render_section(spec, layout, out)
    print(f"DONE in {time.perf_counter() - t0:.1f} s")


def _write_manifest(pdir: Path, manifest) -> None:
    """part,r,g,b,opacity — consumed by paraview/torsion_box.py."""
    lines = ["part,r,g,b,opacity"]
    for name, rgb, op in manifest:
        lines.append(f"{name},{rgb[0]:.3f},{rgb[1]:.3f},{rgb[2]:.3f},{op:.3f}")
    (pdir / "manifest.csv").write_text("\n".join(lines) + "\n")


def _render_section(spec: AmazonMastSpec, layout: CellLayout, out: Path) -> None:
    """Clean conformal root cross-section (line art — matplotlib is fine for 2-D; the 3-D is the
    ParaView render). Caps lie ON the ellipse — this is the shape, not a stack of rectangles."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path as MPath

    def ring(outer, inner, fc, alpha=1.0, lw=0.8):
        """Annulus PathPatch (even-odd hole) so the hollow closed-wire section shows."""
        v = np.vstack([outer, outer[0], inner[::-1], inner[-1]])
        codes = ([MPath.MOVETO] + [MPath.LINETO] * (len(outer) - 1) + [MPath.CLOSEPOLY]
                 + [MPath.MOVETO] + [MPath.LINETO] * (len(inner) - 1) + [MPath.CLOSEPOLY])
        return PathPatch(MPath(v, codes), fc=fc, ec="k", lw=lw, alpha=alpha)

    fig, ax = plt.subplots(figsize=(12, 4.6))
    ax.set_facecolor("white")
    c0, t0 = spec.chord_at_z(0.0), spec.thickness_at_z(0.0)
    oml = spec.section_oml(0.0, n_pts=260)
    env = _centered_ellipse(c0 - 2 * T_SHELL, t0 - 2 * T_SHELL, 260)

    # shell ring (OML → inset), hollow
    ax.add_patch(ring(oml, env, SHELL_RGB, 0.55, lw=1.0))
    ax.plot([], [], "s", color=SHELL_RGB, label=f"FW shell ({T_SHELL*1e3:.0f} mm)")

    sec = cell_sections(env, layout)
    cap = _cap_wall(0.0, spec.sail_track_length)
    for k, cell in enumerate(sec.cells):
        _, rgb, legend = _cell_style(k, layout.n_cells)
        o = resample_closed_polyline(np.asarray(cell, float), 200)
        inner = offset(_face(o), amount=-cap).faces()[0].outer_wire()
        iw = np.array([((inner @ (i / 160)).X, (inner @ (i / 160)).Y) for i in range(161)])
        ax.fill(o[:, 0], o[:, 1], color=rgb, ec="k", lw=0.9)             # cap material
        ax.fill(iw[:, 0], iw[:, 1], color="white", ec="k", lw=0.6)       # hollow void (closed wire)
        ax.plot([], [], "s", color=rgb, label=f"{legend} (hollow, cap {cap*1e3:.0f} mm)")
    for ch in sec.channels:                       # the TRUE fillet-gap channels (top + bottom)
        for p in (ch.top_poly, ch.bottom_poly):
            if len(p) >= 3:
                ax.fill(p[:, 0], p[:, 1], color=GOLD, ec="k", lw=0.6)
    ax.plot([], [], "s", color=GOLD, label="UD longeron (fillet-gap channel)")

    ax.set_aspect("equal")
    ax.grid(alpha=0.18)
    ax.legend(loc="center left", bbox_to_anchor=(1.0, 0.5), fontsize=10, framealpha=0.95)
    ax.set_title("Amazon-baseline wingmast — conformal multi-cell torsion box (root, 750×300 mm)\n"
                 f"{layout.n_cells} conformal cells (caps ON the ellipse) + corner longerons, inside the FW shell",
                 fontsize=12, weight="bold")
    ax.set_xlabel("chord  X [m]")
    ax.set_ylabel("normal  Y [m]")
    fig.tight_layout()
    fig.savefig(str(out / "amazon_torsion_box_section.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  rendered exports/amazon_torsion_box_section.png")


if __name__ == "__main__":
    main()
