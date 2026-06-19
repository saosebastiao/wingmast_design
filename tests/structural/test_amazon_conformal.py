"""Phase-X5 — as-built conformal multi-cell torsion-box sizer (`R-AMZ-7`)."""
from __future__ import annotations

import numpy as np

from wingmast_design.geometry.amazon_mast import AmazonMastSpec
from wingmast_design.structural.amazon_conformal import (
    ConformalParams,
    conformal_section,
    estimate_conformal_mass,
)
from wingmast_design.structural.amazon_sizing import estimate_amazon_mast_mass


def test_conformal_sized_designs_are_feasible():
    """Every conformal-sized design protects caps + shell (strength) and the cap panel
    (orthotropic buckling λ ≥ 1.5) — on the REAL cell cross-section, not an idealised box."""
    spec = AmazonMastSpec()
    for n in (3, 4, 5):
        r = estimate_conformal_mass(spec, ConformalParams(n_cells=n))
        assert r.feasible
        assert r.max_cap_util <= 1.0 + 1e-6
        assert r.max_shell_util <= 1.0 + 1e-6
        assert r.min_buckle_lambda >= 1.5 - 1e-6


def test_buckling_governs_and_cap_tapers():
    """The conformal box is cap-panel-buckling governed, and the sized cap wall tapers root→tip
    (more moment + thicker section at the root)."""
    spec = AmazonMastSpec()
    p = ConformalParams(n_cells=3)
    r = estimate_conformal_mass(spec, p)
    assert r.governing_fracs.get("panel-buckling", 0.0) > 0.5
    t_root = conformal_section(0.0, spec, p)[0]
    t_mid = conformal_section(11.0, spec, p)[0]
    t_tip = conformal_section(21.0, spec, p)[0]
    assert t_root > t_mid > t_tip


def test_conformal_is_sponberg_class_not_dramatically_lighter():
    """HONEST finding (reverses the idealised-box X4 claim): once the structure must fill the
    section conformally (no box-fraction to game) + wrap a structural FW shell, the buildable
    multi-cell torsion box is Sponberg-CLASS — within ~20 %, NOT the -30 % the box model implied."""
    spec = AmazonMastSpec()
    amz = estimate_amazon_mast_mass(spec).mass_per_mast_kg
    r3 = estimate_conformal_mass(spec, ConformalParams(n_cells=3), amazon_per_mast_kg=amz)
    assert 0.85 * amz < r3.mass_per_mast_kg < 1.25 * amz       # same class
    assert r3.vs_amazon_pct is not None
    # 3 cells is the lightest conformal count (more cells ⇒ more web mass, no buckling win here)
    r4 = estimate_conformal_mass(spec, ConformalParams(n_cells=4))
    assert r3.mass_per_mast_kg < r4.mass_per_mast_kg


def test_mass_bookkeeping_and_schedule():
    spec = AmazonMastSpec()
    r = estimate_conformal_mass(spec, ConformalParams(n_cells=3))
    assert r.mass_both_masts_kg == np.float64(2.0) * r.mass_per_mast_kg
    assert abs(r.mass_per_mast_kg - (r.wing_kg + r.stock_kg)) < 1e-6
    assert len(r.cap_schedule) == ConformalParams().n_int
    assert r.cap_schedule[0][0] == 0.0                        # starts at the root
