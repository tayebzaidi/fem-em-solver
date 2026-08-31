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

## Basis / element order — mandatory in every `SPEC.md`

Ansys and FEniCS name curl-conforming bases by different conventions — HFSS by
the polynomial order of the tangential field, FEniCS by the Nédélec index — and
they are **off by one**. Our production order is `degree = 1`, which is what
HFSS calls **Zero Order**, *not* its default **First Order**. A replication run
at AED's defaults therefore compares a 20-unknown element against our
6-unknown one: a discretization difference that would land in the same column
as the physics.

| HFSS name | unknowns/tet | ours | measured DOF/tet |
|---|---|---|---|
| Zero Order | 6 (edges only) | `degree=1` — **our production order** | **6** |
| **First Order** *(HFSS default)* | 20 (edges + faces) | `degree=2` | **20** |
| Second Order | 45 | `degree=3` | **45** |
| Mixed Order | per element | **no equivalent** — `TimeHarmonicSolver.degree` is one global int | — |

The right-hand column is measured on our side (0.11 image, 2026-08-28); the
HFSS column is the standard basis definition and is **not yet confirmed**
against AED's own output.

Every `SPEC.md` solver section therefore carries a *Basis / element order*
line stating the ruling of §7 `ANS-5` (weekly planning review, 2026-08-30):

- AED is run **twice** and both columns are reported — **(a) Zero Order**, the
  matched discretization and the **adjudication** column, and **(b) First
  Order** (the AED default), an **order-sensitivity** column. Our side stays at
  one order; `ANS-5` does not re-open the production element order.
- **Mixed Order is forbidden.** We have no per-element order and could not
  reproduce such a run, so it is not comparable to any run of ours.
- Each `SPEC.md` asks the operator to **confirm the unknowns-per-tetrahedron
  figure AED prints** in its matrix statistics, per run, so the table above
  stops being an assumption.
- `COMPARISON.md` carries the matching *Solve metadata* rows — **basis order**
  and unknowns/tet — with one AED column per order.

Numbers already returned from AED at an unrecorded order stand as an
**order-unknown** column; the review decides whether they stay, are re-run, or
are annotated.

## Cases

- `loop_over_lossy_slab_10MHz/` — **ANS-1**, commissioned 2026-08-09
  (weekly review). Coil-loading ΔZ of a circular loop over a σ = 100 S/m
  slab at 10 MHz, on `MAT-6`'s gated physics (ΔR vs Dodd–Deeds to 1.58%).
  `SPEC.md` committed; runnable half is §7 chunk `ANS-1`; ready for operator
  replication when that chunk closes (it then goes to the dashboard's
  Waiting-on-you list).
