"""Optimized specs for a scaled Amazon free-standing wingmast.

Two independent scales:
  * s_L (length)  = total_m / 25.63         — mast height
  * s_S (section) = stock_od_mm / 500        — chord / thickness / bearing-stock OD
If stock_od is omitted, s_S = s_L (pure geometric scale-up, RM ∝ L⁴). If stock_od is given, the
section is scaled independently (a fatter/slimmer mast at the same height); the LOAD stays at the
length-geometric RM (same boat) unless you pass an RM override — a fatter section just buys bending
depth. The optimal internal DVs re-solve per run (the cap layup, especially, shifts with the regime).

Usage: just py runs/scaled_optimize.py [TOTAL_M] [STOCK_OD_MM] [RM_kNm]
"""
import sys
import time
from dataclasses import replace

from wingmast_design.geometry.amazon_mast import AMAZON_RM_NM, AMAZON_TOTAL_MAST_M, AmazonMastSpec
from wingmast_design.structural.amazon_conformal import (
    ConformalParams,
    conformal_tip_deflection,
    estimate_conformal_mass,
    optimize_conformal,
)

TOTAL_M = float(sys.argv[1]) if len(sys.argv) > 1 else 38.0
STOCK_OD_MM = float(sys.argv[2]) if len(sys.argv) > 2 else None
RM_OVERRIDE = float(sys.argv[3]) * 1e3 if len(sys.argv) > 3 else None

S_L = TOTAL_M / AMAZON_TOTAL_MAST_M
S_S = (STOCK_OD_MM / 500.0) if STOCK_OD_MM else S_L         # 500 mm = Amazon deck stock OD
RM = RM_OVERRIDE if RM_OVERRIDE else AMAZON_RM_NM * S_L ** 4   # length-geometric (same boat) unless overridden


class ScaledMast:
    """Amazon spec with independent length (s_L) and section (s_S) scales."""

    def __init__(self, base: AmazonMastSpec, s_l: float, s_s: float):
        self.b, self.sl, self.ss = base, s_l, s_s

    # --- length-scaled (mast height / journal stations) ---
    @property
    def sail_track_length(self): return self.b.sail_track_length * self.sl
    @property
    def below_root_length(self): return self.b.below_root_length * self.sl
    @property
    def transition_length(self): return self.b.transition_length * self.sl
    @property
    def heel_z(self): return self.b.heel_z * self.sl
    @property
    def partners_z(self): return self.b.partners_z * self.sl
    @property
    def bury(self): return self.b.bury * self.sl
    @property
    def span(self): return self.sail_track_length
    @property
    def total_length(self): return self.sail_track_length + self.below_root_length
    # --- section-scaled (chord / thickness / bearing stock OD) ---
    @property
    def deck_od(self): return self.b.deck_od * self.ss
    @property
    def heel_od(self): return self.b.heel_od * self.ss
    @property
    def root_chord(self): return self.b.root_chord * self.ss
    @property
    def rotation_center_xc(self): return self.b.rotation_center_xc          # fraction — unscaled
    @property
    def n_airfoil_points(self): return self.b.n_airfoil_points

    def chord_at_z(self, z): return self.b.chord_at_z(z / self.sl) * self.ss
    def thickness_at_z(self, z): return self.b.thickness_at_z(z / self.sl) * self.ss
    def section_oml(self, z, n_pts=None): return self.b.section_oml(z / self.sl, n_pts) * self.ss
    def _stock_od_at_z(self, z): return self.b._stock_od_at_z(z / self.sl) * self.ss


spec = ScaledMast(AmazonMastSpec(), S_L, S_S)
print(f"=== {TOTAL_M:.0f} m mast | length×{S_L:.3f}, section×{S_S:.3f} "
      f"{'(geometric)' if abs(S_S-S_L)<1e-6 else '(independent section scale)'} ===")
print(f"  sail track {spec.sail_track_length:.1f} m | root {spec.chord_at_z(0)*1e3:.0f}×"
      f"{spec.thickness_at_z(0)*1e3:.0f} mm → masthead {spec.chord_at_z(spec.span)*1e3:.0f}×"
      f"{spec.thickness_at_z(spec.span)*1e3:.0f} mm | stock OD {spec.deck_od*1e3:.0f}(deck)→"
      f"{spec.heel_od*1e3:.0f}(heel) | RM {RM/1e3:.0f} kN·m (design {2.5*RM/1e3:.0f})"
      f"{'  [RM overridden]' if RM_OVERRIDE else ''}\n")

base = ConformalParams(rm_Nm=RM, n_int=70)
t0 = time.perf_counter()
print(f"{'n':>2} {'mass_kg':>8} {'wing':>6} {'stock':>6} {'rootcap_mm':>10} {'f0':>5} {'helix':>6} "
      f"{'λ':>5} {'tip_m':>6} {'tip_%':>6} {'gov':>9}")
runs = []
for n in (3, 4, 5, 6):
    b = optimize_conformal(spec, n, 1881.0, base=base, seed=1, maxiter=35, popsize=12, workers=1)
    p = replace(b.params, n_int=240)
    r = estimate_conformal_mass(spec, p)
    tip, pct = conformal_tip_deflection(spec, p)
    runs.append((n, r, p, tip, pct))
    print(f"{n:>2} {r.mass_per_mast_kg:8.0f} {r.wing_kg:6.0f} {r.stock_kg:6.0f} {r.root_cap_mm:9.1f}m "
          f"{p.layup_f0:5.2f} {p.shell_helix_deg:5.1f}° {r.min_buckle_lambda:5.2f} {tip:6.2f} {pct:5.1f}% "
          f"{max(r.governing_fracs, key=r.governing_fracs.get):>9}")
n, r, p, tip, pct = min(runs, key=lambda x: x[1].mass_per_mast_kg)
print(f"\nOPTIMUM: {n} cells → {r.mass_per_mast_kg:.0f} kg/mast ({2*r.mass_per_mast_kg:.0f} kg both), "
      f"cap {p.layup_f0*100:.0f}% 0°, root cap {r.root_cap_mm:.0f} mm, helix {p.shell_helix_deg:.0f}°, "
      f"tip {tip:.1f} m ({pct:.0f}%)   [wall {time.perf_counter()-t0:.0f} s]")

# write the design file the CAD export reads (regenerable; carries the length/section scales)
import json  # noqa: E402
from pathlib import Path  # noqa: E402

tag = f"{int(round(TOTAL_M))}m" + (f"_od{int(round(STOCK_OD_MM))}" if STOCK_OD_MM else "")
out = Path(__file__).resolve().parent.parent / "exports" / f"conformal_best_{tag}.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps({
    "n_cells": p.n_cells, "blend_radius": p.blend_radius, "t_web": p.t_web, "t_shell": p.t_shell,
    "shell_helix_deg": p.shell_helix_deg, "layup_f0": p.layup_f0, "layup_f45": p.layup_f45,
    "layup_f90": p.layup_f90, "s_l": S_L, "s_s": S_S, "mass_per_mast_kg": r.mass_per_mast_kg,
    "vs_amazon_pct": r.vs_amazon_pct, "cap_schedule": r.cap_schedule}, indent=2))
print(f"wrote {out}  →  export the CAD with:  TORSION_BOX_DESIGN={out} just example 62_amazon_torsion_box")
