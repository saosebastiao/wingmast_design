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
    from wingmast_design.structural.amazon_eigen import verify_cap_panel_eigen
    from wingmast_design.structural.amazon_myway import MyWayParams
    from wingmast_design.viz import check, kv, stamp, table

    return (
        AmazonMastSpec,
        MyWayParams,
        check,
        kv,
        mo,
        plt,
        stamp,
        table,
        time,
        verify_cap_panel_eigen,
    )


@app.cell
def _(mo):
    mo.md(r"""
    # 05 · Eigen-verify the governing cap-panel buckling  (R-AMZ-5, Article III)

    Interactive view of `examples/05_amazon_eigen_verify.py` *(run the script for
    the headless measurement record: `just example 05_amazon_eigen_verify`)*.

    **Phase X4 closure.** The mass-optimal project-method Amazon mast is sized so
    its **cap-panel** orthotropic buckling λ = 1.5 (the governing local mode). This
    closes Article III with TWO independent eigen checks of that governing station:

    * the **EXACT analytical** orthotropic simply-supported plate eigenvalue
      (`σ_cr = 2π²·K·(t/b)²` *is* the exact eigenvalue of `sin(mπx/a)·sin(πy/b)`) —
      confirms the closed form the sizer used to the digit;
    * an independent **converged-mesh shell-FEA** eigen (laminate DKT+CST element +
      membrane-stress geometric stiffness + dense Cholesky `linear_buckling`).

    **Article III in action:** the FEA's *linear-w* geometric stiffness is
    **unconservatively overstiff** (~20 %) for the high-D11/D22 cap panel — exactly
    the "coarse eigen is unconservatively overstiff" failure mode the Article warns
    about, here in the Kσ formulation. So feasibility is judged on the
    **conservative exact/closed-form floor (λ = 1.5)**, with the FEA confirming only
    *more* margin, never less.
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## The optimized design  (X4 mass-optimal: 3 spars, narrow-deep box, near-0° shell)

    The five knobs below default to the X4 mass-optimal `MyWayParams`
    (`n_cells=3, box_frac_chord=0.45, box_frac_thick=0.88, t_shell=0.0025,
    t_web=0.003`) — so the notebook at defaults reproduces the script exactly.
    """)
    return


@app.cell
def _(mo):
    n_cells = mo.ui.slider(start=2, stop=6, value=3, step=1, label="n_cells")
    box_frac_chord = mo.ui.slider(
        start=0.30, stop=0.70, value=0.45, step=0.01, label="box_frac_chord"
    )
    box_frac_thick = mo.ui.slider(
        start=0.50, stop=0.95, value=0.88, step=0.01, label="box_frac_thick"
    )
    t_shell = mo.ui.number(
        start=0.0010, stop=0.0060, value=0.0025, step=0.0001, label="t_shell [m]"
    )
    t_web = mo.ui.number(
        start=0.0010, stop=0.0060, value=0.0030, step=0.0001, label="t_web [m]"
    )
    mo.vstack([n_cells, box_frac_chord, box_frac_thick, t_shell, t_web])
    return box_frac_chord, box_frac_thick, n_cells, t_shell, t_web


@app.cell
def _(
    AmazonMastSpec,
    MyWayParams,
    box_frac_chord,
    box_frac_thick,
    kv,
    n_cells,
    t_shell,
    t_web,
):
    spec = AmazonMastSpec()
    opt = MyWayParams(
        n_cells=int(n_cells.value),
        box_frac_chord=float(box_frac_chord.value),
        box_frac_thick=float(box_frac_thick.value),
        t_shell=float(t_shell.value),
        t_web=float(t_web.value),
    )
    design_view = kv(
        {
            "n_cells (filament-wound spars)": f"{opt.n_cells}",
            "box_frac_chord (box width / chord)": f"{opt.box_frac_chord:.2f}",
            "box_frac_thick (box depth / thickness)": f"{opt.box_frac_thick:.2f}",
            "t_shell (FW outer shell)": f"{opt.t_shell * 1e3:.1f} mm",
            "t_web (FW web wall)": f"{opt.t_web * 1e3:.1f} mm",
            "buckling SF target (λ ≥)": f"{opt.buckle_sf}",
        },
        title="Chosen project-method design (X4 mass-optimal at defaults)",
    )
    design_view
    return opt, spec


