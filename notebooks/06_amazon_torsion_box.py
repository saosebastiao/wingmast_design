import marimo

__generated_with = "0.23.10"
app = marimo.App(width="medium")


@app.cell
def _():
    import json
    import os
    import time
    from pathlib import Path

    import marimo as mo
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path as MPath

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
    from wingmast_design.geometry.cells import _split_upper_lower as split_upper_lower
    from wingmast_design.geometry.cells import _y_on as y_on
    from wingmast_design.viz import check, kv, stamp

    return (
        BuildLine,
        BuildPart,
        BuildSketch,
        Color,
        Compound,
        MPath,
        Path,
        PathPatch,
        Plane,
        Polyline,
        ScaledAmazonMast,
        add,
        check,
        export_step,
        export_stl,
        json,
        kv,
        loft,
        make_face,
        mo,
        np,
        os,
        plt,
        split_upper_lower,
        stamp,
        time,
        y_on,
    )


@app.cell
def _(mo):
    mo.md(r"""
    # 06 · Project-Amazon continuous multi-cell torsion box  (R-AMZ-6, Article XI)

    Interactive view of `examples/06_amazon_torsion_box.py` *(run the script for the
    headless measurement record: `just example 06_amazon_torsion_box`)*. **The
    definitive assembly viz.**

    The members are **conformal cells** — a tube spar is round, a box spar is
    rectangular; these are neither. Each cell's caps lie **ON the airfoil ellipse**
    (curved), so the section reads as the mast it is. The build (project glossary
    terms):

    * **N conformal cells** filling the chord — the **D-cell** (curved LE skin +
      web), interior cell(s) (curved top+bottom caps between two webs), and the TE
      cell — each a hollow, filament-wound CFRP closed section, co-bonded
      side-by-side;
    * **UD longerons** nestled in the inter-cell **corner channels** (the voids the
      cells' blended corners leave under the shell, top + bottom of each shared web);
    * the **filament-wound outer shell** fairing the assembly to the OML;
    * the **round bearing stock** (OD500→OD450) below the deck partners.

    Together = a **multi-cell (N-cell) torsion box**. The section morphs
    **airfoil→round** through the transition (`section_oml`), so the cells / longerons
    / shell loft straight **through the stock** — the outer shell itself becomes the
    round bearing journals. ONE continuous structure heel→masthead, no separate tube.
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Sized design  (`exports/conformal_best.json`)

    The design is read from a JSON (default `exports/conformal_best.json`, the
    as-built re-size; override with env `TORSION_BOX_DESIGN` to export a scaled
    mast). It carries the cell count / blend / walls / cap schedule so the CAD walls
    **ARE** the sized walls, and optional length / section scales `s_l`/`s_s`
    (1.0 = Amazon baseline). With no JSON present a clearly-labelled *representative*
    fallback (3 cells, taper walls) is used instead.
    """)
    return


@app.cell
def _(Path, json, mo, np, os):
    # --- build parameters (ported verbatim from the example's module level) -------------------
    N_ST = 13                      # spanwise stations (loft sections) over the wing
    N_PTS = 96                     # points per cell outline
    RHO = 1600.0                   # CFRP density [kg/m³]

    design_path_str = os.environ.get(
        "TORSION_BOX_DESIGN",
        str(Path(mo.notebook_dir()).parent / "exports" / "conformal_best.json"),
    )
    sized_path = Path(design_path_str)
    SIZED = json.loads(sized_path.read_text()) if sized_path.exists() else None

    if SIZED:                                                   # sized design (Amazon or scaled)
        N_CELLS = int(SIZED["n_cells"])
        BLEND = float(SIZED["blend_radius"])
        T_SHELL = float(SIZED["t_shell"])
        T_WEB = float(SIZED["t_web"])
        S_L = float(SIZED.get("s_l", 1.0))
        S_S = float(SIZED.get("s_s", 1.0))
        CAP_Z = np.array([z for z, _ in SIZED["cap_schedule"]])
        CAP_T = np.array([t for _, t in SIZED["cap_schedule"]])
        T_CAP_ROOT, T_CAP_TIP = float(CAP_T[0]), float(CAP_T[-1])
    else:                                                       # representative fallback
        N_CELLS = 3
        BLEND = 0.030
        T_SHELL = 0.003
        T_WEB = 0.004
        S_L = S_S = 1.0
        CAP_Z = CAP_T = np.empty(0)
        T_CAP_ROOT, T_CAP_TIP = 0.009, 0.0025

    LE_RGB = (0.20, 0.55, 0.85)       # cell caps
    GOLD = (0.95, 0.78, 0.15)         # webs
    SHELL_RGB = (0.62, 0.64, 0.70)    # FW shell
    return (
        BLEND,
        CAP_T,
        CAP_Z,
        GOLD,
        LE_RGB,
        N_CELLS,
        N_PTS,
        N_ST,
        RHO,
        SHELL_RGB,
        SIZED,
        S_L,
        S_S,
        T_CAP_ROOT,
        T_CAP_TIP,
        T_SHELL,
        T_WEB,
        sized_path,
    )


