#!/usr/bin/env python
"""Fidelity check for a Fusion 360 -> build123d translation.

The objective "done" gate for the `fusion-to-build123d` skill: regenerate the
translated build123d solid and diff it against the Fusion-exported STEP ground
truth on volume / bounding-box / centre-of-mass / solid & face counts. It is
tuned to make the silent unit failures LOUD: a ~10x volume/length ratio is the
cm->mm conversion miss (kb.md gotcha #1), a ~57.3x (180/pi) length ratio points
at a rad->deg miss feeding a dimension.

Usage (build123d 0.10.0; use the repo venv):

    # compare two STEP files (export your build123d result to STEP first):
    .venv/bin/python fidelity_check.py mine.step fusion.step

    # or, from Python, compare a live build123d shape to the Fusion STEP:
    from fidelity_check import compare_to_step
    ok, report = compare_to_step(my_part, "fusion.step")

Exit code 0 = within tolerance, 1 = out of tolerance, 2 = usage/load error.
It catches GROSS geometry mismatch, NOT "filleted the wrong edge" — pair it
with a visual check and the selector review (see SKILL.md).
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass

from build123d import Shape, import_step

# A missed cm->mm conversion scales one length by 10 (volume by up to 10**3);
# a rad->deg miss feeding a dimension scales by 180/pi ~= 57.3.
RAD_DEG = 180.0 / math.pi


@dataclass(frozen=True)
class Metrics:
    volume: float
    bbox: tuple[float, float, float]
    center: tuple[float, float, float]
    n_solids: int
    n_faces: int

    @classmethod
    def of(cls, shape: Shape) -> "Metrics":
        bb = shape.bounding_box()
        sz, c = bb.size, shape.center()  # ty: ignore[unresolved-attribute]  # real at runtime; build123d stubs incomplete
        return cls(
            volume=float(shape.volume),  # ty: ignore[unresolved-attribute]  # Shape.volume property exists at runtime
            bbox=(float(sz.X), float(sz.Y), float(sz.Z)),
            center=(float(c.X), float(c.Y), float(c.Z)),
            n_solids=len(shape.solids()),
            n_faces=len(shape.faces()),
        )


def _ratio(a: float, b: float) -> float:
    return a / b if abs(b) > 1e-12 else math.inf


def _scale_hint(ratios: list[float]) -> str | None:
    """Name the likely unit bug behind a set of length/volume ratios."""
    for r in ratios:
        for factor, name in ((10.0, "cm->mm (x10) length"), (1000.0, "cm->mm (x10) volume"),
                             (RAD_DEG, "rad->deg (x57.3)")):
            if abs(r - factor) / factor < 0.05 or abs(r - 1 / factor) / (1 / factor) < 0.05:
                return name
    return None


def compare(candidate: Shape, reference: Shape, *,
            rel_tol: float = 0.02, abs_tol_mm: float = 0.05) -> tuple[bool, str]:
    """Diff `candidate` (the translation) against `reference` (the Fusion STEP)."""
    a, b = Metrics.of(candidate), Metrics.of(reference)
    lines, ok = [], True

    vol_ratio = _ratio(a.volume, b.volume)
    vol_rel = abs(a.volume - b.volume) / max(abs(b.volume), 1e-12)
    vol_ok = vol_rel <= rel_tol
    ok &= vol_ok
    lines.append(f"  volume     : {a.volume:14.3f} vs {b.volume:14.3f}  "
                 f"rel={vol_rel:.2e} ratio={vol_ratio:.3f}  {'ok' if vol_ok else 'FAIL'}")

    length_ratios = []
    for ax, ca, cb in zip("XYZ", a.bbox, b.bbox):
        rel = abs(ca - cb) / max(abs(cb), 1e-12)
        bad = rel > rel_tol and abs(ca - cb) > abs_tol_mm
        ok &= not bad
        length_ratios.append(_ratio(ca, cb))
        lines.append(f"  bbox.{ax}    : {ca:14.3f} vs {cb:14.3f}  "
                     f"rel={rel:.2e}  {'FAIL' if bad else 'ok'}")

    for ax, ca, cb in zip("XYZ", a.center, b.center):
        d = abs(ca - cb)
        bad = d > abs_tol_mm and d > rel_tol * max(abs(cb), 1.0)
        ok &= not bad
        lines.append(f"  center.{ax}  : {ca:14.3f} vs {cb:14.3f}  "
                     f"d={d:.3e}  {'FAIL' if bad else 'ok'}")

    for name, ca, cb in (("solids", a.n_solids, b.n_solids), ("faces", a.n_faces, b.n_faces)):
        same = ca == cb
        # face-count mismatch is a WARNING (fillets/tangent merges legitimately differ), not a hard fail
        lines.append(f"  {name:<10}: {ca:14d} vs {cb:14d}  {'ok' if same else 'WARN (differs)'}")
        if name == "solids" and not same:
            ok = False

    hint = _scale_hint([vol_ratio] + length_ratios)
    if hint:
        lines.append(f"  >> LIKELY UNIT BUG: ratio matches {hint}. Check the cm->mm / rad->deg helper.")
    return ok, "\n".join(lines)


def compare_to_step(candidate: Shape, step_path: str, **kw) -> tuple[bool, str]:
    return compare(candidate, import_step(step_path), **kw)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2
    try:
        cand, ref = import_step(argv[1]), import_step(argv[2])
    except Exception as exc:  # noqa: BLE001 - report any load failure to the user
        print(f"error loading STEP: {type(exc).__name__}: {exc}")
        return 2
    ok, report = compare(cand, ref)
    print(f"candidate: {argv[1]}\nreference: {argv[2]}\n{report}")
    print("\nRESULT:", "WITHIN TOLERANCE" if ok else "OUT OF TOLERANCE")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
