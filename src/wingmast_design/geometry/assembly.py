"""Twin-rig rotating-wingmast assembly (`R-GG-6`, parent `G-1`).

Composes the parameterized geometry into the tandem two-mast assembly: each mast's OML
solid (`build_rotating_mast_solid`) placed at the fore-and-aft `mast_spacing`. The cell
/ longeron / outer-shell **section set** + the geometric-fit check are produced per mast by
`cells` / `fit` (the 3-D lofting of the cells into the assembly is a follow-up
on the Phase-S mesh; G.6 ships the OML assembly + the validated section set + export).
"""
from __future__ import annotations

from build123d import Compound, Pos

from .cells import CellSection
from .fit import FitResult, check_fit
from .parameters import MastGeometryParameters
from .rotating_mast import build_rotating_mast_solid


def build_wingmast_assembly(params: MastGeometryParameters | None = None) -> Compound:
    """The tandem twin-rig OML assembly: fore + aft masts at ``mast_spacing`` along +X."""
    params = params or MastGeometryParameters.reference()
    spec = params.to_mast_spec()
    solid = build_rotating_mast_solid(spec)

    # Both masts are distinct translated copies (Pos * solid returns a new located shape) —
    # no aliasing of, or transient label-clobbering on, the shared `solid` (G-review finding).
    fore = Pos(0.0, 0.0, 0.0) * solid
    fore.label = "mast_fore"
    aft = Pos(params.mast_spacing, 0.0, 0.0) * solid
    aft.label = "mast_aft"
    return Compound(label="twin_wingmast", children=[fore, aft])


def assembly_fit(params: MastGeometryParameters | None = None) -> FitResult:
    """Geometric-fit verdict (`R-GG-4`) for the (identical) per-mast cell build."""
    params = params or MastGeometryParameters.reference()
    return check_fit(params.to_mast_spec(), params.to_cell_layout())


def assembly_root_section(params: MastGeometryParameters | None = None) -> CellSection:
    """The cell / longeron / shell section set at the wing root (for inspection/export)."""
    from .cells import mast_cell_sections

    params = params or MastGeometryParameters.reference()
    return mast_cell_sections(params.to_mast_spec(), 0.0, params.to_cell_layout())
