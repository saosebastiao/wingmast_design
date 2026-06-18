"""Estimate Project Amazon's as-built mast mass (Phase X2, `R-AMZ-3`).

Reproduces Amazon *as Sponberg built and sized it* — a **carbon box spar** (the primary
structural element) inside the frozen 2.5:1 ellipse OML, with bonded glass LE/TE fairings as
non-structural mass — and his **own sizing rules** (`docs/respec_research/sponberg_amazon_prior_art.md`):

  * load = the boat's **max righting moment × FoS** (design = 2.5 × 251 = 627 kN·m/mast), spread
    constant from the partners to the gooseneck then tapered linearly to zero at the masthead and
    the heel (`D-AMZ-3`);
  * at each station the wall = the governing **max** of (a) the **strength** wall for M(z) at the
    laminate compressive allowable and (b) Sponberg's **section-shape buckling floor t ≥ 0.03·panel**
    (his "t/ID ≥ 0.03" rule for a 50–80 % UD laminate);
  * the heeling moment bends the mast in the **thickness** (300 mm) direction — the *weak* axis —
    which is exactly why his 2.5:1 depth matters; that governs the strength wall.

This is the mass figure his papers never published. It is a **first-order analytical estimate**
(closed-form thin-walled box section + Sponberg's wall law) with a sensitivity band over the
flagged derived inputs; deflection is FEA-verified (`solve_frame_journal`) and local buckling is
closed-form-verified. (The converged-mesh *eigen* buckling, Article III, runs in X3/X4 on the
meshed box-spar model where the geometric-stiffness machinery applies.)
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..geometry.amazon_mast import AMAZON_DESIGN_MOMENT_NM, AMAZON_RM_NM, AmazonMastSpec
from ..materials.unidir import T800_EPOXY, UDPly, laminate_stiffness
from .frame import BeamSection
from .journal_bc import JournalBC, solve_frame_journal


@dataclass(frozen=True)
class AmazonSizingParams:
    """The flagged, swept inputs behind the Amazon mass estimate (`D-AMZ-3..6`)."""

    box_frac_chord: float = 0.60          # box width / chord (rest = LE/TE glass fairings)
    box_frac_thick: float = 0.70          # box height / section thickness (the bending depth)
    sigma_allow_Pa: float = 600.0e6       # cap axial compressive allowable (70/15/15 prepreg, ~½ knockdown)
    buckle_t_over_panel: float = 0.03     # Sponberg's t/ID ≥ 0.03 section-shape floor
    rho_carbon: float = 1600.0            # carbon/epoxy laminate density [kg/m³]
    fairing_mass_frac: float = 0.25       # glass LE/TE fairing mass as a fraction of carbon box mass
    fos: float = 2.5                      # Sponberg's Amazon-era factor of safety
    rm_Nm: float = AMAZON_RM_NM           # boat max righting moment (per mast)
    n_int: int = 400                      # spanwise integration stations
    ply: UDPly = T800_EPOXY               # ~1996 prepreg carbon UD
    layup_f0: float = 0.70                # axial / ±45 / 90 (Sponberg 60–80 % UD)
    layup_f45: float = 0.15
    layup_f90: float = 0.15

    @property
    def design_moment_Nm(self) -> float:
        return self.fos * self.rm_Nm


# ---------------------------------------------------------------------------------------------
# Section properties (closed-form thin-walled)
# ---------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class SectionProps:
    A: float            # wall area [m²]
    I_heel: float       # 2nd moment about the chord axis (heeling, depth = thickness) [m⁴]
    I_chord: float      # 2nd moment about the normal axis (fore-aft, depth = chord) [m⁴]
    S_heel: float       # section modulus, heeling (weak) axis [m³]
    perimeter: float    # [m]
    panel: float        # widest unsupported panel (for the buckling floor) [m]


def box_props(chord: float, thickness: float, t_wall: float, fc: float, ft: float) -> SectionProps:
    """Thin-walled rectangular carbon box (width = fc·chord, height = ft·thickness) inside the
    ellipse. Heeling bends about the chord axis (depth = box height h)."""
    w = fc * chord
    h = ft * thickness
    I_heel = w * t_wall * (h / 2.0) ** 2 * 2.0 + t_wall * h ** 3 / 6.0   # flanges + webs
    I_chord = h * t_wall * (w / 2.0) ** 2 * 2.0 + t_wall * w ** 3 / 6.0
    S_heel = I_heel / (h / 2.0)
    return SectionProps(A=2.0 * t_wall * (w + h), I_heel=I_heel, I_chord=I_chord,
                        S_heel=S_heel, perimeter=2.0 * (w + h), panel=w)


def round_props(od: float, t_wall: float) -> SectionProps:
    """Thin-walled round bearing stock (below the deck)."""
    I = np.pi * od ** 3 * t_wall / 8.0
    return SectionProps(A=np.pi * od * t_wall, I_heel=I, I_chord=I,
                        S_heel=I / (od / 2.0), perimeter=np.pi * od, panel=od)


# ---------------------------------------------------------------------------------------------
# Design-moment envelope (Sponberg, D-AMZ-3) and the wall-sizing law
# ---------------------------------------------------------------------------------------------
def design_moment_at_z(z: float, spec: AmazonMastSpec, m_base_Nm: float) -> float:
    """Bending moment at height z: constant ``m_base`` from the partners to the wing root
    (gooseneck), tapering linearly to zero at the masthead and at the heel."""
    if z >= 0.0:                                              # wing: taper to 0 at masthead
        return m_base_Nm * max(0.0, 1.0 - z / spec.sail_track_length)
    if z >= spec.partners_z:                                  # partners→gooseneck: constant max
        return m_base_Nm
    return m_base_Nm * max(0.0, (z - spec.heel_z) / (spec.partners_z - spec.heel_z))  # stock→0 at heel


def _section_at_z(z: float, spec: AmazonMastSpec, t_wall: float, p: AmazonSizingParams) -> SectionProps:
    if z >= 0.0:
        return box_props(spec.chord_at_z(z), spec.thickness_at_z(z), t_wall,
                         p.box_frac_chord, p.box_frac_thick)
    if z >= spec.partners_z:                                  # transition: blend box↔round by area
        return box_props(spec.root_chord, spec.thickness_at_z(0.0), t_wall,
                         p.box_frac_chord, p.box_frac_thick)
    return round_props(spec._stock_od_at_z(z), t_wall)


def size_wall_at_z(z: float, spec: AmazonMastSpec, p: AmazonSizingParams) -> tuple[float, str]:
    """Sponberg's wall law at z: max of the strength wall (M / σ_allow) and the section-shape
    buckling floor (0.03·panel). Returns (t_wall, governing constraint name)."""
    m = design_moment_at_z(z, spec, p.design_moment_Nm)
    geom = _section_at_z(z, spec, 1.0, p)                     # unit-wall props (S, panel scale linearly)
    t_strength = m / (p.sigma_allow_Pa * geom.S_heel) if geom.S_heel > 0 else 0.0
    t_buckle = p.buckle_t_over_panel * geom.panel
    return (t_strength, "strength") if t_strength >= t_buckle else (t_buckle, "buckling-floor")


# ---------------------------------------------------------------------------------------------
# Mass estimate + verification
# ---------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class AmazonMassResult:
    mass_per_mast_kg: float
    mass_both_masts_kg: float
    carbon_box_kg: float
    fairing_kg: float
    stock_kg: float
    root_wall_mm: float
    governing_fracs: dict[str, float]    # span fraction governed by each constraint
    tip_defl_m: float
    tip_defl_pct_height: float
    min_local_buckling_lambda: float


def estimate_amazon_mast_mass(spec: AmazonMastSpec, p: AmazonSizingParams | None = None) -> AmazonMassResult:
    """Integrate Sponberg's sized wall along the mast → carbon box mass + glass fairings, ×2 masts.
    Deflection FEA-verified at the operational moment; local buckling closed-form-verified."""
    p = p or AmazonSizingParams()
    z_wing = np.linspace(0.0, spec.sail_track_length, p.n_int)
    z_below = np.linspace(spec.heel_z, 0.0, p.n_int // 4)

    # --- carbon box (wing, z ≥ 0) ---
    box_dm = []
    gov_count = {"strength": 0, "buckling-floor": 0}
    for z in z_wing:
        t_wall, gov = size_wall_at_z(z, spec, p)
        sec = _section_at_z(z, spec, t_wall, p)
        box_dm.append(sec.A * p.rho_carbon)
        gov_count[gov] += 1
    carbon_box_kg = float(np.trapezoid(box_dm, z_wing))
    root_wall_mm = size_wall_at_z(0.0, spec, p)[0] * 1e3

    # --- round bearing stock (below the deck) ---
    stock_dm = [(_section_at_z(z, spec, size_wall_at_z(z, spec, p)[0], p).A) * p.rho_carbon
                for z in z_below]
    stock_kg = float(np.trapezoid(stock_dm, z_below))

    fairing_kg = p.fairing_mass_frac * carbon_box_kg          # glass LE/TE fairings (non-structural)
    per_mast = carbon_box_kg + stock_kg + fairing_kg
    gov_total = sum(gov_count.values())
    gov_fracs = {k: v / gov_total for k, v in gov_count.items()}

    tip_defl, defl_pct = _verify_deflection(spec, p)
    lam = _verify_local_buckling(spec, p)

    return AmazonMassResult(
        mass_per_mast_kg=per_mast, mass_both_masts_kg=2.0 * per_mast,
        carbon_box_kg=carbon_box_kg, fairing_kg=fairing_kg, stock_kg=stock_kg,
        root_wall_mm=root_wall_mm, governing_fracs=gov_fracs,
        tip_defl_m=tip_defl, tip_defl_pct_height=defl_pct, min_local_buckling_lambda=lam,
    )


def _verify_deflection(spec: AmazonMastSpec, p: AmazonSizingParams) -> tuple[float, float]:
    """FEA deflection of the sized, tapered mast under the OPERATIONAL moment (RM_max, not the
    2.5× design) via journal BCs — Sponberg checks deflection at sailing load, not max design."""
    n_nodes = 40
    zs = np.linspace(spec.heel_z, spec.sail_track_length, n_nodes)
    nodes = np.column_stack([np.zeros(n_nodes), np.zeros(n_nodes), zs])
    elements = np.column_stack([np.arange(n_nodes - 1), np.arange(1, n_nodes)])
    A_lam, _, _ = laminate_stiffness(p.ply, f0=p.layup_f0, f45=p.layup_f45,
                                     f90=p.layup_f90, thickness=1.0)
    E = 0.9 * float(A_lam[0, 0])                              # cap axial laminate modulus (sets box EI)
    G = E / 2.6
    sections = []
    for a, b in elements:
        zc = 0.5 * (zs[a] + zs[b])
        t_wall = size_wall_at_z(zc, spec, p)[0]
        sec = _section_at_z(zc, spec, t_wall, p)
        # heeling bends about the chord axis (weak, I_heel); equivalent radius for the proxy
        sections.append(BeamSection(A=sec.A, Iy=sec.I_heel, Iz=sec.I_chord,
                                    J=sec.I_heel + sec.I_chord, r=np.sqrt(sec.I_heel / sec.A)))
    # operational lateral (heeling, +Y) load ∝ chord on the wing, scaled to RM_max at the partners
    loads = np.zeros((n_nodes, 6))
    wing = zs >= 0.0
    chords = np.array([spec.chord_at_z(z) if z >= 0 else 0.0 for z in zs])
    arm = zs - spec.partners_z
    w_shape = chords * wing
    denom = float(np.trapezoid(w_shape * arm, zs))
    w = w_shape * (p.rm_Nm / denom) if denom > 0 else w_shape
    # lump ∫w dz to nodal Fy (trapezoid tributary)
    dz = np.gradient(zs)
    loads[:, 1] = w * dz
    journal = JournalBC(partners_node=int(np.argmin(np.abs(zs - spec.partners_z))),
                        heel_node=0, k_radial_Npm=1e11, k_axial_Npm=1e11, k_torsion_Nm_rad=1e9)
    res, _ = solve_frame_journal(nodes, elements, sections, E=E, G=G, journal=journal, loads=loads)
    tip = abs(res.displacements[-1, 1])                       # +Y (athwartships) tip deflection
    return tip, 100.0 * tip / spec.sail_track_length


def _verify_local_buckling(spec: AmazonMastSpec, p: AmazonSizingParams) -> float:
    """Closed-form cap-compression (orthotropic plate) buckling margin at the sized walls —
    confirms Sponberg's t/0.03·panel floor leaves a section-shape-buckling reserve. Returns the
    min λ = σ_cr / σ_applied over the wing, evaluated at the **operating** load (RM_max — the
    physical maximum; the boat capsizes before it can load the mast to the 2.5× notional ultimate),
    eigen-only (no SF)."""
    _, D, _ = laminate_stiffness(p.ply, f0=p.layup_f0, f45=p.layup_f45, f90=p.layup_f90, thickness=1.0)
    lams = []
    for z in np.linspace(0.0, spec.sail_track_length, 60):
        t_wall, _ = size_wall_at_z(z, spec, p)
        if t_wall <= 0:
            continue
        sec = _section_at_z(z, spec, t_wall, p)
        m = design_moment_at_z(z, spec, p.rm_Nm)              # OPERATING moment (RM_max), not 2.5×
        sigma = m / sec.S_heel if sec.S_heel > 0 else 0.0     # cap compressive stress at operating M
        if sigma <= 0:
            continue
        D11 = D[0, 0] * t_wall ** 3                           # bending stiffness of the actual wall
        b = sec.panel                                         # unsupported flange width
        sigma_cr = 4.0 * np.pi ** 2 * D11 / (b ** 2 * t_wall)  # simply-supported plate, kc≈4
        lams.append(sigma_cr / sigma)
    return float(min(lams)) if lams else float("inf")


def amazon_mass_band(spec: AmazonMastSpec | None = None) -> dict[str, AmazonMassResult]:
    """Low / central / high mass over the flagged inputs (box fill, σ_allow, fairing, bury)."""
    spec = spec or AmazonMastSpec()
    central = AmazonSizingParams()
    low = AmazonSizingParams(box_frac_chord=0.55, box_frac_thick=0.65, sigma_allow_Pa=800e6,
                             fairing_mass_frac=0.15)
    high = AmazonSizingParams(box_frac_chord=0.65, box_frac_thick=0.75, sigma_allow_Pa=450e6,
                              fairing_mass_frac=0.40)
    spec_low = AmazonMastSpec(below_root_length=spec.below_root_length - 0.5)   # shorter bury
    spec_high = AmazonMastSpec(below_root_length=spec.below_root_length + 0.1)
    return {
        "low": estimate_amazon_mast_mass(spec_low, low),
        "central": estimate_amazon_mast_mass(spec, central),
        "high": estimate_amazon_mast_mass(spec_high, high),
    }
