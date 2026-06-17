"""Phase-A.3 — survival bare-wingmast feathering envelope (`R-AE-3`, parent `R-LOAD-2`,
basis §4)."""
from __future__ import annotations

from wingmast_design.aero.operational import op2
from wingmast_design.aero.survival import (
    Q_CAT3,
    Q_CAT5,
    BareMast,
    dynamic_pressure,
    locked_broadside,
    surv1_feathered,
    surv1f_fault,
    surv2_cat5,
)


def test_hurricane_dynamic_pressures():
    assert abs(Q_CAT3 - 1621.0) < 2.0          # 100 kt
    assert abs(Q_CAT5 - 3042.0) < 2.0          # 137 kt
    assert dynamic_pressure(0.0) == 0.0


def test_bare_mast_planform_is_small():
    m = BareMast()
    assert abs(m.area_m2 - 22.0) < 1e-9        # c_mast 1.0 × span 22 (NOT the wingsail chord)


def test_surv1_feathered_below_operational():
    _, s1 = surv1_feathered()
    assert 7.8e3 <= surv1_feathered()[0].bending_Nm <= 8.0e3       # lo (Cd 0.02) ≈ 7.8 kN·m
    assert 38.0e3 <= s1.bending_Nm <= 40.0e3                       # hi (Cd 0.10) ≈ 39 kN·m
    # the design assumption: feathered survival is below the operational governing case
    assert s1.bending_Nm < op2().design_bending_Nm


def test_surv1f_fault_band():
    lo, hi = surv1f_fault()
    assert 388.0e3 <= lo.bending_Nm <= 396.0e3                     # Cl 1.0 ≈ 392
    assert 466.0e3 <= hi.bending_Nm <= 476.0e3                     # Cl 1.2 ≈ 471
    assert hi.regime == "off_axis_fault"
    assert hi.eigen_verify                                          # fault case → n≥24 (Phase S)


def test_surv2_cat5_and_locked():
    _, s2 = surv2_cat5()
    assert 730.0e3 <= s2.bending_Nm <= 890.0e3                     # ~730–880
    assert s2.q_Pa == Q_CAT5
    lk = locked_broadside()
    assert 580.0e3 <= lk.bending_Nm <= 595.0e3                     # ~590; worst regime
    assert lk.coeff == 1.5


def test_c_mast_scales_survival_linearly():
    base = surv1f_fault(BareMast(c_mast_m=1.0))[1].bending_Nm
    doubled = surv1f_fault(BareMast(c_mast_m=2.0))[1].bending_Nm
    assert abs(doubled - 2.0 * base) < 1.0     # A_mast = c_mast·span ⇒ linear in c_mast (D-4)
