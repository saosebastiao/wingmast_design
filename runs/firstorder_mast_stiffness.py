"""First-order stiffness/strength/buckling estimate for the bare box-spar wingmast.

A *representative* analytical check (NOT a converged FEA) to ground the geometry decision —
replacing the earlier non-representative toy (isotropic solid rod + tip point load). Here:

  * the operational load (OP-2, RM-capped base moment) is **distributed along the span** ∝ chord
    and **scaled so its moment about the base datum equals the design base moment** (so 160.5
    kN·m is reproduced by construction; the resultant arm is then *derived*, ~11 m, NOT pinned
    to the CE). The base datum is taken at z=0 (the wing root) for this first-order check — the
    0.9 m partners offset is absorbed into the simplification (a ~4% lever change the
    deflection/buckling conclusion is insensitive to);
  * the section is a **box spar with UD caps at the section depth** (E1 ~135 GPa carbon, the
    bending load path is the laid 0° longerons), tapering root→tip;
  * checked against R-PERF: deflection ≤ 2% span (0.44 m), strength R ≥ 2, and a first-order
    cap-compression local-buckling margin (with an orthotropic knockdown — see below).

Caveats (first-order, direction of error stated):
  * the local-buckling λ uses an isotropic plate formula knocked down by ``BUCKLE_KNOCKDOWN``
    to stand in for the orthotropic 0°-cap transverse softness (E2 ~ E1/16); the *isotropic*
    number is OPTIMISTIC by ~2–3×, so the knocked-down λ is the one to judge on, and even it is
    only a screen — Article III requires an eigen check at n≥24 for survival;
  * mass is **caps + webs** (the web/shear material grows ~linearly with depth), so the
    deepen-vs-widen comparison is mass-fair, not cap-only.

Run: `just py runs/firstorder_mast_stiffness.py`
"""
from __future__ import annotations

import numpy as np

# --- operational load (OP-2, per mast) ---
M_BASE = 160.5e3        # N·m design base bending at the partners (RM-capped; Phase A)
SPAN = 22.0             # m exposed wing
DEFL_LIMIT = 0.44       # m, 2% span (R-PERF-2, operational)

# --- material (UD T700/epoxy) ---
E_CAP = 110.0e9         # Pa, effective axial modulus of a 0°-dominated cap (E1 135 GPa, knocked down)
SIGMA_ALLOW = 1200.0e6  # Pa, UD compressive design allowable (conservative; basis §6)
RHO = 1600.0           # kg/m^3 CFRP
NU = 0.3
BUCKLE_KNOCKDOWN = 0.4  # orthotropic 0°-cap penalty on the isotropic plate σ_cr (first-order;
                        # transverse stiffness E2 ~ E1/16 ⇒ the isotropic formula is optimistic)


