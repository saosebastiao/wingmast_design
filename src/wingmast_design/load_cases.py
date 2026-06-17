"""Typed structural load-case collection — the single source of truth (Article XII).

A `StructuralLoadCase` is one *structural* design point: a body-load acceleration
vector (gravity ± heel/slam), the buckling safety factor it is verified at, the
skin/ply datum direction, and a **category** that classifies it as

  * ``OPERATIONAL``    — serviceability (deflection/twist) **and** ultimate, or
  * ``SURVIVAL``       — ultimate only (no serviceability idealisation — Article IV), or
  * ``MANUFACTURING``  — a constraint set (hoop prestress, bondline), not a bending case.

The category drives `serviceability_applies`, which is the **single switch** that
keeps deflection/twist limits off survival cases (Constitution Article IV: "never
size to an idealisation that understates load … serviceability limits apply to
operational cases only").

This module is distinct from `aero.cases` (the legacy dinghy *aerodynamic* envelope,
frozen by the re-scope) and from `aero.loads` (the apparent-wind solver plumbing).
The Oyster-595 twin-rig **magnitudes** (heel, slam g, OP-2 70:30 split, SURV-1/1f
AoA, DAF) are deliberately **not** defined here yet — they are pinned in Phase A once
decision gates D-1/D-2/D-4 resolve (`docs/specification.md` §4, `docs/plan.md` Phase A).
What lives here today is the *typed container* those values will populate, plus the
**legacy shell-beam structural constants** promoted out of `runs/` so they are defined
exactly once (the former `runs/chain_rebuild.py` literals).

See `docs/specs/00-rescope-groundwork/` (`R-LOAD-1`, `R-GND-5/6`).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np

Vec3 = tuple[float, float, float]


class CaseCategory(Enum):
    """Load-case classification (Constitution Article IV)."""

    OPERATIONAL = "operational"      # serviceability + ultimate
    SURVIVAL = "survival"            # ultimate only
    MANUFACTURING = "manufacturing"  # constraint set, not a bending case

    @property
    def serviceability_applies(self) -> bool:
        """True only for OPERATIONAL — serviceability (deflection/twist) limits
        MUST NOT constrain survival or manufacturing cases (Article IV)."""
        return self is CaseCategory.OPERATIONAL


@dataclass(frozen=True)
class StructuralLoadCase:
    """One structural design point in the typed load collection (`R-LOAD-1`).

    Frozen so a case can't be mutated mid-run. `accel` is the body-load
    acceleration vector applied to the lumped mass (gravity, optionally rotated
    into a heel attitude or augmented by a slam g); `datum` is the skin/ply datum
    direction the laminate frame is measured from.
    """

    name: str
    category: CaseCategory
    accel: Vec3                       # body-load acceleration vector, m/s^2
    buckling_safety_factor: float     # closed-form buckling SF this case is held to
    datum: Vec3 = (0.0, 0.0, 1.0)     # skin/ply datum direction
    description: str = ""

    @property
    def serviceability_applies(self) -> bool:
        """Deflection/twist limits apply to this case iff it is operational (Article IV)."""
        return self.category.serviceability_applies


# ---------------------------------------------------------------------------
# Canonical structural constants — promoted from runs/ (single source, Article XII).
#
# These are the legacy SHELL-BEAM operating values (upright + 30 deg heel gravity,
# closed-form buckling SF 1.5, span-aligned skin datum) reproduced **byte-identically**
# from the former `runs/chain_rebuild.py` literals, so the `runs/` scripts import them
# rather than each redefining them. They are NOT the Oyster-595 twin-rig values
# (those land in Phase A — see module docstring). Aliases G0/TH/ACCELS/SF/DATUM are
# provided for a minimal-diff import in the legacy run scripts.
# ---------------------------------------------------------------------------

GRAVITY_MS2: float = 9.81
LEGACY_HEEL_RAD: float = np.radians(30.0)
# tuple[Vec3, ...]: the legacy set is 2 (upright + heel); slam/survival runs extend it.
LEGACY_ACCELS: tuple[Vec3, ...] = (
    (0.0, 0.0, -GRAVITY_MS2),
    (0.0, GRAVITY_MS2 * np.sin(LEGACY_HEEL_RAD), -GRAVITY_MS2 * np.cos(LEGACY_HEEL_RAD)),
)
LEGACY_BUCKLING_SF: float = 1.5
SKIN_DATUM: Vec3 = (0.0, 0.0, 1.0)

# Back-compat aliases for the legacy run scripts (byte-identical objects).
G0 = GRAVITY_MS2
TH = LEGACY_HEEL_RAD
ACCELS = LEGACY_ACCELS
SF = LEGACY_BUCKLING_SF
DATUM = SKIN_DATUM


def legacy_shellbeam_cases() -> tuple[StructuralLoadCase, ...]:
    """The shell-beam-era operational structural collection (upright + 30 deg heel
    gravity at SF 1.5), as the typed container. Both are OPERATIONAL — this is the
    legacy aero × {upright, heel} body-load set the V.6 chain sized against. The
    survival/slam cases are intentionally absent here (the re-scope re-derives them).
    """
    return (
        StructuralLoadCase(
            name="upright",
            category=CaseCategory.OPERATIONAL,
            accel=LEGACY_ACCELS[0],
            buckling_safety_factor=LEGACY_BUCKLING_SF,
            datum=SKIN_DATUM,
            description="gravity, upright attitude (legacy shell-beam)",
        ),
        StructuralLoadCase(
            name="heel_30deg",
            category=CaseCategory.OPERATIONAL,
            accel=LEGACY_ACCELS[1],
            buckling_safety_factor=LEGACY_BUCKLING_SF,
            datum=SKIN_DATUM,
            description="gravity rotated into 30 deg heel (legacy shell-beam)",
        ),
    )
