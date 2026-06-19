"""Conformal-cell + longeron-channel + outer-shell cross-section geometry (`R-GG-3`, parent
`R-GEO-5`).

The prescribed build is **≥3 convex hollow cells** placed side-by-side inside the
airfoil, co-bonded; the **inter-cell longeron channels** are the voids their rounded
(blend-curve) corners leave at the shared interfaces; a **filament-wound outer shell** fairs
the assembly to the OML. This module produces that as a per-station **section set** (closed
2-D polylines) — the "section-set + loft" strategy (`D-GG-…`): light, OCC-boolean-free, and
directly meshable by Phase S. Lofting the sections spanwise into the assembly is Phase G.6.

The key coupling (`R-GEO-5`): the longeron-channel cross-section is **computed from the blend
radius** — rounding the cell corners with radius ``blend_radius`` leaves a void at each
web↔OML junction whose area grows as ``blend_radius²`` (`longeron_void_area`). That is the
blend-radius → channel-void → longeron strength/mass lever Phase O will trade.

Geometry frame at a station: x = chord (LE small-x → TE large-x), y = section normal.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

# A filleted 90° corner of radius r leaves, between the arc and the square corner, a void of
# area r²(1 - π/4). A longeron channel has 2 such corners (top + bottom of the shared web),
# and the channel is shared by the two adjacent cells → 2 sides ⇒ ~4 corner-voids.
_CORNER_VOID = 1.0 - np.pi / 4.0
_VOIDS_PER_CHANNEL = 4.0


def longeron_void_area(blend_radius: float) -> float:
    """Inter-cell longeron-channel void area implied by the blend-corner radius (the
    `R-GEO-5` coupling): ``≈ 4·r²·(1 - π/4)`` — monotone increasing in ``blend_radius``."""
    r = float(blend_radius)
    return _VOIDS_PER_CHANNEL * _CORNER_VOID * r * r


@dataclass(frozen=True)
class CellLayout:
    """Chordwise cell layout. ``web_fracs`` are the internal web positions as fractions
    of the chord (between LE and TE); ``None`` → even division into ``n_cells`` bands."""

    n_cells: int = 3
    web_fracs: tuple[float, ...] | None = None
    # Defaults sized for the bare-WINGMAST section (~0.5–1.0 m chord, ~0.1–0.18 m thick),
    # NOT the 4 m wingsail. The blend radius + walls are mm-scale for this small section.
    blend_radius: float = 0.015       # corner radius → longeron channel (m)
    cell_wall: float = 0.004          # geometry placeholder (true value sized in Phase O)
    shell_wall: float = 0.003         # geometry placeholder

    def web_positions(self, x_le: float, x_te: float) -> np.ndarray:
        """Internal web x-positions (n_cells - 1 of them) across the chord."""
        if self.web_fracs is not None:
            fr = np.asarray(self.web_fracs, dtype=float)
            assert len(fr) == self.n_cells - 1, "web_fracs must be n_cells-1 long"
        else:
            fr = np.arange(1, self.n_cells) / self.n_cells
        return x_le + fr * (x_te - x_le)


@dataclass(frozen=True)
class LongeronChannel:
    x: float                 # chordwise position of the shared web
    void_area: float         # from blend_radius (the coupling)
    polyline: np.ndarray     # representative channel cross-section


@dataclass(frozen=True, eq=False)
class CellSection:
    """The cell / longeron / shell section set at one station."""

    cells: list[np.ndarray]              # ≥3 cell outlines (closed, filleted corners)
    channels: list[LongeronChannel]      # inter-cell longeron channels
    outer_shell: np.ndarray              # OML polyline the wound shell follows
    webs: np.ndarray = field(default_factory=lambda: np.empty(0))


def _split_upper_lower(oml: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Split a project-ordered OML (upper-TE→LE→lower-TE) into upper & lower surfaces,
    each sorted LE→TE ascending in x."""
    le = int(np.argmin(oml[:, 0]))
    upper = oml[: le + 1][::-1]
    lower = oml[le:]
    return upper, lower


def _y_on(surface: np.ndarray, x: np.ndarray) -> np.ndarray:
    return np.interp(x, surface[:, 0], surface[:, 1])


