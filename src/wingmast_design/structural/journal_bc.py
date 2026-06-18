"""Journal / bearing boundary conditions for the rotating wingmast (`R-S-1`, parent `R-CON-3`).

The mast is **not** root-clamped — it is supported at **two spanwise-separated journal
bearings** (deck-partners upper, heel-step lower) and is **free to rotate about its own (span)
axis**. We model each bearing as a **finite-stiffness radial support** (penalty springs on the
two cross-span translations), the heel additionally reacting **axial thrust** (gravity down the
stock), and a finite **pivot-axis torsional** spring (the rotation drive / actuator holding the
AoA — and the only thing resisting the otherwise-free rotation rigid-body mode).

Why springs, not a clamp or Lagrange multipliers (`D-S-a`): a real journal has finite radial
compliance, springs are the simplest augmentation of the assembled `K` (reuse the solver, no
saddle-point system), they compose with the buckling eigen, and — critically — **a
journal-supported spar buckles differently than a clamped one**, so the boundary must be modelled,
not assumed (the audit's concern).

DOF convention (per node, `structural.frame`): [ux, uy, uz, rx, ry, rz], **span = +Z**. So
radial = ux/uy, axial = uz, pivot rotation = rz.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from .frame import BeamSection, FrameResult, assemble_frame_K, recover_frame_forces


@dataclass(frozen=True)
class JournalBC:
    """Two journal bearings (node indices) + finite stiffnesses. The two radial supports,
    spanwise-separated by the bury, react the bending as a couple; the heel reacts thrust; the
    torsional spring is the rotation drive (also stabilises the free pivot rotation mode)."""

    partners_node: int                 # upper journal (deck-partners)
    heel_node: int                     # lower journal (heel-step)
    k_radial_Npm: float = 1.0e9        # radial bearing stiffness (finite, high) [N/m]
    k_axial_Npm: float = 1.0e9         # heel thrust support [N/m]
    k_torsion_Nm_rad: float = 1.0e7    # rotation-drive / actuator holding the AoA [N·m/rad]

    def spring_dofs(self) -> list[tuple[int, float]]:
        """(global DOF index, stiffness) pairs for the bearing springs."""
        p, h = self.partners_node, self.heel_node
        return [
            (6 * p + 0, self.k_radial_Npm), (6 * p + 1, self.k_radial_Npm),   # partners radial X,Y
            (6 * h + 0, self.k_radial_Npm), (6 * h + 1, self.k_radial_Npm),   # heel radial X,Y
            (6 * h + 2, self.k_axial_Npm),                                    # heel axial thrust Z
            (6 * h + 5, self.k_torsion_Nm_rad),                               # pivot-axis drive Rz
        ]


def apply_journal_springs(K: sp.spmatrix, bc: JournalBC) -> sp.csr_matrix:
    """Return ``K`` with the bearing springs added to its diagonal (a new CSR matrix)."""
    ndof = K.shape[0]
    diag = np.zeros(ndof)
    for dof, k in bc.spring_dofs():
        diag[dof] += k
    return (K + sp.diags(diag)).tocsr()


def journal_reactions(bc: JournalBC, u: np.ndarray) -> dict[str, float]:
    """Bearing reaction forces/moments (= spring stiffness × displacement at each spring DOF).
    Sign: the force the bearing exerts on the mast (opposes the displacement)."""
    out: dict[str, float] = {}
    p, h = bc.partners_node, bc.heel_node
    out["partners_Fx"] = -bc.k_radial_Npm * u[6 * p + 0]
    out["partners_Fy"] = -bc.k_radial_Npm * u[6 * p + 1]
    out["heel_Fx"] = -bc.k_radial_Npm * u[6 * h + 0]
    out["heel_Fy"] = -bc.k_radial_Npm * u[6 * h + 1]
    out["heel_Fz"] = -bc.k_axial_Npm * u[6 * h + 2]
    out["pivot_Mz"] = -bc.k_torsion_Nm_rad * u[6 * h + 5]
    return out


def solve_frame_journal(
    nodes: np.ndarray, elements: np.ndarray, sections: list[BeamSection], *,
    E: float, G: float, journal: JournalBC, loads: np.ndarray,
) -> tuple[FrameResult, dict[str, float]]:
    """Solve a journal-supported frame (no clamp): assemble K, add the bearing springs, solve the
    full system, recover internal forces + the journal reactions. Returns (result, reactions)."""
    K, transforms, klocals = assemble_frame_K(nodes, elements, sections, E=E, G=G)
    K = apply_journal_springs(K, journal)
    f = loads.reshape(-1).astype(float)
    u = spla.spsolve(K.tocsc(), f)
    disp = u.reshape(nodes.shape[0], 6)
    axial, bending, torsion = recover_frame_forces(u, elements, transforms, klocals)
    result = FrameResult(displacements=disp, axial_force=axial, bending_moment=bending, torsion=torsion)
    return result, journal_reactions(journal, u)
