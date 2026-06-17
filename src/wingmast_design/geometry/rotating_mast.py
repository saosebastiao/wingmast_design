"""Rotating wingmast geometry stack (`R-GG-2`, parent `R-GEO-1`/`R-GEO-2`).

The full bottom-to-top anatomy as named zones with their own Z-extents:

    heel-step (lower journal) → stock (rotating circular bury through the hull)
    → deck-partners (upper journal) → transition (circle→airfoil) → wing root
    → tapered airfoil wing → tip.

Z convention (geometry frame: chord +X, span +Z, normal +Y; rotation axis at X=Y=0):

    z = span                                            wing tip
    z ∈ [0, span]                                       tapered airfoil wing
    z = 0                                               wing root
    z ∈ [-transition_length, 0]                         transition (root airfoil→stock circle)
    z = -transition_length                              deck-partners = UPPER journal
    z ∈ [-(transition_length+stock_length), -transition_length]   stock (the bury)
    z = -(transition_length+stock_length)               heel-step = LOWER journal

Distinct from the legacy demo `WingSpec`: this is the forward Oyster-595 mast spec —
Kulfan/CST airfoils (root≠tip blend), a **rotational-center foil offset** (the rotation axis
on the chord, `R-GEO-2`), **entasis** (convex spanwise bow, `D-5`), and the two tagged
**journal stations** Phase S turns into bearing BCs. It REUSES the audited loft helpers
(`_section_face`, `_transition_blend`, `ruled` loft) and the airfoil ordering — composition,
not mutation of the frozen `WingSpec` (refines `D-GG-e`).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from build123d import BuildPart, Plane, add, loft

from .kulfan import CSTAirfoil, blend, naca0018_cst
from .wing import _section_face, _transition_blend


def _default_airfoil() -> CSTAirfoil:
    return naca0018_cst()


@dataclass(frozen=True, eq=False)
class RotatingMastSpec:
    """Parametric rotating-wingmast geometry (one mast). ``eq=False`` — holds CST airfoils
    (ndarray weights). All lengths in metres."""

    span: float = 22.0                       # exposed wing, root (z=0) → tip
    root_chord: float = 4.0
    tip_chord: float = 2.4                   # taper ratio 0.6
    root_airfoil: CSTAirfoil = field(default_factory=_default_airfoil)
    tip_airfoil: CSTAirfoil = field(default_factory=_default_airfoil)
    rotation_center_xc: float = 0.25         # rotation axis on the chord (x/c) — R-GEO-2
    entasis_frac: float = 0.0                # max convex spanwise bow / span (0 = straight)
    transition_length: float = 0.9          # circle→airfoil fairing height
    stock_length: float = 3.1                # bury = upper→lower journal spacing
    stock_diameter: float | None = None      # None → inscribed circle at the root section
    n_sections: int = 6                      # spanwise wing sections (root..tip)
    n_transition_sections: int = 4
    n_airfoil_points: int = 160              # ~ 2 × per-side

    # --- airfoil / chord along the span ------------------------------------------------
    def chord_at_z(self, z: float) -> float:
        """Linear taper root→tip for z ≥ 0; root chord in the transition/stock (z < 0)."""
        if z <= 0.0:
            return self.root_chord
        f = min(z / self.span, 1.0)
        return self.root_chord + f * (self.tip_chord - self.root_chord)

    def airfoil_at_frac(self, frac: float) -> CSTAirfoil:
        """Blended CST section at spanwise fraction ``frac`` (0=root, 1=tip) — `R-GEO-3`."""
        return blend(self.root_airfoil, self.tip_airfoil, float(np.clip(frac, 0.0, 1.0)))

    def _contour(self, frac: float) -> np.ndarray:
        return self.airfoil_at_frac(frac).coords(n_points_per_side=self.n_airfoil_points // 2)

    # --- stock sizing ------------------------------------------------------------------
    @property
    def inscribed_stock_radius(self) -> float:
        """Largest circle inscribed in the root section, centred at the rotation axis,
        floored to the cm (manufacturable stock). Upper bound on the stock radius."""
        c = (self.root_airfoil.coords(n_points_per_side=self.n_airfoil_points // 2)
             - np.array([self.rotation_center_xc, 0.0])) * self.root_chord
        r = float(np.min(np.hypot(c[:, 0], c[:, 1])))
        return np.floor(r * 100.0) / 100.0

    @property
    def effective_stock_diameter(self) -> float:
        if self.stock_diameter is None:
            return 2.0 * self.inscribed_stock_radius
        return float(self.stock_diameter)

    def stock_fits(self) -> bool:
        """The stock circle must fit inside the root section (R-CON-1 precursor)."""
        return self.effective_stock_diameter <= 2.0 * self.inscribed_stock_radius + 1e-9

    # --- zones / journals --------------------------------------------------------------
    @property
    def partners_z(self) -> float:
        """Deck-partners station (upper journal) = top of the stock."""
        return -self.transition_length

    @property
    def heel_z(self) -> float:
        """Heel-step station (lower journal) = bottom of the stock."""
        return -(self.transition_length + self.stock_length)

    @property
    def journal_stations(self) -> tuple[float, float]:
        """(upper_journal_z, lower_journal_z) — the bearing-couple stations for Phase S."""
        return (self.partners_z, self.heel_z)

    @property
    def zone_z_extents(self) -> dict[str, tuple[float, float]]:
        """Named zones → (z_lo, z_hi), contiguous and ordered bottom→top."""
        return {
            "heel_step": (self.heel_z, self.heel_z),
            "stock": (self.heel_z, self.partners_z),
            "deck_partners": (self.partners_z, self.partners_z),
            "transition": (self.partners_z, 0.0),
            "wing": (0.0, self.span),
        }

    def entasis_offset(self, z: float) -> float:
        """Convex spanwise bow (chord-direction +X), peaking mid-span, 0 at root/tip and
        below the root (the stock/transition stay on the straight rotation axis). `D-5`."""
        if self.entasis_frac == 0.0 or z <= 0.0:
            return 0.0
        f = min(z / self.span, 1.0)
        return self.entasis_frac * self.span * float(np.sin(np.pi * f))


def build_rotating_mast_solid(spec: RotatingMastSpec):
    """Loft the wing + transition + stock as one solid (`ruled=True`).

    Sections run top (tip) → bottom (heel) so the loft proceeds one way. The wing sections
    carry the blended CST airfoil + entasis offset; the transition morphs the root section
    to the stock circle; the stock is two identical circles between the journals.
    """
    diameter = spec.effective_stock_diameter
    pivot = spec.rotation_center_xc
    n = spec.n_airfoil_points
    sections: list = []

    # Wing: tip → root, blended CST airfoil, chord taper, entasis bow.
    for i in reversed(range(spec.n_sections)):
        frac = i / (spec.n_sections - 1)
        z = frac * spec.span
        face = _section_face(
            spec.chord_at_z(z), 0.0, pivot, diameter, blend=0.0, n_pts=n,
            contour=spec._contour(frac),
        )
        sections.append(Plane(origin=(spec.entasis_offset(z), 0.0, z)) * face)

    # Transition: root airfoil (blend 0 at z=0, already the last wing section) → stock circle.
    root_contour = spec._contour(0.0)
    for j in range(1, spec.n_transition_sections + 2):
        u = j / (spec.n_transition_sections + 1)
        z = -spec.transition_length * u
        face = _section_face(
            spec.root_chord, 0.0, pivot, diameter, blend=_transition_blend(u), n_pts=n,
            contour=root_contour,
        )
        sections.append(Plane(origin=(0.0, 0.0, z)) * face)

    # Stock: a straight cylinder (blend=1 circle) between the two journals.
    stock_face = _section_face(
        spec.root_chord, 0.0, pivot, diameter, blend=1.0, n_pts=n, contour=root_contour,
    )
    sections.append(Plane(origin=(0.0, 0.0, spec.heel_z)) * stock_face)

    with BuildPart() as part:
        for face in sections:
            add(face)
        loft(ruled=True)
    return part.part
