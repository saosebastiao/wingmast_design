"""Phase-0 re-scope groundwork acceptance tests (`docs/specs/00-rescope-groundwork/`).

Fast, no-FEA unit checks that the scaffolding the later phases build on is in place:
the typed structural load layer + its Article-IV serviceability gate (`R-GND-5`), the
byte-identical promotion of the structural constants (`R-GND-6`), the promoted section
builder (`R-GND-7`), the dinghy-aero / tube-spar / truss legacy quarantine
(`R-GND-1/2/3`), and the absence of dangling shell-beam doc links (`R-GND-4`).
"""
from __future__ import annotations

import dataclasses
import re
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]


# --- R-GND-5: typed structural load case + serviceability gate (Article IV) ---------

def test_case_category_serviceability_gate():
    from wingmast_design.load_cases import CaseCategory

    assert CaseCategory.OPERATIONAL.serviceability_applies is True
    # Survival + manufacturing cases MUST NOT carry serviceability (deflection/twist)
    # limits — never size to a serviceability idealisation (Constitution Article IV).
    assert CaseCategory.SURVIVAL.serviceability_applies is False
    assert CaseCategory.MANUFACTURING.serviceability_applies is False


def test_structural_load_case_is_frozen_and_gated():
    from wingmast_design.load_cases import CaseCategory, StructuralLoadCase

    op = StructuralLoadCase(
        name="op", category=CaseCategory.OPERATIONAL,
        accel=(0.0, 0.0, -9.81), buckling_safety_factor=1.5,
    )
    surv = dataclasses.replace(op, name="surv", category=CaseCategory.SURVIVAL)
    assert op.serviceability_applies is True
    assert surv.serviceability_applies is False
    with pytest.raises(dataclasses.FrozenInstanceError):
        op.name = "mutated"  # type: ignore[misc]


# --- R-GND-6: byte-identical constant promotion (single source, Article XII) ---------

def test_promoted_constants_byte_identical():
    from wingmast_design import load_cases as lc

    # Exactly the former runs/chain_rebuild.py literals, recomputed the same way.
    assert lc.GRAVITY_MS2 == 9.81
    assert lc.LEGACY_HEEL_RAD == np.radians(30.0)
    g, th = 9.81, np.radians(30.0)
    assert lc.LEGACY_ACCELS == (
        (0.0, 0.0, -g),
        (0.0, g * np.sin(th), -g * np.cos(th)),
    )
    assert lc.LEGACY_BUCKLING_SF == 1.5
    assert lc.SKIN_DATUM == (0.0, 0.0, 1.0)
    # Back-compat aliases the legacy run scripts import are the same objects.
    assert (lc.G0, lc.TH, lc.ACCELS, lc.SF, lc.DATUM) == (
        lc.GRAVITY_MS2, lc.LEGACY_HEEL_RAD, lc.LEGACY_ACCELS,
        lc.LEGACY_BUCKLING_SF, lc.SKIN_DATUM,
    )


def test_legacy_shellbeam_cases_are_operational():
    from wingmast_design.load_cases import LEGACY_ACCELS, legacy_shellbeam_cases

    cases = legacy_shellbeam_cases()
    assert len(cases) == 2
    assert all(c.serviceability_applies for c in cases)  # both operational
    assert (cases[0].accel, cases[1].accel) == LEGACY_ACCELS


def test_runs_chain_rebuild_no_longer_redefines_constants_or_builder():
    """R-GND-6/7: the chain script sources the constants + section builder from
    src/ — it must not redefine them locally any more."""
    src = (REPO / "runs" / "chain_rebuild.py").read_text()
    assert "G0 = 9.81" not in src
    assert "def build_sections_from_result" not in src
    assert "from wingmast_design.load_cases import" in src


# --- R-GND-7: promoted FEA section builder is importable from src/ -------------------

def test_build_sections_from_result_promoted():
    from wingmast_design.beams import build_sections_from_result

    assert callable(build_sections_from_result)


