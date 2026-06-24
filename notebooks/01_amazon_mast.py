import marimo

__generated_with = "0.23.10"
app = marimo.App(width="medium")


@app.cell
def _():
    import time
    from pathlib import Path

    import marimo as mo
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

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
    from wingmast_design.viz import check, kv, stamp, table

    return (
        AMAZON_DESIGN_MOMENT_NM,
        AMAZON_FOS,
        AMAZON_RM_NM,
        AMAZON_STATIONS_MM,
        AMAZON_TC,
        AmazonMastSpec,
        Path,
        build_amazon_mast_solid,
        check,
        export_step,
        export_stl,
        kv,
        mo,
        plt,
        stamp,
        table,
        time,
    )


@app.cell
def _(mo):
    mo.md(r"""
    # 01 · Project-Amazon baseline wingmast OML

    Interactive view of `examples/01_amazon_mast.py` *(run the script for the
    headless measurement record: `just example 01_amazon_mast`)*.

    Reproduces Eric Sponberg's **Project Amazon** free-standing rotating-wingmast
    OML from his published station table — a constant **2.5:1 ellipse**
    (750×300 mm at the deck → 300×120 mm at the masthead, modified-entasis taper,
    round OD500/OD450 bearing stock). Checks every station against the published
    dimensions (**R-AMZ-1**), reports the two journal stations, and exports
    STL + STEP (**R-AMZ-6**, Article XI).
    """)
    return


@app.cell
def _(
    AMAZON_DESIGN_MOMENT_NM,
    AMAZON_FOS,
    AMAZON_RM_NM,
    AMAZON_TC,
    AmazonMastSpec,
    kv,
):
    spec = AmazonMastSpec()
    summary = kv(
        {
            "total mast (heel → masthead)": f"{spec.total_length:.3f} m",
            "sail track (wing, root → masthead)": f"{spec.sail_track_length:.3f} m",
            "section": f"constant 2.5:1 ellipse (t/c {AMAZON_TC})",
            "RM_max (his own)": f"{AMAZON_RM_NM / 1e3:.0f} kN·m",
            "factor of safety": f"{AMAZON_FOS}",
            "design moment": f"{AMAZON_DESIGN_MOMENT_NM / 1e3:.0f} kN·m / mast",
        },
        title="Sponberg PBB No.55 (1998) / SNAME 37(2) (2000)",
    )
    summary
    return (spec,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Live OML section — drag root → masthead
    """)
    return


@app.cell
def _(mo):
    z_frac = mo.ui.slider(
        start=0.0, stop=1.0, value=0.0, step=0.01, label="span fraction  z / sail-track"
    )
    z_frac
    return (z_frac,)


@app.cell
def _(plt, spec, z_frac):
    z_sel = z_frac.value * spec.sail_track_length
    oml = spec.section_oml(z_sel, n_pts=240)
    c_mm = spec.chord_at_z(z_sel) * 1e3
    t_mm = spec.thickness_at_z(z_sel) * 1e3

    fig, ax = plt.subplots(figsize=(7, 3))
    ax.fill(oml[:, 0], oml[:, 1], color="#3d7fb8", alpha=0.35, ec="k", lw=1.0)
    ax.set_aspect("equal")
    ax.grid(alpha=0.2)
    ax.set_title(
        f"OML section at z = {z_sel:.2f} m   —   chord {c_mm:.0f} × thick {t_mm:.0f} mm   "
        f"(t/c {t_mm / c_mm:.3f})"
    )
    ax.set_xlabel("chord X [m]")
    ax.set_ylabel("Y [m]")
    fig
    return


@app.cell
def _(AMAZON_STATIONS_MM, check, mo, spec, table):
    worst = 0.0
    rows = []
    for i, (cmm, tmm) in enumerate(AMAZON_STATIONS_MM):
        z = spec._station_fracs[i] * spec.sail_track_length
        c = spec.chord_at_z(z) * 1e3
        t = spec.thickness_at_z(z) * 1e3
        err = max(abs(c - cmm), abs(t - tmm))
        worst = max(worst, err)
        rows.append(
            [
                f"st{i}",
                f"{z:.2f}",
                f"{c:.1f} × {t:.1f}",
                f"{cmm:.1f} × {tmm:.1f}",
                f"{t / c:.3f}",
                f"{err:.3f}",
            ]
        )

    amz1_ok = worst <= 1.0
    fidelity_view = mo.vstack(
        [
            table(
                ["station", "z [m]", "chord × thick [mm]", "published [mm]", "t/c", "err [mm]"],
                rows,
                title="Station-table fidelity (R-AMZ-1)",
            ),
            check(
                "R-AMZ-1 station fidelity",
                amz1_ok,
                f"worst station error {worst:.3f} mm  ≤  1 mm requirement",
            ),
        ]
    )
    # R-AMZ-1 hard gate (the visible badge above mirrors this; a headless run
    # `python notebooks/01_amazon_mast.py` exits non-zero if it ever breaks):
    assert amz1_ok, "R-AMZ-1: station OML must match the published table within 1 mm"
    fidelity_view
    return


@app.cell
def _(kv, spec):
    upper, lower = spec.journal_stations
    journals = kv(
        {
            "deck-partners (upper journal)": f"z = {upper:.2f} m, OD {spec.deck_od * 1e3:.0f} mm",
            "heel (lower journal)": f"z = {lower:.2f} m, OD {spec.heel_od * 1e3:.0f} mm",
            "bury (bearing-couple arm)": (
                f"{spec.bury:.2f} m  ({100 * spec.bury / spec.total_length:.1f}% of mast)"
            ),
        },
        title="Journal stations",
    )
    journals
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Build + export the lofted OML solid  (R-AMZ-6, Article XI)

    Lofting the solid and writing CAD is a deliberate **milestone export** with a
    disk side-effect, so it is gated behind the button (and keeps this notebook
    instant to open / smoke-test). Press it to loft `build_amazon_mast_solid`,
    check validity, and write `exports/amazon_mast.{stl,step}`.
    """)
    return


@app.cell
def _(mo):
    build_btn = mo.ui.run_button(label="🔧 Build solid + export STL / STEP")
    build_btn
    return (build_btn,)


@app.cell
def _(
    Path,
    build_amazon_mast_solid,
    build_btn,
    check,
    export_step,
    export_stl,
    mo,
    spec,
    stamp,
    time,
):
    mo.stop(
        not build_btn.value,
        mo.md(
            "ℹ️ Press **🔧 Build solid + export STL / STEP** above to loft the OML "
            "solid (R-AMZ-6, Article XI) and write `exports/amazon_mast.{stl,step}`."
        ),
    )
    t0 = time.perf_counter()
    solid = build_amazon_mast_solid(spec)
    amz6_ok = solid.is_valid
    out_dir = Path(mo.notebook_dir()).parent / "exports"
    out_dir.mkdir(exist_ok=True)
    export_stl(solid, str(out_dir / "amazon_mast.stl"))
    export_step(solid, str(out_dir / "amazon_mast.step"))
    build_secs = time.perf_counter() - t0

    build_view = mo.vstack(
        [
            check(
                "R-AMZ-6 solid valid",
                amz6_ok,
                f"OML volume {solid.volume:.3f} m³ — wrote `exports/amazon_mast.{{stl,step}}`",
            ),
            stamp("build + export (STL + STEP)", build_secs),
        ]
    )
    assert amz6_ok, "R-AMZ-6: lofted Amazon mast solid must be valid"
    build_view
    return


if __name__ == "__main__":
    app.run()
