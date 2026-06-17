"""Phase-G.2 — rotating wingmast geometry stack (`R-GG-2`, parent `R-GEO-1`/`R-GEO-2`)."""
from __future__ import annotations

import numpy as np

from wingmast_design.geometry.kulfan import CSTAirfoil, naca0018_cst
from wingmast_design.geometry.rotating_mast import (
    RotatingMastSpec,
    build_rotating_mast_solid,
)


def test_zone_extents_contiguous_and_ordered():
    s = RotatingMastSpec()
    z = s.zone_z_extents
    # bottom → top: heel ≤ stock ≤ partners ≤ transition ≤ root(0) ≤ tip
    assert z["heel_step"][0] == s.heel_z
    assert z["stock"] == (s.heel_z, s.partners_z)
    assert z["deck_partners"][0] == s.partners_z
    assert z["transition"] == (s.partners_z, 0.0)
    assert z["wing"] == (0.0, s.span)
    assert s.heel_z < s.partners_z < 0.0 < s.span
    # the bury (journal spacing) equals the stock length
    assert abs((s.partners_z - s.heel_z) - s.stock_length) < 1e-9


def test_journal_stations():
    s = RotatingMastSpec(transition_length=0.9, stock_length=3.1)
    upper, lower = s.journal_stations
    assert upper == -0.9              # deck-partners
    assert lower == -0.9 - 3.1        # heel-step
    assert upper > lower


def test_stock_fits_within_inscribed_circle():
    s = RotatingMastSpec()
    assert s.effective_stock_diameter == 2.0 * s.inscribed_stock_radius
    assert s.stock_fits()
    # an oversized explicit stock must report not-fitting (R-CON-1 precursor)
    big = RotatingMastSpec(stock_diameter=2.0 * s.inscribed_stock_radius + 0.5)
    assert not big.stock_fits()


def test_entasis_bow_profile():
    straight = RotatingMastSpec(entasis_frac=0.0)
    assert straight.entasis_offset(straight.span * 0.5) == 0.0
    bowed = RotatingMastSpec(entasis_frac=0.02)
    assert bowed.entasis_offset(0.0) == 0.0                     # zero at root
    assert abs(bowed.entasis_offset(bowed.span)) < 1e-9         # zero at tip
    assert bowed.entasis_offset(-1.0) == 0.0                    # straight below the root
    mid = bowed.entasis_offset(bowed.span * 0.5)
    assert mid > 0.0 and abs(mid - 0.02 * bowed.span) < 1e-9    # peak ≈ frac·span at mid


def test_airfoil_blend_endpoints():
    root = naca0018_cst()
    tip = CSTAirfoil(upper_weights=root.upper_weights * 0.6, lower_weights=root.lower_weights * 0.6)
    s = RotatingMastSpec(root_airfoil=root, tip_airfoil=tip)
    assert np.allclose(s.airfoil_at_frac(0.0).upper_weights, root.upper_weights)
    assert np.allclose(s.airfoil_at_frac(1.0).upper_weights, tip.upper_weights)
    mid = s.airfoil_at_frac(0.5).upper_weights
    assert np.allclose(mid, 0.5 * (root.upper_weights + tip.upper_weights))


def test_rotation_center_offset_shifts_inscribed_circle():
    """The rotational-center foil offset (`R-GEO-2`) moves the rotation axis on the chord;
    placing it nearer the thick mid-chord enlarges the inscribed stock circle."""
    fwd = RotatingMastSpec(rotation_center_xc=0.20).inscribed_stock_radius
    mid = RotatingMastSpec(rotation_center_xc=0.30).inscribed_stock_radius
    assert mid >= fwd  # 0.30c is closer to max-thickness (~0.30c for NACA-0018) → larger circle


def test_build_solid_spans_heel_to_tip():
    s = RotatingMastSpec(n_sections=4, n_transition_sections=2)
    solid = build_rotating_mast_solid(s)
    assert solid.is_valid
    assert solid.volume > 0.0
    bb = solid.bounding_box()
    assert abs(bb.min.Z - s.heel_z) < 1e-6      # heel at the bottom
    assert abs(bb.max.Z - s.span) < 1e-6        # tip at the top


def test_entasis_changes_the_solid():
    base = build_rotating_mast_solid(RotatingMastSpec(n_sections=4, n_transition_sections=2))
    bowed = build_rotating_mast_solid(
        RotatingMastSpec(n_sections=4, n_transition_sections=2, entasis_frac=0.03)
    )
    assert bowed.is_valid
    # the bow shifts material aft (+X) at mid-span → centre of mass moves in +X
    assert bowed.center().X > base.center().X + 1e-3
