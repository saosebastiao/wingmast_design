"""Phase-A deliverable: the typed design-load collection + the D-2 verdict (`R-AE-7`, `G-2`).

Builds the OP-1/OP-2/SURV-1/SURV-1f/SURV-2 typed collection (per mast), names the governing
case, and prints the conditional D-2 feathering verdict with its derived breakevens — the
load envelope Phases S and O size against.

Run: `just example 55_aero_envelope`
"""
from __future__ import annotations

import time

from wingmast_design.aero import (
    design_load_collection,
    feathering_verdict,
    governing_case,
    op2,
)
from wingmast_design.aero.operational import rm_sensitivity_band


def main() -> None:
    t0 = time.perf_counter()
    coll = design_load_collection()

    print("Typed design-load collection (per mast) — Oyster-595 twin wingmast")
    print(f"  {'case':<9}{'category':<13}{'bending kN·m':<14}{'torque':<9}{'reserve':<9}{'eigen n≥24':<12}{'governs'}")
    for c in coll:
        print(f"  {c.name:<9}{c.category.value:<13}{c.design_bending_Nm / 1e3:<14.0f}"
              f"{c.design_torque_Nm / 1e3:<9.1f}{c.reserve_factor:<9}{str(c.eigen_verify):<12}{c.governs}")

    g = governing_case(coll)
    lo, hi = rm_sensitivity_band(0.70)
    print(f"\n  GOVERNING: {g.name} = {g.design_bending_Nm / 1e3:.0f} kN·m "
          f"(RM-band {lo / 1e3:.0f}–{hi / 1e3:.0f} kN·m over RM 150–225)")

    v = feathering_verdict(op2_bending_Nm=op2().design_bending_Nm)
    print(f"\n  D-2 (conditional): governs '{v.governing_case}' at central inputs; {v.conditions}")
    print(f"  feathering robustness: stable={v.stable}, Scruton {v.scruton_feathered:.0f} (robust), "
          f"fault FoS {v.fault_fos}")
    print(f"\nDONE in {time.perf_counter() - t0:.2f} s")


if __name__ == "__main__":
    main()
