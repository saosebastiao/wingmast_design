"""Amazon-baseline wingmast geometry (Phase X1, `R-AMZ-1`).

Reproduces the **outer mould line of Eric Sponberg's *Project Amazon* free-standing rotating
wingmast** — the closest built prior art (dossier: `docs/respec_research/sponberg_amazon_prior_art.md`).
The OML is taken verbatim from Sponberg's own drawings (Professional BoatBuilder No. 55, 1998,
Fig. on p.50; SNAME *Marine Technology* 37(2), 2000, Figs. 17–18), which agree to the digit.

**This OML is FROZEN (`D-AMZ-1`):** the section is a constant **2.5:1 ellipse** (t/c = 0.40,
"symmetric lens") the full wing length, scaled by a **modified-entasis** chord taper (fatter in
the mid-span than a straight taper — the published station chords sit a sinusoidal ~112 mm bulge
above linear). Below the wing root the section morphs to a **round bearing stock** (OD 500 at the
deck partners → OD 450 at the heel) for the two roller bearings. We do **not** vary this envelope;
the project beats Sponberg by internal structure + manufacturing + optimization, not by reshaping
the wing (see `docs/specs/04-amazon-baseline/spec.md`).

Geometry frame (shared with `rotating_mast`): chord +X, span +Z, normal +Y; rotation axis at
X=Y=0; z=0 at the **wing root** (station 0, the max 750×300 section just above the gooseneck);
the wing runs z ∈ [0, sail_track]; the transition + stock are at z < 0 down to the heel.

    z = sail_track_length                     masthead (station 6, 300×120)
    z ∈ (0, sail_track_length)                tapered elliptical wing (entasis)
    z = 0                                      wing root = station 0 (750×300, max section)
    z ∈ [-transition_length, 0)               ellipse → OD500 morph (gooseneck/collar)
    z = -transition_length                     deck partners = UPPER journal (OD 500)
    z ∈ [-below_root_length, -transition_length]   stock, OD 500 → OD 450 (the bury)
    z = -below_root_length                     heel = LOWER journal (OD 450)

Reuses the audited loft helpers (`wing._section_face`, `_transition_blend`, `ruled` loft) and the
project airfoil ordering — composition, not a new loft path.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from build123d import BuildPart, Plane, add, loft

from .wing import _section_face, _transition_blend

# --- Published Amazon mast particulars (Sponberg PBB No.55 1998 / SNAME 37(2) 2000) ---------
# Station table: (chord_mm, thickness_mm), station 0 (deck/root) → 6 (masthead). Constant 2.5:1.
AMAZON_STATIONS_MM: tuple[tuple[float, float], ...] = (
    (750.0, 300.0),   # 0 — wing root, deck level, MAX section
    (737.5, 295.0),   # 1
    (700.0, 280.0),   # 2
    (637.5, 255.0),   # 3 — entasis bulge peaks here (~+112 mm over linear)
    (550.0, 220.0),   # 4
    (437.5, 175.0),   # 5
    (300.0, 120.0),   # 6 — masthead
)
AMAZON_TC: float = 0.40                  # constant 2.5:1 ellipse (thickness / chord)
AMAZON_TOTAL_MAST_M: float = 25.630      # heel → masthead
AMAZON_SAIL_TRACK_M: float = 21.938      # ≈ wing length (root → masthead)
AMAZON_DECK_OD_M: float = 0.500          # deck-partners bearing (upper journal)
AMAZON_HEEL_OD_M: float = 0.450          # heel bearing (lower journal)

# --- Design loads (his own; `D-AMZ-2`) — apples-to-apples benchmark ------------------------
AMAZON_RM_NM: float = 251.0e3            # max righting moment = 185,000 ft·lbf
AMAZON_FOS: float = 2.5                  # Sponberg's Amazon-era factor of safety
AMAZON_DESIGN_MOMENT_NM: float = AMAZON_RM_NM * AMAZON_FOS   # 627 kN·m design / mast


def ellipse_coords(n_per_side: int = 80) -> np.ndarray:
    """Unit-chord 2.5:1 ellipse (t/c = ``AMAZON_TC``) as an (N, 2) contour in the project
    ordering (upper-TE → LE → lower-TE, cosine-spaced, **duplicate TE at the end** so it drops
    straight into ``wing._section_face``). x ∈ [0, 1] (LE→TE), y = ±(t/c)/2·√(1−((x−½)/½)²)."""
    theta = np.linspace(0.0, np.pi, int(n_per_side))      # x: LE(0) → TE(1), cosine-spaced
    x = 0.5 * (1.0 - np.cos(theta))
    y = (AMAZON_TC / 2.0) * np.sqrt(np.clip(1.0 - ((x - 0.5) / 0.5) ** 2, 0.0, 1.0))
    upper = np.column_stack([x[::-1], y[::-1]])           # TE → LE (inclusive of LE)
    lower = np.column_stack([x[1:], -y[1:]])              # LE(+1) → TE  (skip the LE duplicate)
    return np.vstack([upper, lower])                      # ends at TE (1,0) = duplicate of start


@dataclass(frozen=True)
class AmazonMastSpec:
    """Project-Amazon mast OML (one mast). All lengths in metres. The OML is fixed — only the
    discretisation knobs and the (sensitivity-swept) ``bury`` are free."""

    sail_track_length: float = AMAZON_SAIL_TRACK_M       # wing length, root → masthead
    below_root_length: float = AMAZON_TOTAL_MAST_M - AMAZON_SAIL_TRACK_M   # root → heel (3.692 m)
    transition_length: float = 0.40                      # ellipse → OD500 morph (gooseneck/collar)
    deck_od: float = AMAZON_DECK_OD_M                    # upper journal bearing OD
    heel_od: float = AMAZON_HEEL_OD_M                   # lower journal bearing OD
    rotation_center_xc: float = 0.50                     # rotation axis at the ellipse centre
    n_wing_sections: int = len(AMAZON_STATIONS_MM)       # = 7 stations
    n_transition_sections: int = 4
    n_airfoil_points: int = 160

    # --- station data --------------------------------------------------------------------
    @property
    def _station_fracs(self) -> np.ndarray:
        return np.linspace(0.0, 1.0, self.n_wing_sections)

    @property
    def _station_chords_m(self) -> np.ndarray:
        return np.array([c for c, _ in AMAZON_STATIONS_MM]) / 1000.0

    @property
    def root_chord(self) -> float:
        return float(self._station_chords_m[0])          # 0.750 (station 0, max)

    @property
    def tip_chord(self) -> float:
        return float(self._station_chords_m[-1])         # 0.300 (masthead)

    # --- chord / thickness along the span (modified-entasis taper) -----------------------
    def chord_at_z(self, z: float) -> float:
        """Chord at span height z. For z ≤ 0 the root chord (station 0); for z > 0 the
        published entasis taper (linear-interpolated between the seven station chords)."""
        if z <= 0.0:
            return self.root_chord
        f = min(z / self.sail_track_length, 1.0)
        return float(np.interp(f, self._station_fracs, self._station_chords_m))

    def thickness_at_z(self, z: float) -> float:
        """Section thickness = constant 2.5:1 (t/c = 0.40) × chord."""
        return AMAZON_TC * self.chord_at_z(z)

    def section_oml(self, z: float, n_pts: int | None = None) -> np.ndarray:
        """Closed OML cross-section polyline (x, y) [m] at height z, centred on the rotation
        axis. Wing (z ≥ 0): the chord-scaled ellipse. Transition/stock (z < 0): morph to the
        round bearing. Traversed upper-TE → LE → lower-TE (first == last at the TE)."""
        n = n_pts if n_pts is not None else self.n_airfoil_points
        contour = ellipse_coords(n // 2)
        if z >= 0.0:
            chord, diameter, blend = self.chord_at_z(z), self.deck_od, 0.0
        elif z >= self.partners_z:
            chord = self.root_chord
            diameter = self.deck_od
            blend = _transition_blend(-z / self.transition_length)
        else:
            chord = self.root_chord
            diameter = self._stock_od_at_z(z)
            blend = 1.0
        c = (contour - np.array([self.rotation_center_xc, 0.0])) * chord
        theta = np.arctan2(c[:, 1], c[:, 0])
        circle = 0.5 * diameter * np.column_stack([np.cos(theta), np.sin(theta)])
        return (1.0 - blend) * c + blend * circle

    def _stock_od_at_z(self, z: float) -> float:
        """Linear OD taper deck_od (partners) → heel_od (heel) along the bury."""
        span = self.partners_z - self.heel_z             # = bury (positive)
        u = (self.partners_z - z) / span if span > 0 else 0.0
        return self.deck_od + float(np.clip(u, 0.0, 1.0)) * (self.heel_od - self.deck_od)

    # --- journals / zones ----------------------------------------------------------------
    @property
    def partners_z(self) -> float:
        """Deck-partners station (upper journal, OD 500)."""
        return -self.transition_length

    @property
    def heel_z(self) -> float:
        """Heel station (lower journal, OD 450)."""
        return -self.below_root_length

    @property
    def bury(self) -> float:
        """Partners → heel spacing (the bearing-couple arm). F_bearing = M_base / bury."""
        return self.partners_z - self.heel_z

    @property
    def journal_stations(self) -> tuple[float, float]:
        return (self.partners_z, self.heel_z)

    @property
    def total_length(self) -> float:
        return self.sail_track_length + self.below_root_length

    # --- duck-type bridge so the audited box-spar partition + check_fit work unchanged ----
    # (`box_spars.mast_box_spar_sections` / `fit.check_fit` consume `span`, `_contour(frac)`,
    #  `chord_at_z`, `rotation_center_xc`). The OML stays frozen — no geometry DV is exposed.
    @property
    def span(self) -> float:
        return self.sail_track_length

    def _contour(self, _frac: float = 0.0) -> np.ndarray:
        """Unit-chord section contour (constant 2.5:1 ellipse; ``_frac`` unused — the section
        shape is span-invariant, only the chord scales)."""
        return ellipse_coords(self.n_airfoil_points // 2)


def build_amazon_mast_solid(spec: AmazonMastSpec):
    """Loft the Amazon wing + transition + tapering round stock as one solid (`ruled=True`).

    Sections run masthead (tip) → heel so the loft proceeds one way: chord-scaled ellipse over
    the wing, a smoothstep morph to the OD500 deck circle, then a straight OD500→OD450 stock
    taper to the heel.
    """
    pivot = spec.rotation_center_xc
    n = spec.n_airfoil_points
    contour = ellipse_coords(n // 2)
    sections: list = []

    # Wing: masthead (station 6) → root (station 0), chord-scaled ellipse (entasis taper).
    for i in reversed(range(spec.n_wing_sections)):
        z = spec._station_fracs[i] * spec.sail_track_length
        face = _section_face(spec.chord_at_z(z), 0.0, pivot, spec.deck_od,
                             blend=0.0, n_pts=n, contour=contour)
        sections.append(Plane(origin=(0.0, 0.0, z)) * face)

    # Transition: root ellipse (blend 0 at z=0) → OD500 deck circle (blend 1 at partners).
    for j in range(1, spec.n_transition_sections + 2):
        u = j / (spec.n_transition_sections + 1)
        z = -spec.transition_length * u
        face = _section_face(spec.root_chord, 0.0, pivot, spec.deck_od,
                             blend=_transition_blend(u), n_pts=n, contour=contour)
        sections.append(Plane(origin=(0.0, 0.0, z)) * face)

    # Stock: straight OD500 (partners) → OD450 (heel) taper.
    heel_face = _section_face(spec.root_chord, 0.0, pivot, spec.heel_od,
                              blend=1.0, n_pts=n, contour=contour)
    sections.append(Plane(origin=(0.0, 0.0, spec.heel_z)) * heel_face)

    with BuildPart() as part:
        for face in sections:
            add(face)
        loft(ruled=True)
    return part.part
