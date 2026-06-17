"""Phase-G.5 — typed geometry parameter set with bounds + increments (`R-GG-5`)."""
from __future__ import annotations

import dataclasses

from wingmast_design.geometry.parameters import (
    GEOMETRY_PARAMS,
    MastGeometryParameters,
    Param,
)


def test_every_parameter_has_bounds_and_increment():
    assert len(GEOMETRY_PARAMS) >= 13
    for name, p in GEOMETRY_PARAMS.items():
        assert isinstance(p, Param)
        assert p.lower <= p.default <= p.upper, f"{name}: default outside bounds"
        assert p.increment > 0.0, f"{name}: non-positive increment"


def test_reference_is_within_bounds():
    ref = MastGeometryParameters.reference()
    assert ref.out_of_bounds() == []


def test_out_of_bounds_is_detected():
    bad = dataclasses.replace(MastGeometryParameters.reference(), blend_radius=0.5)
    assert "blend_radius" in bad.out_of_bounds()


def test_builds_geometry_objects():
    ref = MastGeometryParameters.reference()
    spec = ref.to_mast_spec()
    layout = ref.to_box_layout()
    assert spec.span == GEOMETRY_PARAMS["span"].default
    assert spec.rotation_center_xc == GEOMETRY_PARAMS["rotation_center_xc"].default
    assert layout.n_spars == int(GEOMETRY_PARAMS["n_box_spars"].default)
    assert layout.blend_radius == GEOMETRY_PARAMS["blend_radius"].default


def test_param_rejects_default_outside_bounds():
    import pytest

    with pytest.raises(AssertionError):
        Param(default=5.0, lower=0.0, upper=1.0, increment=0.1)
