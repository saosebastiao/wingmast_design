# Detailed specs

Per-feature spec-driven artifacts. One directory per feature, numbered sequentially:
`docs/specs/<NN-feature>/` with `spec.md` (what + why + acceptance) and `plan.md`
(how + steps + deliverable). Each traces to the parent requirement IDs in
`docs/specification.md` and the phase in `docs/plan.md`. See the `spec-workflow` skill.

Copy `_template/` to start. Findings still go to `docs/findings.md` (never here).

Suggested first specs (critical path — next session):
- `00-rescope-groundwork` (Phase 0)
- `01-rotating-geometry` (Phase G)
- `02-tandem-aero-loads` (Phase A) — includes the **D-2 feathering-robustness / survival-AoA** study