@app.cell
def _(
    BLEND,
    N_CELLS,
    SIZED,
    S_L,
    S_S,
    T_CAP_ROOT,
    T_CAP_TIP,
    T_SHELL,
    T_WEB,
    kv,
    sized_path,
):
    _src = "SIZED cap schedule" if SIZED else "representative walls"
    design_view = kv(
        {
            "source": f"`{sized_path}` ({'found' if SIZED else 'MISSING → representative fallback'})",
            "schedule": _src,
            "n_cells": f"{N_CELLS}",
            "blend radius": f"{BLEND * 1e3:.1f} mm",
            "shell wall t_shell": f"{T_SHELL * 1e3:.1f} mm",
            "web wall t_web": f"{T_WEB * 1e3:.1f} mm",
            "cap schedule (root→tip)": f"{T_CAP_ROOT * 1e3:.1f} → {T_CAP_TIP * 1e3:.1f} mm",
            "length scale s_l / section scale s_s": f"{S_L:.3f} / {S_S:.3f}",
        },
        title="Loaded design",
    )
    design_view
    return


@app.cell
def _(BuildLine, BuildPart, BuildSketch, Polyline, add, loft, make_face, np):
    # --- LOCAL helpers ported verbatim from examples/06 (behaviour-identical) -----------------
    def face_of(poly: np.ndarray):
        pts = [(float(x), float(y)) for x, y in poly[:-1]]
        with BuildSketch() as sk:
            with BuildLine():
                Polyline(*pts, close=True)
            make_face()
        return sk.sketch

    def loft_faces(faces, ruled=True):
        with BuildPart() as part:
            for f in faces:
                add(f)
            loft(ruled=ruled)
        return part.part

    def inset(poly: np.ndarray, t: float) -> np.ndarray:
        """Inward normal offset of a convex closed polyline by ``t`` (keeps the project ordering,
        so it works through the airfoil→round morph). Used to get the shell-inner envelope."""
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

    return face_of, inset, loft_faces


