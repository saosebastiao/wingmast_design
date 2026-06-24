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

    from wingmast_design.geometry.amazon_mast import (
        AMAZON_DESIGN_MOMENT_NM,
        AMAZON_RM_NM,
        AmazonMastSpec,
    )
    from wingmast_design.structural.amazon_sizing import (
        AmazonSizingParams,
        amazon_mass_band,
        estimate_amazon_mast_mass,
        size_wall_at_z,
    )
    from wingmast_design.viz import kv, stamp, table

    return (
        AMAZON_DESIGN_MOMENT_NM,
        AMAZON_RM_NM,
        AmazonMastSpec,
        AmazonSizingParams,
        amazon_mass_band,
        estimate_amazon_mast_mass,
        kv,
        mo,
        plt,
        size_wall_at_z,
        stamp,
        table,
        time,
    )


@app.cell
def _(mo):
    mo.md(r"""
    # 02 · Project-Amazon as-built mast mass estimate  (R-AMZ-3)

    Interactive view of `examples/02_amazon_mass_estimate.py` *(run the script for
    the headless measurement record: `just example 02_amazon_mass_estimate`)*.

    Reproduces Amazon **as Sponberg built and sized it** — a **carbon box spar**
    (the primary structure) inside the frozen 2.5:1 ellipse OML with bonded glass
    LE/TE fairings as non-structural mass — and his **own sizing rules**:

    * load = the boat's **max righting moment × FoS** (design = 2.5 × 251 ≈
      627 kN·m/mast), spread constant partners→gooseneck then tapered to zero at
      the masthead and heel (`D-AMZ-3`);
    * at each station wall = the governing **max** of the **strength** wall
      (M / σ_allow) and Sponberg's **section-shape buckling floor** (t ≥ 0.03·panel);
    * the heeling moment bends the mast in the **thickness** (weak) direction.

    This is the mass figure his papers never published — a first-order analytical
    estimate with a sensitivity band, an **FEA** deflection check, and a
    closed-form local-buckling margin. It is an *estimate*, not a hard requirement,
    so there is no `R-AMZ` assert here — only narration + a measured wall-clock stamp.
    """)
    return


@app.cell
def _(AMAZON_DESIGN_MOMENT_NM, AMAZON_RM_NM, AmazonMastSpec, kv):
    spec = AmazonMastSpec()
    load_summary = kv(
        {
            "RM_max (boat, per mast)": f"{AMAZON_RM_NM / 1e3:.0f} kN·m",
            "factor of safety": "2.5",
            "design moment": f"{AMAZON_DESIGN_MOMENT_NM / 1e3:.0f} kN·m / mast",
            "wall law": "max(strength, Sponberg t/0.03·panel buckling floor), tapered",
        },
        title="Load chain (Sponberg PBB No.55 / SNAME 37(2))",
    )
    load_summary
    return (spec,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Controls — the flagged, swept sizing inputs (`D-AMZ-3..6`)

    Defaults reproduce the source script's fixed `AmazonSizingParams()` exactly, so
    the notebook-at-defaults equals the script. Drag to explore the sensitivity.
    """)
    return


@app.cell
def _(mo):
    sl_box_chord = mo.ui.slider(
        start=0.40, stop=0.80, value=0.60, step=0.01, label="box width / chord", show_value=True
    )
    sl_box_thick = mo.ui.slider(
        start=0.50, stop=0.85, value=0.70, step=0.01, label="box height / thickness", show_value=True
    )
    sl_sigma = mo.ui.slider(
        start=300.0, stop=900.0, value=600.0, step=10.0,
        label="σ_allow [MPa] (axial compressive)", show_value=True,
    )
    sl_buckle = mo.ui.slider(
        start=0.020, stop=0.045, value=0.030, step=0.001,
        label="t/panel buckling floor", show_value=True,
    )
    sl_rho = mo.ui.slider(
        start=1400.0, stop=1800.0, value=1600.0, step=10.0,
        label="ρ carbon [kg/m³]", show_value=True,
    )
    sl_fairing = mo.ui.slider(
        start=0.10, stop=0.50, value=0.25, step=0.01,
        label="fairing mass frac (of box)", show_value=True,
    )
    sl_fos = mo.ui.slider(
        start=2.0, stop=3.0, value=2.5, step=0.1, label="factor of safety", show_value=True
    )
    controls = mo.vstack(
        [sl_box_chord, sl_box_thick, sl_sigma, sl_buckle, sl_rho, sl_fairing, sl_fos]
    )
    controls
    return (
        sl_box_chord,
        sl_box_thick,
        sl_buckle,
        sl_fairing,
        sl_fos,
        sl_rho,
        sl_sigma,
    )


@app.cell
def _(
    AmazonSizingParams,
    sl_box_chord,
    sl_box_thick,
    sl_buckle,
    sl_fairing,
    sl_fos,
    sl_rho,
    sl_sigma,
):
    params = AmazonSizingParams(
        box_frac_chord=sl_box_chord.value,
        box_frac_thick=sl_box_thick.value,
        sigma_allow_Pa=sl_sigma.value * 1e6,
        buckle_t_over_panel=sl_buckle.value,
        rho_carbon=sl_rho.value,
        fairing_mass_frac=sl_fairing.value,
        fos=sl_fos.value,
    )
    return (params,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Wall thickness vs height — Sponberg's tapered wall law
    """)
    return