# --- R-GND-1/2/3: legacy quarantine off the forward API -----------------------------

def test_dinghy_aero_off_forward_api():
    import wingmast_design.aero as aero

    assert "DESIGN_CASES" not in aero.__all__
    assert "LoadCase" not in aero.__all__
    # Still importable via the direct (frozen-legacy) module path.
    from wingmast_design.aero.cases import DESIGN_CASES  # noqa: F401


def test_tube_spar_off_forward_api():
    import wingmast_design.structural as structural

    assert "size_tube_spar" not in structural.__all__
    assert "TubeSparSizing" not in structural.__all__
    from wingmast_design.structural.beam import size_tube_spar  # noqa: F401


def test_legacy_modules_marked_frozen_or_archived():
    import wingmast_design.aero.cases as cases
    import wingmast_design.structural.beam as beam
    import wingmast_design.truss as truss

    assert "FROZEN LEGACY" in (cases.__doc__ or "")
    assert "FROZEN LEGACY" in (beam.__doc__ or "")
    assert "ARCHIVED" in (truss.__doc__ or "")


def test_top_level_package_does_not_export_legacy():
    import wingmast_design as wm

    for sym in ("DESIGN_CASES", "LoadCase", "size_tube_spar", "TubeSparSizing"):
        assert sym not in getattr(wm, "__all__", [])


def test_forward_aero_solver_decoupled_from_frozen_cases():
    """Import-graph (not just __all__) check: the forward aero solver must not import
    the frozen dinghy module. `LoadCase` (the type) lives in aero.loads; only the
    dinghy *values* are in aero.cases. The sole src/ importer of the frozen module is
    the bannered-legacy scenario.py (its DESIGN_CASES default, pending Phase-A)."""
    src = REPO / "src" / "wingmast_design"
    for mod in ("aero/loads.py", "aero/model.py", "aero/__init__.py"):
        text = (src / mod).read_text()
        assert not re.search(r"^\s*from\s+[\w.]*\bcases\s+import", text, re.M), \
            f"forward aero module {mod} imports the frozen cases"
    # LoadCase is single-typed: cases re-exports the loads definition.
    from wingmast_design.aero.cases import LoadCase as LC_cases
    from wingmast_design.aero.loads import LoadCase as LC_loads
    assert LC_cases is LC_loads
    # Audit every src/ module: the only importer of the frozen aero.cases is scenario.py.
    importers = [
        p.name for p in src.rglob("*.py")
        if re.search(r"^\s*from\s+[\w.]*\bcases\s+import", p.read_text(), re.M)
    ]
    assert set(importers) <= {"scenario.py"}, f"unexpected frozen-cases importers: {importers}"
    assert "LEGACY" in (src / "scenario.py").read_text()[:700]  # sole importer is bannered


def test_no_runs_script_redefines_promoted_constants():
    """R-GND-6 'defined once': no runs/ script re-derives the promoted G0/TH scalars."""
    offenders = []
    for p in (REPO / "runs").glob("*.py"):
        text = p.read_text()
        if "G0 = 9.81" in text or "TH = np.radians(30.0)" in text:
            offenders.append(p.name)
    assert offenders == [], f"runs scripts still re-derive promoted constants: {offenders}"


# --- R-GND-4: no dangling shell-beam doc links --------------------------------------

@pytest.mark.parametrize("doc", ["findings.md", "plan.md"])
def test_no_dangling_shellbeam_doc_links(doc):
    """Markdown links `](...X.md...)` whose target file was removed by the re-scope
    must be gone. Descriptive *mentions* of the filenames (no `](`) are allowed."""
    text = (REPO / "docs" / doc).read_text()
    links = re.findall(r"\]\(([^)]+)\)", text)
    for target in links:
        path_part = target.split("#", 1)[0]
        assert "improvement_backlog.md" not in path_part, f"dangling link in {doc}: {target}"
        assert "guided_generative_design.md" not in path_part, f"dangling link in {doc}: {target}"