def analyse(chord_root=1.0, taper=0.6, tc=0.18, t_cap=0.004, box_frac=0.6, n_spars=3, n=400):
    z = np.linspace(0.0, SPAN, n)
    chord = chord_root * (1.0 + (taper - 1.0) * z / SPAN)
    depth = tc * chord                              # section thickness = bending depth

    # distributed load w(z) ∝ chord, SCALED so its moment about z=0 = M_BASE (reproduced exactly);
    # the resultant force + arm (centroid) are then derived, not assumed = CE.
    w = chord * (M_BASE / np.trapezoid(chord * z, z))   # N/m  ⇒  ∫ w·z dz = M_BASE
    F_total = np.trapezoid(w, z)
    centroid = np.trapezoid(w * z, z) / F_total         # derived resultant arm (≈ M_BASE/F)

    # bending moment M(z) = ∫_{z'≥z} w(z')·(z'−z) dz'
    M = np.array([np.trapezoid(w[z >= zi] * (z[z >= zi] - zi), z[z >= zi]) for zi in z])
    assert abs(M[0] - M_BASE) < 1e-3 * M_BASE, f"base moment {M[0]:.0f} != design {M_BASE:.0f}"

    # box section: caps (area b·t_cap at ±depth/2) dominate I; + a web contribution
    b = box_frac * chord
    A_cap = b * t_cap
    I = 2.0 * A_cap * (depth / 2.0) ** 2 + 2.0 * (t_cap * depth ** 3 / 12.0)
    EI = E_CAP * I

    # tip deflection: double-integrate curvature κ = M/EI (handles taper)
    kappa = M / EI
    slope = np.concatenate([[0.0], np.cumsum((kappa[:-1] + kappa[1:]) / 2 * np.diff(z))])
    defl = np.concatenate([[0.0], np.cumsum((slope[:-1] + slope[1:]) / 2 * np.diff(z))])
    tip_defl = defl[-1]

    # base bending stress + strength reserve
    sigma_base = M[0] * (depth[0] / 2.0) / I[0]
    R = SIGMA_ALLOW / sigma_base

    # first-order cap-compression local buckling: cap panel between webs (width b/n_spars).
    # isotropic plate formula × orthotropic knockdown (the isotropic value is OPTIMISTIC).
    b_panel = b[0] / n_spars
    sigma_cr_iso = 4.0 * np.pi ** 2 * E_CAP / (12.0 * (1 - NU ** 2)) * (t_cap / b_panel) ** 2
    sigma_cr = BUCKLE_KNOCKDOWN * sigma_cr_iso
    lam_buckle = sigma_cr / sigma_base

    # structural mass (this mast): both caps + two webs (web area t_cap·depth each) — mass-fair
    cap_mass = np.trapezoid(2.0 * A_cap, z) * RHO
    web_mass = np.trapezoid(2.0 * t_cap * depth, z) * RHO
    mass = cap_mass + web_mass

    return dict(tip_defl=tip_defl, defl_ratio=tip_defl / DEFL_LIMIT, centroid=centroid,
                sigma_base_MPa=sigma_base / 1e6, R=R, lam_buckle=lam_buckle, mass=mass,
                cap_mass=cap_mass, web_mass=web_mass, depth_root=depth[0])


def deflection_crossover_tc(lo=0.10, hi=0.80, **kw):
    """Bisection for the t/c at which tip deflection first meets the limit (other params fixed)."""
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if analyse(tc=mid, **kw)["defl_ratio"] <= 1.0:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


def line(label, r):
    flag = "OK " if r["defl_ratio"] <= 1.0 else "XX "
    print(f"  {flag}{label:<30} defl {r['tip_defl']:.2f} m ({r['defl_ratio']:.1f}× limit)  "
          f"σ {r['sigma_base_MPa']:.0f} MPa (R {r['R']:.1f})  buckling λ {r['lam_buckle']:.1f}  "
          f"mass {r['mass']:.0f} kg  depth {r['depth_root']:.2f} m")


if __name__ == "__main__":
    print(f"OP-2 base moment {M_BASE/1e3:.0f} kN·m, distributed ∝chord (resultant arm derived ≈ "
          f"{analyse()['centroid']:.1f} m); deflection limit {DEFL_LIMIT} m\n")
    print("Baseline mast (1.0 m chord, t/c 0.18, 4 mm caps):")
    line("baseline", analyse())
    print("\nDeeper section (raise t/c at the 1.0 m chord):")
    for tc in (0.18, 0.30, 0.45, 0.60):
        line(f"t/c {tc}", analyse(tc=tc))
    xc = deflection_crossover_tc()
    print(f"  → deflection crossover at t/c ≈ {xc:.2f} (1.0 m chord, 4 mm caps); "
          f"buckling λ there = {analyse(tc=xc)['lam_buckle']:.1f} (knocked-down, screen only)")
    print("\nLarger chord (keep t/c 0.18):")
    for c in (1.0, 2.0, 3.0, 4.0):
        line(f"chord {c} m", analyse(chord_root=c, taper=0.6))
    print("\nMore cap material (1.0 m chord, t/c 0.18):")
    for t in (0.004, 0.010, 0.020, 0.040):
        line(f"caps {t*1e3:.0f} mm", analyse(t_cap=t))
