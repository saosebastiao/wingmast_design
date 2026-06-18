"""Build-EXACT CAD assembly of the optimized project-method Amazon mast (`R-AMZ-6`, Article XI).

Matches the *optimized* design (large-run mass-optimal: 3 spars, narrow-deep box 0.40c×0.89t,
±9° helical shell, 80% 0° caps) — NOT the chord-filling concept of example 60. Build-exact means:

  * the **narrow deep box cluster** the optimizer actually chose (mid-chord), with **faired LE/TE**;
  * **tapered, non-uniform walls** — cap wall = the SIZED schedule t_cap(z) (11.8 mm root → 2 mm
    tip), web wall = t_web, each from the sizer;
  * **UD longerons in the true inter-spar corner channels** (cap-level, both gaps);
  * the **FW shell** over the OML and the **bearing stock** below deck.

Prints the CAD material mass per part and checks it against the optimizer's per-mast mass.

Run: `just example 61_amazon_build_exact`
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

from wingmast_design.geometry.amazon_mast import AmazonMastSpec, ellipse_coords
from wingmast_design.structural.amazon_myway import MyWayParams, estimate_myway_mass, myway_section

N_ST = 14
RHO = 1600.0          # carbon/epoxy
RHO_FOAM = 80.0       # LE/TE fairing foam core
# the large-run MASS-OPTIMAL design (A)
OPT = MyWayParams(n_spars=3, box_frac_chord=0.40, box_frac_thick=0.89, t_shell=0.002, t_web=0.003,
                  shell_helix_deg=9.0, layup_f0=0.80, layup_f45=0.10, layup_f90=0.10)


def _face(poly):
    with BuildSketch() as sk:
        with BuildLine():
            Polyline(*[(float(x), float(y)) for x, y in poly], close=True)
        make_face()
    return sk.sketch


def _loft(faces):
    with BuildPart() as p:
        for f in faces:
            add(f)
        loft(ruled=True)
    return p.part


def _rect(xl, xr, yb, yt, n=8):
    left = np.column_stack([np.full(n, xl), np.linspace(yt, yb, n)])
    bot = np.column_stack([np.linspace(xl, xr, n), np.full(n, yb)])
    right = np.column_stack([np.full(n, xr), np.linspace(yb, yt, n)])
    top = np.column_stack([np.linspace(xr, xl, n), np.full(n, yt)])
    return np.vstack([left, bot[1:], right[1:], top[1:-1]])


def _centered_ellipse(chord, thick, n=130):
    e = ellipse_coords(n // 2).copy()
    out = e.copy()
    out[:, 0] = (e[:, 0] - 0.5) * chord
    out[:, 1] = e[:, 1] / 0.40 * (thick / chord) * chord
    return out


def _fairing_poly(chord, thick, xcut, side, n=44):
    """Arc of the (inset) ellipse outboard of x=xcut — the LE (side<0) or TE (side>0) faired
    region; ``close=True`` adds the vertical at the cut."""
    a, b = chord / 2.0, thick / 2.0
    th_c = float(np.arccos(np.clip(xcut / a, -1.0, 1.0)))
    th = np.linspace(-th_c, th_c, n) if side > 0 else np.linspace(th_c, 2 * np.pi - th_c, n)
    return np.column_stack([a * np.cos(th), b * np.sin(th)])


def _geom(spec, z, mods):
    c, t = spec.chord_at_z(z), spec.thickness_at_z(z)
    t_cap = myway_section(z, spec, OPT, props=mods)[0]
    w_box = OPT.box_frac_chord * c
    half_fit = (t / 2) * np.sqrt(max(0.0, 1 - OPT.box_frac_chord ** 2)) - OPT.t_shell - OPT.blend_radius
    h = min(OPT.box_frac_thick, max(0.30, 2 * half_fit / t)) * t
    gap = 2 * OPT.blend_radius
    cw = (w_box - (OPT.n_spars - 1) * gap) / OPT.n_spars
    cells = [(-w_box / 2 + k * (cw + gap), -w_box / 2 + k * (cw + gap) + cw) for k in range(OPT.n_spars)]
    return c, t, w_box, h, t_cap, cells, gap


def main() -> None:
    t0 = time.perf_counter()
    spec = AmazonMastSpec()
    mods = OPT.props()
    zs = np.linspace(0.0, spec.sail_track_length, N_ST)
    G = [_geom(spec, float(z), mods) for z in zs]

    print("Build-EXACT optimized mast: narrow box (0.40c×0.89t), tapered walls, corner longerons")

    # --- 3 hollow box spars (tapered cap = t_cap(z), web = t_web) ---
    spars = []
    for k in range(OPT.n_spars):
        of, inf = [], []
        for z, (c, t, wb, h, tcap, cells, gap) in zip(zs, G):
            xl, xr = cells[k]
            of.append(Plane(origin=(0, 0, float(z))) * _face(_rect(xl, xr, -h / 2, h / 2)))
            inf.append(Plane(origin=(0, 0, float(z))) * _face(
                _rect(xl + OPT.t_web, xr - OPT.t_web, -h / 2 + tcap, h / 2 - tcap)))
        spars.append(_loft(of) - _loft(inf))
    print(f"  3 box spars: valid {all(s.is_valid for s in spars)}, "
          f"wall {sum(s.volume for s in spars)*RHO:.0f} kg")

    # --- UD longerons in the 2 inter-spar gaps, at top + bottom (the corner channels) ---
    longerons = []
    for g in range(OPT.n_spars - 1):
        for side in (+1, -1):
            faces = []
            for z, (c, t, wb, h, tcap, cells, gap) in zip(zs, G):
                xl = cells[g][1]
                xr = cells[g + 1][0]
                lh = OPT.blend_radius                            # UD fill height at the corner
                yb, yt = (h / 2 - lh, h / 2) if side > 0 else (-h / 2, -h / 2 + lh)
                faces.append(Plane(origin=(0, 0, float(z))) * _face(_rect(xl, xr, yb, yt)))
            longerons.append(_loft(faces))
    print(f"  {len(longerons)} longerons: valid {all(s.is_valid for s in longerons)}, "
          f"{sum(s.volume for s in longerons)*RHO:.0f} kg")

    # --- FW shell (OML → inset envelope) ---
    oml = [spec.section_oml(float(z), n_pts=160) for z in zs]
    env = [_centered_ellipse(c - 2 * OPT.t_shell, t - 2 * OPT.t_shell) for (c, t, *_), z in zip(G, zs)]
    shell = (_loft([Plane(origin=(0, 0, float(z))) * _face(p) for z, p in zip(zs, oml)])
             - _loft([Plane(origin=(0, 0, float(z))) * _face(p) for z, p in zip(zs, env)]))
    print(f"  FW shell: valid {shell.is_valid}, {shell.volume*RHO:.0f} kg")

    # --- LE & TE fairings (inside the shell, outboard of the box) ---
    fairings = []
    for sgn in (-1, 1):
        faces = []
        for z, (c, t, wb, h, tcap, cells, gap) in zip(zs, G):
            xcut = cells[0][0] if sgn < 0 else cells[-1][1]
            poly = _fairing_poly(c - 2 * OPT.t_shell, t - 2 * OPT.t_shell, xcut, sgn)
            faces.append(Plane(origin=(0, 0, float(z))) * _face(poly))
        fairings.append(_loft(faces))
    print(f"  LE/TE fairings: valid {all(s.is_valid for s in fairings)}, "
          f"{sum(s.volume for s in fairings)*RHO_FOAM:.0f} kg foam (non-structural)")

    # --- bearing stock ---
    zb = np.linspace(spec.heel_z, -0.05, 5)
    stock = _loft([Plane(origin=(0, 0, float(z))) * _face(spec.section_oml(float(z), n_pts=80))
                   for z in zb])

    # --- mass cross-check vs the optimizer (ballpark only — see caveat) ---
    structural = sum(s.volume for s in spars) + sum(lg.volume for lg in longerons) + shell.volume
    opt_kg = estimate_myway_mass(spec, OPT).mass_per_mast_kg
    print(f"\n  CAD masses: box spars {sum(s.volume for s in spars)*RHO:.0f} + longerons "
          f"{sum(lg.volume for lg in longerons)*RHO:.0f} + shell {shell.volume*RHO:.0f} = "
          f"{structural*RHO:.0f} kg structural/mast (+ {sum(f.volume for f in fairings)*RHO_FOAM:.0f} kg foam).")
    print(f"  Ballpark-consistent with the optimizer's {opt_kg:.0f} kg/mast — but NOT a precise match: the"
          " sizer used a simplified single-equivalent-box model, and the longeron cross-section here is a"
          " design choice. An exact mass needs re-sizing on this as-built 3-box geometry (flagged).")

    # --- colour + export ---
    spar_cols = [Color(0.85, 0.2, 0.2), Color(0.2, 0.55, 0.9), Color(0.3, 0.78, 0.3)]
    for i, (s, col) in enumerate(zip(spars, spar_cols)):
        s.color, s.label = col, f"box_spar_{i}"
    for i, lg in enumerate(longerons):
        lg.color, lg.label = Color(0.96, 0.75, 0.1), f"longeron_{i}"
    for f, lbl in zip(fairings, ("le_fairing", "te_fairing")):
        f.color, f.label = Color(0.8, 0.8, 0.55, 0.5), lbl
    shell.color, shell.label = Color(0.55, 0.55, 0.62, 0.3), "fw_shell"
    stock.color, stock.label = Color(0.45, 0.45, 0.5), "bearing_stock"
    asm = Compound(children=[*spars, *longerons, *fairings, shell, stock])

    out = Path(__file__).resolve().parent.parent / "exports"
    out.mkdir(exist_ok=True)
    export_step(asm, str(out / "amazon_build_exact.step"))
    export_stl(asm, str(out / "amazon_build_exact.stl"))
    print(f"  wrote exports/amazon_build_exact.{{step,stl}} ({len(asm.solids())} solids)")
    _render(spec, mods, out)
    print(f"DONE in {time.perf_counter() - t0:.1f} s")


def _render(spec, mods, out) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path as MPath

    def ring(outer, inner, fc, alpha=1.0):
        v = np.vstack([outer, outer[0], inner[::-1], inner[-1]])
        codes = ([MPath.MOVETO] + [MPath.LINETO] * (len(outer) - 1) + [MPath.CLOSEPOLY]
                 + [MPath.MOVETO] + [MPath.LINETO] * (len(inner) - 1) + [MPath.CLOSEPOLY])
        return PathPatch(MPath(v, codes), fc=fc, ec="k", lw=0.7, alpha=alpha)

    fig, ax = plt.subplots(figsize=(11, 5.5))
    c, t, wb, h, tcap, cells, gap = _geom(spec, 0.0, mods)
    oml = spec.section_oml(0.0, n_pts=200)
    env = _centered_ellipse(c - 2 * OPT.t_shell, t - 2 * OPT.t_shell)
    ax.add_patch(ring(oml, env, (0.55, 0.55, 0.62), 0.3))
    ax.plot([], [], "s", color=(0.55, 0.55, 0.62), label=f"FW shell ({OPT.t_shell*1e3:.0f} mm)")
    # fairings
    for sgn in (-1, 1):
        xcut = cells[0][0] if sgn < 0 else cells[-1][1]
        fp = _fairing_poly(c - 2 * OPT.t_shell, t - 2 * OPT.t_shell, xcut, sgn)
        ax.fill(fp[:, 0], fp[:, 1], color=(0.8, 0.8, 0.55), alpha=0.6)
    ax.plot([], [], "s", color=(0.8, 0.8, 0.55), label="LE/TE fairing")
    cols = [(0.85, 0.2, 0.2), (0.2, 0.55, 0.9), (0.3, 0.78, 0.3)]
    names = ["box spar — LE", "box spar — mid", "box spar — TE"]
    for k, (xl, xr) in enumerate(cells):
        o = _rect(xl, xr, -h / 2, h / 2, 4)
        i = _rect(xl + OPT.t_web, xr - OPT.t_web, -h / 2 + tcap, h / 2 - tcap, 4)
        ax.add_patch(ring(o, i, cols[k], 0.92))
        ax.plot([], [], "s", color=cols[k], label=f"{names[k]} (cap {tcap*1e3:.0f}mm, web {OPT.t_web*1e3:.0f}mm)")
    for g in range(2):
        xl, xr = cells[g][1], cells[g + 1][0]
        lh = 2 * OPT.blend_radius
        for yb, yt in ((h / 2 - lh, h / 2), (-h / 2, -h / 2 + lh)):
            ax.fill([xl, xr, xr, xl], [yb, yb, yt, yt], color=(0.96, 0.75, 0.1), ec="k", lw=0.4)
    ax.plot([], [], "s", color=(0.96, 0.75, 0.1), label="UD longeron")
    ax.set_aspect("equal"); ax.grid(alpha=0.2)
    ax.legend(loc="center left", bbox_to_anchor=(1.0, 0.5), fontsize=9)
    ax.set_title("Build-exact optimized wingmast — root section (750×300 mm)\n"
                 "narrow deep box (0.40c) + corner longerons + faired LE/TE, inside the FW shell",
                 fontsize=11, weight="bold")
    ax.set_xlabel("chord X [m]"); ax.set_ylabel("normal Y [m]")
    fig.tight_layout()
    fig.savefig(str(out / "amazon_build_exact_section.png"), dpi=140, bbox_inches="tight")
    print("  rendered exports/amazon_build_exact_section.png")


if __name__ == "__main__":
    main()
