import marimo

__generated_with = "0.23.10"
app = marimo.App(width="medium")


@app.cell
def _():
    import time

    import marimo as mo
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from wingmast_design.geometry.amazon_mast import AmazonMastSpec
    from wingmast_design.structural.amazon_myway import (
        MyWayParams,
        estimate_myway_mass,
        myway_fit,
        myway_section,
    )
    from wingmast_design.structural.amazon_sizing import estimate_amazon_mast_mass
    from wingmast_design.viz import check, kv, stamp, table

    return (
        AmazonMastSpec,
        MyWayParams,
        check,
        estimate_amazon_mast_mass,
        estimate_myway_mass,
        kv,
        mo,
        myway_fit,
        myway_section,
        plt,
        stamp,
        table,
        time,
    )


@app.cell
def _(mo):
    mo.md(r"""
    # 03 · Rebuild the Amazon OML the project way  (R-AMZ-4)

    Interactive view of `examples/03_amazon_myway_build.py` *(run the script for
    the headless measurement record: `just example 03_amazon_myway_build`)*.

    Same frozen 2.5:1 ellipse, same Amazon loads/criteria — but built **this
    project's way**: *N* filament-wound cells across the chord + co-bonded UD
    channel longerons in the inter-cell voids + a filament-wound outer shell.

    The structural thesis vs Sponberg's single box + glass fairings: **closer
    webs ⇒ smaller cap panels**, so the multi-spar wall drops OFF Amazon's
    buckling floor (13.5 mm) onto the much lower **strength** requirement; the
    structural **FW shell** sits at the extreme fibre and lets the caps be
    thinner; the **UD longerons** add 0° bending material in the channels for
    free. This confirms manufacturability (`check_fit`, **R-AMZ-4**) and reports
    the first-order mass of each spar-count vs the X2 his-construction estimate.
    (X4 then optimizes the internal distribution to minimise mass.)
    """)
    return


@app.cell
def _(AmazonMastSpec, MyWayParams, estimate_amazon_mast_mass, kv):
    spec = AmazonMastSpec()
    amz = estimate_amazon_mast_mass(spec)
    E_cap, E_shell = MyWayParams().moduli()

    baseline = kv(
        {
            "baseline (Sponberg single box + glass fairings, X2)": (
                f"{amz.mass_per_mast_kg:.0f} kg/mast"
            ),
            "cap laminate (laid 0/±45/90)": f"0° cap {E_cap / 1e9:.0f} GPa",
            "shell laminate (helical FW)": f"{E_shell / 1e9:.0f} GPa",
        },
        title="Project-method laminates vs the his-construction baseline",
    )
    baseline
    return amz, spec


@app.cell
def _(mo):
    mo.md(r"""
    ## Controls — spar-count set + the X3 internal design knobs

    The dropdown picks which spar counts to compare; defaults `{3, 4}` reproduce
    the script's 3-vs-4 comparison. The sliders are the `MyWayParams` internal
    knobs (box fraction of chord / thickness, FW shell wall, FW web wall) — their
    **defaults equal the dataclass defaults**, so the notebook-at-defaults equals
    the script.
    """)
    return


@app.cell
def _(mo):
    n_set = mo.ui.dropdown(
        options={"3 vs 4 (script)": "3,4", "3, 4, 5": "3,4,5"},
        value="3 vs 4 (script)",
        label="spar counts to compare",
    )
    box_frac_chord = mo.ui.slider(
        start=0.45, stop=0.75, value=0.60, step=0.01, label="box_frac_chord"
    )
    box_frac_thick = mo.ui.slider(
        start=0.50, stop=0.80, value=0.70, step=0.01, label="box_frac_thick"
    )
    t_shell = mo.ui.slider(
        start=0.002, stop=0.006, value=0.003, step=0.0005, label="t_shell [m]"
    )
    t_web = mo.ui.slider(
        start=0.002, stop=0.008, value=0.004, step=0.0005, label="t_web [m]"
    )
    controls = mo.vstack([n_set, box_frac_chord, box_frac_thick, t_shell, t_web])
    controls
    return box_frac_chord, box_frac_thick, n_set, t_shell, t_web


