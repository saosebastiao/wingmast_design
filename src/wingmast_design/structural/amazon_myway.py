"""Rebuild the Amazon OML with THIS project's manufacturing concept (Phase X3, `R-AMZ-4`).

Same frozen 2.5:1 ellipse, sized to the same Amazon loads/criteria — but built the project way:
**N filament-wound box spars** across the chord + **co-bonded UD channel longerons** in the
inter-spar voids + a **filament-wound outer shell** (`docs/specs/04-amazon-baseline/spec.md`).

The structural thesis vs Sponberg's single box + glass fairings:

  * **closer webs ⇒ smaller cap panels** — the buckling-floor wall is ``0.03·(cell width)``, and
    the cell width is ``box·chord / n_spars`` (vs his full box width). So the multi-spar wall drops
    OFF Amazon's buckling floor (13.5 mm) onto the much lower **strength** requirement — the
    material his section "wastes" on section-shape stability;
  * the **FW shell** is structural — it sits at the extreme fibre (±t/2, outboard of the box caps
    at ±h/2), so it carries bending and lets the caps be thinner — but it wraps the whole perimeter
    (a mass it must earn back);
  * the **UD longerons** add 0° bending material in the channels for free (the blend-radius void).

X3 sizes this first-order (cap wall = max(strength-with-shell-help, 0.03·cell-panel); web/shell at
manufacturing minima; longerons from the blend-radius void) for ``n_spars ∈ {3, 4}`` → mass vs the
X2 (his-construction) estimate. **X4 then OPTIMIZES** the wall/cap/shell/longeron distribution to
minimise mass — X3 is the starting point, not the optimum.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..geometry.amazon_mast import AmazonMastSpec
from ..geometry.box_spars import BoxSparLayout, longeron_void_area
from ..materials.unidir import (
    T800_EPOXY,
    UDPly,
    laminate_stiffness,
    reduced_stiffness_Q,
    transformed_Qbar,
)
from .amazon_sizing import AmazonSizingParams, design_moment_at_z, round_props, size_wall_at_z


def balanced_helical(ply: UDPly, helix_deg: float) -> tuple[float, float, float]:
    """Balanced ±θ filament-wound laminate (the wound shell). Returns:

      * **E_x** [Pa] — axial modulus (the ± pair cancels extension–shear coupling, so it stays
        near E1 at low θ: ~98 % at 5°, ~92 % at 10°, ~80 % at 15°);
      * **K** [Pa, per unit thickness] — orthotropic buckling coefficient √(D11·D22)+D12+2·D66;
      * **strength_frac** — first-ply axial design-strength fraction vs the 0° fibre value. The
        balance suppresses the per-ply matrix shear, so strength holds far better than a single
        off-axis ply would (~99 % at 5°, ~84 % at 10°, then transverse-limited: ~39 % at 15°).
    """
    Q = reduced_stiffness_Q(ply)
    th = np.radians(float(helix_deg))
    c, s = np.cos(th), np.sin(th)
    Qb = 0.5 * (transformed_Qbar(Q, float(helix_deg)) + transformed_Qbar(Q, -float(helix_deg)))
    Ex = Qb[0, 0] - Qb[0, 1] ** 2 / Qb[1, 1]
    Du = Qb / 12.0                                              # smeared per-unit-thickness D
    K = float(np.sqrt(Du[0, 0] * Du[1, 1]) + Du[0, 1] + 2.0 * Du[2, 2])
    # first-ply axial strength (max-stress), laminate-constrained (γ_xy = 0 for balanced ±θ)
    nuxy = Qb[0, 1] / Qb[1, 1]
    ex = 1.0 / Ex
    ey = -nuxy * ex
    e1, e2, g12 = ex * c * c + ey * s * s, ex * s * s + ey * c * c, 2.0 * (ey - ex) * s * c
    s1, s2, t12 = Q @ np.array([e1, e2, g12])                   # per unit applied σx
    cands = [ply.Xt_Pa / abs(s1) if s1 else 1e30,
             ply.Yt_Pa / abs(s2) if s2 else 1e30,
             ply.S12_Pa / abs(t12) if t12 else 1e30]
    return float(Ex), K, float(min(cands) / ply.Xt_Pa)


@dataclass(frozen=True)
class MyWayParams:
    """Internal design knobs for the project-method build (sized in X3, optimised in X4)."""

    n_spars: int = 3
    box_frac_chord: float = 0.60          # box region width / chord
    box_frac_thick: float = 0.70          # box height / thickness (bending depth)
    blend_radius: float = 0.020           # corner radius → longeron channel void
    t_web: float = 0.004                  # FW web wall (manufacturing min, X3)
    t_shell: float = 0.003                # FW outer shell (manufacturing min, X3)
    cap_t_min: float = 0.002              # cap manufacturing floor
    sigma_allow_cap_Pa: float = 600.0e6   # 0°-dominated cap axial allowable (~½ knockdown)
    buckle_t_over_panel: float = 0.03     # geometric section-shape floor (a lower bound)
    buckle_sf: float = 1.5                # orthotropic panel-buckling SF at the operating load (λ ≥ 1.5)
    rho: float = 1600.0                   # carbon/epoxy density
    fos: float = 2.5
    rm_Nm: float = 251.0e3
    n_int: int = 400
    ply: UDPly = T800_EPOXY
    layup_f0: float = 0.70                # cap layup (0° / ±45 / 90) — LAID, can be true 0°
    layup_f45: float = 0.15
    layup_f90: float = 0.15
    # FW shell: a balanced ±θ helical (validated: behaves near-0° for BOTH stiffness and strength
    # at a low helix angle — the ± pair cancels the per-ply matrix shear). The helix angle is a DV.
    shell_helix_deg: float = 10.0

    @property
    def design_moment_Nm(self) -> float:
        return self.fos * self.rm_Nm

    def moduli(self) -> tuple[float, float]:
        """(cap axial modulus, shell axial modulus) [Pa]."""
        e_cap, e_sh, _, _ = self.props()
        return e_cap, e_sh

    def props(self) -> tuple[float, float, float, float]:
        """(E_cap, E_shell, K_cap, K_shell): axial moduli [Pa] + orthotropic panel-buckling
        coefficients ``K = √(D11·D22)+D12+2·D66`` (per unit thickness). Cap = laid 0/±45/90;
        shell = balanced ±``shell_helix_deg`` filament-wound."""
        A, D, _ = laminate_stiffness(self.ply, f0=self.layup_f0, f45=self.layup_f45,
                                     f90=self.layup_f90, thickness=1.0)
        e_cap = 0.9 * float(A[0, 0])
        k_cap = float(np.sqrt(D[0, 0] * D[1, 1]) + D[0, 1] + 2.0 * D[2, 2])
        e_sh, k_sh, _ = balanced_helical(self.ply, self.shell_helix_deg)
        return e_cap, 0.9 * e_sh, k_cap, k_sh

    def shell_allow_Pa(self) -> float:
        """Shell axial design allowable = cap allowable × the helix first-ply strength fraction
        (validated balanced-helical model — preserved to ~10°, transverse-limited beyond)."""
        _, _, frac = balanced_helical(self.ply, self.shell_helix_deg)
        return self.sigma_allow_cap_Pa * frac


def _shell_integrals(oml: np.ndarray) -> tuple[float, float]:
    """(perimeter ∮ds, second moment ∮y²ds about the chord axis) of the OML polyline."""
    d = np.diff(oml, axis=0)
    ds = np.hypot(d[:, 0], d[:, 1])
    y_mid = 0.5 * (oml[:-1, 1] + oml[1:, 1])
    return float(ds.sum()), float(np.sum(y_mid ** 2 * ds))


@dataclass(frozen=True)
class MyWaySection:
    A_cap: float
    A_web: float
    A_shell: float
    A_long: float
    I_heel: float          # total athwartships bending second moment [m⁴]
    cell_width: float      # cap buckling panel [m]
    cap_sigma: float       # cap compressive stress at design M [Pa]
    shell_sigma: float     # shell extreme-fibre stress at design M [Pa]
    EI: float = 0.0        # composite bending stiffness E·I [N·m²]
    panel_buckle_lambda: float = float("inf")   # cap orthotropic panel λ at the operating moment

    @property
    def A_total(self) -> float:
        return self.A_cap + self.A_web + self.A_shell + self.A_long


def myway_section(z: float, spec: AmazonMastSpec, p: MyWayParams,
                  props: tuple[float, float, float, float] | None = None) -> tuple[float, MyWaySection, str]:
    """Size the cap wall at z (composite/modulus-weighted section) and return
    (t_cap, section properties, governing constraint). The wall protects: the 0° caps and the
    near-0° shell in STRENGTH, and the cap panel in orthotropic BUCKLING (λ ≥ buckle_sf at the
    operating load) — not just a geometric floor."""
    E_cap, E_shell, K_cap, _K_shell = props if props is not None else p.props()
    chord = spec.chord_at_z(z)
    thick = spec.thickness_at_z(z)
    oml = spec.section_oml(z)
    w_box = p.box_frac_chord * chord
    # the flat box must fit INSIDE the curved ellipse: at the box edge (u = box_frac_chord) the
    # ellipse half-thickness is (t/2)·√(1−u²); leave shell + fillet clearance. So the achievable
    # box depth is clipped per-station (tighter at the thin masthead — fixed clearances eat more).
    half_fit = (thick / 2.0) * np.sqrt(max(0.0, 1.0 - p.box_frac_chord ** 2)) - p.t_shell - p.blend_radius
    box_ft = min(p.box_frac_thick, max(0.30, 2.0 * half_fit / thick)) if thick > 0 else p.box_frac_thick
    h = box_ft * thick
    cell_w = w_box / p.n_spars

    perim, I_shell_unit = _shell_integrals(oml)
    A_shell = perim * p.t_shell
    I_shell = I_shell_unit * p.t_shell
    n_web = p.n_spars + 1
    A_web = n_web * h * p.t_web
    I_web = n_web * p.t_web * h ** 3 / 12.0
    a_long_each = longeron_void_area(p.blend_radius)          # UD longerons in the channels
    n_long = 2 * (p.n_spars - 1)
    A_long = n_long * a_long_each
    I_long = n_long * a_long_each * (h / 2.0) ** 2

    m = design_moment_at_z(z, spec, p.design_moment_Nm)
    m_op = design_moment_at_z(z, spec, p.rm_Nm)                    # operating moment (RM_max)
    # --- composite STRENGTH: EI must protect the 0° caps (at ±h/2) AND the near-0° shell (±t/2) ---
    EI_req = max(E_cap * m * (h / 2.0) / p.sigma_allow_cap_Pa,
                 E_shell * m * (thick / 2.0) / p.shell_allow_Pa()) if m > 0 else 0.0
    EI_fixed = E_shell * I_shell + E_shell * I_web + E_cap * I_long
    I_caps_need = max(0.0, (EI_req - EI_fixed) / E_cap)
    t_strength = I_caps_need / (2.0 * w_box * (h / 2.0) ** 2) if w_box > 0 else 0.0
    # --- orthotropic cap-panel BUCKLING: σ_cr = 2π²·K_cap·(t/cell)² ≥ buckle_sf · σ_cap,op, with
    # the FULL composite EI (cap EI grows with t, shell+longerons fixed). λ(t)=C·t²·(a·t+b)=SF is a
    # cubic in t — solve exactly (Newton) so the buckling reserve is the target 1.5, not over-built.
    t_buckle = 0.0
    if m_op > 0 and w_box > 0 and h > 0 and K_cap > 0:
        a = E_cap * 2.0 * w_box * (h / 2.0) ** 2                   # cap EI per unit wall
        b = E_shell * (I_shell + I_web) + E_cap * I_long          # fixed (shell+web+longeron) EI
        C = 2.0 * np.pi ** 2 * K_cap / (cell_w ** 2 * E_cap * m_op * (h / 2.0))
        t = (p.buckle_sf / (C * a)) ** (1.0 / 3.0)                 # caps-only seed (overestimate)
        for _ in range(12):
            f = C * a * t ** 3 + C * b * t ** 2 - p.buckle_sf
            fp = 3.0 * C * a * t ** 2 + 2.0 * C * b * t
            if fp <= 0:
                break
            t_new = max(0.5 * t, t - f / fp)
            if abs(t_new - t) < 1e-7:
                t = t_new
                break
            t = t_new
        t_buckle = max(0.0, t)
    t_floor = p.buckle_t_over_panel * cell_w
    t_cap = max(t_strength, t_buckle, t_floor, p.cap_t_min)
    gov = (max((t_strength, "strength"), (t_buckle, "panel-buckling"),
               (t_floor, "buckle-floor"), (p.cap_t_min, "cap-min"), key=lambda kv: kv[0])[1])

    A_cap = 2.0 * w_box * t_cap
    I_cap = 2.0 * w_box * t_cap * (h / 2.0) ** 2 + 2.0 * w_box * t_cap ** 3 / 12.0
    EI = E_cap * (I_cap + I_long) + E_shell * (I_shell + I_web)    # composite bending stiffness
    cap_sigma = E_cap * m * (h / 2.0) / EI if EI > 0 else 0.0      # modulus-weighted strength stresses
    shell_sigma = E_shell * m * (thick / 2.0) / EI if EI > 0 else 0.0
    # actual orthotropic panel λ at the OPERATING load. ONLY the hollow box cap (width = cell, void
    # below) free-panel-buckles; the FW shell is wound over the faired box+longeron+gap-fill mandrel
    # (constitution manufacturing model) → backed, so it does not free-panel-buckle (strength only).
    cap_sig_op = E_cap * m_op * (h / 2.0) / EI if EI > 0 else 0.0
    lam = (2.0 * np.pi ** 2 * K_cap * (t_cap / cell_w) ** 2 / cap_sig_op) if cap_sig_op > 0 else float("inf")
    sec = MyWaySection(A_cap=A_cap, A_web=A_web, A_shell=A_shell, A_long=A_long,
                       I_heel=I_cap + I_shell + I_web + I_long, cell_width=cell_w,
                       cap_sigma=cap_sigma, shell_sigma=shell_sigma, EI=EI, panel_buckle_lambda=lam)
    return t_cap, sec, gov


def myway_tip_deflection(spec: AmazonMastSpec, p: MyWayParams) -> tuple[float, float]:
    """Wing-tip deflection at the OPERATING moment (RM_max) by double-integrating M/EI over the
    tapered composite section (Sponberg's own method: heel + partners fixed). Returns (m, % height)."""
    mods = p.props()
    z = np.linspace(0.0, spec.sail_track_length, 240)
    m = np.array([design_moment_at_z(zz, spec, p.rm_Nm) for zz in z])
    ei = np.array([max(myway_section(zz, spec, p, props=mods)[1].EI, 1.0) for zz in z])
    kappa = m / ei
    slope = np.concatenate([[0.0], np.cumsum((kappa[:-1] + kappa[1:]) / 2 * np.diff(z))])
    defl = np.concatenate([[0.0], np.cumsum((slope[:-1] + slope[1:]) / 2 * np.diff(z))])
    tip = float(defl[-1])
    return tip, 100.0 * tip / spec.sail_track_length


@dataclass(frozen=True)
class MyWayMassResult:
    n_spars: int
    mass_per_mast_kg: float
    mass_both_masts_kg: float
    wing_kg: float
    stock_kg: float
    root_cap_mm: float
    governing_fracs: dict[str, float]
    max_shell_util: float
    max_cap_util: float
    min_buckle_lambda: float = float("inf")
    buckle_sf: float = 1.5
    vs_amazon_pct: float | None = None

    @property
    def feasible(self) -> bool:
        return (self.max_shell_util <= 1.0 + 1e-6 and self.max_cap_util <= 1.0 + 1e-6
                and self.min_buckle_lambda >= self.buckle_sf - 1e-6)


def estimate_myway_mass(spec: AmazonMastSpec, p: MyWayParams,
                        amazon_per_mast_kg: float | None = None) -> MyWayMassResult:
    """Integrate the project-method section mass over the mast for ``p.n_spars`` spars."""
    z_wing = np.linspace(0.0, spec.sail_track_length, p.n_int)
    mods = p.props()
    dm, gov_count = [], {"strength": 0, "panel-buckling": 0, "buckle-floor": 0, "cap-min": 0}
    shell_util = cap_util = root_cap_mm = 0.0
    min_buckle_lambda = float("inf")
    for i, z in enumerate(z_wing):
        t_cap, sec, gov = myway_section(z, spec, p, props=mods)
        dm.append(sec.A_total * p.rho)
        gov_count[gov] = gov_count.get(gov, 0) + 1
        if i == 0:
            root_cap_mm = t_cap * 1e3
        shell_util = max(shell_util, sec.shell_sigma / p.shell_allow_Pa())
        cap_util = max(cap_util, sec.cap_sigma / p.sigma_allow_cap_Pa)
        min_buckle_lambda = min(min_buckle_lambda, sec.panel_buckle_lambda)
    wing_kg = float(np.trapezoid(dm, z_wing))

    # round bearing stock below the deck — same as the X2 build (the journal is unchanged)
    az = AmazonSizingParams(box_frac_chord=p.box_frac_chord, box_frac_thick=p.box_frac_thick,
                            buckle_t_over_panel=p.buckle_t_over_panel, rho_carbon=p.rho,
                            sigma_allow_Pa=p.sigma_allow_cap_Pa, fos=p.fos, rm_Nm=p.rm_Nm)
    z_below = np.linspace(spec.heel_z, 0.0, p.n_int // 4)
    stock_dm = [round_props(spec._stock_od_at_z(z), size_wall_at_z(z, spec, az)[0]).A * p.rho
                for z in z_below if z < spec.partners_z]
    z_stock = [z for z in z_below if z < spec.partners_z]
    stock_kg = float(np.trapezoid(stock_dm, z_stock)) if len(stock_dm) > 1 else 0.0

    per_mast = wing_kg + stock_kg
    tot = sum(gov_count.values())
    gov_fracs = {k: v / tot for k, v in gov_count.items()}
    vs = (100.0 * (per_mast - amazon_per_mast_kg) / amazon_per_mast_kg
          if amazon_per_mast_kg else None)
    return MyWayMassResult(
        n_spars=p.n_spars, mass_per_mast_kg=per_mast, mass_both_masts_kg=2.0 * per_mast,
        wing_kg=wing_kg, stock_kg=stock_kg, root_cap_mm=root_cap_mm,
        governing_fracs=gov_fracs, max_shell_util=shell_util, max_cap_util=cap_util,
        min_buckle_lambda=min_buckle_lambda, buckle_sf=p.buckle_sf, vs_amazon_pct=vs,
    )


def myway_fit(spec: AmazonMastSpec, p: MyWayParams):
    """Manufacturability verdict (`check_fit`) for the project-method build on the Amazon OML."""
    from ..geometry.fit import check_fit
    layout = BoxSparLayout(n_spars=p.n_spars, blend_radius=p.blend_radius,
                           spar_wall=p.t_web, shell_wall=p.t_shell)
    z_stations = np.linspace(0.0, spec.sail_track_length, 9)
    return check_fit(spec, layout, z_stations=z_stations)