def _fillet_corner(a: np.ndarray, c: np.ndarray, b: np.ndarray, r: float, n_arc: int = 6):
    """Round the corner at ``c`` (between edges c→a and c→b) with radius ``r``.

    Returns the arc points replacing ``c`` (tangent to both edges, trimmed by the available
    edge length). Falls back to ``[c]`` if the corner is too tight to fillet.
    """
    a, c, b = np.asarray(a, float), np.asarray(c, float), np.asarray(b, float)
    ua, ub = a - c, b - c
    la, lb = np.hypot(*ua), np.hypot(*ub)
    if la < 1e-9 or lb < 1e-9:
        return [c]
    ua, ub = ua / la, ub / lb
    cos_t = float(np.clip(np.dot(ua, ub), -1.0, 1.0))
    half = np.arccos(cos_t) / 2.0
    if half < 1e-6 or half > np.pi / 2 - 1e-6:
        return [c]
    trim = r / np.tan(half)                       # distance from corner to each tangent point
    trim = min(trim, 0.49 * la, 0.49 * lb)        # don't overrun the edges
    if trim < 1e-6:
        return [c]
    r_eff = trim * np.tan(half)
    pa, pb = c + ua * trim, c + ub * trim         # tangent points
    bis = ua + ub
    bis = bis / np.hypot(*bis)
    center = c + bis * (r_eff / np.sin(half))
    a0 = np.arctan2(pa[1] - center[1], pa[0] - center[0])
    a1 = np.arctan2(pb[1] - center[1], pb[0] - center[0])
    if a1 < a0 - np.pi:
        a1 += 2 * np.pi
    elif a1 > a0 + np.pi:
        a1 -= 2 * np.pi
    ang = np.linspace(a0, a1, n_arc)
    return [center + r_eff * np.array([np.cos(t), np.sin(t)]) for t in ang]


def _cell_outline(upper, lower, x_l, x_r, r_blend, is_le, is_te, n_chord=24):
    """One cell: OML-upper cap (x_l→x_r) + right web + OML-lower cap + left web,
    with the web↔OML corners filleted (radius ``r_blend``). LE/TE cells keep the nose/tail
    curve instead of a web on that side."""
    xs = np.linspace(x_l, x_r, n_chord)
    up = np.column_stack([xs, _y_on(upper, xs)])
    lo = np.column_stack([xs, _y_on(lower, xs)])
    # corners: top-left, top-right (web), bottom-right, bottom-left (web)
    out: list = []
    # top cap left→right. For an internal cell the top-LEFT corner (up[0]) is rounded by the
    # left-web fillet appended at the END — emitting the sharp up[0] here too would duplicate
    # the corner and self-cross the outline (the G-review HIGH finding); so emit up[0] only at
    # the LE cell, where the left side is the nose curve, not a web.
    if is_le:
        out += [up[0]]
    out += list(up[1:-1])
    # top-right corner → right web → bottom-right corner (fillet if internal web)
    if is_te:
        out += [up[-1], lo[-1]]                          # tail: caps meet at TE, no web
    else:
        out += _fillet_corner(up[-2], up[-1], lo[-1], r_blend)
        out += _fillet_corner(up[-1], lo[-1], lo[-2], r_blend)
    # bottom cap right→left
    out += list(lo[-2:0:-1])
    # bottom-left corner → left web → top-left corner (fillet if internal web)
    if is_le:
        out += [lo[0]]                                   # nose: caps meet at LE, no web
    else:
        out += _fillet_corner(lo[1], lo[0], up[0], r_blend)
        out += _fillet_corner(lo[0], up[0], up[1], r_blend)
    return np.asarray(out, float)


def cell_sections(oml: np.ndarray, layout: CellLayout) -> CellSection:
    """Partition an OML section into ≥3 filleted cells + the inter-cell longeron
    channels (void from the blend radius) + the outer-shell (= OML) polyline."""
    assert layout.n_cells >= 3, "R-GEO-5 requires ≥3 cells"
    upper, lower = _split_upper_lower(oml)
    x_le, x_te = float(upper[0, 0]), float(upper[-1, 0])
    webs = layout.web_positions(x_le, x_te)
    bounds = np.concatenate([[x_le], webs, [x_te]])

    cells = []
    for k in range(layout.n_cells):
        cells.append(_cell_outline(
            upper, lower, bounds[k], bounds[k + 1], layout.blend_radius,
            is_le=(k == 0), is_te=(k == layout.n_cells - 1),
        ))

    channels = []
    void = longeron_void_area(layout.blend_radius)
    half = 0.5 * np.sqrt(void)                       # equal-area square half-side
    for xw in webs:
        # `polyline` is a SCHEMATIC equal-area marker centred at the web (area == void_area);
        # the physical void is split between the top & bottom web↔OML corner junctions. The
        # load-bearing quantity is `void_area` (the blend-radius coupling), not this outline.
        y_mid = 0.5 * float(_y_on(upper, np.array([xw]))[0] + _y_on(lower, np.array([xw]))[0])
        poly = np.array([
            [xw - half, y_mid - half], [xw + half, y_mid - half],
            [xw + half, y_mid + half], [xw - half, y_mid + half],
        ])
        channels.append(LongeronChannel(x=float(xw), void_area=void, polyline=poly))

    return CellSection(cells=cells, channels=channels, outer_shell=np.asarray(oml, float),
                       webs=np.asarray(webs, float))


def mast_cell_sections(spec, z: float, layout: CellLayout) -> CellSection:
    """Convenience: build the cell section set at wing height ``z`` of a
    `RotatingMastSpec` (uses its blended CST OML at that station)."""
    frac = max(0.0, min(z / spec.span, 1.0))
    contour = spec._contour(frac)
    chord = spec.chord_at_z(z)
    oml = (contour - np.array([spec.rotation_center_xc, 0.0])) * chord
    return cell_sections(oml, layout)
