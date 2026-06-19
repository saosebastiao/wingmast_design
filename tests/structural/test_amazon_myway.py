"""Phase-X3 — rebuild Amazon's OML with the project method (`R-AMZ-4`)."""
from __future__ import annotations

import numpy as np

from wingmast_design.geometry.amazon_mast import AmazonMastSpec
from wingmast_design.structural.amazon_myway import (
    MyWayParams,
    estimate_myway_mass,
    myway_fit,
    myway_section,
)
from wingmast_design.structural.amazon_sizing import estimate_amazon_mast_mass


def test_partition_is_manufacturable_for_3_and_4_spars():
    """R-AMZ-4: the box-spar / longeron / shell partition fits the frozen Amazon ellipse."""
    spec = AmazonMastSpec()
    for n in (3, 4):
        fit = myway_fit(spec, MyWayParams(n_cells=n))
        assert fit.feasible, f"{n}-spar build must pass check_fit"
        assert fit.members_valid


def test_closer_webs_lower_the_buckling_floor_wall():
    """More spars ⇒ smaller cell panel ⇒ lower buckling-floor wall (the project's lever vs
    Amazon's full-box-width floor)."""
    spec = AmazonMastSpec()
    # at the thin masthead region the buckling floor governs; the cell wall must shrink with n_cells
    z = 0.8 * spec.sail_track_length
    _, sec3, _ = myway_section(z, spec, MyWayParams(n_cells=3))
    _, sec4, _ = myway_section(z, spec, MyWayParams(n_cells=4))
    assert sec4.cell_width < sec3.cell_width
    # and Amazon's single-box floor (0.03 · full box width) is far thicker than either cell floor
    p = MyWayParams()
    amazon_floor = p.buckle_t_over_panel * p.box_frac_chord * spec.chord_at_z(z)
    assert sec3.cell_width < p.box_frac_chord * spec.chord_at_z(z)
    assert amazon_floor > p.buckle_t_over_panel * sec3.cell_width


def test_composite_section_keeps_the_soft_shell_feasible():
    """The modulus-weighted sizing must keep BOTH the 0° caps and the soft helical shell within
    their allowables (the naive geometric-I model overstressed the shell)."""
    spec = AmazonMastSpec()
    for n in (3, 4):
        r = estimate_myway_mass(spec, MyWayParams(n_cells=n))
        assert r.feasible
        assert r.max_cap_util <= 1.0 + 1e-6
        assert r.max_shell_util <= 1.0 + 1e-6


def test_myway_beats_sponberg_at_first_order():
    """The project method (multi-spar + longerons + structural FW shell) is lighter than
    Sponberg's single box + glass fairings at the same OML + loads, even before optimization."""
    spec = AmazonMastSpec()
    amz = estimate_amazon_mast_mass(spec)
    feasible = []
    for n in (3, 4):
        r = estimate_myway_mass(spec, MyWayParams(n_cells=n), amazon_per_mast_kg=amz.mass_per_mast_kg)
        if r.feasible:
            feasible.append(r)
            assert r.mass_per_mast_kg < amz.mass_per_mast_kg     # lighter than his
            assert r.vs_amazon_pct is not None and r.vs_amazon_pct < 0.0
    assert feasible, "at least one spar count feasible"
    # 3 spars is lighter than 4 here (fewer webs once the buckling floor is met)
    r3 = estimate_myway_mass(spec, MyWayParams(n_cells=3))
    r4 = estimate_myway_mass(spec, MyWayParams(n_cells=4))
    assert r3.mass_per_mast_kg < r4.mass_per_mast_kg


def test_mass_bookkeeping():
    spec = AmazonMastSpec()
    r = estimate_myway_mass(spec, MyWayParams(n_cells=3))
    assert r.mass_both_masts_kg == np.float64(2.0) * r.mass_per_mast_kg
    assert r.mass_per_mast_kg == r.wing_kg + r.stock_kg
    assert 400.0 < r.mass_per_mast_kg < 700.0
