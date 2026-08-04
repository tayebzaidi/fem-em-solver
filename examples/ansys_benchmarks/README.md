# Ansys Electronics Desktop benchmark cases

Cross-validation cases for direct replication in Ansys Electronics Desktop
(HFSS / Circuit), per PROJECT_PLAN.md §5.4. Cases are commissioned by the
weekly planning review, only on gated physics — roughly one per phase
milestone.

Each case is a directory `<case>/` containing:

- `SPEC.md` — the replication spec, precise enough to build in AED with **no
  judgement calls**: geometry with dimensions, materials (σ, εᵣ, μᵣ),
  boundary conditions, port definitions, drive frequencies, mesh guidance,
  and exactly which quantities to export.
- The runnable script (executed via `./run_examples.sh`), producing
  combined-XDMF output and a metrics JSON.
- `COMPARISON.md` — our numbers filled in, blank columns for the AED numbers.
  The human operator runs the AED replication and fills them in; the next
  weekly review adjudicates (agreements become §7 gates, disagreements become
  known-issues entries and diagnosis chunks).

No cases exist yet: the first is commissioned when a phase milestone lands on
gated physics (see PROJECT_PLAN.md §10, long-horizon roadmap).
