"""Typed rotating-wingmast geometry parameter set with bounds + increments (`R-GG-5`,
parent `R-GEO-2`).

This is where the specification's "every parameter has bounds and increments" is satisfied
(`docs/specification.md` §3 defers the concrete numbers here). `GEOMETRY_PARAMS` is the
**normative table** (seeded from `docs/engineering_basis.md` §2 — an assumed concept, *TBD*
values await the cited decisions); `MastGeometryParameters` is a chosen point in it that
builds the `RotatingMastSpec` + `BoxSparLayout` consumed by the assembler.
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields

from .box_spars import BoxSparLayout
from .kulfan import CSTAirfoil, naca0018_cst
from .rotating_mast import RotatingMastSpec


@dataclass(frozen=True)
class Param:
    """One design parameter: default + (lower, upper) bounds + grid increment."""

    default: float
    lower: float
    upper: float
    increment: float

    def __post_init__(self) -> None:
        assert self.lower <= self.default <= self.upper, "default must lie within bounds"
        assert self.increment > 0.0, "increment must be positive"

    def in_bounds(self, value: float) -> bool:
        return self.lower <= value <= self.upper


#: Normative parameter table (per mast; basis §2). Keys match `MastGeometryParameters` fields.
GEOMETRY_PARAMS: dict[str, Param] = {
    "span": Param(22.0, 18.0, 26.0, 0.5),
    "root_chord": Param(4.0, 3.0, 5.0, 0.1),
    "tip_chord": Param(2.4, 1.5, 3.5, 0.1),     # taper ratio (tip/root) is DERIVED, not a DV
    "airfoil_tc": Param(0.18, 0.15, 0.22, 0.01),  # reference t/c; the CST weights are the true DV
    "rotation_center_xc": Param(0.25, 0.20, 0.35, 0.01),
    "entasis_frac": Param(0.0, 0.0, 0.03, 0.005),
    "stock_diameter": Param(0.70, 0.30, 0.90, 0.01),  # explicit; None ⇒ inscribed @ root
    "transition_length": Param(0.9, 0.5, 1.5, 0.1),
    "stock_length": Param(3.1, 2.5, 4.0, 0.1),
    "mast_spacing": Param(6.0, 4.0, 8.0, 0.25),         # twin-rig axis-to-axis
    "c_mast": Param(1.0, 0.6, 1.6, 0.1),                # bare-wingmast survival chord (TBD)
    "n_box_spars": Param(3, 3, 5, 1),
    "blend_radius": Param(0.04, 0.02, 0.08, 0.005),
    "spar_wall": Param(0.006, 0.003, 0.020, 0.001),     # geometry placeholder (sized in Phase O)
    "shell_wall": Param(0.004, 0.002, 0.012, 0.001),    # geometry placeholder
}


@dataclass(frozen=True, eq=False)
class MastGeometryParameters:
    """A chosen point in `GEOMETRY_PARAMS` (defaults = the reference twin-rig), plus the
    root/tip CST airfoils. Builds the geometry objects the assembler consumes."""

    span: float = GEOMETRY_PARAMS["span"].default
    root_chord: float = GEOMETRY_PARAMS["root_chord"].default
    tip_chord: float = GEOMETRY_PARAMS["tip_chord"].default
    airfoil_tc: float = GEOMETRY_PARAMS["airfoil_tc"].default
    rotation_center_xc: float = GEOMETRY_PARAMS["rotation_center_xc"].default
    entasis_frac: float = GEOMETRY_PARAMS["entasis_frac"].default
    stock_diameter: float | None = None              # None ⇒ inscribed circle at the root
    transition_length: float = GEOMETRY_PARAMS["transition_length"].default
    stock_length: float = GEOMETRY_PARAMS["stock_length"].default
    mast_spacing: float = GEOMETRY_PARAMS["mast_spacing"].default
    c_mast: float = GEOMETRY_PARAMS["c_mast"].default
    n_box_spars: int = int(GEOMETRY_PARAMS["n_box_spars"].default)
    blend_radius: float = GEOMETRY_PARAMS["blend_radius"].default
    spar_wall: float = GEOMETRY_PARAMS["spar_wall"].default
    shell_wall: float = GEOMETRY_PARAMS["shell_wall"].default
    root_airfoil: CSTAirfoil = field(default_factory=naca0018_cst)
    tip_airfoil: CSTAirfoil = field(default_factory=naca0018_cst)

    @classmethod
    def reference(cls) -> "MastGeometryParameters":
        """The Oyster-595 twin-rig reference (all defaults)."""
        return cls()

    def out_of_bounds(self) -> list[str]:
        """Names of any scalar parameter outside its (lower, upper) bound (empty = valid).
        Parameters left as ``None`` (e.g. stock_diameter ⇒ inscribed) are skipped."""
        bad = []
        for f in fields(self):
            if f.name not in GEOMETRY_PARAMS:
                continue
            v = getattr(self, f.name)
            if v is None:
                continue
            if not GEOMETRY_PARAMS[f.name].in_bounds(v):
                bad.append(f.name)
        return bad

    def to_mast_spec(self) -> RotatingMastSpec:
        return RotatingMastSpec(
            span=self.span, root_chord=self.root_chord, tip_chord=self.tip_chord,
            root_airfoil=self.root_airfoil, tip_airfoil=self.tip_airfoil,
            rotation_center_xc=self.rotation_center_xc, entasis_frac=self.entasis_frac,
            transition_length=self.transition_length, stock_length=self.stock_length,
            stock_diameter=self.stock_diameter,
        )

    def to_box_layout(self) -> BoxSparLayout:
        return BoxSparLayout(
            n_spars=int(self.n_box_spars), blend_radius=self.blend_radius,
            spar_wall=self.spar_wall, shell_wall=self.shell_wall,
        )
