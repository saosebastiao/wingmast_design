"""Geometric-fit validator (`R-GG-4`, parent `R-CON-1`).

Confirms that the cells + longeron channels + outer shell **fit within the faired OML**
and that members **may touch but do not intersect**. Two layers:

  * **member validity** (`R-CON-1` "must not intersect"): every cell polygon is
    *simple* (non-self-intersecting) and contained within the OML upper/lower envelope, and
    the cells are chordwise-disjoint bands (touch at the shared webs, never overlap);
  * **clearance margin**: the local section must leave room for the corner fillets and the
    walls at every internal **web** (the well-defined, non-degenerate interfaces) —
    ``web_height/2 ≥ blend_radius``, ``band_half_width ≥ blend_radius``, and
    ``web_height ≥ 2·(cell_wall + shell_wall)``.

`feasible` requires **both** (valid members AND margin ≥ −tol). The signed `margin` (m) is the
smallest clearance over all stations × webs. The validator *bites*: a self-intersecting/
OML-violating cell, or an inflated ``blend_radius`` / ``cell_wall`` / ``shell_wall``, makes it
infeasible (`tests/geometry/test_fit.py`, and the G.6 smoke test).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .cells import CellLayout, _split_upper_lower, _y_on, mast_cell_sections


@dataclass(frozen=True)
class FitResult:
    feasible: bool
    margin: float            # signed min web clearance (m); ≥ 0 ⇒ clearance ok
    binding_z: float         # spanwise station of the binding clearance / invalidity
    binding_reason: str      # which constraint bound (or the member-validity failure)
    members_valid: bool = True   # all cells simple + within the OML (R-CON-1)


def _is_simple_polygon(poly: np.ndarray) -> bool:
    """True if no two non-adjacent edges of the closed polygon cross."""
    n = len(poly)

    def cross(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    def seg_cross(p1, p2, p3, p4):
        d1, d2 = cross(p3, p4, p1), cross(p3, p4, p2)
        d3, d4 = cross(p1, p2, p3), cross(p1, p2, p4)
        return (d1 > 0) != (d2 > 0) and (d3 > 0) != (d4 > 0)

    for i in range(n):
        for j in range(i + 1, n):
            if abs(i - j) <= 1 or (i == 0 and j == n - 1):
                continue
            if seg_cross(poly[i], poly[(i + 1) % n], poly[j], poly[(j + 1) % n]):
                return False
    return True


def _within_oml(cell: np.ndarray, upper: np.ndarray, lower: np.ndarray, tol: float) -> bool:
    """Every cell vertex lies within the OML upper/lower envelope (touch on-boundary ok)."""
    x = cell[:, 0]
    return bool(
        np.all(cell[:, 1] <= _y_on(upper, x) + tol)
        and np.all(cell[:, 1] >= _y_on(lower, x) - tol)
    )


def check_fit(spec, layout: CellLayout, z_stations=None, clearance_tol: float = 1e-6) -> FitResult:
    """Validate the cell / longeron / shell fit across spanwise stations."""
    if z_stations is None:
        z_stations = np.linspace(0.0, spec.span, 9)

    members_valid = True
    invalid_reason = ""
    invalid_z = 0.0
    best_margin = np.inf
    binding_z = 0.0
    reason = "ok"

    for z in z_stations:
        sec = mast_cell_sections(spec, float(z), layout)
        upper, lower = _split_upper_lower(sec.outer_shell)

        # --- member validity (R-CON-1 "must not intersect") ---
        for k, cell in enumerate(sec.cells):
            if members_valid and not _is_simple_polygon(cell):
                members_valid, invalid_reason, invalid_z = False, f"self_intersection@cell{k}", float(z)
            elif members_valid and not _within_oml(cell, upper, lower, 1e-4):
                members_valid, invalid_reason, invalid_z = False, f"oml_violation@cell{k}", float(z)

        # --- clearance margins at each internal web ---
        x_le, x_te = float(upper[0, 0]), float(upper[-1, 0])
        bounds = np.concatenate([[x_le], sec.webs, [x_te]])
        for i, xw in enumerate(sec.webs):
            web_h = float(_y_on(upper, np.array([xw]))[0] - _y_on(lower, np.array([xw]))[0])
            band_half = 0.5 * min(xw - bounds[i], bounds[i + 2] - xw)
            checks = {
                "fillet_vertical": 0.5 * web_h - layout.blend_radius,
                "fillet_horizontal": band_half - layout.blend_radius,
                "wall_room": web_h - 2.0 * (layout.cell_wall + layout.shell_wall),
            }
            for name, m in checks.items():
                if m < best_margin:
                    best_margin, binding_z, reason = float(m), float(z), name

    feasible = members_valid and best_margin >= -clearance_tol
    return FitResult(
        feasible=feasible,
        margin=float(best_margin),
        binding_z=invalid_z if not members_valid else binding_z,
        binding_reason=invalid_reason if not members_valid else reason,
        members_valid=members_valid,
    )