@app.cell
def _(mo):
    mo.md(r"""
    ## Run the converged-mesh eigen verification

    The converged-mesh shell-FEA eigen sweep (ny = 8 → 24 across the panel) is a
    **measured ~2 s, ~1.4 GB** job, so it is gated behind the button — slider edits
    above re-derive the design instantly without re-firing the FEA. Press it to run
    `verify_cap_panel_eigen(spec, opt)`.
    """)
    return


@app.cell
def _(mo):
    run_btn = mo.ui.run_button(label="🔬 Run eigen verification (converged-mesh FEA)")
    run_btn
    return (run_btn,)


@app.cell
def _(mo, opt, run_btn, spec, time, verify_cap_panel_eigen):
    mo.stop(
        not run_btn.value,
        mo.md(
            "ℹ️ Press **🔬 Run eigen verification (converged-mesh FEA)** above to "
            "eigen-verify the governing cap panel (R-AMZ-5, Article III)."
        ),
    )
    t0 = time.perf_counter()
    r = verify_cap_panel_eigen(spec, opt)
    verify_secs = time.perf_counter() - t0
    return r, verify_secs


@app.cell
def _(kv, r):
    station_view = kv(
        {
            "governing station z": f"{r.z_station:.1f} m",
            "cell width (cap buckling panel)": f"{r.cell_width_m * 1e3:.0f} mm",
            "cap wall": f"{r.cap_wall_mm:.1f} mm",
            "operating stress": f"{r.sigma_op_MPa:.0f} MPa",
            "critical aspect a/b": f"{r.aspect:.2f}",
        },
        title="Governing cap panel (binding station, min closed-form λ)",
    )
    station_view
    return


@app.cell
def _(kv, r):
    eigen_view = kv(
        {
            "closed-form λ (used by the sizer)": f"{r.closed_form_lambda:.3f}",
            "EXACT analytical SS-plate eigen λ": (
                f"{r.exact_analytical_lambda:.3f}  ← confirms the closed form to "
                "the digit (it IS the exact eigenvalue)"
            ),
            "converged-mesh shell-FEA eigen λ": (
                f"{r.fea_lambda_converged:.3f}  (+{r.fea_overstiff_pct:.0f} % — the "
                "linear-w Kσ is unconservatively overstiff here)"
            ),
        },
        title="Closed-form vs EXACT analytical vs converged FEA",
    )
    eigen_view
    return


@app.cell
def _(r, table):
    conv_rows = [[f"{ny}", f"{lam:.3f}"] for ny, lam in r.convergence]
    conv_table = table(
        ["ny across panel", "λ"],
        conv_rows,
        title="Shell-FEA mesh convergence (ny → λ)",
    )
    conv_table
    return


@app.cell
def _(plt, r):
    nys = [ny for ny, _ in r.convergence]
    lams = [lam for _, lam in r.convergence]

    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.plot(nys, lams, "o-", color="#3d7fb8", lw=1.5, label="shell-FEA eigen λ")
    ax.axhline(
        1.5,
        color="#b8443d",
        ls="--",
        lw=1.2,
        label="exact floor λ = 1.5 (feasibility)",
    )
    ax.axhline(
        r.exact_analytical_lambda,
        color="#3da06b",
        ls=":",
        lw=1.0,
        label=f"exact analytical λ = {r.exact_analytical_lambda:.2f}",
    )
    ax.set_xlabel("ny across panel (mesh density)")
    ax.set_ylabel("buckling multiplier λ")
    ax.set_title("Converged-mesh FEA eigen vs the conservative exact floor")
    ax.grid(alpha=0.2)
    ax.legend(fontsize=8)
    fig
    return


@app.cell
def _(check, mo, r, stamp, verify_secs):
    verdict_view = mo.vstack(
        [
            check(
                "R-AMZ-5 / Article III buckling-feasible",
                r.feasible,
                f"conservative exact floor λ = {r.exact_analytical_lambda:.2f} ≥ 1.5 "
                f"(FEA λ = {r.fea_lambda_converged:.2f} confirms only more margin)",
            ),
            stamp("eigen verification (converged-mesh shell-FEA)", verify_secs),
        ]
    )
    verdict_view
    return


if __name__ == "__main__":
    app.run()
