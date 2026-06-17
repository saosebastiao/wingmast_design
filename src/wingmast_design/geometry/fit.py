"""Geometric-fit validator (`R-GG-4`, parent `R-CON-1`).

Confirms that the box spars + longeron channels + outer shell **fit within the faired OML**
and that members **may touch but do not intersect**. With the section-set geometry, the
binding fit failures are local to the internal **webs** (the well-defined, non-degenerate
interfaces — unlike the sharp TE where thickness → 0):

  * the corner **fillets** of two adjacent spars must not overlap — vertically
    (``web_height/2 ≥ blend_radius``) or horizontally (``band_half_width ≥ blend_radius``);
  * the outer **shell** must have room — ``web_height ≥ 2·shell_wall``.

Returns a signed **margin** (metres): ≥ 0 ⇒ feasible (the smallest clearance over all
stations × webs), < 0 ⇒ the binding member overruns the OML/each-other. The validator
*bites*: inflating ``blend_radius`` or ``shell_wall`` past the local section drives it
negative (`tests/geometry/test_fit.py`, and the G.6 smoke test).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .box_spars import BoxSparLayout, _split_upper_lower, _y_on, mast_box_spar_sections


@dataclass(frozen=True)
class FitResult:
    feasible: bool
    margin: float            # signed min clearance (m); ≥ 0 ⇒ feasible
    binding_z: float         # spanwise station of the binding clearance
    binding_reason: str      # which constraint bound


def check_fit(spec, layout: BoxSparLayout, z_stations=None, clearance_tol: float = 1e-6) -> FitResult:
    """Validate the box-spar / longeron / shell fit across spanwise stations."""
    if z_stations is None:
        z_stations = np.linspace(0.0, spec.span, 9)

    best_margin = np.inf
    binding_z = 0.0
    reason = "ok"
    for z in z_stations:
        sec = mast_box_spar_sections(spec, float(z), layout)
        upper, lower = _split_upper_lower(sec.outer_shell)
        x_le, x_te = float(upper[0, 0]), float(upper[-1, 0])
        bounds = np.concatenate([[x_le], sec.webs, [x_te]])
        for i, xw in enumerate(sec.webs):
            web_h = float(_y_on(upper, np.array([xw]))[0] - _y_on(lower, np.array([xw]))[0])
            band_half = 0.5 * min(xw - bounds[i], bounds[i + 2] - xw)
            checks = {
                "fillet_vertical": 0.5 * web_h - layout.blend_radius,
                "fillet_horizontal": band_half - layout.blend_radius,
                "shell_room": web_h - 2.0 * layout.shell_wall,
            }
            for name, m in checks.items():
                if m < best_margin:
                    best_margin, binding_z, reason = float(m), float(z), name

    return FitResult(
        feasible=best_margin >= -clearance_tol,
        margin=float(best_margin),
        binding_z=binding_z,
        binding_reason=reason,
    )