@app.cell
def _(CAP_T, CAP_Z, T_CAP_ROOT, T_CAP_TIP, np):
    def cap_wall_at(z: float, span: float) -> float:
        if CAP_T.size:                               # the SIZED schedule (CAD walls == sizer)
            return float(np.interp(z, CAP_Z, CAP_T))
        f = min(max(z / span, 0.0), 1.0)             # representative taper
        return T_CAP_ROOT + f * (T_CAP_TIP - T_CAP_ROOT)

    return (cap_wall_at,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Live conformal cross-section — reactive preview (cheap)

    Root + stock cross-sections (line art) showing the continuous build's
    representation: **FW shell ring** + **cell-cap annular wall** + **internal
    webs** — and how it morphs airfoil→round. The controls below default to the
    loaded sized values, so the preview-at-defaults equals the script's render. This
    uses only `section_oml` + `inset` + web geometry — **no lofting**.
    """)
    return


@app.cell
def _(BLEND, N_CELLS, T_SHELL, T_WEB, mo):
    n_cells_ui = mo.ui.slider(start=3, stop=8, value=N_CELLS, step=1, label="n_cells")
    blend_ui = mo.ui.slider(
        start=0.002, stop=0.040, value=BLEND, step=0.001, label="blend radius [m]"
    )
    t_shell_ui = mo.ui.slider(
        start=0.001, stop=0.006, value=T_SHELL, step=0.0005, label="t_shell [m]"
    )
    t_web_ui = mo.ui.slider(
        start=0.001, stop=0.008, value=T_WEB, step=0.0005, label="t_web [m]"
    )
    mo.vstack([n_cells_ui, blend_ui, t_shell_ui, t_web_ui])
    return blend_ui, n_cells_ui, t_shell_ui, t_web_ui


@app.cell
def _(
    GOLD,
    LE_RGB,
    MPath,
    PathPatch,
    SHELL_RGB,
    S_L,
    S_S,
    ScaledAmazonMast,
    blend_ui,
    cap_wall_at,
    inset,
    n_cells_ui,
    np,
    plt,
    split_upper_lower,
    t_shell_ui,
    t_web_ui,
    y_on,
):
    # reactive cross-section render (port of _render_section), driven by the sliders.
    spec_preview = ScaledAmazonMast(s_l=S_L, s_s=S_S)
    n_cells_preview = int(n_cells_ui.value)
    t_shell_preview = float(t_shell_ui.value)
    t_web_preview = float(t_web_ui.value)
    # blend_ui is shown for the conformal corner radius (informational here; the section's
    # cap/web geometry below is set by t_shell / cap schedule / t_web, matching the example).
    _blend_preview = float(blend_ui.value)

    def _ring(outer, inner, fc, alpha=1.0, lw=0.8):
        v = np.vstack([outer, outer[0], inner[::-1], inner[-1]])
        codes = ([MPath.MOVETO] + [MPath.LINETO] * (len(outer) - 1) + [MPath.CLOSEPOLY]
                 + [MPath.MOVETO] + [MPath.LINETO] * (len(inner) - 1) + [MPath.CLOSEPOLY])
        return PathPatch(MPath(v, codes), fc=fc, ec="k", lw=lw, alpha=alpha)

    sec_fig, _axs = plt.subplots(1, 2, figsize=(12, 4.6))
    for _ax, (_z, _lbl) in zip(_axs, [(0.0, "wing root (airfoil)"),
                                      (0.55 * spec_preview.heel_z, "stock (round bearing journal)")]):
        _oml = spec_preview.section_oml(float(_z), n_pts=260)
        _env = inset(_oml, t_shell_preview)
        _cap = cap_wall_at(float(_z), spec_preview.sail_track_length)
        _env_in = inset(_env, _cap)
        _ax.add_patch(_ring(_oml, _env, SHELL_RGB, 0.55, lw=1.0))      # FW shell
        _ax.add_patch(_ring(_env, _env_in, LE_RGB, 1.0))             # cell caps (void inside)
        _up, _lo = split_upper_lower(np.asarray(_env, float))
        _xle, _xte = float(_env[:, 0].min()), float(_env[:, 0].max())
        for _k in range(1, n_cells_preview):
            _xw = _xle + _k / n_cells_preview * (_xte - _xle)
            _yhi = float(y_on(_up, np.array([_xw]))[0]) - _cap
            _ylo = float(y_on(_lo, np.array([_xw]))[0]) + _cap
            _ax.fill([_xw - t_web_preview / 2, _xw + t_web_preview / 2,
                      _xw + t_web_preview / 2, _xw - t_web_preview / 2],
                     [_ylo, _ylo, _yhi, _yhi], color=GOLD, ec="k", lw=0.4)
        _ax.set_aspect("equal")
        _ax.grid(alpha=0.18)
        _ax.set_title(_lbl, fontsize=11, weight="bold")
        _ax.set_xlabel("chord X [m]")
    for _lab, _col in [("FW shell", SHELL_RGB), ("cell caps", LE_RGB), ("webs", GOLD)]:
        _axs[0].plot([], [], "s", color=_col, label=_lab)
    _axs[0].legend(loc="upper right", fontsize=9, framealpha=0.95)
    sec_fig.suptitle(f"Continuous multi-cell torsion box — {n_cells_preview} cells run masthead→heel, "
                     "morphing from airfoil (wing) to a round multi-cell (stock journal)",
                     fontsize=12, weight="bold")
    sec_fig.tight_layout()
    sec_fig
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Build 3D assembly + export STL / STEP  (R-AMZ-6, Article XI)

    Lofting the continuous structure (shell + cap wall + webs through the
    airfoil→round morph), writing **one STL per part** into `exports/torsion_box/`,
    a coloured **mm-scaled STEP** `exports/amazon_torsion_box.step`, the
    `manifest.csv`, and the section PNG is a deliberate **milestone export** with a
    disk side-effect (measured ~21.8 s, ~10 GB). It is gated behind the button so
    this notebook stays instant to open / smoke-test. Press it to build, check every
    part is valid, and report the per-part masses.
    """)
    return


