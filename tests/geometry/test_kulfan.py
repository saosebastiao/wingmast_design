"""Phase-G.1 — Kulfan/CST airfoil source (`R-GG-1`, parent `R-GEO-4`/`R-GEO-3`).

Asserts the CST wrapper reproduces NACA-0018 within a *measured* tolerance, preserves the
project contour ordering (upper-TE -> LE -> lower-TE), and blends root!=tip monotonically.
"""
from __future__ import annotations

import numpy as np

from wingmast_design.geometry.airfoil import naca_00xx_coords
from wingmast_design.geometry.kulfan import CSTAirfoil, blend, fit_cst, naca0018_cst


def _split(c: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Split a project-ordered contour into (upper, lower), each LE->TE ascending in x."""
    le = int(np.argmin(c[:, 0]))
    return c[: le + 1][::-1], c[le:]


def _max_dev(a: np.ndarray, b: np.ndarray) -> float:
    """Max |Δy| between two contours, compared as y(x) on a common cosine x-grid."""
    xg = 0.5 * (1.0 - np.cos(np.linspace(0.0, np.pi, 200)))
    ua, la = _split(a)
    ub, lb = _split(b)
    du = np.abs(np.interp(xg, ua[:, 0], ua[:, 1]) - np.interp(xg, ub[:, 0], ub[:, 1]))
    dl = np.abs(np.interp(xg, la[:, 0], la[:, 1]) - np.interp(xg, lb[:, 0], lb[:, 1]))
    return float(max(du.max(), dl.max()))


def _max_thickness(a: CSTAirfoil) -> float:
    c = a.coords()
    up, lo = _split(c)
    xg = np.linspace(0.02, 0.98, 60)
    return float(np.max(np.interp(xg, up[:, 0], up[:, 1]) - np.interp(xg, lo[:, 0], lo[:, 1])))


def test_naca0018_reproduced_within_measured_tolerance():
    # Measured deviation is ~1.7e-4 (chord-normalized); 5e-4 is the asserted ceiling.
    dev = _max_dev(naca_00xx_coords(0.18, n=320), naca0018_cst().coords(n_points_per_side=160))
    assert dev < 5.0e-4, f"NACA-0018 CST fit deviates {dev:.2e} > 5e-4"


def test_naca0018_weights_are_symmetric():
    a = naca0018_cst()
    assert np.allclose(a.upper_weights, -a.lower_weights, atol=1.0e-6)
    assert abs(a.leading_edge_weight) < 1.0e-9  # symmetric ⇒ no LE camber weight


def test_contour_ordering_convention():
    """upper-TE -> LE -> lower-TE: first & last at the TE, LE at the min-x index, x dips
    to the LE then rises (the project ordering; not required to be exactly closed)."""
    c = naca0018_cst().coords(n_points_per_side=120)
    assert c.ndim == 2 and c.shape[1] == 2
    le = int(np.argmin(c[:, 0]))
    assert np.allclose(c[0], [1.0, 0.0], atol=2.0e-3)   # upper TE
    assert np.allclose(c[-1], [1.0, 0.0], atol=2.0e-3)  # lower TE
    assert abs(c[le, 0]) < 1.0e-6                        # LE at x≈0
    assert 0 < le < len(c) - 1                           # LE interior
    # x monotone-decreasing to LE then monotone-increasing to TE
    assert np.all(np.diff(c[: le + 1, 0]) <= 1e-9)
    assert np.all(np.diff(c[le:, 0]) >= -1e-9)
    # upper side is y>=0 near mid-chord, lower side y<=0
    assert c[le // 2, 1] >= 0.0 and c[le + (len(c) - le) // 2, 1] <= 0.0


def test_root_tip_blend_is_monotone():
    root = naca0018_cst()
    tip = CSTAirfoil(upper_weights=root.upper_weights * 0.6, lower_weights=root.lower_weights * 0.6)
    tvals = [_max_thickness(blend(root, tip, u)) for u in (0.0, 0.25, 0.5, 0.75, 1.0)]
    assert tvals[0] > tvals[-1]                                   # root thicker than tip
    assert all(x >= y - 1e-9 for x, y in zip(tvals, tvals[1:]))   # monotone root->tip
    assert abs(tvals[0] - 0.18) < 5e-3                            # root ≈ NACA-0018 t/c


def test_fit_roundtrip_arbitrary_airfoil():
    """fit_cst then regenerate reproduces an arbitrary (cambered) contour."""
    base = naca0018_cst()
    cambered = CSTAirfoil(
        upper_weights=base.upper_weights + 0.05,
        lower_weights=base.lower_weights + 0.02,
    )
    refit = fit_cst(cambered.coords(n_points_per_side=160), n_weights_per_side=8)
    assert _max_dev(cambered.coords(160), refit.coords(160)) < 1.0e-3