@app.cell
def _(
    MyWayParams,
    amz,
    box_frac_chord,
    box_frac_thick,
    check,
    estimate_myway_mass,
    mo,
    myway_fit,
    myway_section,
    n_set,
    spec,
    t_shell,
    t_web,
    table,
):
    n_list = [int(x) for x in n_set.value.split(",")]

    cmp_rows = []
    fit_results = []
    best = None
    for n in n_list:
        p = MyWayParams(
            n_cells=n,
            box_frac_chord=box_frac_chord.value,
            box_frac_thick=box_frac_thick.value,
            t_shell=t_shell.value,
            t_web=t_web.value,
        )
        fit = myway_fit(spec, p)
        t_root, _, gov = myway_section(0.0, spec, p)
        r = estimate_myway_mass(spec, p, amazon_per_mast_kg=amz.mass_per_mast_kg)
        fit_results.append((n, fit))
        gov_str = ", ".join(f"{k} {v:.2f}" for k, v in r.governing_fracs.items())
        cmp_rows.append(
            [
                f"{n}",
                "YES" if fit.feasible else "NO",
                f"{fit.margin * 1e3:.0f}",
                f"{t_root * 1e3:.1f} ({gov})",
                f"{r.mass_per_mast_kg:.0f} / {r.mass_both_masts_kg:.0f}",
                f"{r.wing_kg:.0f} + {r.stock_kg:.0f}",
                "YES" if r.feasible else "NO",
                f"{r.max_cap_util:.2f} / {r.max_shell_util:.2f}",
                gov_str,
                f"{r.vs_amazon_pct:+.1f}%",
            ]
        )
        if r.feasible and (best is None or r.mass_per_mast_kg < best[1]):
            best = (n, r.mass_per_mast_kg, r.vs_amazon_pct)

    all_manufacturable = all(fit.feasible for _, fit in fit_results)
    detail = "; ".join(
        f"{n}-spar margin {fit.margin * 1e3:.0f} mm" for n, fit in fit_results
    )

    cmp_view = mo.vstack(
        [
            table(
                [
                    "n cells",
                    "manuf.",
                    "fit margin [mm]",
                    "root cap wall [mm] (gov)",
                    "mass/mast / both [kg]",
                    "= wing + stock [kg]",
                    "feasible",
                    "cap / shell util",
                    "governing fracs",
                    "vs Amazon",
                ],
                cmp_rows,
                title="Project-method build — 3 vs 4 cells (vs Amazon's 13.5 mm buckling-floor)",
            ),
            check(
                "R-AMZ-4 each compared spar-count is manufacturable",
                all_manufacturable,
                detail,
            ),
        ]
    )
    # R-AMZ-4 hard gate (the visible badge mirrors this; a headless run
    # `python notebooks/03_amazon_myway_build.py` exits non-zero if it breaks):
    for _n, _fit in fit_results:
        assert _fit.feasible, f"R-AMZ-4: {_n}-spar build must be manufacturable"
    assert best is not None, "at least one spar count must be feasible"
    cmp_view
    return best, n_list


@app.cell
def _(best, kv):
    n_b, m_b, pct_b = best
    verdict = kv(
        {
            "best first-order": (
                f"{n_b} cells → {m_b:.0f} kg/mast ({pct_b:+.1f}% vs Sponberg)"
            ),
            "both masts": f"{2 * m_b:.0f} kg",
            "next step": (
                "X4 optimizes the wall/cap/shell/longeron distribution to push further."
            ),
        },
        title="BEST feasible spar count",
    )
    verdict
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Mass per mast by spar count — Amazon baseline as reference line
    """)
    return


@app.cell
def _(
    MyWayParams,
    amz,
    box_frac_chord,
    box_frac_thick,
    estimate_myway_mass,
    n_list,
    plt,
    spec,
    t_shell,
    t_web,
    time,
):
    t0 = time.perf_counter()
    masses = []
    for _n in n_list:
        _p = MyWayParams(
            n_cells=_n,
            box_frac_chord=box_frac_chord.value,
            box_frac_thick=box_frac_thick.value,
            t_shell=t_shell.value,
            t_web=t_web.value,
        )
        _r = estimate_myway_mass(spec, _p, amazon_per_mast_kg=amz.mass_per_mast_kg)
        masses.append(_r.mass_per_mast_kg)
    plot_secs = time.perf_counter() - t0

    fig, ax = plt.subplots(figsize=(7, 3.5))
    xs = [str(_n) for _n in n_list]
    bars = ax.bar(xs, masses, color="#3d7fb8", alpha=0.85, ec="k")
    ax.axhline(
        amz.mass_per_mast_kg,
        color="#b8433d",
        ls="--",
        lw=1.5,
        label=f"Amazon baseline {amz.mass_per_mast_kg:.0f} kg",
    )
    for b, m in zip(bars, masses):
        ax.text(
            b.get_x() + b.get_width() / 2,
            m,
            f"{m:.0f}",
            ha="center",
            va="bottom",
            fontsize=9,
        )
    ax.set_xlabel("spar count (n cells)")
    ax.set_ylabel("mass per mast [kg]")
    ax.set_title("Project-method mass/mast vs Sponberg's single-box baseline")
    ax.legend()
    ax.grid(alpha=0.2, axis="y")
    fig
    return (plot_secs,)


@app.cell
def _(plot_secs, stamp):
    stamp("3 vs 4 cell mass sweep", plot_secs)
    return


if __name__ == "__main__":
    app.run()
