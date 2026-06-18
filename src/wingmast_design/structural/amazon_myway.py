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
from ..materials.unidir import T800_EPOXY, UDPly, laminate_stiffness
from .amazon_sizing import AmazonSizingParams, design_moment_at_z, round_props, size_wall_at_z


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
    sigma_allow_shell_Pa: float = 300.0e6 # helical FW shell axial allowable (lower than caps)
    buckle_t_over_panel: float = 0.03     # Sponberg's section-shape floor, now on the CELL panel
    rho: float = 1600.0                   # carbon/epoxy density
    fos: float = 2.5
    rm_Nm: float = 251.0e3
    n_int: int = 400
    ply: UDPly = T800_EPOXY
    layup_f0: float = 0.70                # cap layup (0° / ±45 / 90)
    layup_f45: float = 0.15
    layup_f90: float = 0.15
    shell_f0: float = 0.10                # FW shell layup (helical-dominated → low axial modulus)
    shell_f45: float = 0.80
    shell_f90: float = 0.10

    @property
    def design_moment_Nm(self) -> float:
        return self.fos * self.rm_Nm

    def moduli(self) -> tuple[float, float]:
        """(cap axial modulus, shell axial modulus) [Pa] from the two laminates."""
        A_cap, _, _ = laminate_stiffness(self.ply, f0=self.layup_f0, f45=self.layup_f45,
                                         f90=self.layup_f90, thickness=1.0)
        A_sh, _, _ = laminate_stiffness(self.ply, f0=self.shell_f0, f45=self.shell_f45,
                                        f90=self.shell_f90, thickness=1.0)
        return 0.9 * float(A_cap[0, 0]), 0.9 * float(A_sh[0, 0])


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

    @property
    def A_total(self) -> float:
        return self.A_cap + self.A_web + self.A_shell + self.A_long


def myway_section(z: float, spec: AmazonMastSpec, p: MyWayParams,
                  moduli: tuple[float, float] | None = None) -> tuple[float, MyWaySection, str]:
    """Size the cap wall at z (composite/modulus-weighted section) and return
    (t_cap, section properties, governing constraint). Sizing protects BOTH the 0° caps and the
    soft helical shell, plus Sponberg's section-shape buckling floor on the cell panel."""
    E_cap, E_shell = moduli if moduli is not None else p.moduli()
    chord = spec.chord_at_z(z)
    thick = spec.thickness_at_z(z)
    oml = spec.section_oml(z)
    w_box = p.box_frac_chord * chord
    h = p.box_frac_thick * thick
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
    # --- composite strength: EI must protect the 0° caps (at ±h/2) AND the soft shell (at ±t/2) ---
    EI_req = max(E_cap * m * (h / 2.0) / p.sigma_allow_cap_Pa,
                 E_shell * m * (thick / 2.0) / p.sigma_allow_shell_Pa) if m > 0 else 0.0
    EI_fixed = E_shell * I_shell + E_shell * I_web + E_cap * I_long
    I_caps_need = max(0.0, (EI_req - EI_fixed) / E_cap)
    t_strength = I_caps_need / (2.0 * w_box * (h / 2.0) ** 2) if w_box > 0 else 0.0
    t_buckle = p.buckle_t_over_panel * cell_w
    t_cap = max(t_strength, t_buckle, p.cap_t_min)
    gov = ("buckling-floor" if t_buckle >= max(t_strength, p.cap_t_min)
           else "strength" if t_strength >= p.cap_t_min else "cap-min")

    A_cap = 2.0 * w_box * t_cap
    I_cap = 2.0 * w_box * t_cap * (h / 2.0) ** 2 + 2.0 * w_box * t_cap ** 3 / 12.0
    EI = E_cap * (I_cap + I_long) + E_shell * (I_shell + I_web)    # composite bending stiffness
    cap_sigma = E_cap * m * (h / 2.0) / EI if EI > 0 else 0.0      # modulus-weighted stresses
    shell_sigma = E_shell * m * (thick / 2.0) / EI if EI > 0 else 0.0
    sec = MyWaySection(A_cap=A_cap, A_web=A_web, A_shell=A_shell, A_long=A_long,
                       I_heel=I_cap + I_shell + I_web + I_long,
                       cell_width=cell_w, cap_sigma=cap_sigma, shell_sigma=shell_sigma)
    return t_cap, sec, gov


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
    vs_amazon_pct: float | None = None

    @property
    def feasible(self) -> bool:
        return self.max_shell_util <= 1.0 + 1e-6 and self.max_cap_util <= 1.0 + 1e-6


def estimate_myway_mass(spec: AmazonMastSpec, p: MyWayParams,
                        amazon_per_mast_kg: float | None = None) -> MyWayMassResult:
    """Integrate the project-method section mass over the mast for ``p.n_spars`` spars."""
    z_wing = np.linspace(0.0, spec.sail_track_length, p.n_int)
    mods = p.moduli()
    dm, gov_count = [], {"strength": 0, "buckling-floor": 0, "cap-min": 0}
    shell_util = cap_util = root_cap_mm = 0.0
    for i, z in enumerate(z_wing):
        t_cap, sec, gov = myway_section(z, spec, p, moduli=mods)
        dm.append(sec.A_total * p.rho)
        gov_count[gov] += 1
        if i == 0:
            root_cap_mm = t_cap * 1e3
        shell_util = max(shell_util, sec.shell_sigma / p.sigma_allow_shell_Pa)
        cap_util = max(cap_util, sec.cap_sigma / p.sigma_allow_cap_Pa)
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
        vs_amazon_pct=vs,
    )


def myway_fit(spec: AmazonMastSpec, p: MyWayParams):
    """Manufacturability verdict (`check_fit`) for the project-method build on the Amazon OML."""
    from ..geometry.fit import check_fit
    layout = BoxSparLayout(n_spars=p.n_spars, blend_radius=p.blend_radius,
                           spar_wall=p.t_web, shell_wall=p.t_shell)
    z_stations = np.linspace(0.0, spec.sail_track_length, 9)
    return check_fit(spec, layout, z_stations=z_stations)