@app.cell
def _(mo):
    build_btn = mo.ui.run_button(
        label="🔧 Build 3D assembly + export STL/STEP (slow ~20 s, ~10 GB)"
    )
    build_btn
    return (build_btn,)


@app.cell
def _(
    Color,
    Compound,
    GOLD,
    LE_RGB,
    N_PTS,
    N_ST,
    Path,
    Plane,
    RHO,
    SHELL_RGB,
    SIZED,
    S_L,
    S_S,
    ScaledAmazonMast,
    T_CAP_ROOT,
    T_CAP_TIP,
    T_SHELL,
    T_WEB,
    build_btn,
    cap_wall_at,
    check,
    export_step,
    export_stl,
    face_of,
    inset,
    kv,
    loft_faces,
    mo,
    n_cells_ui,
    np,
    split_upper_lower,
    stamp,
    time,
    y_on,
):
    mo.stop(
        not build_btn.value,
        mo.md(
            "ℹ️ Press **🔧 Build 3D assembly + export STL/STEP** above to loft the "
            "continuous torsion box (R-AMZ-6, Article XI) and write "
            "`exports/torsion_box/*.stl`, `exports/amazon_torsion_box.step`, "
            "`manifest.csv` + the section PNG."
        ),
    )
    t0 = time.perf_counter()
    spec = ScaledAmazonMast(s_l=S_L, s_s=S_S)
    span = spec.sail_track_length
    n_cells = int(n_cells_ui.value)
    # ONE continuous structure heel→masthead: the section morphs airfoil→round through the
    # transition (section_oml), so the cells/longerons/shell loft straight THROUGH the stock —
    # the outer shell itself becomes the round bearing journals. Dense stations through the morph.
    zs = np.unique(np.concatenate([np.linspace(spec.heel_z, spec.partners_z, 7),
                                   np.linspace(spec.partners_z, 0.0, 14),
                                   np.linspace(0.0, span, N_ST)]))

    # --- nested closed sections (each morphs airfoil→round as ONE convex curve → lofts cleanly) --
    oml = [spec.section_oml(float(z), n_pts=2 * (N_PTS // 2)) for z in zs]
    env = [inset(o, T_SHELL) for o in oml]                       # shell inner
    caps = [cap_wall_at(float(z), span) for z in zs]
    env_in = [inset(e, c) for e, c in zip(env, caps)]           # cap inner = cell-void boundary

    def _tube(outer_polys, inner_polys):
        return (loft_faces([Plane(origin=(0, 0, float(z))) * face_of(np.asarray(p, float))
                            for z, p in zip(zs, outer_polys)])
                - loft_faces([Plane(origin=(0, 0, float(z))) * face_of(np.asarray(p, float))
                              for z, p in zip(zs, inner_polys)]))

    shell = _tube(oml, env)                                       # FW outer skin → round journals
    cap_wall = _tube(env, env_in)                                 # the cell caps (one annular wall)

    # --- internal webs at the N-1 band boundaries, spanning the cell void, lofted through morph
    webs = []
    for k in range(1, n_cells):
        faces = []
        for z, e, c in zip(zs, env, caps):
            xle, xte = float(e[:, 0].min()), float(e[:, 0].max())
            xw = xle + k / n_cells * (xte - xle)
            up, lo = split_upper_lower(np.asarray(e, float))
            yhi = float(y_on(up, np.array([xw]))[0]) - c
            ylo = float(y_on(lo, np.array([xw]))[0]) + c
            rect = np.array([[xw - T_WEB / 2, ylo], [xw + T_WEB / 2, ylo],
                             [xw + T_WEB / 2, yhi], [xw - T_WEB / 2, yhi], [xw - T_WEB / 2, ylo]])
            faces.append(Plane(origin=(0, 0, float(z))) * face_of(rect))
        webs.append(loft_faces(faces))

    shell_kg = shell.volume * RHO
    caps_kg = cap_wall.volume * RHO
    webs_kg = sum(w.volume for w in webs) * RHO
    struct = shell.volume + cap_wall.volume + sum(w.volume for w in webs)
    _src = "SIZED cap schedule" if SIZED else "representative walls"

    # --- colour, label, export (per-part STL for ParaView + a coloured STEP) -------------------
    out_dir = Path(mo.notebook_dir()).parent / "exports"
    pdir = out_dir / "torsion_box"
    pdir.mkdir(parents=True, exist_ok=True)
    parts = [(cap_wall, "cell_caps", LE_RGB)]
    parts += [(w, f"web_{i}", GOLD) for i, w in enumerate(webs)]
    parts += [(shell, "fw_shell", SHELL_RGB)]
    manifest = []
    for s, name, rgb in parts:
        s.color, s.label = Color(*rgb, 0.3 if name == "fw_shell" else 1.0), name
        export_stl(s, str(pdir / f"{name}.stl"))
        manifest.append((name, rgb, 0.3 if name == "fw_shell" else 1.0))

    asm = Compound(children=[s for s, _, _ in parts])
    # STEP in MILLIMETRES (OCC/STEP unit) → scale each labelled body ×1000 and rebuild the
    # Compound (scaling the whole Compound at once drops the body names).
    mm_parts = []
    for p, _rgb, _op in parts:
        q = p.scale(1000.0)
        q.label, q.color = p.label, p.color
        mm_parts.append(q)
    export_step(Compound(children=mm_parts), str(out_dir / "amazon_torsion_box.step"))

    manifest_lines = ["part,r,g,b,opacity"]
    for name, rgb, op in manifest:
        manifest_lines.append(f"{name},{rgb[0]:.3f},{rgb[1]:.3f},{rgb[2]:.3f},{op:.3f}")
    (pdir / "manifest.csv").write_text("\n".join(manifest_lines) + "\n")

    all_valid = shell.is_valid and cap_wall.is_valid and all(w.is_valid for w in webs)
    build_secs = time.perf_counter() - t0

    build_view = mo.vstack(
        [
            check(
                "R-AMZ-6 parts valid",
                all_valid,
                f"shell / caps / {len(webs)} webs all is_valid — wrote {len(manifest)} part "
                f"STLs → `exports/torsion_box/` + `amazon_torsion_box.step` "
                f"({len(asm.solids())} named solid bodies)",
            ),
            kv(
                {
                    "shell": f"{shell_kg:.0f} kg  ({T_SHELL * 1e3:.0f} mm wall)",
                    "cell caps": (
                        f"{caps_kg:.0f} kg  (caps {T_CAP_ROOT * 1e3:.0f}→"
                        f"{T_CAP_TIP * 1e3:.1f} mm, masthead→heel)"
                    ),
                    "webs": f"{webs_kg:.0f} kg  ({len(webs)} internal webs → {n_cells} cells)",
                    "continuous structural mass / mast": f"{struct * RHO:.0f} kg  ({_src})",
                },
                title="Continuous torsion-box masses",
            ),
            stamp("build + per-part STL + STEP + manifest", build_secs),
        ]
    )
    build_view
    return out_dir, span, spec


@app.cell
def _(mo):
    mo.md(r"""
    ## Section PNG export  (Article XI)

    Re-render the root + stock conformal cross-section at the **built** stations and
    write `exports/amazon_torsion_box_section.png` — the standing stress/assembly viz
    artefact. Also gated (depends on the built `spec`).
    """)
    return


@app.cell
def _(
    GOLD,
    LE_RGB,
    MPath,
    PathPatch,
    SHELL_RGB,
    T_SHELL,
    T_WEB,
    cap_wall_at,
    inset,
    n_cells_ui,
    np,
    out_dir,
    plt,
    span,
    spec,
    split_upper_lower,
    stamp,
    time,
    y_on,
):
    # depends on the gated `spec`/`out_dir`/`span` → only runs after the build button fires.
    t_png = time.perf_counter()
    n_cells_png = int(n_cells_ui.value)

    def _ring2(outer, inner, fc, alpha=1.0, lw=0.8):
        v = np.vstack([outer, outer[0], inner[::-1], inner[-1]])
        codes = ([MPath.MOVETO] + [MPath.LINETO] * (len(outer) - 1) + [MPath.CLOSEPOLY]
                 + [MPath.MOVETO] + [MPath.LINETO] * (len(inner) - 1) + [MPath.CLOSEPOLY])
        return PathPatch(MPath(v, codes), fc=fc, ec="k", lw=lw, alpha=alpha)

    png_fig, _axs = plt.subplots(1, 2, figsize=(12, 4.6))
    for _ax, (_z, _lbl) in zip(_axs, [(0.0, "wing root (airfoil)"),
                                      (0.55 * spec.heel_z, "stock (round bearing journal)")]):
        _oml = spec.section_oml(float(_z), n_pts=260)
        _env = inset(_oml, T_SHELL)
        _cap = cap_wall_at(float(_z), span)
        _env_in = inset(_env, _cap)
        _ax.add_patch(_ring2(_oml, _env, SHELL_RGB, 0.55, lw=1.0))
        _ax.add_patch(_ring2(_env, _env_in, LE_RGB, 1.0))
        _up, _lo = split_upper_lower(np.asarray(_env, float))
        _xle, _xte = float(_env[:, 0].min()), float(_env[:, 0].max())
        for _k in range(1, n_cells_png):
            _xw = _xle + _k / n_cells_png * (_xte - _xle)
            _yhi = float(y_on(_up, np.array([_xw]))[0]) - _cap
            _ylo = float(y_on(_lo, np.array([_xw]))[0]) + _cap
            _ax.fill([_xw - T_WEB / 2, _xw + T_WEB / 2, _xw + T_WEB / 2, _xw - T_WEB / 2],
                     [_ylo, _ylo, _yhi, _yhi], color=GOLD, ec="k", lw=0.4)
        _ax.set_aspect("equal")
        _ax.grid(alpha=0.18)
        _ax.set_title(_lbl, fontsize=11, weight="bold")
        _ax.set_xlabel("chord X [m]")
    for _lab, _col in [("FW shell", SHELL_RGB), ("cell caps", LE_RGB), ("webs", GOLD)]:
        _axs[0].plot([], [], "s", color=_col, label=_lab)
    _axs[0].legend(loc="upper right", fontsize=9, framealpha=0.95)
    png_fig.suptitle(f"Continuous multi-cell torsion box — {n_cells_png} cells run masthead→heel, "
                     "morphing from airfoil (wing) to a round multi-cell (stock journal)",
                     fontsize=12, weight="bold")
    png_fig.tight_layout()
    png_fig.savefig(str(out_dir / "amazon_torsion_box_section.png"), dpi=150, bbox_inches="tight")

    png_view = stamp("rendered exports/amazon_torsion_box_section.png", time.perf_counter() - t_png)
    png_view
    return


if __name__ == "__main__":
    app.run()
