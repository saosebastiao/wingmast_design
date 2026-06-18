"""Optimize the project-method Amazon mast to beat Sponberg (Phase X4, `R-AMZ-5`).

Minimises per-mast mass over the **internal** section geometry only (box chord/depth fractions,
FW shell + web walls), per spar count n ∈ {3, 4, 5} — the external OML stays **frozen** (`D-AMZ-1`).
The inner cap-wall sizer (`amazon_myway`) keeps every design feasible (cap + shell strength, the
0.03·cell-panel buckling floor); the optimizer trades the levers X3 exposed — chiefly a thicker
near-0° FW shell at the extreme fibre vs the inner box caps, and the spar count vs web mass —
subject to manufacturability (`check_fit`). The optimum is then **buckling-verified** with a
closed-form orthotropic cap/shell panel check at the operating load.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np
from scipy.optimize import differential_evolution

from ..geometry.amazon_mast import AmazonMastSpec
from .amazon_myway import (
    MyWayParams,
    MyWayMassResult,
    estimate_myway_mass,
    myway_fit,
    myway_tip_deflection,
)

# design vector: [box_frac_chord, box_frac_thick, t_shell, t_web, shell_helix_deg, cap_f0]
_BOUNDS = [(0.40, 0.68), (0.50, 0.92), (0.002, 0.016), (0.003, 0.008), (4.0, 18.0), (0.55, 0.80)]


def _params(x: np.ndarray, n_spars: int, base: MyWayParams) -> MyWayParams:
    f0 = float(x[5])
    off = 0.5 * (1.0 - f0)                                    # balance ±45 / 90 in the cap
    return replace(base, n_spars=n_spars, box_frac_chord=float(x[0]), box_frac_thick=float(x[1]),
                   t_shell=float(x[2]), t_web=float(x[3]), shell_helix_deg=float(x[4]),
                   layup_f0=f0, layup_f45=off, layup_f90=off)


def _objective(x: np.ndarray, spec: AmazonMastSpec, n_spars: int, base: MyWayParams,
               defl_cap_m: float | None) -> float:
    # NOTE: `check_fit` is NOT called here — the OML-following box_spar partition is independent
    # of the box-fraction DVs, so manufacturability is constant across the search for a fixed
    # (n_spars, walls). It is verified ONCE on the optimum in `optimize_myway`. This keeps each
    # eval cheap. Strength + cap-buckling are met by the inner sizer; deflection is an OPTIONAL cap.
    p = _params(x, n_spars, base)
    r = estimate_myway_mass(spec, p)
    if not r.feasible:
        return 1e4 + 1e3 * (r.max_cap_util + r.max_shell_util)     # strength/buckling infeasible
    if defl_cap_m is not None:
        d, _ = myway_tip_deflection(spec, p)
        if d > defl_cap_m:
            return 1e4 + 1e3 * (d - defl_cap_m)                    # stiffness-matched constraint
    return r.mass_per_mast_kg


@dataclass(frozen=True)
class BeatResult:
    n_spars: int
    params: MyWayParams
    mass_per_mast_kg: float
    mass_both_masts_kg: float
    vs_amazon_pct: float
    min_panel_buckling_lambda: float
    tip_defl_m: float
    tip_defl_pct: float
    fit_margin_mm: float
    result: MyWayMassResult


def optimize_myway(spec: AmazonMastSpec, n_spars: int, amazon_per_mast_kg: float,
                   base: MyWayParams | None = None, *, seed: int = 0, defl_cap_m: float | None = None,
                   maxiter: int = 40, popsize: int = 12, workers: int = 1) -> BeatResult:
    """Differential-evolution minimisation of per-mast mass for a fixed spar count. Strength +
    cap-buckling (λ ≥ 1.5) are met by the inner sizer; ``defl_cap_m`` optionally caps deflection.
    DV = [box_frac_chord, box_frac_thick, t_shell, t_web, shell_helix_deg, cap_f0]."""
    base = base or MyWayParams()
    opt = differential_evolution(
        _objective, _BOUNDS, args=(spec, n_spars, base, defl_cap_m), seed=seed, tol=1e-5,
        maxiter=maxiter, popsize=popsize, polish=True, init="sobol", workers=workers, updating=
        ("deferred" if workers != 1 else "immediate"),
    )
    p = _params(opt.x, n_spars, base)
    r = estimate_myway_mass(spec, p, amazon_per_mast_kg=amazon_per_mast_kg)
    fit = myway_fit(spec, p)
    d, dpct = myway_tip_deflection(spec, p)
    return BeatResult(
        n_spars=n_spars, params=p, mass_per_mast_kg=r.mass_per_mast_kg,
        mass_both_masts_kg=r.mass_both_masts_kg, vs_amazon_pct=r.vs_amazon_pct or 0.0,
        min_panel_buckling_lambda=r.min_buckle_lambda, tip_defl_m=d, tip_defl_pct=dpct,
        fit_margin_mm=fit.margin * 1e3, result=r,
    )


def optimize_amazon_beat(spec: AmazonMastSpec | None = None, amazon_per_mast_kg: float = 646.0,
                         *, spar_counts=(3, 4, 5), seed: int = 0, defl_cap_m: float | None = None,
                         maxiter: int = 40, popsize: int = 12, workers: int = 1
                         ) -> tuple[BeatResult, list[BeatResult]]:
    """Optimize each spar count and return (best, all) — the headline X4 result."""
    spec = spec or AmazonMastSpec()
    runs = [optimize_myway(spec, n, amazon_per_mast_kg, seed=seed, defl_cap_m=defl_cap_m,
                           maxiter=maxiter, popsize=popsize, workers=workers) for n in spar_counts]
    best = min(runs, key=lambda r: r.mass_per_mast_kg)
    return best, runs
