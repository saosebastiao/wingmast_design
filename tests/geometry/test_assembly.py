"""Phase-G.6 — twin-rig assembly + the geometric-fit smoke test (`R-GG-6`, parent `G-1`)."""
from __future__ import annotations

import dataclasses

from wingmast_design.geometry.assembly import (
    assembly_fit,
    build_wingmast_assembly,
)
from wingmast_design.geometry.parameters import MastGeometryParameters


def test_assembly_is_two_valid_masts():
    asm = build_wingmast_assembly(MastGeometryParameters.reference())
    masts = list(asm.children)
    assert len(masts) == 2
    assert {m.label for m in masts} == {"mast_fore", "mast_aft"}
    for m in masts:
        assert m.is_valid
        assert m.volume > 0.0


def test_tandem_masts_separated_by_spacing():
    params = MastGeometryParameters.reference()
    asm = build_wingmast_assembly(params)
    by = {m.label: m for m in asm.children}
    dx = by["mast_aft"].center().X - by["mast_fore"].center().X
    assert abs(dx - params.mast_spacing) < 1e-6


def test_fit_smoke_passes_on_reference_and_bites_on_inflation():
    """R-GG-6: the geometric-fit check passes on the reference and FAILS when a member is
    inflated past the OML (the validator actually bites)."""
    ref = MastGeometryParameters.reference()
    assert assembly_fit(ref).feasible

    inflated = dataclasses.replace(ref, blend_radius=0.5)
    assert not assembly_fit(inflated).feasible
