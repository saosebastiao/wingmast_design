"""Phase-0 groundwork: exercise the re-scoped scaffolding end-to-end.

Demonstrates the deliverables of `docs/specs/00-rescope-groundwork/`:

  1. the **typed structural load layer** (`wingmast_design.load_cases`) — the legacy
     shell-beam collection plus a forward Oyster-595-stub, showing the Article-IV
     serviceability gate (deflection/twist apply to operational cases only);
  2. the **promoted FEA section builder** (`beams.build_sections_from_result`),
     single-sourced out of `runs/` (Article XII);
  3. a round-tripped **CAD assembly export** (STL + STEP) via the existing
     `beams.build_assembly` — the standing assembly-viz export (Article XI).

Phase 0 ships no sizing optimum, so the load magnitudes are deliberately the legacy
values / placeholders; the Oyster-595 numbers land in Phase A (gates D-1/D-2/D-4).

Run: `just example 53_rescope_groundwork`
"""
from __future__ import annotations

import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from build123d import export_step, export_stl

from wingmast_design.beams import build_assembly, build_sections_from_result
from wingmast_design.geometry import medium_wingsail
from wingmast_design.load_cases import (
    CaseCategory,
    StructuralLoadCase,
    legacy_shellbeam_cases,
)
from wingmast_design.viz import show_in_viewer


def _print_cases(title: str, cases: tuple[StructuralLoadCase, ...]) -> None:
    print(f"\n{title}")
    print(f"  {'name':<14}{'category':<15}{'serviceability':<15}{'accel (m/s^2)'}")
    for c in cases:
        flag = "yes" if c.serviceability_applies else "NO (ultimate-only)"
        print(f"  {c.name:<14}{c.category.value:<15}{flag:<15}{c.accel}")


def main() -> None:
    t0 = time.perf_counter()

    # 1) Typed structural load layer ------------------------------------------------
    _print_cases("Legacy shell-beam structural cases (single-sourced from src/):",
                 legacy_shellbeam_cases())

    # A forward Oyster-595 *stub* — values are placeholders (Phase A pins them), but
    # the category drives the serviceability gate exactly as the real cases will.
    oyster_stub = (
        StructuralLoadCase("OP-2", CaseCategory.OPERATIONAL,
                           accel=(0.0, 9.81 * np.sin(np.radians(25.0)), -9.81 * np.cos(np.radians(25.0))),
                           buckling_safety_factor=1.5,
                           description="worst single mast 70:30 (placeholder heel)"),
        StructuralLoadCase("SURV-1f", CaseCategory.SURVIVAL,
                           accel=(0.0, 0.0, -9.81), buckling_safety_factor=3.0,
                           description="feathering-fault off-axis (placeholder)"),
    )
    _print_cases("Forward Oyster-595 stub (magnitudes are placeholders — Phase A):",
                 oyster_stub)
    surv = [c for c in oyster_stub if not c.serviceability_applies]
    print(f"\n  Article-IV check: {len(surv)} survival case(s) correctly exclude "
          f"serviceability limits: {[c.name for c in surv]}")

    # 2) Promoted FEA section builder ----------------------------------------------
    # Minimal sized-result stand-in (Phase 0 has no optimum): solid circular beams,
    # so the model argument is unused and the builder returns circular sections.
    stub_result = SimpleNamespace(
        radii=np.array([0.030, 0.025, 0.020]), t_hollow=None, r_tube=None, t_wall=None)
    sections, gusset, _gusset_sec = build_sections_from_result(None, stub_result)
    print(f"\nbuild_sections_from_result (promoted to src/): {len(sections)} sections, "
          f"areas mm^2 = {[round(s.A * 1e6, 1) for s in sections]}; gusset={gusset}")

    # 3) CAD assembly export (round-trip STL + STEP) -------------------------------
    spec = medium_wingsail
    asm = build_assembly(spec)
    out = Path(__file__).resolve().parent.parent / "exports"
    out.mkdir(exist_ok=True)
    export_stl(asm, str(out / "groundwork_assembly.stl"))
    export_step(asm, str(out / "groundwork_assembly.step"))
    print(f"\nWrote {out}/groundwork_assembly.{{stl,step}} "
          f"({len(asm.children)} children)")

    print(f"\nDONE in {time.perf_counter() - t0:.1f} s")
    show_in_viewer(asm, names=["groundwork_assembly"])


if __name__ == "__main__":
    main()
