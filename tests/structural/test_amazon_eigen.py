"""Phase-X4 closure — eigen verification of the governing cap panel (`R-AMZ-5`, Article III)."""
from __future__ import annotations

import numpy as np
import pytest

from wingmast_design.materials.unidir import laminate_stiffness, T800_EPOXY
from wingmast_design.geometry.amazon_mast import AmazonMastSpec
from wingmast_design.structural.amazon_eigen import (
    cap_panel_eigen_lambda,
    exact_ortho_ss_lambda,
    verify_cap_panel_eigen,
)
from wingmast_design.structural.amazon_myway import MyWayParams


def test_exact_analytical_equals_the_sizer_closed_form():
    """The closed form the sizer uses IS the exact orthotropic SS-plate eigenvalue."""
    _, D, _ = laminate_stiffness(T800_EPOXY, f0=0.70, f45=0.15, f90=0.15, thickness=0.003)
    b, t, sigma = 0.08, 0.003, 100e6
    lam_exact = exact_ortho_ss_lambda(D, t, b, sigma)
    # closed form 2π²·K·(t/b)² / σ with K from D(thickness=1)
    _, Du, _ = laminate_stiffness(T800_EPOXY, f0=0.70, f45=0.15, f90=0.15, thickness=1.0)
    K = np.sqrt(Du[0, 0] * Du[1, 1]) + Du[0, 1] + 2 * Du[2, 2]
    lam_cf = 2 * np.pi**2 * K * (t / b) ** 2 / sigma
    assert lam_exact == pytest.approx(lam_cf, rel=1e-9)


def test_fea_reduces_to_isotropic_kc4_for_an_isotropic_plate():
    """Sanity: the laminate-element eigen reproduces the isotropic SS-plate kc=4 reference (this
    is the same machinery as tests/structural/test_eigen_buckling.py)."""
    E, nu, t, b = 70e9, 0.3, 0.004, 1.0
    Dm = E / (1 - nu**2) * np.array([[1, nu, 0], [nu, 1, 0], [0, 0, (1 - nu) / 2]])
    A = t * Dm
    D = t**3 / 12 * Dm
    sigma0 = 1.0e6
    lam = cap_panel_eigen_lambda(A, D, t, b, sigma0, ny=16, aspect=1.0)   # square plate
    sigma_cr_ref = 4.0 * np.pi**2 * (E * t**3 / (12 * (1 - nu**2))) / (b**2 * t)
    assert lam * sigma0 == pytest.approx(sigma_cr_ref, rel=0.06)


@pytest.mark.sizing
def test_governing_cap_panel_is_eigen_feasible():
    """Closure: the optimized design's governing cap panel is buckling-feasible — exact λ ≥ 1.5,
    and the converged FEA confirms ≥ 1.5 (overstiff, so it only adds margin)."""
    spec = AmazonMastSpec()
    opt = MyWayParams(n_cells=3, box_frac_chord=0.45, box_frac_thick=0.88,
                      t_shell=0.0025, t_web=0.003)
    r = verify_cap_panel_eigen(spec, opt)
    assert r.exact_analytical_lambda == pytest.approx(1.5, abs=0.05)   # design target met exactly
    assert r.fea_lambda_converged >= 1.5                              # FEA confirms feasibility
    assert r.fea_overstiff_pct > 0.0                                  # FEA is overstiff (non-conservative)
    # mesh-converged: last two FEA points within 1%
    last = [l for _, l in r.convergence][-2:]
    assert abs(last[0] - last[1]) / last[1] < 0.01
    assert r.feasible
