---
name: spec-workflow
description: Use when starting a new feature/capability, writing or updating a constitution/specification/plan/detailed-spec, or deciding where a new design or requirements document belongs in this repo. The spec-driven flow is constitution -> specification -> plan -> per-feature detailed spec+plan -> implementation.
---

# Spec-driven workflow

This project runs **spec-driven** (Constitution Article XIII). Every artifact traces to the
one above it. Do not start implementing a non-trivial capability before its detailed spec
exists and is consistent with the constitution.

## The hierarchy (precedence top-down)

| Level | File | Holds |
|---|---|---|
| Constitution | `docs/constitution.md` | supreme principles (how we decide) |
| Specification | `docs/specification.md` | top-level requirements `R-*` / goals `G-*` / decisions `D-*` |
| Engineering basis | `docs/engineering_basis.md` | the verified numbers + provenance behind the spec |
| High-level plan | `docs/plan.md` | forward phases 0/G/A/S/M/O/V (no findings) |
| Detailed specs | `docs/specs/<NN-feature>/spec.md` + `plan.md` | per-feature requirements + steps |
| Findings | `docs/findings.md` | append-only results + decisions log (no forward plan) |

`CLAUDE.md` is the operational layer beneath the constitution.

## Starting a feature

1. Pick the plan phase (e.g. "Phase G.2 rotating-mast geometry").
2. Create `docs/specs/<NN-feature>/` (copy `docs/specs/_template/`). Number `NN` sequentially.
3. Write `spec.md`: scope, the requirements it satisfies (cite the parent `R-*`/`G-*` IDs),
   acceptance tests, and any new local decisions. **Tighten, never relax, constitution
   principles.**
4. Write `plan.md`: the implementation steps, which existing modules are reused/refactored
   (cite the audit verdicts), the FD-validation tests required (Article IX), and the
   deliverable example + smoke test.
5. Implement. End in a runnable `examples/` script + passing test + a recorded finding
   (`record-finding` skill) with measured wall-clock.

## Conventions

- Requirement IDs: `R-<area>-<n>` (testable), `G-<n>` (goal), `D-<n>` (decision/assumption),
  `OUT-n` (out of scope). MUST/SHOULD/MAY per RFC-2119.
- A spec states **what + why + acceptance**; a plan states **how + steps + deliverable**.
  Keep findings out of both.
- When a decision/assumption (`D-*`) is resolved or an open question (basis §9) is answered,
  record it in `docs/findings.md` and update the spec's `D-*` row.
- Amending the constitution: bump its semver and append a decisions-log row (see its
  §Governance).
