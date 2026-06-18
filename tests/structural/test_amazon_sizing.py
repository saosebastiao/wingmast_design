"""Phase-X2 — Amazon as-built mast mass estimate (`R-AMZ-3`)."""
from __future__ import annotations

import numpy as np
import pytest

from wingmast_design.geometry.amazon_mast import AmazonMastSpec
from wingmast_design.structural.amazon_sizing import (
    AmazonSizingParams,
    amazon_mass_band,
    box_props,
    design_moment_at_z,
    estimate_amazon_mast_mass,
    round_props,
    size_wall_at_z,
)


def test_box_props_match_hand_calc():
    """Thin-walled rectangular box: I_heel = w·t·(h/2)²·2 + t·h³/6, A = 2t(w+h)."""
    chord, thick, t_wall, fc, ft = 0.75, 0.30, 0.012, 0.60, 0.70
    w, h = fc * chord, ft * thick
    bp = box_props(chord, thick, t_wall, fc, ft)
    assert bp.A == pytest.approx(2 * t_wall * (w + h))
    assert bp.I_heel == pytest.approx(w * t_wall * (h / 2) ** 2 * 2 + t_wall * h ** 3 / 6)
    assert bp.S_heel == pytest.approx(bp.I_heel / (h / 2))
    assert bp.panel == pytest.approx(w)
    # heeling axis (depth = thickness) is the WEAK axis: I_heel < I_chord
    assert bp.I_heel < bp.I_chord


def test_round_props_match_hand_calc():
    rp = round_props(0.5, 0.015)
    assert rp.A == pytest.approx(np.pi * 0.5 * 0.015)
    assert rp.I_heel == pytest.approx(np.pi * 0.5 ** 3 * 0.015 / 8)
    assert rp.panel == pytest.approx(0.5)


def test_moment_envelope_zero_top_max_partners_zero_heel():
    s = AmazonMastSpec()
    m0 = 627.0e3
    assert design_moment_at_z(s.sail_track_length, s, m0) == pytest.approx(0.0)   # masthead
    assert design_moment_at_z(0.0, s, m0) == pytest.approx(m0)                     # wing root
    assert design_moment_at_z(s.partners_z, s, m0) == pytest.approx(m0)            # partners (max)
    assert design_moment_at_z(s.heel_z, s, m0) == pytest.approx(0.0)               # heel
    # monotone decreasing up the wing, decreasing down the stock
    assert design_moment_at_z(5.0, s, m0) > design_moment_at_z(15.0, s, m0)
    assert design_moment_at_z(-1.0, s, m0) > design_moment_at_z(-3.0, s, m0)


def test_wall_is_buckling_floor_and_matches_sponberg_box():
    """The wing is governed by Sponberg's t ≥ 0.03·panel floor; the root wall reproduces his
    ~12.7 mm box annotation (model validation)."""
    s = AmazonMastSpec()
    p = AmazonSizingParams()
    t_root, gov = size_wall_at_z(0.0, s, p)
    assert gov == "buckling-floor"
    assert t_root == pytest.approx(p.buckle_t_over_panel * p.box_frac_chord * s.root_chord)
    assert 12.0e-3 < t_root < 15.0e-3        # ≈ Sponberg's 12.7 mm box


def test_mass_estimate_is_reasonable_and_consistent():
    s = AmazonMastSpec()
    r = estimate_amazon_mast_mass(s)
    assert r.mass_both_masts_kg == pytest.approx(2.0 * r.mass_per_mast_kg)
    assert r.carbon_box_kg > r.fairing_kg > 0.0        # box is the primary mass
    # a free-standing Open-60 carbon mast: a few hundred kg/mast
    assert 350.0 < r.mass_per_mast_kg < 1000.0
    # buckling-floor governs the whole wing; buckling reserve at operating load
    assert r.governing_fracs["buckling-floor"] > 0.95
    assert r.min_local_buckling_lambda > 1.5


def test_mass_grows_with_righting_moment_and_softer_allowable():
    s = AmazonMastSpec()
    base = estimate_amazon_mast_mass(s, AmazonSizingParams())
    # the buckling-floor wall is RM-independent, but the strength wall (and thus the stock /
    # any strength-governed region) grows with RM → mass non-decreasing in RM
    heavier_rm = estimate_amazon_mast_mass(s, AmazonSizingParams(rm_Nm=2.0 * 251e3))
    assert heavier_rm.mass_per_mast_kg >= base.mass_per_mast_kg - 1e-6
    # a thicker box fill ⇒ more wall area ⇒ more mass
    fatter = estimate_amazon_mast_mass(s, AmazonSizingParams(box_frac_chord=0.70))
    assert fatter.mass_per_mast_kg > base.mass_per_mast_kg


def test_sensitivity_band_is_ordered():
    band = amazon_mass_band()
    assert (band["low"].mass_both_masts_kg
            < band["central"].mass_both_masts_kg
            < band["high"].mass_both_masts_kg)
