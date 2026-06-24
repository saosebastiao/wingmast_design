"""marimo rendering helpers for the interactive wingmast notebooks.

The notebooks under ``notebooks/`` are a parallel, interactive view of the
``examples/*.py`` measurement-record scripts. They share these presentation
helpers so every notebook reads consistently:

  * Feasibility / fidelity checks (``R-AMZ-*`` requirements, Article II) render
    as a coloured PASS/FAIL badge via :func:`check`. The badge is a *mirror* of
    the real ``assert`` that stays in the cell — run a notebook headless
    (``uv run python notebooks/NN.py``) and a broken check still exits non-zero,
    so the notebook remains a real measurement gate, not just a pretty view.
  * Wall-clock is measured, never estimated (Article I), and shown via
    :func:`stamp`.
  * ``print`` loops of station/comparison data become markdown tables
    (:func:`table`) or key/value summary blocks (:func:`kv`).

marimo is a *dev* dependency: it is imported lazily inside each function, so
importing :mod:`wingmast_design.viz` (or the package) never requires marimo and
the runtime package stays marimo-free.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence


def _mo():
    """Lazy marimo import (keeps the runtime package marimo-free)."""
    import marimo as mo

    return mo


def _cell(x: Any) -> str:
    """Format one table/kv cell. Floats are left to the caller (they know the
    right precision); everything else is ``str``-ified, with pipes escaped so a
    stray ``|`` cannot break the markdown table."""
    return str(x).replace("|", "\\|")


def check(label: str, passed: bool, detail: str = ""):
    """Render a green (pass) / red (fail) badge for a requirement check.

    Pair it with the matching ``assert`` in the same cell so a headless run
    still fails loudly — this badge is the human-readable mirror, not the gate.

    Args:
        label:  the requirement / check name, e.g. ``"R-AMZ-1 station fidelity"``.
        passed: the boolean verdict (usually the same condition as the assert).
        detail: optional one-line detail, e.g. ``"worst 0.3 mm ≤ 1 mm"``.
    """
    mo = _mo()
    icon = "✅" if passed else "❌"
    verdict = "PASS" if passed else "FAIL"
    tail = f"  \n{detail}" if detail else ""
    return mo.callout(
        mo.md(f"{icon} **{label} — {verdict}**{tail}"),
        kind="success" if passed else "danger",
    )


def stamp(label: str, seconds: float):
    """Wall-clock stamp (Article I: measure, never estimate).

    ``seconds`` must be a *measured* duration (``time.perf_counter()`` delta),
    not a guess.
    """
    mo = _mo()
    return mo.md(f"⏱ **{label}** — measured **{seconds:.2f} s** wall-clock")


def table(headers: Sequence[Any], rows: Sequence[Sequence[Any]], *, title: str | None = None):
    """Markdown table from a header row + body rows (replaces a ``print`` loop).

    Callers pre-format numbers to the precision they want; cells are otherwise
    stringified. Returns a ``marimo`` markdown object.
    """
    mo = _mo()
    head = "| " + " | ".join(_cell(h) for h in headers) + " |"
    sep = "| " + " | ".join("---" for _ in headers) + " |"
    body = "\n".join("| " + " | ".join(_cell(c) for c in row) + " |" for row in rows)
    md = "\n".join([head, sep, body])
    if title:
        md = f"**{title}**\n\n{md}"
    return mo.md(md)


def kv(mapping: Mapping[str, Any] | Sequence[tuple[str, Any]], *, title: str | None = None):
    """Key/value summary block (bulleted ``**key:** value`` list) from a mapping
    or a sequence of ``(key, value)`` pairs."""
    mo = _mo()
    items = mapping.items() if isinstance(mapping, Mapping) else mapping
    lines = [f"- **{k}:** {_cell(v)}" for k, v in items]
    md = "\n".join(lines)
    if title:
        md = f"**{title}**\n\n{md}"
    return mo.md(md)
