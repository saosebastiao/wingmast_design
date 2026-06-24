import marimo

__generated_with = "0.23.10"
app = marimo.App(width="medium")


@app.cell
def _():
    import time

    import marimo as mo
    import matplotlib

    matplotlib.use("Agg")

    from wingmast_design.geometry.amazon_mast import AmazonMastSpec
    from wingmast_design.structural.amazon_optimize import optimize_amazon_beat
    from wingmast_design.structural.amazon_sizing import estimate_amazon_mast_mass
    from wingmast_design.viz import check, kv, stamp, table

    return (
        AmazonMastSpec,
        check,
        estimate_amazon_mast_mass,
        kv,
        mo,
        optimize_amazon_beat,
        stamp,
        table,
        time,
    )


@app.cell
def _(mo):
    mo.md(r"""
    # 04 · Beat Sponberg — FEA-in-the-loop min-mass (R-AMZ-5)

    Interactive view of `examples/04_amazon_beat.py` *(run the script for the
    headless measurement record: `just example 04_amazon_beat`)*.

    **Phase X4.** FEA-in-the-loop min-mass optimization over the **INTERNAL**
    section geometry only — box chord/depth fractions, FW shell + web walls, cap
    layup, spar count ∈ {3, 4, 5} — with the external **Amazon OML frozen**
    (`D-AMZ-1`). At Amazon's own loads/criteria (strength + orthotropic cap-panel
    buckling λ ≥ 1.5). Two points are reported so the win is shown both ways:

    - **(A)** mass-optimal at Amazon's criteria (no deflection cap);
    - **(B)** stiffness-matched (also deflection ≤ Amazon's).

    The headline is the full progression **Sponberg → my-method first-order →
    OPTIMIZED**. The optimization is differential evolution — slow, not in CI —
    so it is **gated behind a button** below.
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Sponberg baseline (X2) — the bar to beat

    `estimate_amazon_mast_mass` reproduces Amazon as Sponberg built it (cheap,
    reactive): per-mast mass, FEA deflection, and the closed-form local-buckling
    margin.
    """)
    return


@app.cell
def _(AmazonMastSpec, estimate_amazon_mast_mass, kv):
    spec = AmazonMastSpec()
    amz = estimate_amazon_mast_mass(spec)
    a_kg, a_defl = amz.mass_per_mast_kg, amz.tip_defl_m

    baseline = kv(
        {
            "Sponberg per-mast mass": f"{a_kg:.0f} kg/mast  (both {2 * a_kg:.0f} kg)",
            "tip deflection": f"{a_defl:.2f} m",
            "local-buckling margin λ": f"{amz.min_local_buckling_lambda:.2f}",
        },
        title="Sponberg (X2) baseline — internal DVs only, OML frozen",
    )
    baseline
    return a_defl, a_kg, spec


@app.cell
def _(mo):
    mo.md(r"""
    ## Optimization controls

    Defaults reproduce the source script exactly: **maxiter = 30**, **seed = 1**.
    Both runs call `optimize_amazon_beat(spec, amazon_per_mast_kg=a_kg,
    maxiter=…, seed=…)`; run (B) additionally passes `defl_cap_m=amz.tip_defl_m`.
    """)
    return


@app.cell
def _(mo):
    maxiter = mo.ui.slider(
        start=5, stop=80, value=30, step=5, label="differential-evolution maxiter"
    )
    seed = mo.ui.number(start=0, stop=9999, value=1, step=1, label="RNG seed")
    mo.vstack([maxiter, seed])
    return maxiter, seed


@app.cell
def _(mo):
    mo.md(r"""
    ## Run the optimization  (R-AMZ-5, Article I)

    Differential evolution over three spar counts × two runs is **slow** — it is
    gated behind the button so the notebook stays instant to open / smoke-test.
    Press it to run (A) the mass-optimal search and (B) the stiffness-matched
    search, both timed with `time.perf_counter()`.
    """)
    return


@app.cell
def _(mo):
    run_btn = mo.ui.run_button(
        label="🚀 Run optimization (slow — differential evolution)"
    )
    run_btn
    return (run_btn,)


@app.cell
def _(
    a_defl,
    a_kg,
    maxiter,
    mo,
    optimize_amazon_beat,
    run_btn,
    seed,
    spec,
    time,
):
    mo.stop(
        not run_btn.value,
        mo.md(
            "ℹ️ Press **🚀 Run optimization** above to run the differential-"
            "evolution search (A: mass-optimal, B: stiffness-matched). Slow — "
            "not in CI."
        ),
    )
    t0 = time.perf_counter()
    bestA, runsA = optimize_amazon_beat(
        spec, amazon_per_mast_kg=a_kg, maxiter=maxiter.value, seed=int(seed.value)
    )
    bestB, runsB = optimize_amazon_beat(
        spec,
        amazon_per_mast_kg=a_kg,
        defl_cap_m=a_defl,
        maxiter=maxiter.value,
        seed=int(seed.value),
    )
    run_secs = time.perf_counter() - t0
    return bestA, bestB, run_secs, runsA, runsB


