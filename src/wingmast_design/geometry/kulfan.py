"""Kulfan / CST airfoil source (`R-GEO-4`, `R-GG-1`).

Wraps AeroSandbox's CST (Kulfan) implementation — already a project dependency — so the
airfoil source supports **arbitrary** shapes, not only NACA sections, while preserving the
project's closed-contour ordering convention:

    (N, 2), cosine-spaced, traversed **upper-TE -> LE -> lower-TE**, closed (first == last
    at the TE), LE at the minimum-x index.

AeroSandbox `get_kulfan_coordinates` already emits this exact ordering, so the wrapper is
thin. NACA-0018 is the reference default, reproduced by CST weights **fit** to the project's
own `naca_00xx_coords` (the validation oracle) via `get_kulfan_parameters`.

Root and tip airfoils may differ via a spanwise blend of the CST weights (`blend`,
`R-GEO-3`). The weights themselves are the airfoil design variables Phase O will optimise.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from aerosandbox.geometry.airfoil.airfoil_families import (
    get_kulfan_coordinates,
    get_kulfan_parameters,
)

from .airfoil import naca_00xx_coords

#: Default number of CST weights per side (the shape resolution / DV count).
N_WEIGHTS_PER_SIDE = 8


@dataclass(frozen=True, eq=False)
class CSTAirfoil:
    """A CST (Kulfan) airfoil defined by its upper/lower shape weights.

    ``eq=False`` because the weights are ndarrays (identity equality is all we need; the
    contour is what matters). Distinct from `aerosandbox.KulfanAirfoil` — this is the
    project-ordering wrapper.
    """

    upper_weights: np.ndarray
    lower_weights: np.ndarray
    leading_edge_weight: float = 0.0
    te_thickness: float = 0.0

    def coords(self, n_points_per_side: int = 80) -> np.ndarray:
        """(N, 2) contour in the project ordering (upper-TE -> LE -> lower-TE, closed)."""
        c = get_kulfan_coordinates(
            lower_weights=np.asarray(self.lower_weights, dtype=float),
            upper_weights=np.asarray(self.upper_weights, dtype=float),
            leading_edge_weight=float(self.leading_edge_weight),
            TE_thickness=float(self.te_thickness),
            n_points_per_side=int(n_points_per_side),
        )
        return np.asarray(c, dtype=float)


def fit_cst(coords: np.ndarray, n_weights_per_side: int = N_WEIGHTS_PER_SIDE) -> CSTAirfoil:
    """Fit CST weights to a given (N, 2) contour (project ordering)."""
    p = get_kulfan_parameters(
        np.asarray(coords, dtype=float), n_weights_per_side=int(n_weights_per_side)
    )
    return CSTAirfoil(
        upper_weights=np.asarray(p["upper_weights"], dtype=float),
        lower_weights=np.asarray(p["lower_weights"], dtype=float),
        leading_edge_weight=float(p["leading_edge_weight"]),
        te_thickness=float(p["TE_thickness"]),
    )


def naca0018_cst(n_weights_per_side: int = N_WEIGHTS_PER_SIDE) -> CSTAirfoil:
    """Reference default: CST weights fit to the project's NACA-0018 oracle.

    Reproduces `geometry.airfoil.naca_00xx_coords(0.18)` to within the tolerance asserted in
    `tests/geometry/test_kulfan.py` (measured, not assumed).
    """
    return fit_cst(naca_00xx_coords(0.18, n=320), n_weights_per_side=n_weights_per_side)


def blend(root: CSTAirfoil, tip: CSTAirfoil, u: float) -> CSTAirfoil:
    """Linear blend of two CST airfoils, ``u`` in [0, 1] (0 = root, 1 = tip) — `R-GEO-3`."""
    u = float(np.clip(u, 0.0, 1.0))

    def lerp(a, b):
        return (1.0 - u) * np.asarray(a, dtype=float) + u * np.asarray(b, dtype=float)

    return CSTAirfoil(
        upper_weights=lerp(root.upper_weights, tip.upper_weights),
        lower_weights=lerp(root.lower_weights, tip.lower_weights),
        leading_edge_weight=(1.0 - u) * root.leading_edge_weight + u * tip.leading_edge_weight,
        te_thickness=(1.0 - u) * root.te_thickness + u * tip.te_thickness,
    )
