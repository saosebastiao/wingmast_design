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
    (chord +X, normal +Y, span +Z). Densities are per unit span. ``base_z_m`` is the datum the
    base bending moment is reported about — the **deck-partners** (upper journal, z=−0.9), the
    structurally-relevant base section where the bearing reacts the moment — NOT the wing root."""

    z: np.ndarray                 # spanwise stations (m), root (0) → tip
    normal_Npm: np.ndarray        # chord-normal (lift/heeling) force / length [N/m]  → +Y
    chordwise_Npm: np.ndarray     # chordwise (drag) force / length [N/m]            → +X
    torsion_Nmpm: np.ndarray      # torsion about the pivot / length [N·m/m]         → Mz (+Z)
    base_z_m: float = -0.9        # the base/datum section (deck partners)

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
        """Bending moment at the base datum (the partners) = ∫ w(z)·(z − base_z) dz."""
        return float(np.trapezoid(self.normal_Npm * (self.z - self.base_z_m), self.z))

    @property
    def resultant_arm_m(self) -> float:
        """Derived height of the load resultant above the base datum (= base_bending / force).
        For a ∝chord (taper 0.6) shape this lands ~11 m above the partners — near, but inboard
        of, a pure resultant-at-CE model; it is a *derived* quantity, not pinned to the CE."""
        return self.base_bending_Nm / self.total_normal_N


def operational_mast_load(
    base_moment_Nm: float, balance: AeroBalance, *,
    base_z_m: float = -0.9, span_m: float = 22.0, wingsail_chord_root_m: float = 3.6,
    taper: float = 0.6, lift_drag_ratio: float = 15.0, n: int = 200,
) -> DistributedMastLoad:
    """Build the distributed mast load for an operational case from its **RM-capped base bending
    moment** (about the partners) + the aero balance.

    The spanwise shape ∝ the (tapering) **wingsail** chord is **scaled so its moment about the
    base datum equals ``base_moment_Nm``** — so the governing OP-2 base moment is reproduced
    *exactly* by construction, with the total force + resultant arm *derived* (not assumed equal
    to the CE). Drag is ``normal / lift_drag_ratio``; the torsion density is ``normal(z) ·
    cop_offset · wingsail_chord(z)`` — the hinge moment from the offset CoP.
    """
    z = np.linspace(0.0, span_m, n)
    chord = wingsail_chord_root_m * (1.0 + (taper - 1.0) * z / span_m)
    arm = z - base_z_m                                                # lever from the base datum
    scale = base_moment_Nm / np.trapezoid(chord * arm, z)            # ⇒ ∫ w·arm = base_moment
    normal = chord * scale
    chordwise = normal / lift_drag_ratio                            # drag component
    torsion = normal * balance.cop_offset_xc * chord                # hinge moment / length
    return DistributedMastLoad(z=z, normal_Npm=normal, chordwise_Npm=chordwise,
                               torsion_Nmpm=torsion, base_z_m=base_z_m)


def nodal_load_vectors(load: DistributedMastLoad, node_z: np.ndarray) -> np.ndarray:
    """Lump a distributed mast load onto structural nodes at heights ``node_z`` (sorted, span
    +Z). Returns an (n_nodes, 6) array [Fx, Fy, Fz, Mx, My, Mz]: chordwise→Fx, normal→Fy,
    torsion→Mz.

    Force/torque-conserving **to machine precision**: each density is integrated over the node's
    tributary span with the density interpolated at the *exact* tributary edges (so no boundary
    sliver is dropped — the piecewise-linear density integrates exactly partition-by-partition).
    """
    node_z = np.asarray(node_z, dtype=float)
    order = np.argsort(node_z)
    zs = node_z[order]
    n_nodes = len(zs)
    # tributary edges: midpoints between nodes; clamped to the load support at the ends
    edges = np.empty(n_nodes + 1)
    edges[1:-1] = 0.5 * (zs[:-1] + zs[1:])
    edges[0], edges[-1] = zs[0], zs[-1]
    z = load.z
    edges = np.clip(edges, z[0], z[-1])

    def _tributary_integral(dens: np.ndarray, lo: float, hi: float) -> float:
        if hi <= lo:
            return 0.0
        interior = z[(z > lo) & (z < hi)]
        zz = np.concatenate(([lo], interior, [hi]))
        return float(np.trapezoid(np.interp(zz, z, dens), zz))

    out = np.zeros((n_nodes, 6))
    for k in range(n_nodes):
        lo, hi = edges[k], edges[k + 1]
        out[order[k], 0] = _tributary_integral(load.chordwise_Npm, lo, hi)  # Fx (drag)
        out[order[k], 1] = _tributary_integral(load.normal_Npm, lo, hi)     # Fy (lift→bending)
        out[order[k], 5] = _tributary_integral(load.torsion_Nmpm, lo, hi)   # Mz (hinge torsion)
    return out
