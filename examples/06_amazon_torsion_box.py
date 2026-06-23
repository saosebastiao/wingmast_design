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

Run: `just example 06_amazon_torsion_box`
"""
from __future__ import annotations

import json
import os
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

from wingmast_design.geometry.amazon_mast import ScaledAmazonMast
from wingmast_design.geometry.cells import _split_upper_lower, _y_on

# ---- build parameters. The design is read from a JSON (default exports/conformal_best.json, the
# as-built re-size; override with env TORSION_BOX_DESIGN to export a scaled mast). It carries the
# cell count / blend / walls / cap schedule so the CAD walls ARE the sized walls, and optional
# length/section scales `s_l`/`s_s` (1.0 = Amazon baseline). --------------------------------------
N_ST = 13                      # spanwise stations (loft sections) over the wing
N_PTS = 96                     # points per cell outline
RHO = 1600.0                   # CFRP density [kg/m³]

_SIZED = None
_sized_path = Path(os.environ.get(
    "TORSION_BOX_DESIGN", Path(__file__).resolve().parent.parent / "exports" / "conformal_best.json"))
if _sized_path.exists():
    _SIZED = json.loads(_sized_path.read_text())

if _SIZED:                                                  # sized design (Amazon or scaled)
    N_CELLS = int(_SIZED["n_cells"])
    BLEND = float(_SIZED["blend_radius"])
    T_SHELL = float(_SIZED["t_shell"])
    T_WEB = float(_SIZED["t_web"])
    S_L = float(_SIZED.get("s_l", 1.0))
    S_S = float(_SIZED.get("s_s", 1.0))
    _CAP_Z = np.array([z for z, _ in _SIZED["cap_schedule"]])
    _CAP_T = np.array([t for _, t in _SIZED["cap_schedule"]])
    T_CAP_ROOT, T_CAP_TIP = float(_CAP_T[0]), float(_CAP_T[-1])
else:                                                       # representative fallback
    N_CELLS = 3
    BLEND = 0.030
    T_SHELL = 0.003
    T_WEB = 0.004
    S_L = S_S = 1.0
    _CAP_Z = _CAP_T = np.empty(0)
    T_CAP_ROOT, T_CAP_TIP = 0.009, 0.0025

_LE_RGB = (0.20, 0.55, 0.85)      # cell caps
GOLD = (0.95, 0.78, 0.15)         # webs
SHELL_RGB = (0.62, 0.64, 0.70)    # FW shell


def _face(poly: np.ndarray):
    pts = [(float(x), float(y)) for x, y in poly[:-1]]
    with BuildSketch() as sk:
        with BuildLine():
            Polyline(*pts, close=True)
        make_face()
    return sk.sketch


def _loft(faces, ruled=True):
    with BuildPart() as part:
        for f in faces:
            add(f)
        loft(ruled=ruled)
    return part.part


def _inset(poly: np.ndarray, t: float) -> np.ndarray:
    """Inward normal offset of a convex closed polyline by ``t`` (keeps the project ordering, so it
    works through the airfoil→round morph). Used to get the shell-inner envelope from any OML."""
    p = np.asarray(poly, float)
    if len(p) > 1 and np.allclose(p[0], p[-1]):
        p = p[:-1]
    n = len(p)
    cen = p.mean(axis=0)

    def innorm(e, b):
        nn = np.array([-e[1], e[0]], float)
        ln = np.hypot(nn[0], nn[1])
        nn = nn / ln if ln > 1e-12 else nn
        return -nn if np.dot(nn, cen - b) < 0 else nn

    out = np.empty((n, 2))
    for i in range(n):
        a, b, c = p[(i - 1) % n], p[i], p[(i + 1) % n]
        n1, n2 = innorm(b - a, b), innorm(c - b, b)
        bis = n1 + n2
        lb = np.hypot(bis[0], bis[1])
        bis = bis / lb if lb > 1e-9 else innorm(c - a, b)
        out[i] = b + bis * (t / max(float(np.dot(bis, n1)), 0.3))
    return np.vstack([out, out[0]])


def _cap_wall(z: float, span: float) -> float:
    if _CAP_T.size:                              # the SIZED schedule (CAD walls == sizer)
        return float(np.interp(z, _CAP_Z, _CAP_T))
    f = min(max(z / span, 0.0), 1.0)             # representative taper
    return T_CAP_ROOT + f * (T_CAP_TIP - T_CAP_ROOT)


def main() -> None:
    t0 = time.perf_counter()
    spec = ScaledAmazonMast(s_l=S_L, s_s=S_S)
    span = spec.sail_track_length
    # ONE continuous structure heel→masthead: the section morphs airfoil→round through the
    # transition (section_oml), so the cells/longerons/shell loft straight THROUGH the stock — the
    # outer shell itself becomes the round bearing journals. Dense stations through the morph.
    zs = np.unique(np.concatenate([np.linspace(spec.heel_z, spec.partners_z, 7),
                                   np.linspace(spec.partners_z, 0.0, 14),   # dense ellipse→round morph
                                   np.linspace(0.0, span, N_ST)]))

    print(f"Continuous conformal torsion box — {N_CELLS} cells lofted masthead→heel "
          "(airfoil morphs to round bearing journals; cells run through the stock, no separate tube)")

    # --- nested closed sections (each morphs airfoil→round as ONE convex curve → lofts cleanly) --
    oml = [spec.section_oml(float(z), n_pts=2 * (N_PTS // 2)) for z in zs]
    env = [_inset(o, T_SHELL) for o in oml]                        # shell inner
    caps = [_cap_wall(float(z), span) for z in zs]
    env_in = [_inset(e, c) for e, c in zip(env, caps)]            # cap inner = the cell-void boundary

    def _tube(outer_polys, inner_polys):
        return (_loft([Plane(origin=(0, 0, float(z))) * _face(np.asarray(p, float)) for z, p in zip(zs, outer_polys)])
                - _loft([Plane(origin=(0, 0, float(z))) * _face(np.asarray(p, float)) for z, p in zip(zs, inner_polys)]))

    shell = _tube(oml, env)                                       # FW outer skin → round journals
    cap_wall = _tube(env, env_in)                                 # the cell caps (one annular wall)
    print(f"  shell:     valid {shell.is_valid}, {shell.volume * RHO:6.0f} kg  ({T_SHELL*1e3:.0f} mm wall)")
    print(f"  cell caps: valid {cap_wall.is_valid}, {cap_wall.volume * RHO:6.0f} kg "
          f"(caps {T_CAP_ROOT*1e3:.0f}→{T_CAP_TIP*1e3:.1f} mm, masthead→heel)")

    # --- internal webs at the N-1 band boundaries, spanning the cell void, lofted through the morph
    webs = []
    for k in range(1, N_CELLS):
        faces = []
        for z, e, c in zip(zs, env, caps):
            xle, xte = float(e[:, 0].min()), float(e[:, 0].max())
            xw = xle + k / N_CELLS * (xte - xle)
            up, lo = _split_upper_lower(np.asarray(e, float))
            yhi = float(_y_on(up, np.array([xw]))[0]) - c
            ylo = float(_y_on(lo, np.array([xw]))[0]) + c
            rect = np.array([[xw - T_WEB / 2, ylo], [xw + T_WEB / 2, ylo],
                             [xw + T_WEB / 2, yhi], [xw - T_WEB / 2, yhi], [xw - T_WEB / 2, ylo]])
            faces.append(Plane(origin=(0, 0, float(z))) * _face(rect))
        webs.append(_loft(faces))
    print(f"  webs:      valid {all(w.is_valid for w in webs)}, "
          f"{sum(w.volume for w in webs) * RHO:6.0f} kg  ({len(webs)} internal webs → {N_CELLS} cells)")

    struct = shell.volume + cap_wall.volume + sum(w.volume for w in webs)
    src = "SIZED cap schedule" if _SIZED else "representative walls"
    print(f"\n  continuous structural mass/mast = {struct * RHO:.0f} kg ({src}; cells run masthead→heel, "
          "stock cells hold the root cap wall — the cells lofted through the stock per the build brief).")

    # --- colour, label, export (per-part STL for ParaView + a coloured STEP) -------------------
    out = Path(__file__).resolve().parent.parent / "exports"
    pdir = out / "torsion_box"
    pdir.mkdir(parents=True, exist_ok=True)
    parts = [(cap_wall, "cell_caps", _LE_RGB)]
    parts += [(w, f"web_{i}", GOLD) for i, w in enumerate(webs)]
    parts += [(shell, "fw_shell", SHELL_RGB)]
    manifest = []
    for s, name, rgb in parts:
        s.color, s.label = Color(*rgb, 0.3 if name == "fw_shell" else 1.0), name
        export_stl(s, str(pdir / f"{name}.stl"))
        manifest.append((name, rgb, 0.3 if name == "fw_shell" else 1.0))

    asm = Compound(children=[s for s, _, _ in parts])
    # STEP is written in MILLIMETRES (the OCC/STEP unit) so it imports at true size in Fusion 360 /
    # SolidWorks / etc. — our model is in metres → scale ×1000. Scale each labelled body and rebuild
    # the Compound (scaling the whole Compound at once drops the body names).
    mm_parts = []
    for p, _, _ in parts:
        q = p.scale(1000.0)
        q.label, q.color = p.label, p.color
        mm_parts.append(q)
    export_step(Compound(children=mm_parts), str(out / "amazon_torsion_box.step"))
    _write_manifest(pdir, manifest)
    print(f"  wrote {len(manifest)} part STLs → exports/torsion_box/ + amazon_torsion_box.step "
          f"(mm; {len(asm.solids())} named solid bodies)")

    _render_section(spec, out, N_CELLS)
    print(f"DONE in {time.perf_counter() - t0:.1f} s")


def _write_manifest(pdir: Path, manifest) -> None:
    """part,r,g,b,opacity — consumed by paraview/torsion_box.py."""
    lines = ["part,r,g,b,opacity"]
    for name, rgb, op in manifest:
        lines.append(f"{name},{rgb[0]:.3f},{rgb[1]:.3f},{rgb[2]:.3f},{op:.3f}")
    (pdir / "manifest.csv").write_text("\n".join(lines) + "\n")


def _render_section(spec, out: Path, n_cells: int) -> None:
    """Root + stock cross-sections (line art) showing the continuous build's representation: FW
    shell ring + cell-cap annular wall + internal webs — and how it morphs airfoil→round."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path as MPath

    def ring(outer, inner, fc, alpha=1.0, lw=0.8):
        v = np.vstack([outer, outer[0], inner[::-1], inner[-1]])
        codes = ([MPath.MOVETO] + [MPath.LINETO] * (len(outer) - 1) + [MPath.CLOSEPOLY]
                 + [MPath.MOVETO] + [MPath.LINETO] * (len(inner) - 1) + [MPath.CLOSEPOLY])
        return PathPatch(MPath(v, codes), fc=fc, ec="k", lw=lw, alpha=alpha)

    fig, axs = plt.subplots(1, 2, figsize=(12, 4.6))
    for ax, (z, lbl) in zip(axs, [(0.0, "wing root (airfoil)"),
                                  (0.55 * spec.heel_z, "stock (round bearing journal)")]):
        oml = spec.section_oml(float(z), n_pts=260)
        env = _inset(oml, T_SHELL)
        cap = _cap_wall(float(z), spec.sail_track_length)
        env_in = _inset(env, cap)
        ax.add_patch(ring(oml, env, SHELL_RGB, 0.55, lw=1.0))            # FW shell
        ax.add_patch(ring(env, env_in, _LE_RGB, 1.0))                   # cell caps (void inside)
        up, lo = _split_upper_lower(np.asarray(env, float))
        xle, xte = float(env[:, 0].min()), float(env[:, 0].max())
        for k in range(1, n_cells):
            xw = xle + k / n_cells * (xte - xle)
            yhi = float(_y_on(up, np.array([xw]))[0]) - cap
            ylo = float(_y_on(lo, np.array([xw]))[0]) + cap
            ax.fill([xw - T_WEB / 2, xw + T_WEB / 2, xw + T_WEB / 2, xw - T_WEB / 2],
                    [ylo, ylo, yhi, yhi], color=GOLD, ec="k", lw=0.4)
        ax.set_aspect("equal")
        ax.grid(alpha=0.18)
        ax.set_title(lbl, fontsize=11, weight="bold")
        ax.set_xlabel("chord X [m]")
    for lab, col in [("FW shell", SHELL_RGB), ("cell caps", _LE_RGB), ("webs", GOLD)]:
        axs[0].plot([], [], "s", color=col, label=lab)
    axs[0].legend(loc="upper right", fontsize=9, framealpha=0.95)
    fig.suptitle(f"Continuous multi-cell torsion box — {n_cells} cells run masthead→heel, "
                 "morphing from airfoil (wing) to a round multi-cell (stock journal)",
                 fontsize=12, weight="bold")
    fig.tight_layout()
    fig.savefig(str(out / "amazon_torsion_box_section.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  rendered exports/amazon_torsion_box_section.png")


if __name__ == "__main__":
    main()