@app.cell
def _(params, size_wall_at_z, spec, table):
    wall_rows = []
    for _z in (0.0, 7.31, 14.63, 21.0):
        _t, _gov = size_wall_at_z(_z, spec, params)
        wall_rows.append([f"{_z:.2f}", f"{_t * 1e3:.1f}", _gov])
    wall_table = table(
        ["z [m]", "t_wall [mm]", "governing"],
        wall_rows,
        title="Wall vs height (size_wall_at_z)",
    )
    wall_table
    return


@app.cell
def _(params, plt, size_wall_at_z, spec):
    import numpy as np

    z_line = np.linspace(0.0, spec.sail_track_length, 80)
    t_line = np.array([size_wall_at_z(z, spec, params)[0] * 1e3 for z in z_line])
    fig_wall, ax_wall = plt.subplots(figsize=(7, 3))
    ax_wall.plot(z_line, t_line, color="#3d7fb8", lw=2.0)
    ax_wall.fill_between(z_line, 0, t_line, color="#3d7fb8", alpha=0.2)
    ax_wall.set_xlabel("height z above gooseneck [m]")
    ax_wall.set_ylabel("wall thickness [mm]")
    ax_wall.set_title("Sponberg tapered wall law along the wing")
    ax_wall.grid(alpha=0.2)
    fig_wall
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Central mass estimate — breakdown + verification
    """)
    return


@app.cell
def _(estimate_amazon_mast_mass, kv, params, spec):
    r = estimate_amazon_mast_mass(spec, params)
    gov_str = ", ".join(f"{k} {v * 100:.0f}%" for k, v in r.governing_fracs.items())
    mass_breakdown = kv(
        {
            "carbon box (wing)": f"{r.carbon_box_kg:.0f} kg",
            "round stock": f"{r.stock_kg:.0f} kg",
            "glass fairings": f"{r.fairing_kg:.0f} kg",
            "PER MAST": f"{r.mass_per_mast_kg:.0f} kg",
            "BOTH MASTS": f"{r.mass_both_masts_kg:.0f} kg",
            "root wall": f"{r.root_wall_mm:.1f} mm  (vs Sponberg's ~12.7 mm box annotation)",
            "governing": gov_str,
            "FEA tip deflection": (
                f"{r.tip_defl_m:.2f} m ({r.tip_defl_pct_height:.0f}% of height) at RM_max "
                "— intentionally flexible, not a sizing constraint in his method"
            ),
            "local buckling λ": f"{r.min_local_buckling_lambda:.2f} at operating load (t/ID floor reserve)",
        },
        title="MASS ESTIMATE (central)",
    )
    mass_breakdown
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Sensitivity band — low / central / high (both masts)

    `amazon_mass_band` sweeps the flagged inputs (box fill, σ_allow, fairing, bury)
    independently of the sliders above, so it always shows the published band.
    """)
    return


@app.cell
def _(amazon_mass_band, mo, spec, stamp, table, time):
    _t0 = time.perf_counter()
    band = amazon_mass_band(spec)  # depends only on spec → computed once, not on slider drag
    band_secs = time.perf_counter() - _t0
    band_rows = []
    for _k in ("low", "central", "high"):
        _b = band[_k]
        band_rows.append(
            [
                _k,
                f"{_b.mass_both_masts_kg:.0f}",
                f"{_b.mass_per_mast_kg:.0f}",
                f"{_b.root_wall_mm:.1f}",
                f"{_b.min_local_buckling_lambda:.2f}",
            ]
        )
    band_table = table(
        ["case", "both masts [kg]", "per mast [kg]", "root wall [mm]", "λ"],
        band_rows,
        title="SENSITIVITY BAND (both masts)",
    )
    mo.vstack(
        [
            band_table,
            stamp(
                "sensitivity-band compute (low/central/high, incl. FEA + buckling)", band_secs
            ),
        ]
    )
    return (band,)


@app.cell
def _(band, plt):
    _cases = ["low", "central", "high"]
    _vals = [band[k].mass_both_masts_kg for k in _cases]
    fig, ax = plt.subplots(figsize=(6, 3.5))
    _bars = ax.bar(_cases, _vals, color=["#7fb83d", "#3d7fb8", "#b8543d"], alpha=0.8, ec="k")
    ax.bar_label(_bars, fmt="%.0f kg", padding=3)
    ax.set_ylabel("both masts [kg]")
    ax.set_title("Amazon two-mast mass — sensitivity band")
    ax.grid(alpha=0.2, axis="y")
    ax.set_ylim(0, max(_vals) * 1.15)
    fig
    return


@app.cell
def _(band, mo):
    lo = band["low"].mass_both_masts_kg
    hi = band["high"].mass_both_masts_kg
    central = band["central"]
    estimate_view = mo.vstack(
        [
            mo.md(
                f"**ESTIMATE:** Amazon's two masts ≈ **{central.mass_both_masts_kg:.0f} kg** "
                f"(band {lo:.0f}–{hi:.0f} kg); ~{central.mass_per_mast_kg:.0f} kg/mast."
            ),
            mo.md(
                f"Root wall **{central.root_wall_mm:.1f} mm** cross-validates Sponberg's "
                "drawing annotation of a **~12.7 mm box** — within ~1 mm, the buckling "
                "floor governing the section (consistent with his t/ID≥0.03 rule)."
            ),
        ]
    )
    estimate_view
    return


if __name__ == "__main__":
    app.run()
