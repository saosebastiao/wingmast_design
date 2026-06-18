"""Phase-X4 — optimize the project-method Amazon mast to beat Sponberg (`R-AMZ-5`)."""
from __future__ import annotations

import numpy as np
import pytest

from wingmast_design.geometry.amazon_mast import AmazonMastSpec
from wingmast_design.structural.amazon_myway import (
    MyWayParams,
    estimate_myway_mass,
    myway_tip_deflection,
)
from wingmast_design.structural.amazon_sizing import estimate_amazon_mast_mass
from wingmast_design.structural.amazon_optimize import _objective, optimize_myway


def test_sizer_enforces_buckling_lambda():
    """Every sized design is cap-panel-buckling feasible (λ ≥ buckle_sf) — the X3-era geometric
    floor was insufficient; the orthotropic panel constraint is now enforced by the sizer."""
    spec = AmazonMastSpec()
    for n in (3, 4, 5):
        r = estimate_myway_mass(spec, MyWayParams(n_spars=n))
        assert r.feasible
        assert r.min_buckle_lambda >= 1.5 - 1e-6


def test_mass_optimum_is_lighter_but_floppier_than_amazon():
    """The mass-optimal design (deep box, thin walls) is both lighter AND — being sized to the
    minimum with no deflection cap — more flexible than Sponberg's buckling-floor-sized mast.
    This is the honest tradeoff the stiffness-matched run (B) addresses."""
    spec = AmazonMastSpec()
    amz = estimate_amazon_mast_mass(spec)
    opt = MyWayParams(n_spars=3, box_frac_thick=0.88, box_frac_chord=0.45,
                      t_shell=0.0025, t_web=0.003)
    r = estimate_myway_mass(spec, opt)
    d_opt, pct = myway_tip_deflection(spec, opt)
    assert d_opt > 0 and pct > 0
    assert r.mass_per_mast_kg < amz.mass_per_mast_kg          # lighter
    assert d_opt > amz.tip_defl_m                             # but floppier than his mast


def test_objective_penalizes_deflection_cap():
    """The optional deflection cap penalizes over-flexible candidates."""
    spec = AmazonMastSpec()
    base = MyWayParams()
    x = np.array([0.45, 0.88, 0.0025, 0.003, 8.0, 0.70])   # floppy mass-optimal point (6 DVs)
    free = _objective(x, spec, 3, base, None)
    capped = _objective(x, spec, 3, base, 1.5)   # cap below its ~3.1 m deflection
    assert free < 1000.0                          # feasible mass
    assert capped > 1000.0                        # penalized (too floppy for the cap)


@pytest.mark.sizing
def test_optimizer_beats_sponberg_feasibly():
    """The optimized design is lighter than Sponberg's 646 kg/mast AND buckling-feasible."""
    spec = AmazonMastSpec()
    best = optimize_myway(spec, 3, 646.0, seed=1, maxiter=12, popsize=10)
    assert best.mass_per_mast_kg < 646.0                  # beats Sponberg
    assert best.vs_amazon_pct < -15.0                     # by a clear margin
    assert best.min_panel_buckling_lambda >= 1.5 - 1e-3   # feasible
    assert best.result.feasible