@app.cell
def _(bestA, runsA, table):
    rowsA = [
        [
            f"n={r.n_cells}",
            f"{r.mass_per_mast_kg:.0f}",
            f"{r.vs_amazon_pct:+.1f}",
            f"{r.min_panel_buckling_lambda:.2f}",
            f"{r.tip_defl_m:.2f}",
            f"{r.fit_margin_mm:.0f}",
        ]
        for r in runsA
    ]
    rowsA.append(
        [
            f"**BEST n={bestA.n_cells}**",
            f"**{bestA.mass_per_mast_kg:.0f}**",
            f"**{bestA.vs_amazon_pct:+.1f}**",
            f"{bestA.min_panel_buckling_lambda:.2f}",
            f"{bestA.tip_defl_m:.2f}",
            f"{bestA.fit_margin_mm:.0f}",
        ]
    )
    tableA = table(
        ["spars", "kg/mast", "vs Amazon %", "λ", "defl [m]", "fit [mm]"],
        rowsA,
        title="(A) mass-optimal — Amazon criteria (strength + cap-buckling λ≥1.5, no deflection cap)",
    )
    tableA
    return


@app.cell
def _(bestB, runsB, table):
    rowsB = [
        [
            f"n={r.n_cells}",
            f"{r.mass_per_mast_kg:.0f}",
            f"{r.vs_amazon_pct:+.1f}",
            f"{r.min_panel_buckling_lambda:.2f}",
            f"{r.tip_defl_m:.2f}",
        ]
        for r in runsB
    ]
    rowsB.append(
        [
            f"**BEST n={bestB.n_cells}**",
            f"**{bestB.mass_per_mast_kg:.0f}**",
            f"**{bestB.vs_amazon_pct:+.1f}**",
            f"{bestB.min_panel_buckling_lambda:.2f}",
            f"{bestB.tip_defl_m:.2f}",
        ]
    )
    tableB = table(
        ["spars", "kg/mast", "vs Amazon %", "λ", "defl [m]"],
        rowsB,
        title="(B) stiffness-matched — also deflection ≤ Amazon's",
    )
    tableB
    return


@app.cell
def _(a_kg, bestA, bestB, check, kv, mo, run_secs, stamp):
    p = bestA.params
    optimal = kv(
        {
            "spars (n_cells)": f"{p.n_cells}",
            "box": f"{p.box_frac_chord:.2f}c × {p.box_frac_thick:.2f}t",
            "FW shell wall": f"{p.t_shell * 1e3:.1f} mm",
            "FW web wall": f"{p.t_web * 1e3:.1f} mm",
            "BEST(A)": (
                f"{bestA.mass_per_mast_kg:.0f} kg/mast ({bestA.vs_amazon_pct:+.1f}%), "
                f"both {bestA.mass_both_masts_kg:.0f} kg"
            ),
            "BEST(B)": (
                f"{bestB.mass_per_mast_kg:.0f} kg/mast ({bestB.vs_amazon_pct:+.1f}%), "
                f"both {bestB.mass_both_masts_kg:.0f} kg, defl {bestB.tip_defl_m:.2f} m"
            ),
        },
        title="Optimal section (A)",
    )
    progression = kv(
        {
            "Sponberg (X2)": f"{a_kg:.0f} kg/mast",
            "my-method first-order (X3)": "~526 kg/mast",
            "OPTIMIZED (X4)": (
                f"{bestA.mass_per_mast_kg:.0f} kg/mast "
                f"({bestA.vs_amazon_pct:+.1f}% vs Sponberg)"
            ),
        },
        title="PROGRESSION  Sponberg → my-method first-order → OPTIMIZED",
    )

    amz5_ok = bestA.vs_amazon_pct < 0.0
    results_view = mo.vstack(
        [
            optimal,
            progression,
            check(
                "R-AMZ-5 beats Sponberg",
                amz5_ok,
                f"BEST(A) {bestA.mass_per_mast_kg:.0f} kg/mast at "
                f"{bestA.vs_amazon_pct:+.1f}%  (must be < 0 %)",
            ),
            stamp("optimization (A + B, differential evolution)", run_secs),
        ]
    )
    results_view
    return


if __name__ == "__main__":
    app.run()
