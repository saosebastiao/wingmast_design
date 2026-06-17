"""Survival load envelope — the bare, furled, feathered wingmast in a hurricane (`R-AE-3`,
parent `R-LOAD-2`, basis §4).

Survival is the **bare wingmast** (soft sail furled), **not** the wingsail: a small rigid
streamlined section of chord ``c_mast`` ≪ the wingsail chord, so the survival planform is
``A_mast = c_mast · span`` (≈ 22 m² placeholder vs ~70 m² wingsail). Loads are
**drag/bluff-body analytical** — ``M = q · C · A_mast · arm`` — **not** the AeroSandbox
lifting-line, which is invalid feathered/stalled (`D-AE-c`). The regimes (basis §4):

  * **SURV-1** feathered ~0° (Cd 0.02–0.10) ⇒ ~8–39 kN·m — **below operational OP-2**;
  * **SURV-1f** feathering-FAULT off-axis (Cl 1.0–1.2) ⇒ ~390–470 kN·m (Cat 3) — the
    fault-tolerance check (mechanism jam / power loss / vane failure), carried at a *reduced*
    FoS under the reliable-feathering baseline (`D-2`; `aero/feathering.py`);
  * **locked broadside** (Cd 1.5) ⇒ ~590 kN·m — the worst regime;
  * **SURV-2** Cat-5 off-axis bound ⇒ ~730–880 kN·m — ultimate sensitivity.

Under reliable feathering (the `D-2` design assumption), **SURV-1 does not govern — OP-2
does** (`aero/operational.py`). Any governing/fault case is flagged for n≥24 eigen (Phase S).
"""
from __future__ import annotations

from dataclasses import dataclass

RHO_AIR = 1.225          # kg/m³ (sea level)
KT_TO_MS = 0.5144

#: Coefficient bands (basis §4).
CD_FEATHERED = (0.02, 0.10)
CL_OFF_AXIS = (1.0, 1.2)
CD_LOCKED = 1.5


def dynamic_pressure(speed_kt: float) -> float:
    """q = ½ρV² at the given wind speed (knots)."""
    v = speed_kt * KT_TO_MS
    return 0.5 * RHO_AIR * v * v


#: Hurricane dynamic pressures (basis §4): Cat 3 ≈ 100 kt, Cat 5 ≈ 137 kt.
Q_CAT3 = dynamic_pressure(100.0)     # ≈ 1621 Pa
Q_CAT5 = dynamic_pressure(137.0)     # ≈ 3042 Pa


@dataclass(frozen=True)
class BareMast:
    """The bare-wingmast survival planform (sail furled). ``c_mast`` is `D-4`/TBD."""

    c_mast_m: float = 1.0            # bare-mast chord — a fraction of the wingsail chord
    span_m: float = 22.0
    arm_m: float = 11.0             # bending arm (CE of the bare-mast load above the partners)

    @property
    def area_m2(self) -> float:
        return self.c_mast_m * self.span_m


@dataclass(frozen=True)
class SurvivalLoad:
    name: str
    regime: str                      # feathered | off_axis_fault | locked
    q_Pa: float
    coeff: float                     # Cd (feathered/locked) or Cl (off-axis)
    bending_Nm: float
    eigen_verify: bool = True        # governing/fault survival cases → n≥24 (Phase S)


def survival_bending(q_Pa: float, coeff: float, mast: BareMast) -> float:
    """``M = q · C · A_mast · arm`` on the bare-mast planform."""
    return q_Pa * coeff * mast.area_m2 * mast.arm_m


def _band(name: str, regime: str, q: float, coeffs: tuple[float, float],
          mast: BareMast) -> tuple[SurvivalLoad, SurvivalLoad]:
    lo, hi = coeffs
    return (
        SurvivalLoad(name + "_lo", regime, q, lo, survival_bending(q, lo, mast)),
        SurvivalLoad(name, regime, q, hi, survival_bending(q, hi, mast)),  # design = upper coeff
    )


def surv1_feathered(mast: BareMast | None = None, q_Pa: float = Q_CAT3) -> tuple[SurvivalLoad, SurvivalLoad]:
    """SURV-1: feathered ~0° (Cd band) — the survival design case; below OP-2."""
    return _band("SURV-1", "feathered", q_Pa, CD_FEATHERED, mast or BareMast())


def surv1f_fault(mast: BareMast | None = None, q_Pa: float = Q_CAT3) -> tuple[SurvivalLoad, SurvivalLoad]:
    """SURV-1f: feathering-FAULT off-axis lift (Cl band) — the fault-tolerance check (`D-2`)."""
    return _band("SURV-1f", "off_axis_fault", q_Pa, CL_OFF_AXIS, mast or BareMast())


def surv2_cat5(mast: BareMast | None = None) -> tuple[SurvivalLoad, SurvivalLoad]:
    """SURV-2: Cat-5 off-axis bound — ultimate sensitivity."""
    return _band("SURV-2", "off_axis_fault", Q_CAT5, CL_OFF_AXIS, mast or BareMast())


def locked_broadside(mast: BareMast | None = None, q_Pa: float = Q_CAT3) -> SurvivalLoad:
    """Locked-broadside (Cd 1.5) — the worst feathering regime (not a win to lock)."""
    mast = mast or BareMast()
    return SurvivalLoad("locked_broadside", "locked", q_Pa, CD_LOCKED,
                        survival_bending(q_Pa, CD_LOCKED, mast))
