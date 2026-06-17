"""Directional, at-the-CoP, spanwise-distributed mast load vectors (`R-AE-5` / `R-S-2`).

The operational aero load is **not** a transverse point force. The deployed wingsail's
**center of pressure sits slightly aft of the mast's rotation axis** (the aero-balance that
passively feathers the sail and gives the control a small, stable hinge moment), so the aero
resultant — acting at that offset CoP — produces, *simultaneously and distributed along the
span*:

  * **chord-normal force** (the lift / heeling component — the dominant bending load),
  * **chordwise force** (drag — a smaller component), and
  * **torsion about the pivot** = (normal force) × (CoP − pivot offset) — the hinge / feathering
    moment the rotation drive reacts and that twists the mast.

The CoP-vs-pivot offset is **one feature** that sets both this operational hinge torque *and*
the passive feathering (the same principle the bare-mast survival `feathering` model uses — see
`AeroBalance`). The load acts on the **wingsail** chord (the aero surface, ~3–4 m), is
transferred to the **mast** structure, and is resolved in the structural frame
(chord +X, normal +Y, span +Z) ready for the FEA.

This module is **geometry-independent of the mast section** (it depends on the aero balance +
the spanwise load distribution, not the structural profile), so it is a stable load foundation
regardless of the mast-section reconsideration.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class AeroBalance:
    """The wingsail center-of-pressure offset aft of the mast pivot (on the wingsail chord) —
    the single feature behind both the operational hinge torque and the passive feathering.

    ``cop_xc`` slightly **aft** of ``pivot_xc`` ⇒ a positive (restoring) offset: the sail
    weathervanes and the hinge moment is small + stabilising (small control effort). This is
    the *same physical principle* as the bare-mast survival `feathering.restoring_margin_xc`
    (there it is the bare-section aerodynamic centre vs the pivot); here it is the deployed
    wingsail's CoP vs the pivot.
    """

    pivot_xc: float = 0.25      # rotation axis on the chord
    cop_xc: float = 0.28        # wingsail CoP at the operating point (slightly aft → stable)

    @property
    def cop_offset_xc(self) -> float:
        """(CoP − pivot)/chord. > 0 ⇒ CoP aft of pivot ⇒ weathervaning + a stabilising hinge."""
        return self.cop_xc - self.pivot_xc


@dataclass(frozen=True)
class DistributedMastLoad:
    """The spanwise-distributed operational load on the mast, in the structural frame
    (chord +X, normal +Y, span +Z). Densities are per unit span."""

    z: np.ndarray                 # spanwise stations (m), root (0) → tip
    normal_Npm: np.ndarray        # chord-normal (lift/heeling) force / length [N/m]  → +Y
    chordwise_Npm: np.ndarray     # chordwise (drag) force / length [N/m]            → +X
    torsion_Nmpm: np.ndarray      # torsion about the pivot / length [N·m/m]         → Mz (+Z)

    @property
    def total_normal_N(self) -> float:
        return float(np.trapezoid(self.normal_Npm, self.z))

    @property
    def total_chordwise_N(self) -> float:
        return float(np.trapezoid(self.chordwise_Npm, self.z))

    @property
    def total_torsion_Nm(self) -> float:
        return float(np.trapezoid(self.torsion_Nmpm, self.z))

    @property
    def base_bending_Nm(self) -> float:
        """Root (z=0) bending moment from the normal load = ∫ w(z)·z dz."""
        return float(np.trapezoid(self.normal_Npm * self.z, self.z))


def operational_mast_load(
    transverse_force_N: float, balance: AeroBalance, *,
    span_m: float = 22.0, wingsail_chord_root_m: float = 3.6, taper: float = 0.6,
    lift_drag_ratio: float = 15.0, n: int = 200,
) -> DistributedMastLoad:
    """Build the distributed mast load for an operational case from its RM-capped transverse
    (heeling) force resultant + the aero balance.

    The transverse force is the chord-normal (lift/heeling) resultant; it is distributed ∝ the
    (tapering) **wingsail** chord along the span (so its centroid sits at the centre of effort).
    Drag is a smaller chordwise component (``normal / lift_drag_ratio``). The torsion density is
    ``normal(z) · cop_offset · wingsail_chord(z)`` — the hinge moment from the offset CoP.
    """
    z = np.linspace(0.0, span_m, n)
    chord = wingsail_chord_root_m * (1.0 + (taper - 1.0) * z / span_m)
    normal = chord / np.trapezoid(chord, z) * transverse_force_N      # ∝ chord, integrates to F
    chordwise = normal / lift_drag_ratio                              # drag component
    torsion = normal * balance.cop_offset_xc * chord                 # hinge moment / length
    return DistributedMastLoad(z=z, normal_Npm=normal, chordwise_Npm=chordwise, torsion_Nmpm=torsion)


def nodal_load_vectors(load: DistributedMastLoad, node_z: np.ndarray) -> np.ndarray:
    """Lump a distributed mast load onto structural nodes at heights ``node_z`` (sorted, span
    +Z). Returns an (n_nodes, 6) array [Fx, Fy, Fz, Mx, My, Mz]: chordwise→Fx, normal→Fy,
    torsion→Mz. Force/torque-conserving (each density integrated over the node's tributary span).
    """
    node_z = np.asarray(node_z, dtype=float)
    order = np.argsort(node_z)
    zs = node_z[order]
    n_nodes = len(zs)
    # tributary edges: midpoints between nodes (half-open at the ends)
    edges = np.empty(n_nodes + 1)
    edges[1:-1] = 0.5 * (zs[:-1] + zs[1:])
    edges[0], edges[-1] = zs[0], zs[-1]

    out = np.zeros((n_nodes, 6))
    z = load.z
    for k in range(n_nodes):
        lo, hi = edges[k], edges[k + 1]
        m = (z >= lo) & (z <= hi)
        if m.sum() < 2:
            continue
        out[order[k], 0] = np.trapezoid(load.chordwise_Npm[m], z[m])   # Fx (drag)
        out[order[k], 1] = np.trapezoid(load.normal_Npm[m], z[m])      # Fy (lift/heeling → bending)
        out[order[k], 5] = np.trapezoid(load.torsion_Nmpm[m], z[m])    # Mz (hinge / pivot torsion)
    return out
