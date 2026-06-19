"""As-built **conformal** section sizer for the multi-cell torsion box (Phase X5, `R-AMZ-7`).

The X3/X4 sizer (`amazon_myway`) modelled the section as one *idealised box* — flat caps at ±h/2
spanning ``box_frac_chord·chord``, with ``box_frac_chord``/``box_frac_thick`` as free DVs. Those
knobs let the optimiser collapse the structure to a narrow deep strut + foam fairing — light, but
**not the build** (the thing the conformal CAD exposed as un-buildable-looking). This module sizes
the section the optimiser CANNOT cheat: the cells **fill the chord** and their caps lie **on the
ellipse**, exactly the `cells.cell_sections` geometry the CAD lofts. So the sized walls and the CAD
are the same object.

Section properties are thin-wall integrals over the *actual* cell polylines: classify each
perimeter edge as a **cap** (on the OML-inset ellipse) or a **web** (interior), then
``A = ∮ t ds`` and ``I = ∮ t y² ds`` about the chord axis (athwartships bending — the weak,
governing direction). Because each cell cap's ``I`` is **linear** in the cap wall ``t_cap``
(``I_cap = t_cap · J_cap``, ``J_cap = ∮_cap y² ds``), the strength + orthotropic-panel-buckling
solve is the same exact cubic-in-t as `amazon_myway` — but on conformal geometry, not a box.

Buckling panel width = each cell's **chordwise cap span** (≈ ``chord/n_cells``); the closed form is
conservative (ignores cap curvature), to be eigen-verified at n ≥ 24 (Article III).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..geometry.amazon_mast import AmazonMastSpec, ellipse_coords
from ..geometry.cells import CellLayout, cell_sections
from ..materials.unidir import T800_EPOXY, UDPly, laminate_stiffness
from .amazon_myway import _shell_integrals, balanced_helical
from .amazon_sizing import AmazonSizingParams, design_moment_at_z, round_props, size_wall_at_z

_ON_ELLIPSE_TOL = 0.06     # |(x/a)²+(y/b)²−1| below this ⇒ edge lies on the cap (else a web)


@dataclass(frozen=True)
class ConformalParams:
    """Design knobs for the as-built conformal multi-cell torsion box. The OML is frozen and the
    cells fill the chord, so the shape DVs of `amazon_myway` are GONE — the freedom is the cell
    count, the corner-blend (→ longeron channel), the FW walls, the shell helix and the cap layup;
    the cap wall ``t_cap(z)`` is SIZED, not a knob."""

    n_cells: int = 3
    blend_radius: float = 0.020           # corner radius → longeron channel void
    t_web: float = 0.004                  # FW web wall (manufacturing min)
    t_shell: float = 0.003                # FW outer shell wall
    cap_t_min: float = 0.002              # cap manufacturing floor
    sigma_allow_cap_Pa: float = 600.0e6   # 0°-dominated cap axial allowable (~½ knockdown)
    buckle_sf: float = 1.5                # orthotropic cap-panel buckling SF at operating load
    rho: float = 1600.0
    fos: float = 2.5
    rm_Nm: float = 251.0e3
    n_int: int = 240
    n_pts: int = 96                       # points per cell outline (integration resolution)
    ply: UDPly = T800_EPOXY
    layup_f0: float = 0.70                # cap layup (0 / ±45 / 90) — LAID, can be true 0°
    layup_f45: float = 0.15
    layup_f90: float = 0.15
    shell_helix_deg: float = 10.0         # balanced ±θ FW shell (near-0° behaviour, validated)

    @property
    def design_moment_Nm(self) -> float:
        return self.fos * self.rm_Nm

    def props(self) -> tuple[float, float, float]:
        """(E_cap, E_shell, K_cap): cap & shell axial moduli [Pa] + cap orthotropic panel-buckling
        coefficient K = √(D11·D22)+D12+2·D66. Cap = laid 0/±45/90; shell = balanced helical."""
        A, D, _ = laminate_stiffness(self.ply, f0=self.layup_f0, f45=self.layup_f45,
                                     f90=self.layup_f90, thickness=1.0)
        e_cap = 0.9 * float(A[0, 0])
        k_cap = float(np.sqrt(D[0, 0] * D[1, 1]) + D[0, 1] + 2.0 * D[2, 2])
        e_sh, _, _ = balanced_helical(self.ply, self.shell_helix_deg)
        return e_cap, 0.9 * e_sh, k_cap

    def shell_allow_Pa(self) -> float:
        _, _, frac = balanced_helical(self.ply, self.shell_helix_deg)
        return self.sigma_allow_cap_Pa * frac


def _env_ellipse(chord_env: float, thick_env: float, n: int) -> np.ndarray:
    e = ellipse_coords(n // 2).copy()
    out = e.copy()
    out[:, 0] = (e[:, 0] - 0.5) * chord_env
    out[:, 1] = e[:, 1] / 0.40 * (thick_env / chord_env) * chord_env
    return out


@dataclass(frozen=True)
class _Geo:
    a: float
    b: float
    chord: float
    thick: float
    J_cap: float          # ∮_cap y² ds  (so I_cap = t_cap · J_cap)
    S_cap: float          # ∮_cap ds     (so A_cap = t_cap · S_cap)
    J_web: float
    S_web: float
    y_capmax: float       # extreme cap fibre |y|
    b_panel: float        # widest cell cap chordwise span (buckling panel)
    perim: float
    I_shell_unit: float   # ∮_OML y² ds  (I_shell = t_shell · I_shell_unit)
    A_long: float
    I_long_unit: float    # Σ_channels ∫y²dA over the TRUE fillet-gap polygons (the longeron void)


def _poly_area_Ix(poly: np.ndarray) -> tuple[float, float]:
    """(area, second moment about y=0) of a simple polygon — exact (shoelace + the matching
    ``I_x = Σ cross·(y0²+y0·y1+y1²)/12`` line integral)."""
    if len(poly) < 3:
        return 0.0, 0.0
    x, y = poly[:, 0], poly[:, 1]
    x1, y1 = np.roll(x, -1), np.roll(y, -1)
    cross = x * y1 - x1 * y
    area = 0.5 * float(np.sum(cross))
    ix = float(np.sum(cross * (y ** 2 + y * y1 + y1 ** 2))) / 12.0
    return abs(area), abs(ix)


def _section_geometry(z: float, spec: AmazonMastSpec, p: ConformalParams) -> _Geo:
    chord, thick = spec.chord_at_z(z), spec.thickness_at_z(z)
    a, b = (chord - 2 * p.t_shell) / 2.0, (thick - 2 * p.t_shell) / 2.0
    env = _env_ellipse(chord - 2 * p.t_shell, thick - 2 * p.t_shell, p.n_pts)
    sec = cell_sections(env, CellLayout(n_cells=p.n_cells, blend_radius=p.blend_radius,
                                        cell_wall=p.t_web, shell_wall=p.t_shell))
    J_cap = S_cap = J_web = S_web = y_capmax = b_panel = 0.0
    for cell in sec.cells:
        pts = np.asarray(cell, float)
        seg = np.vstack([pts, pts[0]])
        mids = 0.5 * (seg[:-1] + seg[1:])
        ds = np.hypot(*(np.diff(seg, axis=0).T))
        # EXACT thin-wall line second moment ∮ y² ds about y=0 for each straight edge:
        # ∫ y² ds = ds·(y0² + y0·y1 + y1²)/3. Reduces to y_mid² for a cap (y0≈y1) but recovers
        # the web's own h³/12 self-bending (a vertical web has y_mid≈0 but spans −h/2…+h/2).
        y0, y1 = seg[:-1, 1], seg[1:, 1]
        edge_y2 = (y0 ** 2 + y0 * y1 + y1 ** 2) / 3.0
        on_cap = np.abs((mids[:, 0] / a) ** 2 + (mids[:, 1] / b) ** 2 - 1.0) < _ON_ELLIPSE_TOL
        J_cap += float(np.sum(edge_y2[on_cap] * ds[on_cap]))
        S_cap += float(np.sum(ds[on_cap]))
        J_web += float(np.sum(edge_y2[~on_cap] * ds[~on_cap]))
        S_web += float(np.sum(ds[~on_cap]))
        if on_cap.any():
            y_capmax = max(y_capmax, float(np.max(np.abs(mids[on_cap, 1]))))
            cap_x = mids[on_cap, 0]
            b_panel = max(b_panel, float(cap_x.max() - cap_x.min()))

    oml = spec.section_oml(z)
    perim, I_shell_unit = _shell_integrals(oml)
    # longerons fill the TRUE fillet-gap channels (the blend_radius lever): exact area + ∫y²dA over
    # each top/bottom channel polygon — so min_radius is a faithful structural variable, not an
    # analytic void approximation, and consistent with the CAD (examples/62).
    A_long = I_long_unit = 0.0
    for ch in sec.channels:
        for cp in (ch.top_poly, ch.bottom_poly):
            ar, ix = _poly_area_Ix(np.asarray(cp, float))
            A_long += ar
            I_long_unit += ix
    return _Geo(a=a, b=b, chord=chord, thick=thick, J_cap=J_cap, S_cap=S_cap, J_web=J_web,
                S_web=S_web, y_capmax=y_capmax, b_panel=b_panel, perim=perim,
                I_shell_unit=I_shell_unit, A_long=A_long, I_long_unit=I_long_unit)


@dataclass(frozen=True)
class ConformalSection:
    t_cap: float
    A_cap: float
    A_web: float
    A_shell: float
    A_long: float
    EI: float
    I_total: float
    cell_panel: float
    cap_sigma: float
    shell_sigma: float
    panel_buckle_lambda: float

    @property
    def A_total(self) -> float:
        return self.A_cap + self.A_web + self.A_shell + self.A_long


def conformal_section(z: float, spec: AmazonMastSpec, p: ConformalParams,
                      props: tuple[float, float, float] | None = None
                      ) -> tuple[float, ConformalSection, str]:
    """Size the cap wall at z from the CONFORMAL geometry and return (t_cap, section, governing).
    Protects the 0° caps + near-0° shell in STRENGTH and the cap panel in orthotropic BUCKLING
    (λ ≥ buckle_sf at the operating load) — all on the real cell cross-section."""
    E_cap, E_shell, K_cap = props if props is not None else p.props()
    g = _section_geometry(z, spec, p)
    m = design_moment_at_z(z, spec, p.design_moment_Nm)
    m_op = design_moment_at_z(z, spec, p.rm_Nm)

    I_shell = g.I_shell_unit * p.t_shell
    I_web = p.t_web * g.J_web
    EI_fixed = E_shell * (I_shell + I_web) + E_cap * g.I_long_unit     # independent of t_cap

    # --- STRENGTH: EI must keep the cap (at y_capmax) AND the shell (at ±t/2) within allowables ---
    EI_req = max(E_cap * m * g.y_capmax / p.sigma_allow_cap_Pa,
                 E_shell * m * (g.thick / 2.0) / p.shell_allow_Pa()) if m > 0 else 0.0
    t_strength = max(0.0, (EI_req - EI_fixed) / (E_cap * g.J_cap)) if g.J_cap > 0 else 0.0

    # --- orthotropic cap-panel BUCKLING: 2π²K(t/b)² ≥ sf·σ_cap,op, with the FULL composite EI.
    # σ_cap,op = E_cap·m_op·y_capmax/EI(t), EI(t)=E_cap·J_cap·t + EI_fixed → cubic in t (Newton). ---
    t_buckle = 0.0
    if m_op > 0 and g.b_panel > 0 and g.J_cap > 0 and K_cap > 0:
        C = 2.0 * np.pi ** 2 * K_cap / (g.b_panel ** 2)
        R = p.buckle_sf * E_cap * m_op * g.y_capmax
        ej = E_cap * g.J_cap
        # f(t) = C·t²·(ej·t + EI_fixed) − R = C·ej·t³ + C·EI_fixed·t² − R
        t = (R / (C * ej)) ** (1.0 / 3.0)                 # caps-only seed (overestimate)
        for _ in range(16):
            f = C * ej * t ** 3 + C * EI_fixed * t ** 2 - R
            fp = 3.0 * C * ej * t ** 2 + 2.0 * C * EI_fixed * t
            if fp <= 0:
                break
            t_new = max(0.5 * t, t - f / fp)
            if abs(t_new - t) < 1e-7:
                t = t_new
                break
            t = t_new
        t_buckle = max(0.0, t)

    t_cap = max(t_strength, t_buckle, p.cap_t_min)
    gov = max((t_strength, "strength"), (t_buckle, "panel-buckling"), (p.cap_t_min, "cap-min"),
              key=lambda kv: kv[0])[1]

    I_cap = t_cap * g.J_cap
    EI = E_cap * (I_cap + g.I_long_unit) + E_shell * (I_web + I_shell)
    cap_sigma = E_cap * m * g.y_capmax / EI if EI > 0 else 0.0
    shell_sigma = E_shell * m * (g.thick / 2.0) / EI if EI > 0 else 0.0
    cap_sig_op = E_cap * m_op * g.y_capmax / EI if EI > 0 else 0.0
    lam = (2.0 * np.pi ** 2 * K_cap * (t_cap / g.b_panel) ** 2 / cap_sig_op
           if cap_sig_op > 0 else float("inf"))
    sec = ConformalSection(
        t_cap=t_cap, A_cap=t_cap * g.S_cap, A_web=p.t_web * g.S_web, A_shell=g.perim * p.t_shell,
        A_long=g.A_long, EI=EI, I_total=I_cap + I_web + I_shell + g.I_long_unit,
        cell_panel=g.b_panel, cap_sigma=cap_sigma, shell_sigma=shell_sigma, panel_buckle_lambda=lam)
    return t_cap, sec, gov


@dataclass(frozen=True)
class ConformalMassResult:
    n_cells: int
    mass_per_mast_kg: float
    mass_both_masts_kg: float
    wing_kg: float
    stock_kg: float
    root_cap_mm: float
    governing_fracs: dict[str, float]
    max_cap_util: float
    max_shell_util: float
    min_buckle_lambda: float
    buckle_sf: float
    cap_schedule: tuple[tuple[float, float], ...]    # (z, t_cap) for the CAD to consume
    vs_amazon_pct: float | None = None

    @property
    def feasible(self) -> bool:
        return (self.max_cap_util <= 1.0 + 1e-6 and self.max_shell_util <= 1.0 + 1e-6
                and self.min_buckle_lambda >= self.buckle_sf - 1e-6)


def estimate_conformal_mass(spec: AmazonMastSpec, p: ConformalParams,
                            amazon_per_mast_kg: float | None = None) -> ConformalMassResult:
    """Integrate the conformal section mass over the wing (+ round stock below deck)."""
    z_wing = np.linspace(0.0, spec.sail_track_length, p.n_int)
    mods = p.props()
    dm, sched = [], []
    gov_count = {"strength": 0, "panel-buckling": 0, "cap-min": 0}
    cap_util = shell_util = root_cap_mm = 0.0
    min_lambda = float("inf")
    for i, z in enumerate(z_wing):
        t_cap, sec, gov = conformal_section(float(z), spec, p, props=mods)
        dm.append(sec.A_total * p.rho)
        sched.append((float(z), float(t_cap)))
        gov_count[gov] = gov_count.get(gov, 0) + 1
        if i == 0:
            root_cap_mm = t_cap * 1e3
        cap_util = max(cap_util, sec.cap_sigma / p.sigma_allow_cap_Pa)
        shell_util = max(shell_util, sec.shell_sigma / p.shell_allow_Pa())
        min_lambda = min(min_lambda, sec.panel_buckle_lambda)
    wing_kg = float(np.trapezoid(dm, z_wing))

    # round bearing stock below the deck — unchanged journal (same as X2/X3)
    az = AmazonSizingParams(buckle_t_over_panel=0.03, rho_carbon=p.rho,
                            sigma_allow_Pa=p.sigma_allow_cap_Pa, fos=p.fos, rm_Nm=p.rm_Nm)
    z_below = np.linspace(spec.heel_z, 0.0, p.n_int // 4)
    z_stock = [z for z in z_below if z < spec.partners_z]
    stock_dm = [round_props(spec._stock_od_at_z(z), size_wall_at_z(z, spec, az)[0]).A * p.rho
                for z in z_stock]
    stock_kg = float(np.trapezoid(stock_dm, z_stock)) if len(stock_dm) > 1 else 0.0

    per_mast = wing_kg + stock_kg
    tot = sum(gov_count.values())
    gov_fracs = {k: v / tot for k, v in gov_count.items()}
    vs = (100.0 * (per_mast - amazon_per_mast_kg) / amazon_per_mast_kg
          if amazon_per_mast_kg else None)
    return ConformalMassResult(
        n_cells=p.n_cells, mass_per_mast_kg=per_mast, mass_both_masts_kg=2.0 * per_mast,
        wing_kg=wing_kg, stock_kg=stock_kg, root_cap_mm=root_cap_mm, governing_fracs=gov_fracs,
        max_cap_util=cap_util, max_shell_util=shell_util, min_buckle_lambda=min_lambda,
        buckle_sf=p.buckle_sf, cap_schedule=tuple(sched), vs_amazon_pct=vs)


def conformal_tip_deflection(spec: AmazonMastSpec, p: ConformalParams) -> tuple[float, float]:
    """Wing-tip deflection at the OPERATING moment (RM_max) by double-integrating M/EI over the
    tapered conformal section. Returns (m, % of wing height)."""
    mods = p.props()
    z = np.linspace(0.0, spec.sail_track_length, 200)
    m = np.array([design_moment_at_z(float(zz), spec, p.rm_Nm) for zz in z])
    ei = np.array([max(conformal_section(float(zz), spec, p, props=mods)[1].EI, 1.0) for zz in z])
    kappa = m / ei
    slope = np.concatenate([[0.0], np.cumsum((kappa[:-1] + kappa[1:]) / 2 * np.diff(z))])
    defl = np.concatenate([[0.0], np.cumsum((slope[:-1] + slope[1:]) / 2 * np.diff(z))])
    return float(defl[-1]), 100.0 * float(defl[-1]) / spec.sail_track_length


# ---------------------------------------------------------------------------------------------
# Optimiser over the REAL remaining freedom (the OML is frozen and the cells fill the chord, so
# there is no box-fraction to game): blend radius, FW web + shell walls, shell helix, cap layup.
# ---------------------------------------------------------------------------------------------
# DV = [blend_radius (min corner radius), t_web, t_shell, shell_helix_deg, cap_f0]. blend_radius
# floor = a filament-wound inside-corner minimum (~6 mm: tighter bridges the tow → voids).
_OPT_BOUNDS = [(0.006, 0.040), (0.003, 0.008), (0.002, 0.010), (5.0, 15.0), (0.55, 0.85)]


def _opt_params(x, n_cells: int, base: ConformalParams) -> ConformalParams:
    from dataclasses import replace
    f0 = float(x[4])
    off = 0.5 * (1.0 - f0)
    return replace(base, n_cells=n_cells, blend_radius=float(x[0]), t_web=float(x[1]),
                   t_shell=float(x[2]), shell_helix_deg=float(x[3]),
                   layup_f0=f0, layup_f45=off, layup_f90=off)


def _opt_objective(x, spec, n_cells, base, defl_cap_m) -> float:
    p = _opt_params(x, n_cells, base)
    r = estimate_conformal_mass(spec, p)
    if not r.feasible:
        return 1e4 + 1e3 * (r.max_cap_util + r.max_shell_util
                            + max(0.0, r.buckle_sf - r.min_buckle_lambda))
    if defl_cap_m is not None:
        d, _ = conformal_tip_deflection(spec, p)
        if d > defl_cap_m:
            return 1e4 + 1e3 * (d - defl_cap_m)
    return r.mass_per_mast_kg


@dataclass(frozen=True)
class ConformalBeatResult:
    n_cells: int
    params: ConformalParams
    result: ConformalMassResult
    mass_per_mast_kg: float
    vs_amazon_pct: float
    min_buckle_lambda: float
    tip_defl_m: float
    de_success: bool = True          # DE convergence flag (False = stopped on maxiter)
    de_nit: int = 0                  # DE iterations used
    at_bounds: int = 0               # # DVs pinned to a bound (corner solution diagnostic)


def optimize_conformal(spec: AmazonMastSpec, n_cells: int, amazon_per_mast_kg: float,
                       base: ConformalParams | None = None, *, seed: int = 0,
                       defl_cap_m: float | None = None, maxiter: int = 40, popsize: int = 12,
                       workers: int = 1) -> ConformalBeatResult:
    """Differential-evolution minimisation of per-mast mass for a fixed cell count. Strength +
    cap-panel buckling (λ ≥ buckle_sf) are met by the inner conformal sizer; ``defl_cap_m``
    optionally caps tip deflection. DV = [blend, t_web, t_shell, shell_helix, cap_f0]."""
    from scipy.optimize import differential_evolution
    base = base or ConformalParams()
    opt = differential_evolution(
        _opt_objective, _OPT_BOUNDS, args=(spec, n_cells, base, defl_cap_m), seed=seed, tol=1e-5,
        maxiter=maxiter, popsize=popsize, polish=True, init="sobol", workers=workers,
        updating=("deferred" if workers != 1 else "immediate"))
    p = _opt_params(opt.x, n_cells, base)
    r = estimate_conformal_mass(spec, p, amazon_per_mast_kg=amazon_per_mast_kg)
    d, _ = conformal_tip_deflection(spec, p)
    at_bounds = sum(abs(xi - lo) < 1e-6 or abs(xi - hi) < 1e-6
                    for xi, (lo, hi) in zip(opt.x, _OPT_BOUNDS))
    return ConformalBeatResult(n_cells=n_cells, params=p, result=r,
                               mass_per_mast_kg=r.mass_per_mast_kg, vs_amazon_pct=r.vs_amazon_pct or 0.0,
                               min_buckle_lambda=r.min_buckle_lambda, tip_defl_m=d,
                               de_success=bool(opt.success), de_nit=int(opt.nit), at_bounds=int(at_bounds))


def optimize_conformal_beat(spec: AmazonMastSpec | None = None, amazon_per_mast_kg: float = 646.0,
                            *, base: ConformalParams | None = None, cell_counts=(3, 4, 5),
                            seed: int = 0, defl_cap_m: float | None = None,
                            maxiter: int = 40, popsize: int = 12, workers: int = 1
                            ) -> tuple[ConformalBeatResult, list[ConformalBeatResult]]:
    spec = spec or AmazonMastSpec()
    runs = [optimize_conformal(spec, n, amazon_per_mast_kg, base=base, seed=seed,
                               defl_cap_m=defl_cap_m, maxiter=maxiter, popsize=popsize,
                               workers=workers) for n in cell_counts]
    best = min(runs, key=lambda r: r.mass_per_mast_kg)
    return best, runs
