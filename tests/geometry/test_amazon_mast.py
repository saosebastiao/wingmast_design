"""Phase-X1 — Project-Amazon baseline wingmast OML (`R-AMZ-1`, parent `R-GEO-1/2/3`)."""
from __future__ import annotations

import numpy as np

from wingmast_design.geometry.amazon_mast import (
    AMAZON_HEEL_OD_M,
    AMAZON_SAIL_TRACK_M,
    AMAZON_STATIONS_MM,
    AMAZON_TC,
    AMAZON_TOTAL_MAST_M,
    AmazonMastSpec,
    build_amazon_mast_solid,
    ellipse_coords,
)


def test_station_table_within_1mm():
    """R-AMZ-1: every published station's (chord, thickness) is reproduced within 1 mm."""
    s = AmazonMastSpec()
    for i, (cmm, tmm) in enumerate(AMAZON_STATIONS_MM):
        z = s._station_fracs[i] * s.sail_track_length
        assert abs(s.chord_at_z(z) * 1e3 - cmm) <= 1.0, f"station {i} chord"
        assert abs(s.thickness_at_z(z) * 1e3 - tmm) <= 1.0, f"station {i} thickness"


def test_constant_2p5_to_1_ellipse():
    """t/c = 0.40 (2.5:1) held constant the full wing length."""
    s = AmazonMastSpec()
    for z in np.linspace(0.0, s.sail_track_length, 25):
        c = s.chord_at_z(z)
        assert abs(s.thickness_at_z(z) / c - AMAZON_TC) < 1e-9


def test_entasis_taper_is_fatter_than_linear_in_midspan():
    """The published chord taper bows ABOVE a straight root→tip line (modified entasis)."""
    s = AmazonMastSpec()
    for z in np.linspace(2.0, s.sail_track_length - 2.0, 7):
        f = z / s.sail_track_length
        linear = s.root_chord + f * (s.tip_chord - s.root_chord)
        assert s.chord_at_z(z) >= linear - 1e-9          # never thinner than linear
    # and strictly fatter near mid-span (station 3 region)
    z_mid = 0.5 * s.sail_track_length
    linear_mid = 0.5 * (s.root_chord + s.tip_chord)
    assert s.chord_at_z(z_mid) > linear_mid + 0.05       # ~+112 mm bulge


def test_published_lengths_and_bury():
    s = AmazonMastSpec()
    assert abs(s.total_length - AMAZON_TOTAL_MAST_M) < 1e-6
    assert abs(s.sail_track_length - AMAZON_SAIL_TRACK_M) < 1e-6
    # bury (partners→heel) lands in Sponberg's 10–15%-of-length rule
    assert 0.10 <= s.bury / s.total_length <= 0.15


def test_journal_stations_ordered():
    s = AmazonMastSpec()
    upper, lower = s.journal_stations
    assert upper == s.partners_z and lower == s.heel_z
    assert upper > lower
    assert s.heel_z < s.partners_z < 0.0 < s.sail_track_length
    # heel stock OD is the published 450 mm
    assert abs(s._stock_od_at_z(s.heel_z) - AMAZON_HEEL_OD_M) < 1e-9


def test_ellipse_contour_is_a_proper_lens():
    e = ellipse_coords(80)
    assert e.ndim == 2 and e.shape[1] == 2
    # unit chord, both ends are points (lens), max half-thickness = t/c/2
    assert abs(e[:, 0].min()) < 1e-9 and abs(e[:, 0].max() - 1.0) < 1e-9
    assert abs(np.abs(e[:, 1]).max() - AMAZON_TC / 2.0) < 1e-3
    # project ordering: starts at the TE (1,0), passes the LE (0,0)
    assert np.allclose(e[0], [1.0, 0.0], atol=1e-9)
    assert np.min(np.hypot(e[:, 0], e[:, 1])) < 1e-9     # an LE point at the origin


def test_solid_is_valid_and_spans_heel_to_masthead():
    s = AmazonMastSpec()
    solid = build_amazon_mast_solid(s)
    assert solid.is_valid
    assert solid.volume > 0.0
    bb = solid.bounding_box()
    assert abs(bb.min.Z - s.heel_z) < 1e-3
    assert abs(bb.max.Z - s.sail_track_length) < 1e-3
    # root chord 0.75 m about the centred pivot ⇒ X within ±0.4 m
    assert bb.max.X <= 0.4 and bb.min.X >= -0.4
