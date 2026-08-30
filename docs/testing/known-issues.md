# Known Issues — failing tests and open defects

**Purpose: tell you whether a failure is yours.**

Every entry below was verified failing *before* the work recorded against it, by
checking out the stated commit and re-running. If you hit one of these, you did not
break it. If you hit something not listed here, you probably did.

That distinction is the whole point of this file. Establishing it after the fact
costs a `git stash` / re-run cycle per failure; it was done five times over on
2026-07-27 and is not worth repeating.

Last audited: 2026-07-27 against `ce92e8c`.

## How to check a failure against this baseline

```bash
# Is this failure mine, or was it already there?
git stash                              # or: git checkout <base> -- <paths>
mpiexec -n 8 python3 -m pytest <the failing test> -q
git stash pop
```

If it fails at the base commit too, add it here rather than fixing it in passing —
unless fixing it is the task.

---

## Failing tests

### ✅ RETIRED 2026-08-27 (`OPS-27` step 2, 21:00 implementer slot) — a **tenth** stale exact cell-count record, and it is a **fifth** mesh with **no sibling**: `test_dodd_deeds_reactance_wire_resolution.py` recorded 366 207 and 0.11 meshes 365 970

> **✅ RETIRED 2026-08-27, 21:00 implementer slot (`OPS-27` step 2).** The
> literal at `:268` is re-recorded 366_207 → **365_970**, exact equality,
> version-tagged with the 0.7.2 digit and the census log in-comment
> (`GEO-16` precedent, no band). Anchor: the projected half re-run from
> `main` at the same four node ids as the census —
> `20260828T022006Z_OPS-27-step2-wire-projected.log`, **4 passed in
> 459.44s**, Status 0, elapsed 462 s, `-n 2` complex, both rank streams
> identical, against the census's `1 failed, 3 passed`. Same collected
> count (4), so exactly this one name flipped. The module's `growth`
> denominator `138_619` at `:263` is **not** a record (it feeds the printed
> ratio and the unmoved `2.0 < growth < 3.5` band) and was left at its
> 0.7.2 digit — step 1 finding 40's prose class.

> **CANDIDATE OWNER: `OPS-27`** (§9 item 2), extending the leg (f) entry
> below. This one refines that entry's shape rather than repeating it: the
> class is now **ten red names over nine modules carrying five distinct
> meshes**, and this fifth mesh is recorded in **exactly one** place, so
> "one re-record retires up to four names" is an upper bound, not the
> typical case — the sweep must still be by value, but the value→module
> map is ragged (4, 3, 1, 1, 1).

| | |
|---|---|
| **Test (1 new name, footered Status 1, at `4586a13`)** | `tests/validation/test_dodd_deeds_reactance_wire_resolution.py::test_the_refinement_landed_on_the_wire_and_not_on_the_far_field` (1 of the module's 6 validation names; the other 5 are green — 2 in the same run, 2 `pinned` in `20260827T201823Z`, the 6th selected in the same node-id list and green) |
| **Log** | `docs/testing/logs/20260827T202222Z_OPS-26-step2g-dodd-wireres-projected.log` — `1 failed, 3 passed in 434.40s`, **Status 1**, elapsed 436 s, `-n 2`, **complex build**, heavy tier, four names selected by node id. Both rank streams identical (434.36 / 434.40 s). |
| **Symptom** | `AssertionError: the mesh is deterministic and only resolution_wire moved, so the cell count must be the probe's 366207; got 365970`, at `test_dodd_deeds_reactance_wire_resolution.py:268`. |
| **Cause — not diagnosed in code** | Same class: an exact-equality cell count recorded on 0.7.2, never swept when `OPS-18` moved the image. Drift **−237 on 366 207 = −0.0647%**, a *fifth* distinct per-mesh figure and the second negative one (−0.093%, −0.065%, +0.032%, +0.075%, +0.233%) — confirming again that no unmeasured record can be predicted from a measured one. The test's stated premise ("the mesh is deterministic and only `resolution_wire` moved") is not what failed; the *record* is stale. |
| **Sibling sweep (zero compute)** | `grep -rn '366207\|366_207' tests/` returns **only** `:268` and its message at `:270` — no sibling module carries this mesh, unlike 138 619 (three modules) and 417 914 (three). |
| **Disposition** | Filed, **not fixed** — `OPS-26` step 2 is a census and lands no fix. Expected on `main`; **not yours**. |

### ✅ RETIRED 2026-08-27 (`OPS-27` steps 1 and 2) — **five more stale exact cell-count records across five modules, and the class collapses to THREE shared meshes, not nine independent constants**

> **✅ THE 417 914 AND 697 401 FAMILIES RETIRED 2026-08-27, 21:00
> implementer slot (`OPS-27` step 2) — this entry is now fully retired.**
> Two edits closed all three remaining names:
> `test_dodd_deeds_resistance_slab_resolution.NCELLS_FINE` and
> `test_coil_loading_larmor_resolution.NCELLS_FINE`, both 417_914 →
> **418_888**, and
> `test_dodd_deeds_reactance_combined_knobs.NCELLS_COMBINED` 697_401 →
> **697_926** — exact equalities, version-tagged, no band, `git diff --
> src/` empty. Anchors from `main`, both rank-stream-identical:
> `20260828T020157Z_OPS-27-step2-slab.log` — **16 passed in 479.37s**,
> Status 0, elapsed 482 s, `-n 2` complex (census: `1 failed, 15 passed`);
> `20260828T021014Z_OPS-27-step2-knobs.log` — **15 passed in 577.00s**,
> Status 0, elapsed 579 s, `-n 8` complex (census: `1 failed, 14 passed`).
> Collected counts identical to the census runs (16 / 15), so exactly the
> two stale-record names flipped. `larmor_resolution` was **edited but not
> re-run in this slot** — it asserts the same 418 888 the slab run
> measured on the same mesh; its re-run is owed to the next census (see
> the `third_rung` entry below, which shares the constant by import).
> **The owed re-run landed 2026-08-28, 16:30 slot (`OPS-27` step 3):**
> `20260828T213049Z_OPS-27-step3-larmor-resolution.log` — **17 passed in
> 424.32s**, Status 0, elapsed 426 s, `-n 2` complex, both rank streams
> identical, against the census's `1 failed, 16 passed` on the same
> collected 17. Nothing is owed on this entry any more.

> **✅ THE 138 619 FAMILY RETIRED 2026-08-27, 19:30 implementer slot
> (`OPS-27` step 1); the 417 914 and 697 401 families closed by step 2
> above.** Four of this entry's six names are green
> from `main` — `richardson_ladder::test_the_rung_has_its_recorded_cell_count`
> `[10MHz]` and `[30MHz]`, `larmor_probe::test_the_mesh_is_the_mat6_step3_baseline`,
> `transition_30mhz::test_the_mesh_is_the_step1_baseline`. Finding 30's
> "the unit of repair is the mesh, not the file" is **confirmed to its
> strongest form here**: all four names read one constant,
> `test_coil_loading_larmor_probe.NCELLS_BASELINE`, imported by the other
> two modules (and by `test_coil_loading_degree2.py`), so **one edit**
> 138_619 → **138_490** retired four reds. Logs, both `-n 2` complex,
> standard tier, both rank streams identical:
> `20260828T003400Z_OPS-27-step1-richardson.log` — **25 passed in 147.00s**,
> Status 0, elapsed 149 s (census: `2 failed, 23 passed`);
> `20260828T003636Z_OPS-27-step1-probe-30mhz.log` — **23 passed in 149.09s**,
> Status 0, elapsed 150 s (census: `2 failed, 21 passed`). Same collected
> counts as the census runs (25 / 23), so only the two stale-record names
> per run flipped. **Still open in this entry:**
> `slab_resolution::test_the_refinement_landed_in_the_slab_and_not_on_the_wire_or_far_field`
> and `larmor_resolution::test_the_mesh_is_the_mat6_step8_fine_rung`
> (417 914 → 418 888) and
> `combined_knobs::test_the_combined_mesh_is_the_probes_and_both_knobs_moved`
> (697 401 → 697 926).

> **CANDIDATE OWNER: `OPS-27`** (§9 item 2), whose rubric as written names
> **two** sites. The census has now found **nine red names over eight
> modules**, and this entry is the one that changes the shape of the job:
> the nine reds carry only **four distinct** 0.7.2-era cell counts, because
> the same mesh is recorded independently in several modules. Re-recording
> is therefore four measurements and ~nine edits, not nine measurements —
> but a per-file fix that misses a sibling leaves a red behind.

| | |
|---|---|
| **Tests (5 new names, all footered Status 1, all at `cf03754`)** | `test_coil_loading_richardson_ladder.py::test_the_rung_has_its_recorded_cell_count[10MHz]` and `[30MHz]`; `test_coil_loading_larmor_probe.py::test_the_mesh_is_the_mat6_step3_baseline`; `test_coil_loading_transition_30mhz.py::test_the_mesh_is_the_step1_baseline`; `test_dodd_deeds_resistance_slab_resolution.py::test_the_refinement_landed_in_the_slab_and_not_on_the_wire_or_far_field`; `test_dodd_deeds_reactance_combined_knobs.py::test_the_combined_mesh_is_the_probes_and_both_knobs_moved`; `test_coil_loading_larmor_resolution.py::test_the_mesh_is_the_mat6_step8_fine_rung` |
| **Logs** | `20260827T183121Z_OPS-26-step2f-richardson.log` (`2 failed, 23 passed in 141.15s`, `-n 2` complex, 143 s); `20260827T185143Z_OPS-26-step2f-probe-30mhz.log` (`2 failed, 21 passed in 137.35s`, `-n 2` complex, 139 s); `20260827T183401Z_OPS-26-step2f-dodd-slab-resolution.log` (`1 failed, 15 passed in 429.91s`, `-n 2` complex, 431 s); `20260827T184138Z_OPS-26-step2f-dodd-combined-knobs.log` (`1 failed, 14 passed in 568.26s`, `-n 8` complex, 570 s); `20260827T185422Z_OPS-26-step2f-larmor-resolution.log` (`1 failed, 16 passed in 428.37s`, `-n 2` complex, 430 s). Rank streams identical on all five. |
| **Symptom** | Each is `AssertionError: … the count must be … <recorded>; got <measured>`, with only three distinct pairs across seven of the nine census names: **138 619 → 138 490** (−129, **−0.093%**) in `richardson_ladder` ×2, `larmor_probe`, `transition_30mhz`; **417 914 → 418 888** (+974, **+0.233%**) in `slab_resolution`, `larmor_resolution` and (leg (e)) `third_rung`; **697 401 → 697 926** (+525, **+0.075%**) in `combined_knobs`. The fourth quantity is leg (d)'s **2 807 309 → 2 808 204** (+0.032%) in `mesh_cache`. |
| **Cause — not diagnosed in code** | 0.11's gmsh meshes the *same* geometry to a slightly different cell count than 0.7.2 did; the records are exact equalities never swept when `OPS-18` re-recorded. **Drift is not one signed constant** — it is −0.093%, +0.032%, +0.075%, +0.233% on four meshes, so it is per-mesh, not a global offset, and cannot be predicted for an unmeasured record. Every affected module's *other* names are green in the same run: the physics reproduces, the cell count does not. |
| **What this adds to `OPS-27`'s rubric** | (1) The sweep must be **by cell-count value across modules**, not per file — 138 619 alone appears in three modules, 417 914 in three. (2) `grep -rn '0\.7\.2' tests/` is insufficient (leg (e)'s note, now confirmed twice): none of these five was reachable by version tag, only by reading a red's assertion message. (3) One re-record of a shared mesh retires up to four red names at once, so the job is **four measurements**, not nine. |
| **Disposition** | Filed, **not fixed** — `OPS-26` step 2 is a census and lands no fix. Expected on `main`; **not yours**. |

### ✅ RETIRED 2026-08-28 (`OPS-27` step 3, 16:30 implementer slot) — `test_coil_loading_larmor_third_rung.py` asserted an **exact** fine-rung cell count recorded on the 0.7.2 image (417 914) and 0.11 meshes 418 888: the **fourth** site of the stale-record class, and the largest drift yet at 0.233%

> **✅ RETIRED 2026-08-28, 16:30 implementer slot (`OPS-27` step 3) — the
> owed re-run executed and the module is green.**
> `20260828T213807Z_OPS-27-step3-thirdrung.log` — **18 passed in 291.03s**,
> Status 0, elapsed 293 s, `-n 8` complex, `TH11_STEP5_RUNG=fine`, heavy
> tier; all eight rank streams identical (290.98–291.05 s). The census read
> `1 failed, 17 passed` on the same collected 18, so exactly the one
> stale-record name flipped and no other name's status moved. No code
> changed in this slot — the import of `NCELLS_FINE` from
> `larmor_resolution` (finding 41) is what re-recorded it in step 2; this
> entry stayed open only for the missing execution. **Cost note (a
> correction to finding 25's inference):** the module's *cold* price was
> never measured — the 900 s window ruled for it returned at 291 s, i.e.
> the 304 s warm figure was essentially the whole price, and this slot's
> `larmor_resolution` window ran first as ruled, so the figure is again
> warm-fixture. The ≥ 500 s cold estimate is **not** confirmed; nothing on
> record measures this module cold.

> **🟡 RE-RECORDED but NOT RE-RUN in the 21:00 slot.** This module holds no
> constant of its own: `:443` asserts the `expected` drawn from the `fine`
> entry of its rung table, which is `NCELLS_FINE` **imported from**
> `tests/validation/test_coil_loading_larmor_resolution` (step 1
> finding 38's import-graph rule, repeating). So the single 417_914 →
> **418_888** edit in `larmor_resolution` re-records this name too, and
> `git diff -- tests/validation/test_coil_loading_larmor_third_rung.py` is
> empty. The same mesh value was **measured green** in the slab run
> (`20260828T020157Z_OPS-27-step2-slab.log`, 16 passed), but this module
> was not itself re-executed: it is a warm-cache-only ~304 s at `-n 8`
> (`OPS-26` finding 25) and did not fit beside the slot's three windows.
> **Re-run owed to the next census.** Entry stays filed until then.

> **CANDIDATE OWNER: `OPS-27`** (§9 item 2) — same class, same remedy
> (re-record exact, version-tagged, `GEO-16` precedent, no band). `OPS-27`'s
> §7 rubric as written names **two** sites; this is a third and the review
> should decide whether to fold it in or leave it for the sweep clause.
> Filed here so it is not lost either way.

| | |
|---|---|
| **Test** | `tests/validation/test_coil_loading_larmor_third_rung.py::test_the_rung_is_inside_the_priced_ceiling` (1 of the module's 7 collected names; the other 6 are green in the same run) |
| **Log** | `docs/testing/logs/20260827T171110Z_OPS-26-step2e-thirdrung-destubbed.log` — `1 failed, 17 passed in 302.31s`, **Status 1**, elapsed 304 s, `-n 8`, **complex build**, `TH11_STEP5_RUNG=fine`, heavy tier. All eight rank streams identical (302.29–302.35 s). Footered, so it counts as a red under the census's fail-closed control. Verified at `b9b8cc7`. |
| **Symptom** | `AssertionError: frequency does not reach the mesh generator, so the count must be the rung's recorded 417914; got 418888`, at `test_coil_loading_larmor_third_rung.py:443`. |
| **Cause — not diagnosed in code** | An **exact-equality** cell-count record made on the **0.7.2** image, compared against a mesh generated by 0.11's gmsh. Drift is **+974 cells on 417 914 = +0.233%** — an order of magnitude larger in relative terms than the `mesh_cache` site's 0.032%, but still far below any geometry change, and the same sign. The test's own premise (*"frequency does not reach the mesh generator"*) is **not** what failed: the count is frequency-independent as claimed, it is the *record* that is stale. Corroborated by the other 6 names in the module — including both complex-power identities, the free-solve dissipation identity and `test_the_fine_rung_reproduces_step2s_recorded_deviation` — passing in the same run, i.e. the physics on this rung reproduces its `TH-11` step-2 record while only the cell count does not. |
| **Class — fourth instance this census** | Same class as leg (d)'s finding 23 (`mesh_cache`, 0.032%), leg (c)'s finding 19 (`test_geometry_floor_discriminator.py`) and `GEO-16`'s two-torus red: **exact-equality records made on 0.7.2, never swept after the 0.11 bump**. Four sites, three distinct quantities (residual, cell count ×2, separation ratio). Note for `OPS-27`: its planned `grep -rn '0\.7\.2' tests/` sweep would **not** necessarily have found this one — the constant at `:443` must be reached by *reading the assertion messages of the census reds*, not only by the version tag, so the sweep clause should be widened to exact-equality mesh counts regardless of tag. |
| **Disposition** | Filed, **not fixed** — `OPS-26` step 2 is a census and lands no fix. Expected on `main`; **not yours**. |

### ✅ RETIRED 2026-08-27 (`OPS-27` step 1, 19:30 implementer slot) — `test_coil_loading_larmor_mesh_cache.py` asserted an **exact** third-rung cell count recorded on the 0.7.2 image (2 807 309) and 0.11 meshes 2 808 204: a 0.032% gmsh drift against an equality record

> **✅ RETIRED 2026-08-27, 19:30 implementer slot.** `NCELLS_THIRD`
> 2_807_309 → **2_808_204**, version-tagged with the 0.7.2 digit and
> `20260827T141059Z_OPS-26-step2d-meshcache-real.log` in-comment, docstring
> copies moved. The disposition line below argues an equality on a mesher
> count is "arguably the wrong shape"; **that call was not taken** — the
> review ruled exact-and-version-tagged (`GEO-16` precedent, no band), and
> `NCELLS_THIRD_CEILING` is unchanged. Green from `main`:
> `20260828T003915Z_OPS-27-step1-meshcache-real.log` — **12 passed, 4
> skipped in 254.75s**, Status 0, elapsed 256 s, `-n 2` **real** build,
> standard tier, both rank streams identical; against the census's `1
> failed, 11 passed, 4 skipped`, i.e. the same 4 `tests/environment`
> complex-only skips and the one red flipped.

> **OWNER ASSIGNED 2026-08-27, 10:30 review: `OPS-27`** (§9 item 2) — the
> stale-record class, one chunk for both open sites; re-record exact and
> version-tagged on the `GEO-16` precedent, no band. Retires with it.

| | |
|---|---|
| **Test** | `tests/validation/test_coil_loading_larmor_mesh_cache.py::test_the_cached_rung_is_the_priced_mesh` (1 of the module's 5 collected names; the other 4 are green in the same run) |
| **Log** | `docs/testing/logs/20260827T141059Z_OPS-26-step2d-meshcache-real.log` — `1 failed, 11 passed, 4 skipped in 217.70s`, **Status 1**, elapsed 219 s, `-n 2`, **real build**, standard tier. Both rank streams identical (217.68 / 217.70 s). Footered, so it counts as a red under the census's fail-closed control. Verified at `5590b81`. |
| **Symptom** | `AssertionError: the third rung meshed to 2808204 cells, not the probe's recorded 2807309: the fixture changed rather than being re-meshed`, `assert 2808204 == 2807309`. The 4 skips are all in `tests/environment` (complex-only tests correctly skipped in the real build), **not** in the census roots. |
| **Cause — not diagnosed in code** | An **exact-equality** cell-count record made by the `TH-11` step-5 probe on the **0.7.2** image, compared against a mesh generated by 0.11's gmsh. The drift is **+895 cells on 2.81 M = +0.032%** — far too small to be a geometry change and exactly the size of a mesher-version tetrahedralisation difference. No `src/` or fixture edit is implicated: the assertion message's own alternative ("the fixture changed rather than being re-meshed") is the *other* branch, and nothing in `git log` touches this fixture since `OPS-18`. |
| **Class — third instance this census** | This is the same defect class as leg (c)'s finding 19 (`test_geometry_floor_discriminator.py`, a pre-`OPS-18` 128 MHz constant) and `GEO-16`'s two-torus red: **records not swept after the 0.11 re-record**. Three sites now. The census's value here is that the class, not the individual constant, is the finding — a review should commission one sweep chunk over all exact-equality records made on 0.7.2 rather than three one-constant fixes. |
| **Disposition** | Filed, **not fixed** — `OPS-26` step 2 is a census and lands no fix (`OPS-26` §7 scope). The fix is a one-constant re-record on the 0.11 image with the basis stated in-comment, and an equality assertion on a mesher cell count is arguably the wrong shape in the first place (a ±0.1% band would survive an image bump); both calls belong to a chunk, not to this slot. Until then this red is expected on `main` and is **not yours**. |

### ✅ RETIRED 2026-08-27 (`OPS-27` step 1, 19:30 implementer slot) — `test_geometry_floor_discriminator.py` asserted the **pre-`OPS-18`** 128 MHz record (1.8260%) and measured `OPS-18`'s re-recorded 1.7686%: a stale constant, not a physics regression

> **✅ RETIRED 2026-08-27, 19:30 implementer slot — landed exactly as ruled.**
> `RECORD_128_RELL2` 0.01826 → **0.017686** and `RECORD_128_SEPARATION`
> 57.31 → **59.16**, version-tagged with the 0.7.2 digits and both census
> logs in-comment (`GEO-16` precedent), every docstring copy moved and the
> dated 2026-08-13 result block annotated rather than rewritten. **No band
> touched** (`REPRODUCTION_BAND` 1%, `CELL_COUNT_BAND` 1% unchanged) and the
> 64 MHz leg untouched. Green from `main`:
> `20260828T003300Z_OPS-27-step1-geomfloor.log` — **12 passed in 46.45s**
> (11 `tests/environment` + this module's one test), Status 0, elapsed 49 s,
> `-n 2` complex, smoke tier, both rank streams identical.

> **OWNER ASSIGNED 2026-08-27, 10:30 review: `OPS-27`** (§9 item 2) —
> `RECORD_128_RELL2` / `RECORD_128_SEPARATION` → `OPS-18`'s 0.017686 /
> 59.16, every docstring copy moved in the same commit. Retires with it.

| | |
|---|---|
| **Test** | `tests/validation/test_geometry_floor_discriminator.py::test_larmor_sphere_residual_at_the_priced_fine_mesh` (the module's only test) |
| **Log** | `docs/testing/logs/20260827T125507Z_OPS-26-step2c-v42-geomfloor.log` — `1 failed in 22.15s`, **Status 1**, elapsed 23 s, `-n 2`, **complex build** (`FEM_EM_REQUIRE_COMPLEX=1`), smoke tier. Both rank streams identical. Footered, so it counts as a red under the census's fail-closed control. Verified at `58c77d9`. |
| **Symptom** | `AssertionError: the 128 MHz relL2 moved to 1.7686% from the recorded 1.8260% (3.14% > 1%) at the mesh it was recorded on. That is a regression in the fixture or this file, not a geometry finding — the 64 MHz reading above must not be interpreted until it is explained`, `assert 0.03141140883816601 < 0.01`. The 64 MHz leg passes; only the 128 MHz record fires. |
| **Cause — not diagnosed in code, but the number is already explained on `main`** | The measured 1.7686% is **`OPS-18`'s value**. PROJECT_PLAN §2 and CLAUDE.md both record that `TH-10`'s 128 MHz figure "is 1.769% on the 0.11 image `main` boots — re-recorded with its mesh by `OPS-18`, 2026-08-22", against the 1.826% originally recorded on the 0.7.2 image at `TH-10` closure (2026-08-13). This file's constant is therefore the **pre-`OPS-18`** one: the assertion is comparing a 0.11 measurement against a 0.7.2 record, and its own message ("a regression in the fixture or this file") names the right disposition — it is *this file*. The test is doing its job; nobody updated it when `OPS-18` re-recorded. |
| **What this does *not* mean** | It is **not** evidence against `TH-10`, and not a new 0.11 break. The 3.14% is the distance between two *recorded* numbers, not a drift in the solve; the solve reproduces `OPS-18` to the digits printed. Do not re-open `TH-10` on this. |
| **Disposition** | Filed, not fixed — `OPS-26` step 2 is a census and lands no fix (`OPS-26` §7, leg (c) scope). The fix is a one-constant re-record with the `OPS-18` mesh cross-referenced in-comment, and it belongs to a chunk that can re-run the priced fine mesh and state the basis; a review should commission it. Until then this red is expected on `main` and is **not yours**. |
| **Census accounting** | Counted as the census's 4th red repo-wide and as leg (b)'s owed complex conversion: the name carried by leg (b) as `deferred — complex-only, SKIPPED in the real build` is now **observed**, and it resolved to a red rather than the green the conversion pattern produced six times in leg (d). |

### ✅ RETIRED 2026-08-28 (`OPS-28`, 22:30 implementer slot) — the whole of `tests/ports/test_port_orientation_sensitivity.py` dies on `'_DummyComm' object has no attribute 'allgather'`: an **`OPS-14` rank-safety reduction broke its test double**, and nothing scheduled has run the module since

> **RETIRED 2026-08-28 by `OPS-28`.** `_DummyComm` gained
> `allgather(value) -> [value]` beside its `allreduce`
> (`tests/ports/test_port_orientation_sensitivity.py:23-31`); `src/` is
> untouched, the reduction stays, the deprecated route stays runnable.
> Bracketed by measurement: `20260828T033037Z_OPS-28-red-baseline.log`
> reproduces the `AttributeError` on both names (`3 failed, 14 passed in
> 1.50s`, Status 1, 3 s) and `20260828T033055Z_OPS-28-gate.log` is
> `2 failed, 15 passed in 0.79s` (Status 1, 2 s) on the identical command.
> **Disposition of the two names.**
> `…::test_port_orientation_flip_changes_induced_voltage_sign` is **green**
> — it asserts the sign-flip identity on the placeholder route
> (`V(P2) = +5.000000e-02 V` aligned, `−5.000000e-02 V` flipped, equal in
> magnitude to `rel=1e-12`, coupling factor `+1.0e-01 → −1.0e-01`), and
> that name is now retired outright.
> `…::test_port_orientation_flip_changes_off_diagonal_sparameter_sign`
> **now reaches its S-matrix assertion and is red there** — it belongs to
> **entry 3** and only to entry 3, which is re-dated below with the
> correction this run measured (the vanishing wave on *this* test is the
> **off-diagonal**, not the diagonal). The `AttributeError` symptom this
> entry filed is gone from both names, so the entry retires whole.

| | |
|---|---|
| **Tests** | `tests/ports/test_port_orientation_sensitivity.py::test_port_orientation_flip_changes_induced_voltage_sign` (**new** — not previously filed anywhere)<br>`tests/ports/test_port_orientation_sensitivity.py::test_port_orientation_flip_changes_off_diagonal_sparameter_sign` (already filed under **known-issues 3**, but for a *different* symptom — see "Relationship to entry 3") |
| **Log** | `docs/testing/logs/20260827T093747Z_OPS-26-step2b-p03-orient.log` — `2 failed, 3 warnings in 0.69s`, **Status 1**, elapsed 2 s, `-n 2`, real build, smoke tier. Footered, so these count as reds under the census's fail-closed control. |
| **Symptom** | Both tests raise, identically and immediately: `src/fem_em_solver/ports/excitation.py:265: in run_placeholder_port_coupling_case` → `{int(v) for values in problem.mesh.comm.allgather(` → `AttributeError: '_DummyComm' object has no attribute 'allgather'`. The second test reaches it one frame deeper, through `sparameters.py:368: in run_n_port_sparameter_sweep`. |
| **Cause — diagnosed, one line, not a 0.11 break** | `OPS-14` hardened `run_placeholder_port_coupling_case` to reduce the rank-local `cell_tags.values` before validating port tags (`excitation.py:262-268`, whose own comment says it is "fixed here so the deprecated route stays *runnable* as `PORT-1` step 4's negative control"). The module's stub comm — `tests/ports/test_port_orientation_sensitivity.py:16-21` — defines `rank` and a `staticmethod allreduce` and **nothing else**, so the new `allgather` call finds no attribute. The reduction is correct and must not be reverted; the double is what is stale. Note the irony recorded verbatim: the change made to keep the deprecated route runnable is what stopped it running, because the module that exercises it is not in any scheduled command. |
| **Relationship to entry 3** | Entry 3 ("Port tests assert a non-zero S-matrix diagonal on a matched port") lists `…::test_port_orientation_flip_changes_off_diagonal_sparameter_sign` as red for the *zero-diagonal* reason. That is no longer the symptom: the test now dies earlier, in the tag reduction, and never reaches its S-matrix assertion. Entry 3's diagnosis is unfalsified but currently **unreachable** on that test. `…::test_port_orientation_flip_changes_induced_voltage_sign` was never in entry 3 at all — it does not touch an S-matrix diagonal — so it is a genuinely new red. Both entries stay open; whichever chunk fixes the double must re-read entry 3 afterwards to see what the module actually asserts. |
| **Why the census counts this as a hit** | This is precisely the class `OPS-26` was commissioned to find (§7 `OPS-26`, "a module that no scheduled command runs can be red or dead indefinitely") — but it is a **new sub-class**: not an un-migrated 0.11 call site (step 1 swept those and `src/`+`tests/` are clean at 434 sites), and not a gmsh regression. It is **test-double drift behind a rank-safety fix**, invisible to `check_dolfinx_api_migration.py` by construction, since `comm.allgather` is a valid mpi4py API and `_DummyComm` is not a DolfinX type. Step 1's static sweep structurally cannot see this; only execution can. |
| **Verified at** | `b39799e`, real build, `-n 2`. |
| **Fix** | **Deliberately not fixed** — `OPS-26` is a census and files rather than repairs, per the item's own rule. The repair is one line (give `_DummyComm` an `allgather` returning `[value]`), but it belongs with a `PORT-0`/`PORT-1` owner who can also dispose of entry 3's assertions on the same module, and it needs a decision this census may not take: whether the deprecated placeholder route is kept runnable at all. |

### ✅ RETIRED 2026-08-28 (`GEO-23` step 2b, 13:30 implementer slot) — ~~🔴 OPEN 2026-08-27, re-headed 2026-08-28 (`GEO-23` step 1) — a **fifth** site of "Invalid boundary mesh (overlapping facets)"~~ — **`tests/materials/test_phantom_material_model.py:110` moved from `resolution=0.03` (does not mesh) to step 1's coarsest meshing rung `0.024`; the module is `4 passed` at `-n 1` and `-n 2` complex, `5464` cells to the digit**

> **GEOMETRY HALF CLOSED 2026-08-28 (`GEO-23` step 2b, 13:30 slot) — the
> sizing lever.** The call site is the only thing that moved: `0.03 → 0.024`,
> the coarsest rung step 1's monotone `-n 1` ladder measured as meshing on
> `coil_phantom_domain` (5 464 cells; the finer rungs are 0.0192 / 0.01536 /
> 0.012288). Nothing in `src/` and no band, tolerance or record was touched —
> the module pins no cell count, so the assertions that had to survive the
> re-mesh are its physics ones, and they all pass. Complex build,
> `FEM_EM_REQUIRE_COMPLEX=1`: `4 passed in 2.66s` at `-n 1`
> (`20260828T183204Z_GEO-23-step2b-phantommaterial-n1.log`, Status 0, 4 s) and
> `4 passed in 1.63s` at `-n 2`
> (`20260828T183214Z_GEO-23-step2b-phantommaterial-n2.log`, Status 0, 3 s),
> against the census red's `1 failed, 3 passed`. The printed global cell count
> is **5464 at both widths**, reproducing the step-1 ladder's 5 464 exactly
> (0.00% against the ±1% band). Both halves of this entry are now closed.

> **DEADLOCK HALF CLOSED 2026-08-28 (`GEO-23` step 2a, 12:00 slot).** The
> `-n 2` command no longer hangs: `coil_phantom_domain`'s rank-0 gmsh build is
> now wrapped, so rank 1 raises
> `RuntimeError: coil_phantom_domain geometry generation failed on rank 0
> (resolution=0.03); this is rank 1` instead of blocking in `_model_to_mesh`.
> **Status 1 in 2 s** where step 1 recorded **Status 124 at 120 s**, summary
> unchanged at `1 failed, 3 passed`
> (`20260828T170347Z_GEO-23-step2a-phantommaterial-n2.log`; `-n 1` control
> unchanged, `20260828T170340Z_…-n1.log`). **The entry stays OPEN for the
> geometry red itself** — the sizing lever (`GEO-23` step 2b) is what retires
> it; only the cost of observing it changed.
>
> **CORRECTED 2026-08-28 by measurement (`GEO-23` step 1, 09:00 slot).** This
> entry's "PASSED on one rank, FAILED on the other" claim does not survive an
> `-n 1` run. At `-n 1` the test is **Status 1 in 2 s** with the same
> `overlapping facets` string (`20260828T140613Z_GEO-23-step1b-phantommaterial-n1.log`,
> `1 failed, 3 passed in 1.18s`), so the failure is a deterministic property of
> the geometry. Re-reading the `-n 2` log with that in hand
> (`20260828T140622Z_…-n2.log`, lines 48–56): the second rank prints its three
> passes and then **nothing** — it never reaches the fourth name. **Absence of
> a verdict is not a PASS.** The `-n 2` Status 124 is the surviving rank
> blocking in the collective after the other raises — a **teardown/raise-path**
> effect, not a partition-dependent trigger. Consequently the row below headed
> "What it adds to `GEO-23`" is withdrawn: there is **no** second
> partition-dependent site, and the resolution-floor reading is *supported*,
> not weakened — `GEO-23` step 1's ladder shows this generator failing only at
> its own `resolution=0.03` and meshing at 0.024 / 0.0192 / 0.01536 / 0.012288.
> The entry stays OPEN (it retires with `GEO-23` step 2); only its *diagnosis*
> is corrected.

| | |
|---|---|
| **Test** | `tests/materials/test_phantom_material_model.py::test_phantom_material_assignment_and_time_harmonic_pipeline_wiring` |
| **Log** | `docs/testing/logs/20260827T093043Z_OPS-26-step2b-materials-complex.log` — complex build, `FEM_EM_REQUIRE_COMPLEX=1`, `-n 2`, `timeout -k 30 180`. **Status 124, elapsed 181 s.** The pytest summary printed (`1 failed, 14 passed, 30 warnings in 20.79s`) and then teardown never returned — the same eat-the-window mechanism as leg (a)'s findings 2 and 11. |
| **Symptom** | Interleaved rank streams show the *same* test resolving differently on the two ranks: `PASSED [ 66%]` on one, `FAILED [100%]` on the other, with `Exception: Invalid boundary mesh (overlapping facets) on surface 1 surface 1`, then `MPI_Abort` on the kill. |
| **Why it was run** | Leg (a) left this name as the one remaining `tests/materials` runtime skip — complex-only, skipped in the real build — and §9 item 1 owed a ~30 s complex command to convert it to green. **The conversion failed**: it converts to a rank-divergent abort instead, so the name stays **`deferred — rank-divergent gmsh abort, no Status-0/1 footer`** in the leg (a) table rather than becoming green. Leg (a)'s totals are unchanged at 184 / 189 (182 green, 2 red, 5 deferred); only this deferral's *reason* is upgraded from "runtime skip" to the above. |
| **Not counted as a red** | Same ruling as leg (a) finding 11, applied for consistency: the census's fail-closed control admits reds **only** from Status-0/1 footered runs, and this run has neither. Filed as a mechanism finding. |
| **What it adds to `GEO-23`** | `GEO-23` was commissioned (03:00 review) to own the "overlapping facets" family across four generators. This is a **fifth** call site and — with `test_boundary_condition_selection.py` — the **second** where the trigger is demonstrably partition-dependent rather than a property of the geometry. Two independent rank-dependent sites materially strengthens leg (a)'s reading that the resolution-floor explanation the three earlier entries share is incomplete, and `GEO-23` step 1's 2 × 3 Status-by-rank-width table should include this module. |
| **Verified at** | `b39799e`, complex build, `-n 2`. |
| **Fix** | Not fixed, not diagnosed further — `OPS-26` files, `GEO-23` owns. |

### ✅ RETIRED 2026-08-28 (`GEO-23` step 2b, 13:30 implementer slot) — ~~🔴 OPEN 2026-08-27 — `test_boundary_condition_selection.py` **deadlocks the whole command** at `-n 2`~~ — **`tests/solver/test_boundary_condition_selection.py:26` moved from `resolution=0.04` (does not mesh) to step 1's coarsest meshing rung `0.032`; the module is `3 passed, 1 skipped` at `-n 1` and `-n 2`, `1213` cells to the digit**

> **GEOMETRY HALF CLOSED 2026-08-28 (`GEO-23` step 2b, 13:30 slot) — the
> sizing lever.** `_make_problem`'s `cylindrical_domain` call moved
> `0.04 → 0.032`, the coarsest rung step 1's monotone `-n 1` ladder measured
> as meshing (1 213 cells; the finer rungs are 0.0256 / 0.02048 / 0.016384).
> Nothing in `src/`, no band and no record: the module pins no cell count, so
> the assertions that had to survive the re-mesh are the boundary-condition
> physics ones, and they all pass. Real build: `3 passed, 1 skipped in 0.94s`
> at `-n 1` (`20260828T183106Z_GEO-23-step2b-bcsel-n1.log`, Status 0, 2 s) and
> `3 passed, 1 skipped in 0.80s` at `-n 2`
> (`20260828T183116Z_GEO-23-step2b-bcsel-n2.log`, Status 0, 2 s), against the
> census red's `1 failed, 2 passed, 1 skipped`; the one skip is the
> `complex_only` name, unchanged. Printed global cell count **1213 at both
> widths**, reproducing the step-1 ladder exactly (0.00% against ±1%). Both
> halves of this entry are now closed.

> **DEADLOCK HALF CLOSED 2026-08-28 (`GEO-23` step 2a, 12:00 slot) — the
> headline "deadlocks the whole command at `-n 2`" no longer holds.**
> `cylindrical_domain`'s rank-0 gmsh build is now wrapped, so rank 1 raises
> `RuntimeError: cylindrical_domain geometry generation failed on rank 0
> (resolution=0.04); this is rank 1` instead of blocking in `_model_to_mesh`.
> **Status 1 in 2 s** where step 1 recorded **Status 124 at 120 s**, summary
> unchanged at `1 failed, 2 passed, 1 skipped`
> (`20260828T170311Z_GEO-23-step2a-bcsel-n2.log`; `-n 1` control unchanged,
> `20260828T170303Z_…-n1.log`). **The entry stays OPEN for the geometry red
> itself** — `GEO-23` step 2b's sizing move is what retires it.
>
> **CORRECTED 2026-08-28 by measurement (`GEO-23` step 1, 09:00 slot) — this
> entry's own requested `-n 1` command has now been spent, and it resolves the
> pre-stated reading against rank-dependence.** At `-n 1` the test is **Status
> 1 in 3 s** with the same `overlapping facets on surface 1 surface 1`
> (`20260828T140041Z_GEO-23-step1a-bcsel-n1.log`,
> `1 failed, 2 passed, 1 skipped in 1.85s`). The failure is therefore a
> deterministic property of the geometry, and `GEO-23` step 1's ladder confirms
> it: `cylindrical_domain` fails **only** at this fixture's own
> `resolution=0.04` and meshes at 0.032 (1 213 cells) / 0.0256 / 0.02048 /
> 0.016384.
>
> **The "one rank raises while the other returns" observation is a
> log-interleave artifact.** In the `-n 2` log
> (`20260828T140055Z_GEO-23-step1a-bcsel-n2.log`, lines 48–54) the apparent
> `PASSED [ 25%]` on the failing name is the *other* rank's verdict for its own
> **first** test, appended mid-line to this rank's name line — the percentages
> settle it (`[ 25%]` cannot be the third of four tests), and the failing
> name's only verdict anywhere in the log is `FAILED [ 75%]`. This is exactly
> the interleave trap `GEO-23`'s §7 entry warns about. What *is* rank-dependent
> is only the **teardown**: one rank raises, the survivor blocks in the
> collective, Status 124 at 121 s. `birdcage_port_domain` is the control —
> it re-raises the rank-0 throw as a `RuntimeError` on every rank and footers
> at Status 1 in 5 s, so wrapping the raise is a step-2 lever that would retire
> the deadlock without touching any mesh. Entry stays OPEN (retires with
> `GEO-23` step 2); only its diagnosis is corrected.
>
> **OWNER ASSIGNED 2026-08-27, 03:00 review: `GEO-23`** step 1 (a) — the
> `-n 1` command named at the foot of this entry is its first move.
>
> **Not a census red.** `OPS-26`'s fail-closed control admits a red only from
> a run with a Status-0-or-1 footer of its own. Both runs below ended
> **Status 124**, so the four tests in this module are counted
> `deferred — module-scoped command deadlocked; no footer`, and the failures
> here are recorded as a **mechanism finding**, not as a counted red. The next
> chunk that owns this must re-establish it in a footered run before treating
> any name below as failing.
>
> **Where this fired.** `tests/solver/test_boundary_condition_selection.py`,
> `mpiexec -n 2`, both builds, `OPS-26` step 2 leg (d) (2026-08-27 00:00
> implementer slot), each as a command containing **only this module**:
>
> | log | build | timeout | Status / elapsed |
> |---|---|---|---|
> | `20260827T050123Z_OPS-26-step2a-legd-m01-bcsel.log` | real | `-k 30 240` | **124 / 241 s** |
> | `20260827T051201Z_OPS-26-step2a-legd-m01-bcsel-complex.log` | complex, `FEM_EM_REQUIRE_COMPLEX=1` | `-k 30 180` | **124 / 180 s** |
>
> **The finding — the same test PASSES on one rank and FAILS on the other, in
> the same run.** The complex log is the clean read of it (the real log's two
> streams interleave mid-line and its per-test attribution cannot be trusted):
>
> ```
> ...::test_time_harmonic_solver_boundary_natural_selects_empty_dirichlet_set PASSED [ 46%]
> ...::test_time_harmonic_solver_boundary_natural_selects_empty_dirichlet_set FAILED [ 93%]
> ```
>
> (`20260827T051201Z_..._bcsel-complex.log:69,76`.) The failing rank raises
>
> ```
> Exception: Invalid boundary mesh (overlapping facets) on surface 1 surface 1
> ```
>
> **That is the mechanism of the hang.** One rank raises inside gmsh and
> leaves the collective; the other completes and blocks in the next
> collective; nothing progresses until `timeout -k 30` sends KILL, and the
> trailer is a PETSc `Caught signal number 15` followed by
> `Abort(59) ... MPI_Abort(MPI_COMM_WORLD, 59)`. This is the `mag:1`-class
> divergence the leg-(c) slot inferred for `tests/solver` as a root
> (`PROJECT_PLAN.md` §7 `OPS-26`, finding 8) — leg (d) localizes it to **this
> one module**: the other **twelve** `tests/solver` modules each returned a
> Status-0 footer when run as their own command.
>
> **Two consequences worth keeping.**
> 1. **"Overlapping facets" is not deterministic.** Every prior entry for that
>    string (`GEO-21` open birdcage; the coil+phantom generator; and
>    `birdcage_port_domain`, the entry below) reads as a property of a
>    geometry. Here the *same* geometry, in the *same* run, meshes on one rank
>    and fails on the other — so at least on this call path the trigger is
>    rank-partition-dependent, which a resolution-floor reading does not
>    explain. Stated as an observation from two runs, not a diagnosis.
> 2. **The second test's failure is the leg-(c) candidate signature.**
>    `test_time_harmonic_solver_boundary_pec_is_applied_to_solve_path` fails
>    with `IndexError: index 0 is out of bounds for axis 0 with size 0` —
>    the identical string the leg-(c) slot recorded on 21 of 23 discarded
>    names. It appears here on a module run in isolation on a swept cache,
>    which makes "one shared cause cascading" more plausible than it was; it
>    is still not established, because this run has no footer either.
>
> **Cache state is exonerated.** The slot opened with
> `find /root/.cache/fenics -name '*.c' -size 0 -print -delete`, which printed
> **nothing** (`20260827T050052Z_OPS-26-step2a-legd-collect.log:34`), and the
> real-build run above was the *first* command after it. The poisoned-stub
> entry lower in this file does not apply.
>
> **Next step for the owning chunk (a `solver`/`mesh` chunk, not the census):**
> run this module at `-n 1`. If it returns a Status-1 footer, the failure is
> real and the deadlock is purely the rank asymmetry; if it goes green, the
> failure itself is partition-dependent. One smoke-tier command settles it.
> `OPS-26` deliberately did not spend it — `-n 1` is not the census's recorded
> width and an observation at it would not count.

### 🔴 OPEN 2026-08-27 (`OPS-26` step 2 leg (a), second slot) — `test_birdcage_volumes_partition_the_box` aborts in gmsh with **the same "Invalid boundary mesh (overlapping facets)"** — this is the **third** geometry to carry that string, and the first on `birdcage_port_domain`'s own production path

> **MEASURED 2026-08-28 (`GEO-23` step 1, 09:00 slot) — geometry-deterministic,
> and this site is the family's positive control.** Red at **both** widths with
> the same string: `-n 1` **Status 1, 4 s** (`1 failed, 2 passed in 2.73s`,
> `20260828T140313Z_GEO-23-step1b-birdcagepart-n1.log`) and `-n 2` **Status 1,
> 5 s** (`20260828T140326Z_…-n2-ports.log`). Note the `-n 2` status: unlike the
> three sibling sites, this one **does not deadlock** — `birdcage_port_domain`
> re-raises the rank-0 gmsh throw as `RuntimeError: birdcage_port_domain
> geometry generation failed on rank 0` on *every* rank, so the command footers
> in 5 s where the unwrapped siblings burn 120 s each. That makes this entry
> the evidence that the family's deadlock is a **raise-path** property, not a
> geometry one, and wrapping the throw is a `GEO-23` step-2 lever that touches
> no mesh, band or record. The two adjacent tests in the module stayed green at
> both widths. Not laddered here — `GEO-21` step 2 already laddered this
> generator and `GEO-23` must not re-record it. Entry stays OPEN.
>
> **OWNER ASSIGNED 2026-08-27, 03:00 review: `GEO-23`** step 1 (b)/(c) —
> taken together with the two sibling entries, as this entry asks.
>
> **Where this fired.**
> `tests/mesh/test_birdcage_port_tags.py::test_birdcage_volumes_partition_the_box`,
> **real** build, `mpiexec -n 2`. Found by the `OPS-26` step 2 execution
> census (2026-08-26 21:00 implementer slot), first in the batch run
> (`20260827T022114Z_OPS-26-step2a-real4-mesh.log`, FAILED at 28% on both
> ranks) and then isolated for its traceback
> (`20260827T022935Z_OPS-26-step2a-mesh-red-tb.log`, **Status 1, 4 s**,
> `1 failed in 2.54s`).
>
> **Symptom, verbatim.**
>
> ```
> Exception: Invalid boundary mesh (overlapping facets) on surface 59 surface 79
> ```
>
> raised from `/usr/local/lib/gmsh.py:2189` inside
> `MeshGenerator.birdcage_port_domain`
> (`src/fem_em_solver/io/mesh.py:3245` → re-raised at `:3275`, wrapped at
> `:3276` as `RuntimeError: birdcage_port_domain geometry generation failed
> on rank 0`). The fragment line printed immediately before the abort is
>
> ```
> [birdcage-mesh] fragment volumes=26 conductor=1.030097e-04(20p) air=1.006440e-02(1p)
> phantom=2.261947e-04(1p) port_P1=8.000000e-07(1p) port_P2=8.000000e-07(1p)
> port_P3=8.000000e-07(1p) port_P4=8.000000e-07(1p)
> ```
>
> so the OCC fragment succeeds and the failure is in 2-D meshing, exactly as
> in the two entries below.
>
> **Why this matters — the string now spans three generators.** `GEO-21`
> filed it on the **open birdcage** conductor sizing, the 19:30 slot filed it
> on the **coil+phantom** generator, and this is `birdcage_port_domain` with
> ports and a phantom. Three different call paths, one symptom. The
> single-generator readings ("a coarse-resolution floor", "a fixture-specific
> sizing") no longer cover the observations; a shared 0.11 gmsh cause is now
> the more economical hypothesis. **Stated as a hypothesis from three shared
> error strings, not as a measurement** — nothing here bisects a resolution
> or attributes a cause.
>
> **Not a kill artifact.** The batch run that found it followed
> `20260827T022014Z_OPS-26-step2a-real3-cheap.log`, which exited **Status 0**,
> so the "do not trust a failure that follows a killed run" rule below does
> not apply; the isolated re-run then reproduced it in 2.54 s with an
> assertion-free gmsh exception, not a `dolfinx/jit.py` `RuntimeError`.
>
> **Adjacent, and green:** the other two tests in the same module pass
> (`test_birdcage_port_layout_diagnostics_match_the_closed_forms`,
> `test_birdcage_port_layout_rejects_too_small_or_overlapping_port_regions`),
> as do `tests/mesh/test_coil_phantom_conforming.py` (2/2) and
> `tests/materials/test_phantom_material_model.py` (3 green, 1 skipped) —
> two of the four coil+phantom consumers the 19:30 slot named as candidates
> to red the same way did **not** red. That narrows the blast radius but does
> not diagnose it.
>
> **Filed, not fixed, not re-recorded**, per the census item's own rule.
> Disposition belongs to a `mesh`-owning chunk, which should take all three
> entries together rather than one at a time.

### ✅ RETIRED 2026-08-28 (`GEO-23` step 2b, 13:30 implementer slot) — ~~🔴 OPEN 2026-08-27 — `test_phantom_field_metrics_and_exports_are_finite` aborts in gmsh with "Invalid boundary mesh (overlapping facets)" on the **coil+phantom** geometry~~ — **`tests/post/test_phantom_field_metrics.py:35` moved from `resolution=0.03` (does not mesh) to step 1's coarsest meshing rung `0.024`; the module is `2 passed` at `-n 1` and `-n 2` complex, `5464` cells to the digit**

> **GEOMETRY HALF CLOSED 2026-08-28 (`GEO-23` step 2b, 13:30 slot) — the
> sizing lever.** Same generator and same rung as the
> `test_phantom_material_model.py` entry above (step 1 found the two modules
> call `coil_phantom_domain` with byte-identical kwargs, so the unit of repair
> is the generator call): `0.03 → 0.024`, 5 464 cells. Nothing in `src/`, no
> band, no record; the module pins no cell count, so the assertions that had
> to survive the re-mesh are its phantom |E|/|B| metric and export ones, and
> they all pass. Complex build, `FEM_EM_REQUIRE_COMPLEX=1`:
> `2 passed in 1.71s` at `-n 1`
> (`20260828T183223Z_GEO-23-step2b-phantommetrics-n1.log`, Status 0, 3 s) and
> `2 passed in 1.67s` at `-n 2`
> (`20260828T183231Z_GEO-23-step2b-phantommetrics-n2.log`, Status 0, 3 s),
> against the census red's `1 failed, 1 passed`. Printed global cell count
> **5464 at both widths**, reproducing the step-1 ladder exactly (0.00%
> against ±1%). Both halves of this entry are now closed.

> **DEADLOCK HALF CLOSED 2026-08-28 (`GEO-23` step 2a, 12:00 slot).** The
> predicted removal below is now measured: with `coil_phantom_domain`'s rank-0
> build wrapped, rank 1 raises
> `RuntimeError: coil_phantom_domain geometry generation failed on rank 0
> (resolution=0.03); this is rank 1` and the `-n 2` command footers at
> **Status 1 in 3 s** where step 1 recorded **Status 124 at 120 s**, summary
> unchanged at `1 failed, 1 passed`
> (`20260828T170331Z_GEO-23-step2a-phantommetrics-n2.log`; `-n 1` control
> unchanged, `20260828T170323Z_…-n1.log`). **The entry stays OPEN for the
> geometry red itself** — `GEO-23` step 2b's sizing move is what retires it.
>
> **MEASURED 2026-08-28 (`GEO-23` step 1, 09:00 slot) — geometry-deterministic,
> with a measured floor one step away.** `-n 1` **Status 1, 3 s**
> (`1 failed, 1 passed in 1.17s`,
> `20260828T140352Z_GEO-23-step1b-phantommetrics-n1.log`); `-n 2` **Status 124,
> 120 s** with a complete summary then `MPI_Abort`
> (`20260828T140401Z_…-n2.log`) — so the abort is a property of the geometry
> and only the *hang* is rank-dependent (see the `birdcage_port_domain` entry
> above: wrapping the raise removes it). The `GEO-23` ladder, one process per
> rung at `-n 1`, shows `coil_phantom_domain` failing **only** at this
> fixture's own `resolution=0.03` and meshing at **0.024 (5 464 cells) /
> 0.0192 (9 330) / 0.01536 (16 177) / 0.012288 (28 485)** — monotone, one
> 0.8-step from green. **This site and
> `tests/materials/test_phantom_material_model.py` are the SAME call**:
> byte-identical `coil_phantom_domain` kwargs, so one sizing change would
> retire both reds. Entry stays OPEN (retires with step 2).
>
> **OWNER ASSIGNED 2026-08-27, 03:00 review: `GEO-23`** step 1 (b)/(c).
>
> **Where this fired.**
> `tests/post/test_phantom_field_metrics.py::test_phantom_field_metrics_and_exports_are_finite`,
> complex build, `FEM_EM_REQUIRE_COMPLEX=1`, `mpiexec -n 2`. Found by the
> `OPS-26` step 2 execution census (2026-08-26 19:30 implementer slot) — i.e.
> by the instrument built to find exactly this class, not by an example.
>
> **Literal symptom** (`20260827T004755Z_OPS-26-step2a-red-tb.log`, isolated,
> `--tb=short`):
>
> ```
> raise Exception(logger.getLastError())
> E   Exception: Invalid boundary mesh (overlapping facets) on surface 1 surface 1
> ```
>
> with the fragment census printed immediately before the abort:
> `[coil-phantom-mesh] fragment volumes=4 masses[m^3]: 1:1.381745e-04,
> 2:1.381745e-04, 3:2.261947e-04, 4:9.865456e-03 | air=4 coil_1=1 coil_2=2
> phantom=3`. **`1 failed, 1 passed in 1.24s`** — the failure is immediate and
> cheap, not a cost or JIT problem. The sibling test in the module,
> `test_evaluate_on_cells_fallback_skips_invalid_cell_point_pairs`, is green.
>
> **Second-order damage — this red burns the whole command.** After the
> failure the ranks diverge and teardown never completes: the isolated run
> printed its full pytest summary at 1.24 s and then sat until `timeout -k 30
> 200` killed it (**Status 124, elapsed 201 s**, PETSc error trailer after the
> summary line). In the census batch the same divergence hung the *next*
> module — `tests/post/test_phantom_phasor_semantics.py` never produced a
> result and the 900 s window was consumed
> (`20260827T003201Z_OPS-26-step2a-complex.log`, Status 124, 901 s). Anyone
> batching `tests/post` must expect to lose the tail of the command, not just
> this test. Budget it isolated.
>
> **Cause.** Not diagnosed. The symptom string is **identical** to the
> `GEO-21` entry immediately below, which measured the coarse end of
> `birdcage_port_domain`'s conductor sizing to have stopped meshing at the
> 0.11 merge. This occurrence is on a **different generator** (the
> coil+phantom fragment path, `air`/`coil_1`/`coil_2`/`phantom`), which is
> evidence that the 0.11 gmsh regression is **not birdcage-specific** — but
> that is a hypothesis stated from one shared error string, not a measurement.
> Whoever takes it should first check whether the fixture's resolution is at
> the coarse end of a continuum, as `GEO-21` step 1 found for the birdcage.
>
> **Not.** Not a tolerance or physics failure — no assertion is reached. Not
> the retired `DummyMagnetostaticSolver` red under §1 (that was an
> `AttributeError` and its code path was deleted by `TH-1`). Not diagnosed as
> real-mode-affected: the census only reached this module in the complex build,
> so the real-mode disposition of this test is **unmeasured**.
>
> **Filed, not fixed** — `OPS-26` step 2 is a census and files reds by
> construction (§9 item 1: "a red found here is filed, never fixed or
> re-recorded in-slot").
>
> **Retire-when:** the test is green through the harness on `main` in both
> builds, with the fixture's meshing resolution recorded.
>
> **Verified at** `18bb604` (tree clean at slot start; no source edited this
> slot).

### ✅ RETIRED 2026-08-28 (`GEO-23` step 1 (d), 09:00 slot) — ~~DEAD MODULE, filed 2026-08-27 (`OPS-26` step 2 leg (a)) — `tests/mesh/test_cylindrical_domain.py` collects **zero tests**~~

> **RETIRED by conversion, not deletion.** The module is now one asserting
> test, `test_cylindrical_domain_tag_volumes_partition_the_mesh`: the identity
> the old script only `print`ed, in quantitative form — the inner and outer tag
> volumes sum to the mesh volume at the shared helper's **1e-9** band (and the
> helper *reduces*, where the old `(ct.values == 1).sum()` counts were
> rank-local and never were) — plus an outer > inner ordering assertion that
> catches a tag swap the sum alone cannot see. `1 passed in 1.38s` at `-n 2`,
> and `tests/mesh --collect-only` now reports **58** where this module
> contributed **0** before
> (`20260828T141217Z_GEO-23-step1d-cylindrical-module.log`, Status 0, 5 s). The
> collection-time mesh build is gone with it — the build now happens inside the
> test. Its `resolution=0.02` was deliberately left unmoved: `GEO-23` step 1's
> ladder puts this generator's floor at 0.04-fails / 0.032-meshes, so 0.02 is
> comfortably inside the meshing range and is not that chunk's to change.
>
> ~~**OWNER ASSIGNED 2026-08-27, 03:00 review: `GEO-23`** step 1 (d) — convert
> to one asserting test or delete; either retires this entry.~~
>
> The file is a module-level *script*, not a test module: it calls
> `MeshGenerator.cylindrical_domain(...)` and `print`s at import time and
> defines no `test_*` function. `--collect-only` on the seven leg-(a)
> directories lists every other module in `tests/mesh` and **omits this one
> entirely** (`20260827T003050Z_OPS-26.log`, 189 collected, Status 0, 5 s) —
> so it contributes 0 to the census denominator while looking, by filename,
> like coverage.
>
> Worse than dead: pytest **imports** it during every collection of
> `tests/mesh`, so its mesh build runs — as collection-time work no
> disposition covers — and any exception it raises would surface as a
> collection error rather than a test failure.
>
> This is the `OPS-26` class in its purest form: a module no scheduled command
> can report on. **Filed, not fixed** — turning it into a real test (or
> deleting it) is a `mesh`-owning chunk's call, not the census's.
>
> **Retire-when:** the file either defines an asserting `test_*` function
> observed green through the harness, or is removed.
>
> **Verified at** `18bb604`.

### 🔴 OPEN 2026-08-25, re-headed 2026-08-26 (`GEO-21` step 2) — `birdcage_port_domain` **cannot mesh a coarse conductor sizing on the 0.11 image**: `conductor_resolution=None` and everything coarser than ~4.8 mm abort in gmsh with "Invalid boundary mesh (overlapping facets)"

> **RULED 2026-08-30, weekly planning review — the floor stays a documented
> limitation, deliberately uncommissioned; it becomes a stated trap, not a
> chunk.** `GEO-23` has since classified the whole "overlapping facets"
> family as geometry-deterministic and closed with "land no fix" by
> commission; every gate that reads this generator is green on a graded
> control (`h_c = 4.8e-3`, ruling (b) of 08-26), and the production
> fixtures — F-small at 116 085 cells and the 16-leg rungs — all mesh with
> `conductor_resolution = 0.4 × ring_minor_radius = 1.6 mm`, three times
> finer than the floor. A root-cause hunt inside gmsh's boolean fragment
> buys nothing the mission needs. **Where it bites next, stated now:** the
> F-human cost probe (`GEO-25`, §7) scales `ring_radius` 0.07 → 0.15 m and
> may be tempted to coarsen the conductor to hold the cell count — it may
> not go coarser than 4.8 mm on the conductors without first re-measuring
> this floor at that scale, and a probe rung that aborts with this string
> is to be recorded against this entry, not diagnosed in-slot. Re-opens as
> a chunk only if that probe finds no affordable rung *above* the floor.

> **✅ The gate-red portion of this entry RETIRED 2026-08-26** (`GEO-21` step 2,
> 04:30 implementer slot), exactly as the retire-when below specifies.
> `test_graded_conductor_sizing_recovers_the_cad_mass` and `mesh:3` are **green
> on `main`**: the negative control moved `None` → `BASELINE_CONTROL_RESOLUTION`
> = 4.8e-3 (the 03:00 review's ruling (b)), version-tagged with the six-rung
> probe table in-comment, and the demoted claim — **fine vs coarse grading**,
> no longer "grading required" — stated in the module docstring and the `mesh:3`
> guide. Gate `20260826T093202Z_GEO-21-step2-gate.log`, `1 passed in 41.11s`,
> Status 0, 43 s, `-n 2`: control **0.846150** at 33 185 cells, 3.2e-3
> **0.916742** at 47 975, graded **0.966977** at 98 666 — every step-1 probe
> figure reproduced exactly, now through the gate's own assertions. Consumer
> check `20260826T093403Z_GEO-21-step2-mesh3.log`, Status 0, 29 s, separation
> 0.120826. `CAD_MASS_GATE`, the `- 0.05` separation guard and `CONDUCTOR_RUNGS`
> are all unmoved; nothing was loosened.
>
> **What stays open is the generator limitation in the heading**, which
> `GEO-21` step 1 measured to be *wider* than "the ungraded path": 9.6e-3 fails
> the same way at a fourth distinct surface pair, so `conductor_resolution=None`
> is the coarsest point of a continuum whose coarse end stopped meshing at the
> 0.11 merge, not a special broken path. Hardening `birdcage_port_domain`
> against it would have to cover coarse *graded* sizings too. Still
> **deliberately not commissioned** — no production path uses a coarse
> conductor sizing now that the control sits at 4.8e-3, and that decision is
> recorded here rather than silently made. **Retire-when:** a chunk that
> hardens the generator, or a gmsh/image change that makes the coarse end mesh
> again — re-measure the ladder before retiring, do not infer it.
>
> **Verified at** the `GEO-21` step 2 landing commit.
>
> ---
>
> *Everything below is the history of the retired gate red, kept because the
> measurements in it are what the disposition rests on.*
>
> **Where this fired.**
> `tests/mesh/test_birdcage_conductor_sizing.py::test_graded_conductor_sizing_recovers_the_cad_mass`,
> and through it `examples/meshing/03_birdcage_graded_conductors.py` (`mesh:3`),
> which imports `CONDUCTOR_RUNGS` / `CAD_MASS_GATE` / `_check_geo9_identities`
> from that module per `ANS-1`. Both build `baseline = _mesh(conductor_resolution=None)`
> **first**, so both abort before the graded rung — the rung that actually
> carries the gate — ever runs.
>
> **Literal symptom** (`20260825T213821Z_EX-30-mesh-birdcage-gate-probe.log`,
> `-n 2`, real, **`1 failed in 2.51s`**, `Status: 1`; the example's own abort is
> `20260825T213142Z_EX-30-mesh-run-1to5.log`, `Status: 1`):
>
> ```
>     baseline = _mesh(conductor_resolution=None)
> E   RuntimeError: birdcage_port_domain geometry generation failed on rank 0
> E   Exception: Invalid boundary mesh (overlapping facets) on surface 59 surface 79
> ```
>
> **Localised, not inferred** — `tests/mesh/probe_birdcage_conductor_resolution.py`
> (new with this entry; measurement only, asserts nothing, imported by nothing),
> `20260825T213926Z_EX-30-mesh-birdcage-resolution-probe.log`, `Status: 0`,
> 39 s, `-n 1`:
>
> ```
> Leg A -- the fixture's global resolution (0.015), conductor sizing swept:
>   h_c = None    (baseline) FAIL  Invalid boundary mesh (overlapping facets) on surface 59 surface 79 (1.8 s)
>   h_c = 3.2000e-03         OK       47975 cells (10.4 s)
>   h_c = 1.6000e-03         OK       98666 cells (20.7 s)
>
> Leg B -- the baseline's conductor sizing (h_c = None), global resolution stepped finer:
>   h = 0.0150              FAIL  ... on surface 59 surface 79 (1.7 s)
>   h = 0.0130              FAIL  ... on surface 48 surface 48 (1.5 s)
>   h = 0.0110              FAIL  ... on surface 65 surface 65 (1.3 s)
> ```
>
> **It is the conductor sizing, not the resolution.** Both `GEO-15` rungs mesh
> at the *same* global 0.015 that the baseline fails at, and refining the global
> size does not walk out of the failure — three finer steps fail on three
> *different* surface pairs. This is the **opposite** reading from the
> `straight_wire_domain` entry below, where `resolution` alone explained
> everything and every geometry failed at h = 0.01; the two findings are the
> same *family* (0.11 gmsh meeting a parameter set no green gate exercises) but
> not the same axis, and a single ruling will not cover both.
>
> **Consequence.** The `GEO-15` graded-conductor CAD-mass gate — the one
> `EX-21` and `mesh:3` rest on — has been **non-executing on `main` since the
> 0.11 merge**, unobserved, in the same class as `OPS-24`'s cavity gate and leg
> (root)'s `MAG-13` convergence gate. What it *would* have measured is now
> partly known: the graded rung meshes at **98 666 cells**, against the
> 2026-08-16 record of 98 474 (0.7.2) — but that number comes from this probe,
> which does not run the gate's assertions, so it is a bracket, not a re-record.
>
> **Not diagnosed further, and deliberately not fixed.** Whether the baseline
> control moves to a sizing that meshes, `birdcage_port_domain` is hardened
> against the ungraded path, or the inverted control is re-chosen is a
> `GEO-15`/`EX-21` ruling, not `EX-30`'s — this chunk files reds, it does not
> repair them, and no band was touched.
>
> **Verified at** `9b679d8`.
>
> **RULED 2026-08-25, 18:00 review — the disposition is commissioned as
> `GEO-21` (§7), following the `MAG-13`→`MAG-19` precedent: `GEO-15`'s ✅ is
> the 0.7.2 close and stands; a new chunk disposes of the 0.11 red.**
> Measure-first, decision rule pre-stated in the `GEO-21` entry: probe
> `h_c = 3.2e-3`'s CAD-mass recovery (10 s, already priced) — if it sits
> clearly below the gate the way `h_c = None`'s 0.7403 did, the baseline
> control moves there version-tagged (old `None` in-comment citing the
> resolution probe log); if it *clears* the gate, the inverted premise has no
> meshable carrier and the finding is reported, never manufactured around.
> The generator finding — `birdcage_port_domain(conductor_resolution=None)`
> cannot mesh on 0.11 at any global resolution tried — **stays in this entry
> even after the gate goes green**: hardening the ungraded path is
> deliberately not commissioned while no production path uses it, and that
> decision is recorded here rather than silently made. **Retire-when
> (narrowed):** the gate-red portion retires with the commit that lands
> `GEO-21` green; the ungraded-path generator limitation then re-heads this
> entry and stays open.
>
> **MEASURED 2026-08-26 (`GEO-21` step 1, 00:00 implementer slot) — the
> ruling's own branch is excluded, and the generator finding gets wider.**
> The red reproduced unchanged first (`20260826T050100Z_GEO-21-step1-red-repro.log`,
> `1 failed in 4.80s`, same surfaces 59/79). Then the number the ruling turned
> on, measured through the gate module's own `_mesh`
> (`20260826T050134Z_GEO-21-step1-cad-mass-probe.log`, `-n 2`, Status 0, 35 s):
>
> ```
>   h_c = 3.2000e-03  cells=  47975  meshed/CAD=0.916742
>   h_c = 1.6000e-03  cells=  98666  meshed/CAD=0.966977
> ```
>
> **0.916742 is neither branch** — not ≤ 0.90, not clearing 0.95 — and it sits
> inside the gate module's pre-registered guard
> `baseline_ratio < CAD_MASS_GATE - 0.05` = 0.90, failing it by 0.016742. So
> moving the baseline control to `h_c = 3.2e-3` would relocate this red to the
> separation guard rather than clear it, and no licence permits loosening a
> guard that says the premise needs re-examining. The graded rung is *not* in
> question: 0.966977 ≥ 0.95, 98 666 cells matching this entry's bracket exactly.
>
> **The generator limitation is broader than "the ungraded path".** A
> coarse-ward graded ladder (`20260826T050319Z_GEO-21-step1-control-ladder.log`,
> `-n 1`, Status 0, 30 s; measurement only, no control adopted) reads
> 3.2e-3 → 0.916742 (width control exact vs `-n 2`), 4.8e-3 → 0.846150,
> 6.4e-3 → 0.767219, and **9.6e-3 → FAIL, "Invalid boundary mesh (overlapping
> facets) on surface 54 surface 86"** — the same failure family as
> `h_c = None`, at a fourth distinct surface pair. `conductor_resolution=None`
> is therefore not a special path that broke: it is the **coarsest point of a
> continuum whose coarse end stopped meshing at the 0.11 merge**. That widens
> the finding this entry keeps open after the gate red retires — hardening
> `birdcage_port_domain` would have to cover coarse graded sizings too, not
> just the `None` default. Still deliberately not commissioned; still no
> production path uses it.
>
> **Gate red stays OPEN**: disposition needs a review ruling between (b) a
> coarse-graded control (4.8e-3 or 6.4e-3, both separating) and (c) retiring
> the baseline comparison — options and their cost in claim-strength are in the
> §7 `GEO-21` entry. Retire-when is unchanged.
>
> **RULED 2026-08-26 03:00 review: option (b), control = `h_c = 4.8e-3`**
> (0.846150 — clears the 0.90 separation guard by 0.0538 with the guard
> unmoved; `6.4e-3` rejected for cliff adjacency, the cliff having moved
> once already at the 0.11 merge; (c) rejected because a graded-side-only
> assertion cannot distinguish broken grading from common-mode drift). The
> demoted claim — **fine-vs-coarse grading**, no longer "grading required" —
> lands in-comment and in the guide with the landing, `GEO-21` step 2,
> §9 item 1. On that landing this gate red retires; the
> generator-continuum finding above re-heads and stays open, still
> deliberately uncommissioned.
>
> **Verified at** `ab55ff1`. **Landed 2026-08-26 — see the retirement note at
> the head of this entry.**

### ✅ RETIRED 2026-08-25 (`EX-30` item 3 half A, 22:30 implementer slot) — `test_kwarg_off_reproduces_the_recorded_mesh` was **red on `main`**: the `GEO-16` kwarg-off cell record read 79 534, the 0.11 image meshes **79 070** (`EX-30` leg (mesh), 2026-08-25)

> **Where this fires.**
> `tests/mesh/test_two_torus_port_sheet.py::test_kwarg_off_reproduces_the_recorded_mesh`
> (`NCELLS_UNGATED_RECORD = 79_534`, line 78), and through the `ANS-1` import
> also `examples/meshing/04_two_torus_port_sheet.py` (`mesh:4`), which fails on
> the same constant.
>
> **Literal symptom** (`20260825T213632Z_EX-30-mesh-gate-probe.log`, `-n 2`,
> real, **`1 failed, 5 passed, 4 warnings in 42.06s`**, `Status: 1`):
>
> ```
> E   AssertionError: the default path meshed 79070 cells against the recorded 79534:
>     the opt-in sheet perturbed the mesh every gated PORT-1 / PORT-10 number was measured on
> E   assert 79070 == 79534
> ```
>
> **The assertion's own premise is *not* what broke.** The message blames the
> opt-in port sheet, and the sheet is innocent: two independent no-sheet builds
> in this leg agree exactly at **79 070** — `mesh:1`
> (`01_two_torus_ports.py`, which does not assert a cell count and ran **green**,
> `[mesh] 79070 cells built in 14.2 s`) and `mesh:4`'s own kwarg-off control
> (`[control] emit_port_sheet=False: 79070 cells in 13.6 s`) — while the
> *sheeted* build is a properly distinct 79 940. So the default path is
> self-consistent on 0.11 and it is the 79 534 record, measured on 0.7.2 in
> `20260817T003524Z_GEO-16.log`, that is stale. The five other assertions in the
> module pass, including the CAD port-interface area and the 0.970–0.980
> meshed-band cross-check the constant's own comment names as its guard.
>
> **Deliberately not re-recorded**, though `EX-30` leg (mesh) holds an in-class
> (1\*) example-record licence for moved cell counts: this constant lives in a
> **gate module**, not an example, and the licence does not reach it. Aligning
> the example's guide to 79 070 while the gate still asserts 79 534 would create
> exactly the example/gate divergence `ANS-1` exists to prevent, so the
> `mesh:1` guide's "79 534 cells / 12.9 s" was left standing too. The review
> owns the call: re-record the gate constant to 79 070 (and the `mesh:1` guide
> with it), or treat the 464-cell move as a regression to diagnose.
>
> **Verified at** `9b679d8`.
>
> **RULED 2026-08-25, 18:00 review — re-record, licensed and scoped to this
> constant.** `NCELLS_UNGATED_RECORD` 79 534 → **79 070**, version-tagged to
> the 0.11 image (gmsh 4.15.2), old digit in-comment citing both
> `20260817T003524Z_GEO-16.log` and this entry's probe log; the `mesh:1` and
> `mesh:4` guide copies move in the **same commit** so example and gate
> cannot diverge. Basis: two independent no-sheet builds agree exactly at
> 79 070 with the sheeted build properly distinct at 79 940 (the sheet is
> exonerated), the module's five other assertions are green including the
> 0.970–0.980 meshed-band guard the constant's comment names, and the −0.58%
> move is in family with the measured 0.11-gmsh mesh motion already ruled
> re-recordable under (1\*) (two-torus solve fixture −0.40%, `TH-10` −0.02%).
> Not a regression to diagnose: the record is a change-detector, and what it
> detected is the documented image change. No band moves. Landing is §9
> item 3 (18:00 queue). **Retire-when:** the commit that lands the re-record
> with the gate module and `mesh:4` green.
>
> **✅ RETIRED 2026-08-25, 22:30 implementer slot — landed exactly as ruled.**
> `NCELLS_UNGATED_RECORD` 79 534 → **79 070**, version-tagged to the 0.11 image
> with the old digit and both provenance logs in-comment; the `mesh:1`
> docstring + guide and the four `mesh:4` guide copies moved in the same commit.
> Green on all three anchors: the gate pair
> (`20260826T033222Z_GEO-16-rerecord-gate-pair.log`, `-n 2`, real, **5 passed
> in 55.84 s**, Status 0, elapsed 57 s) printing `[GEO-16 control] cells=79070`
> and the 0.970–0.980 meshed-band cross-check at **0.974490841**; `mesh:4`
> (`20260826T033350Z_GEO-16-rerecord-mesh4.log`, Status 0, 31 s) —
> `[mesh] 79940` sheeted, `[control] emit_port_sheet=False: 79070 cells in
> 13.9 s (record 79070)`, sheet tags absent; `mesh:1`
> (`20260826T033431Z_GEO-16-rerecord-mesh1.log`, Status 0, 16 s) —
> `[mesh] 79070 cells built in 14.1 s`. No band moved. Also re-recorded under
> the same (1\*) class: the `mesh:4` guide's sheet-facet count 84 → **82** and
> its wall-time/cell-count row, both un-asserted guide figures.

### ✅ RETIRED 2026-08-25 (`EX-30` item 3 half B, 22:30 implementer slot) — `mesh:5`'s **inverted control lost its separation**: the clamps-only mesh *cleared* the 0.755 floor it is asserted to fail, by 6e-6 (`EX-30` leg (mesh), 2026-08-25)

> **Where this fires.** `examples/meshing/05_region_resolution_policy.py`
> (`mesh:5`), line 255 — the `EX-18`/`EX-20` inverted-assertion pattern:
> `assert recovery["clamps_only"][tag] < POLICY_MIN_CAD_RECOVERY`.
>
> **Literal symptom** (`20260825T213601Z_EX-30-mesh-run-5.log`, `-n 2`, real,
> `Status: 1`, 7 s):
>
> ```
>   clamps_only  cells=   19618  mesh=  2.40 s
>   policy       cells=   20745  mesh=  2.65 s
> AssertionError: clamps-only mesh recovers 0.755006 of tag 1 (coil_1)'s CAD volume,
>   clearing the 0.755 floor the policy is supposed to be needed for
>   (on record: 0.754685 / 0.752565). The control no longer separates —
>   the premise needs re-examining, not the floor.
> ```
>
> **This is example-side only; the gate module is green.**
> `tests/mesh/test_mesh_tag_integrity.py` passed all four of its tests in the
> same probe run (`20260825T213632Z_EX-30-mesh-gate-probe.log`) because it
> asserts the floor **one-sidedly on the policy mesh** (`policy_volumes[tag] /
> cad_volume >= POLICY_MIN_CAD_RECOVERY`, line 248) and never asserts that the
> clamps-only control fails it. The stricter inverted claim exists only in the
> example, which is why only the example is red.
>
> **The margin is the whole finding: 0.755006 against a 0.755 floor** — the
> control clears it by 6.0e-6 relative, having sat at 0.754685 on 0.7.2, a
> 3.2e-4 move. The example's own comment anticipates this shape ("a baseline
> sitting at 0.949 would clear 'fails the gate' while saying nothing"), and
> `CONTROL_SEPARATION = 0.05` exists for the `mesh:3` fixture but has no
> counterpart here.
>
> **Deliberately not re-recorded and not widened.** The (1\*) licence covers
> moved cell counts and CAD masses, not a control's separation premise, and
> moving `POLICY_MIN_CAD_RECOVERY` or the record to recover the assertion would
> be loosening a gate — the assertion message itself says the premise is what
> needs re-examining. A `GEO-17` ruling: re-choose the clamps-only control so it
> fails by a stated margin, or retire the inverted claim.
>
> **Verified at** `9b679d8`.
>
> **RULED 2026-08-25, 18:00 review — re-choose the control, measure-first;
> demote to report only if no separating control exists.** The example may
> not carry an inverted assertion whose separation is 6e-6 on a record that
> moved 3.2e-4 under an image change. The landing (§9 item 3, second half)
> probes the clamps-only configuration at 2–3 coarser sizings (~2.4 s per
> mesh) and adopts the coarsest sensible control that **fails the 0.755
> floor with ≥ 0.05 relative separation** — the `CONTROL_SEPARATION`
> precedent the example itself cites for the `mesh:3` fixture — old sizing
> in-comment, version-tagged. If no clamps-only sizing both fails the floor
> and remains a legitimate control, the inverted assertion is demoted to a
> printed report and the guide states the finding honestly: on 0.11 the
> clamps-only mesh already recovers the floor, so the policy's necessity is
> not demonstrable on this fixture at this floor. `POLICY_MIN_CAD_RECOVERY`,
> the one-sided gate-module assertion, and the records never move.
> **Retire-when:** the commit that lands `mesh:5` green under whichever
> branch the measurement selects.
>
> **✅ RETIRED 2026-08-25, 22:30 implementer slot — the re-choose branch, not
> the demotion.** A separating sizing exists, so the inverted assertion stays
> an assertion. The probe
> (`20260826T033622Z_GEO-17-mesh5-sizing-probe.log`, `-n 1`, 8 s) measured coil
> meshed/CAD at four uniform sizings — h = 0.015: 0.755006 / 0.750454 (margin
> **−0.000006**, the red); **h = 0.018: 0.649812 / 0.648431 (margin +0.105188 /
> +0.106569, SEPARATES)**; h = 0.020: 0.595547 / 0.579713; h = 0.025:
> 0.471986 / 0.510423. `CONTROL_RESOLUTION = 0.018` adopted as the first
> candidate that separates, with the whole table in-comment; the probe stopped
> there rather than hunting a margin.
>
> The control is a **third build**, not a re-pointed one: `UNIFORM_VOLUMES_RECORD`
> is a `GEO-17` gate constant measured at h = 0.015, so moving the clamps-only
> sizing would have broken negative control (a) — the `OPS-17` table
> reproduction at 1e-9 — which is not licensed to move. The clamps-only mesh
> therefore stays as that reproduction and as the baseline the refine/coarsen
> sign identities read against; the new `coarse_control` build carries only the
> inverted assertion, now gated at `CONTROL_SEPARATION = 0.05` rather than on
> the bare `<` that went red. `SIZING_SEPARATION` is asserted against **both**
> baselines (+0.078411 / +0.085109 against clamps-only, +0.183605 / +0.187132
> against the coarse control) so keeping the tighter of the two is not quietly
> dropped. `POLICY_MIN_CAD_RECOVERY`, the one-sided gate-module assertion and
> every record are untouched; `tests/mesh/test_mesh_tag_integrity.py` was not
> edited at all.
>
> Green: `20260826T033758Z_GEO-17-mesh5-control-rechoice.log` and the
> post-doc-edit confirm `20260826T033959Z_GEO-17-mesh5-confirm.log` (both
> `-n 2`, real, Status 0, 8 / 9 s), printing the control's failing margin.

### 🔴 OPEN 2026-08-25 (`OPS-26` step 1, 15:00 implementer slot) — two `scripts/probes/` scripts were **never migrated to dolfinx 0.11**: they construct `fem.petsc.LinearProblem` without 0.11's required `petsc_options_prefix`

> **Where this fires.** `scripts/probes/mag13_step2b_recovery.py:180` and
> `scripts/probes/post3_step3_debug.py:55`. Neither is a test, neither is an
> example, and **nothing scheduled runs either of them** — which is exactly the
> shape `OPS-26` exists to enumerate. They are one-off diagnostic probes kept
> for their write-ups.
>
> **Literal symptom** (static, from the sweep — these scripts were not
> executed; `20260825T200918Z_OPS-26.log`, `Status: 1`, 4 s):
>
> ```
> scripts/probes/mag13_step2b_recovery.py:180: [missing-required]
>   dolfinx.fem.petsc.LinearProblem — required parameter
>   'petsc_options_prefix' not supplied
> scripts/probes/post3_step3_debug.py:55: [missing-required] (same)
> ```
>
> 0.11 made `petsc_options_prefix` a keyword-only parameter with no default, so
> each line raises `TypeError` on the first call. `src/` and `tests/` carry
> **zero** such sites (log `20260825T200851Z_OPS-26.log`, 434 resolved call
> sites over 29 APIs, `violations=0`) — the migration is complete everywhere a
> gate can reach; these two are outside that reach.
>
> **Not diagnosed further, and deliberately not fixed** — `OPS-26` files
> survivors rather than repairing them in-slot, and a probe script's value is
> its recorded output, not its ability to re-run. Fixing them is a two-line
> change whenever someone wants one of them again.
>
> **Verified at** `e26c128` (tree state of the 15:00 slot).
> **Retire when** both sites take `petsc_options_prefix`, or the scripts are
> deleted; `tests/environment/test_dolfinx_api_migration.py::test_filed_survivors_outside_the_gated_roots_are_unchanged`
> pins the survivor set at exactly these two and goes red in **either**
> direction, so this entry cannot rot silently.

### ✅ CLOSED 2026-08-25 (`MAG-19` step 2, 21:00 implementer slot) — `tests/validation/test_convergence.py::TestConvergence::test_h_refinement_straight_wire` was **red on `main`**: the fitted rate is **1.90** against the `MAG-13` band `[0.7, 1.5]`, because the finest rung's error collapsed 9.26% → **4.4605%** on the 0.11 image

> **Where this fires.** `tests/validation/test_convergence.py::TestConvergence::test_h_refinement_straight_wire`,
> real build, on **`main`** at `878fa3e`. Not a worksite, not an example path:
> the gate itself. It was found from the example side — `examples/magnetostatics/06_h_convergence_rate.py`
> imports `RATE_MIN`, `RATE_MAX`, `RESOLUTIONS`, `solve_h_refinement` and
> `fit_convergence_rate` from this very module (the `ANS-1` rule, already
> applied), so `-e 6` runs the gate's computation — and the gate was then
> probed directly to confirm it, rather than inferred.
>
> **Literal symptom** (`20260825T141636Z_EX-30-root-mag6-gate-probe.log`,
> `1 failed in 143.11s`, `Status: 1`, `-n 2`, both rank footers identical):
>
> ```
> Convergence rate: 1.90
> Expected rate for linear elements: ~1.0
> AssertionError: Convergence rate 1.90 outside [0.7, 1.5] (expected ~1.0 for
>   N1curl degree 1); errors [0.21841667267163878, 0.15384842035994292,
>   0.04460534278989355] at h [0.004, 0.0025, 0.0018]
> ```
>
> **What moved, rung by rung.** The band is unchanged; the error ladder is not.
> Against the `MAG-13` record (`20260730T125522Z_MAG-13.log`, 0.7.2):
>
> | h (m) | cells (0.11) | rel L2 (0.11) | rel L2 on record | move |
> | --- | --- | --- | --- | --- |
> | 0.0040 | 38 740 | 21.8417% | 22.19% | −0.35 pp |
> | 0.0025 | 147 235 | 15.3848% | 12.75% | +2.63 pp |
> | 0.0018 | 383 146 | 4.4605% | 9.26% | **−4.80 pp** |
>
> The middle rung is exactly the 147 235 cells / 15.3848% the retired
> `MAG-18` entry below already names, so two of the three rungs are accounted
> for by the documented 0.11 gmsh mesh motion. The **finest rung is not**: a
> better-than-halved error is what levers the fitted slope from 1.10 to 1.90.
> The sequence is still monotone, so the example's own negative control
> (monotone decay) passes — it is the *rate* that breaks, on the upper edge
> the gate's docstring says has teeth precisely because "a rate well above 1.5
> means one resolution in the sequence is anomalous".
>
> **Update 2026-08-25 (`MAG-19` step 1, 13:30 implementer slot) — the
> discriminating measurement is done, and it selects *neither* pre-stated
> reading.** Both norms were run on the *same* four solves (added rung
> h = 0.0030) via `tests/validation/probe_straight_wire_dual_norm.py`;
> log `20260825T183555Z_MAG-19-step1-dualnorm-fits.log`, 160 s at `-n 2`,
> Status 0. The red reproduces digit for digit (three original rungs within
> 1.321e-06 relative of the row above; sampled three-rung fit **1.9038**) and
> so does the `E_Ω` negative control through the imported machinery (fit
> **1.6854**; the h = 0.0025 `E_Ω` record within **2.094e-08**) — so the
> `ANS-1` import is sound and what moved is the measurement.
>
> | h (m) | cells | sampled 10-pt | `E_Ω` |
> | --- | --- | --- | --- |
> | 0.0040 | 38 740 | 21.841675% | 25.286827% |
> | 0.0030 | 88 018 | 18.473177% | 14.288381% |
> | 0.0025 | 147 235 | 15.384843% | 10.617170% |
> | 0.0018 | 383 146 | 4.460528% | 6.645807% |
>
> Sampled pairwise rates 0.5822 / 0.7456 / 1.9894 / 1.0034 / 2.7819 / 3.7690;
> `E_Ω` 1.9843 / 1.8464 / 1.6735 / 1.6288 / 1.4985 / 1.4261. Reading (a) fails
> because the sampled ladder carries a **second** out-of-band pair that avoids
> h = 0.0018 (0.004→0.003 at 0.5822, on the rung (a) would promote); reading
> (b) fails because the sampled norm is *not* unstable everywhere — dropping
> h = 0.0018 alone returns the fit to **0.7309**, inside the band. The new
> constraint: `E_Ω` is the stable instrument but sits **above 1.5 on every
> subset** (fits 1.6661–1.8588), so transferring the two-sided [0.7, 1.5] onto
> it would be red on arrival — its live gate is one-sided ≥ 0.7, which it
> meets on 6/6 pairs. **Nothing was re-recorded and no band was moved**;
> `MAG-19` stays 🟡 with three options for the review in its §7 entry. This
> entry stays open: the gate is still red on `main` for the reason above.
>
> **Cause: not diagnosed.** Two readings fit and this slot did not
> discriminate them: (a) the h = 0.0018 rung's mesh moved enough on 0.11 that
> its sampled 10-point error is anomalous, in which case the sequence needs
> re-choosing the way `MAG-13` excluded h = 0.0035; (b) the sampled 10-point
> norm is the wrong instrument on 0.11 and the `MAG-18` `E_Ω` norm — which
> **is** green on 0.11 at rate 1.6854 (see the retired entry below) — is the
> one to gate. Deciding between them is a `MAG-13`/`MAG-18` question, not an
> `EX-30` one; **nothing was re-recorded and no band was moved.**
>
> **Owning chunk:** `MAG-13` (the band and the resolution sequence), with
> `OPS-18` as the image that moved the ladder under it. **Consequence for
> `EX-30`:** `examples/magnetostatics/06_h_convergence_rate.py` exits 1 for
> this reason and nothing else — its artifact
> (`h_convergence_rate_combined.xdmf`) is written *before* the assertion and
> did refresh, so it is not in the stale census.
>
> **RULED 2026-08-25, 18:00 review — option (i): the rate duty transfers to
> the `E_Ω` ladder under `E_Ω`'s own one-sided ≥ 0.7 criterion, which
> `MAG-18` already gates live and green on 0.11.**
> `test_h_refinement_straight_wire` keeps its monotone-decay assertion and
> prints the error table as a report; the two-sided [0.7, 1.5] on the sampled
> 10-point statistic is **retired with its basis stated**, not widened: that
> statistic swings 34% of its own value under its sampler (measured on both
> images, `OPS-18` step 3 attempt 5) and the band already failed on 0.7.2 at
> `n_points = 8` — the gate was passing on a sampler choice, and `MAG-18`
> built `E_Ω` precisely to replace it. On option (iii)'s question: the upper
> edge is **not** re-imposed on `E_Ω` — no two-sided band has ever been
> validated on 0.11 for either statistic, under-convergence (the ≥ 0.7 side)
> is the failure mode a rate gate exists to catch, and a superconvergence
> guard, if ever wanted, must be commissioned with its own measured basis
> (a weekly-review question, deliberately not opened here). Option (ii)
> rejected: a 0.03 margin on a statistic with a 34% sampler swing is not a
> gate. Landing is `MAG-19` step 2 (§9 item 2, 18:00 queue); `mag:6` imports
> `RATE_MIN`/`RATE_MAX`/the fit from this module, so the landing reconciles
> the example to the transferred duty in the same commit (old text
> in-comment) and runs `-e 6` as the consumer check. **Retire-when:** the
> commit that lands `MAG-19` step 2 green including `mag:6`.
>
> **RETIRED 2026-08-25, 21:00 implementer slot — the retire-when is met, in
> one commit, on four logged runs at `-n 2`, real build, on `main`.**
> (1) *The red reproduced first*, before anything was edited:
> `20260826T020124Z_MAG-19-step2-red.log`, Status 1, 145.27 s — 21.8417% /
> 15.3848% / 4.4605% at 38 740 / 147 235 / 383 146 cells, rate **1.90**, the
> same digits `20260825T141636Z` and `MAG-19` step 1 recorded. (2) *The
> disposition's own green*: `20260826T020508Z_MAG-19-step2-green.log`,
> `1 passed` / Status 0 / 142.36 s on **bit-identical** errors (the fit still
> prints, at 1.9038, as a report beside the retired band and the duty owner).
> (3) *Negative control — `MAG-18`'s gate module green **untouched***, zero
> edits to `test_straight_wire.py`: `20260826T020739Z_MAG-19-step2-mag18.log`,
> `7 passed` / Status 0 / 362.68 s, `E_Ω` 25.2868 → 10.6172 → 6.6458% at fitted
> rate **1.6854 ≥ 0.7**, the h = 0.0025 record 1.0617170177e-01 and the
> natural-BC ratio 0.3285 — all three reproducing the 2026-08-23 re-gate, so
> the duty was transferred to a gate that is executing and green, not to a
> claim. (4) *Consumer check*: `20260826T021403Z_MAG-19-step2-e6.log`,
> `-e 6 -n 2`, Status 0 / 148 s, "All assertions hold", printing the same three
> errors, the report-only rate and the duty owner.
>
> **No band moved anywhere.** `RATE_MIN` / `RATE_MAX` keep their values and
> their names; what changed is that nothing on this ladder asserts on them.
> **One residual, filed rather than fixed:** `test_straight_wire.py::TestStraightWire::test_straight_wire_convergence`
> still gates a *two-rung, 8-point sampled* fit on the same two-sided band, and
> it is green (fitted **0.7900** in run (3)). It was outside `MAG-19`'s scope
> and inside the module this landing had to leave untouched, so it was left
> alone and is named in-comment at the constants. Whether the ruling's "no
> upper edge on a sampled statistic" extends there is a review question, not an
> implementer's.
>
> **RULED 2026-08-26 03:00 review: commissioned as `MAG-20`** (§7,
> measure-first, not queued this interval). Ruling (i) is *not* inherited by
> fiat onto a currently-green test — the residual gets its own `n_points`
> sweep on its own two rungs with a pre-stated decision rule: retire the
> two-sided band under the ruling-(i) pattern if the fit crosses either edge
> under the sampler; keep it, recorded as *validated*, if it is stable at
> every count. Either outcome is a measurement.
>
> **RESIDUAL CLOSED 2026-08-28 (`MAG-20` step 1, 00:00 implementer slot) — the
> band is KEPT, validated by measurement.** The sweep on this test's own two
> rungs and its own 0.4 R window fits **0.7900 / 0.7246 / 0.9934** at
> `n_points` 8 / 10 / 20 — **no crossing of either edge of [0.7, 1.5]** — so the
> pre-stated rule's *keep* branch fires and nothing moved: `RATE_MIN`/`RATE_MAX`
> unchanged, no assertion added or removed, the disposition is an in-comment
> measurement record at the assertion. Probe
> `tests/validation/probe_straight_wire_convergence_npoints.py`, log
> `20260828T050130Z_MAG-20-step1-npoints-probe.log` (49 s, `-n 2`); anchor
> `test_straight_wire.py` `7 passed / 369.95 s / Status 0`
> (`20260828T050256Z_MAG-20-step1-anchor-module.log`) with `E_Ω` 1.6854 and the
> h = 0.0025 record 1.0617170193e-01 untouched. **Two findings left open for the
> review, not defects on `main`:** the sampler swing on this window is 6–7% of
> the error (vs 34% on the 0.8 R window), but it still moves the rate by 37% of
> its own value, and the n = 10 row clears `RATE_MIN` by only **0.0246**. The
> test is green at all three counts; the thin margin is recorded in the
> `MAG-20` §7 entry as findings 45–46.

### ✅ RETIRED 2026-08-30 (weekly planning review — size-field licence **denied**, the `GEO-23` step-2a wrap ruled sufficient) — ~~`MeshGenerator.straight_wire_domain` has a **coarse-resolution floor on the dolfinx 0.11 image**: `resolution = 0.01` aborts inside gmsh with duplicated facets for every geometry tried, `0.008` and finer mesh, and the threshold between them is unbisected — no guard exists, so a too-coarse request still fails illegibly~~ (originally 🔴 OPEN 2026-08-25, re-headed 2026-08-26 by `EX-30` leg (root))

> **RULED 2026-08-30, weekly planning review — the size field is NOT
> licensed into `src/`, and this entry retires on the wrap.** The 08-28
> ruling left one question here: whether the gmsh Distance→Threshold size
> field that `GEO-22` step 2/2c measured (18/18 OK, 0 fallbacks, 19 823 vs
> 21 830 cells at `h = 0.008`, asserted at `-n 1` and `-n 2`) should land in
> `straight_wire_domain`. It should not, for three reasons that are each
> sufficient: (1) it moves four **Phase-1** records for no physics gain —
> `mag:1`'s 21 830 and the three `MAG-13`/`MAG-18` ladder records — and §10's
> element-order note already rules that Phase 1 is complete and not worth
> re-gating; (2) the defect the entry names — a too-coarse request failing
> *illegibly* — is fixed: `GEO-23` step 2a's raise path lands the failure
> on every rank in seconds, and `GEO-22` step 1 proved there is no floor to
> guard (the `[0.008, 0.010]` sweep is non-monotone and bit-reproducible),
> so a guard would be a fiction; (3) the example that fired this moved to
> `resolution = 0.008` on 2026-08-25 and has been green since. The
> size-field probe and its asserted gate (`tests/mesh/test_straight_wire_size_field_probe.py`)
> stay as the on-record measurement of *why* the coarse rung fails (a
> fallback triangulation under the unfielded mesher), available to any
> future generator that needs it — and the first place to look if a
> **new** geometry meets the same string is `GEO-23`'s classification, not
> this entry. Nothing re-recorded, no band moved, `src/` untouched.

> **Where this fires.** `./run_examples.sh -e 1`, real build, on **`main`** at
> `878fa3e`. The crash is in the mesh generator, before any solve, so the
> example produces nothing: its **seven** repo-root artifacts
> (`straight_wire_{A,B}.bp`, `straight_wire_{A,B,B_analytical}.xdmf`,
> `straight_wire_combined.{h5,xdmf}`) are the entire remainder of leg
> (root)'s stale census.
>
> **Literal symptom** (`20260825T140159Z_EX-30-root-run-mag1to2.log`,
> `Status: 124` — the 124 is a post-`MPI_Abort` teardown hang against the
> runner's `-t 300`, not a compute overrun; the failure itself is immediate):
>
> ```
> Info    : Reconstructing mesh...
> Info    :  - Creating surface mesh
> Info    : Found two duplicated facets.
> Info    :   1st: [145, 20, 216] #1
> Info    :   2nd: [145, 20, 216] #1
> Error   : Invalid boundary mesh (overlapping facets) on surface 1 surface 1
> ...
>   File "/workspace/src/fem_em_solver/io/mesh.py", line 304, in straight_wire_domain
>     gmsh.model.mesh.generate(3)
> Exception: Invalid boundary mesh (overlapping facets) on surface 1 surface 1
> ```
>
> **`MeshGenerator.straight_wire_domain` is not broken in general** — the
> *same* generator meshed three times in the same slot, in the run immediately
> after, at 38 740 / 147 235 / 383 146 cells
> (`20260825T141141Z_EX-30-root-run-mag6.log`). The parameter sets differ, and
> the example's is exercised by **no** gate:
>
> | | wire_length | domain_radius | resolution |
> | --- | --- | --- | --- |
> | `01_straight_wire.py:118-121` | 0.3 | 0.04 | **0.01** |
> | `test_straight_wire.py:62-65` | 0.20 | 0.03 | 0.0025 |
> | `test_convergence.py:41-61` | 0.2 | 0.03 | 0.004 / 0.0025 / 0.0018 |
>
> **Cause, localised — it is `resolution` alone, and the geometry is
> irrelevant.** `tests/validation/probe_straight_wire_mesh_resolution.py`
> walks the two axes separately
> (`20260825T142512Z_EX-30-root-mag1-mesh-probe.log`, `Status: 0`, **29 s**,
> `-n 1`; the probe documents why `-n 1` — a gmsh throw on rank 0 deadlocks
> the collective `_model_to_mesh` on the others):
>
> ```
> Leg A -- the example's geometry (L = 0.3, R = 0.04), resolution swept:
>   h = 0.0100  FAIL  Invalid boundary mesh (overlapping facets) on surface 1 surface 1 (0.3 s)
>   h = 0.0080  OK       21830 cells (2.6 s)
>   h = 0.0060  OK       34250 cells (4.2 s)
>   h = 0.0050  OK       55306 cells (7.0 s)
>   h = 0.0040  OK       98778 cells (13.0 s)
>
> Leg B -- the example's resolution (h = 0.01), geometry stepped to the gate's:
>   L = 0.30  R = 0.040 FAIL  ...
>   L = 0.30  R = 0.030 FAIL  ...
>   L = 0.20  R = 0.040 FAIL  ...
>   L = 0.20  R = 0.030 FAIL  ...
> ```
>
> So: **`h = 0.01` is the only failing rung, it fails for every geometry
> tried including the gate's own `L = 0.20 / R = 0.030`, and everything from
> `h = 0.008` down meshes.** This is therefore *not* "the example's box is
> unusual" — it is a coarse-resolution floor in `straight_wire_domain` on the
> 0.11 image, and the gate's geometry would hit it too if any gate ever ran
> that coarse. None does, which is why only the example sees it. The failure
> is instant (0.2–0.3 s) and perfectly reproducible across all five cases.
>
> **Still not diagnosed:** *why* 0.01 specifically. The obvious suspect is the
> wire cylinder — `resolution = 0.01` is 1.67× the wire *diameter*
> (2·0.003 m), so the wire surface cannot carry a well-formed facet loop —
> but `h = 0.008` is still 1.33× that diameter and meshes fine, so the
> threshold is not simply "coarser than the wire". Bisecting 0.008–0.010 was
> not run. `straight_wire_domain` is untouched since the 0.11 API migration
> (`d176bc1`, `OPS-18` step 2), so this is image behaviour, not a repo
> regression.
>
> **Owning chunk:** unassigned — a review call, and the localisation above
> makes it a cheap one. Two fixes are available: move the example off
> `resolution = 0.01` (0.008 costs 2.6 s of meshing and is the nearest
> working rung), or give `straight_wire_domain` a guard/clamp so a
> too-coarse request fails legibly instead of inside gmsh. `EX-30` leg (root)
> has no licence for either. **Nothing was re-recorded.**
>
> **RULED 2026-08-25, 10:30 review: the example moves to
> `resolution = 0.008`** (old 0.01 kept in-comment citing the probe log
> `20260825T142512Z_EX-30-root-mag1-mesh-probe.log`), executed inside
> `EX-30` leg (root)'s completion slot — owning chunk is now `EX-30`.
> **No guard is written in-slot**: the threshold is unbisected
> (0.008 works, 0.010 fails, the boundary between them is unmeasured), and
> a guard constant without a measured boundary would encode a guess. The
> coarse-resolution floor itself stays on record **in this entry** as
> documented 0.11-image behaviour after the example fix lands — the entry
> then re-heads as the floor finding (the example symptom retired), and
> retires fully only when a measured-threshold guard lands in
> `straight_wire_domain` or the upstream image moves the floor.
>
> **EXAMPLE SYMPTOM RETIRED 2026-08-26 (`EX-30` leg (root) completion, 12:00
> implementer slot); the floor finding above stays OPEN.** The ruling was
> executed exactly as written: `01_straight_wire.py:120` moved
> `resolution` `0.01` → **`0.008`**, with the old value and the probe's full
> reasoning in-comment at the constant. `-e 1 -n 2` is now **green from
> `main`** (`20260826T170155Z_EX-30-root2-run-mag1.log`, Status 0, **9 s**,
> real build) and meshes at **21 830 cells / 4 662 vertices** — the probe's
> `h = 0.0080 OK 21830 cells` reproduced exactly, which is the confirmation
> that the localisation was right and not a coincidence of that probe's
> geometry. Closed forms unmoved and reproduced: `B(3 mm)` analytic
> `6.666667e-05 T` = `μ₀I/2πr`, analytic decay ratio `B(3 mm)/B(38 mm)` =
> **12.67** = 38/3. The example's derived figures moved with the mesh
> (relL2 65.8739% → **51.9781%**, max rel 85.2498% → **76.7330%**, numerical
> decay 29.83 → **20.31**, energy 2.307201e-08 → **2.630243e-08 J**) and are
> re-recorded version-tagged in `01_straight_wire.md` under the leg's (1\*)
> guide-table licence, old digits in-comment. The seven `straight_wire_*`
> artifacts cleared: census `stale=7` → **`stale=0`**
> (`20260826T170118Z_…-precensus.log` → `20260826T171345Z_…-postcensus.log`,
> `dead=0 guide=0 exit=0`).
>
> **What is still open, and it is the whole reason this entry survives:** no
> guard was written, so `straight_wire_domain(resolution=0.01)` still aborts
> inside gmsh with `Invalid boundary mesh (overlapping facets)` rather than
> raising something a caller can read. The threshold in `[0.008, 0.010)`
> remains unbisected and *why* 0.01 specifically remains undiagnosed (the
> wire-diameter hypothesis is contradicted by 0.008 working at 1.33× the
> diameter). **Retire-when:** a measured-threshold guard lands in
> `straight_wire_domain`, or the upstream image moves the floor and that is
> measured. **Owning chunk:** unassigned — `EX-30` owned only the example
> fix, and it is done.
>
> **OWNER ASSIGNED 2026-08-26, 18:00 review: `GEO-22`** — bisect
> `[0.008, 0.010)` on both geometries with the existing `-n 1` probe, land a
> `ValueError` guard at the *measured* `h_ok`, gate it with the exception
> type, the probe cell count and `mag:1`'s unmoved 21 830; the straight-wire
> gate ladders are the negative control. Full rubric in the §7 entry;
> queued as a §9 spare. This entry retires when that guard lands.
>
> **RE-HEADED 2026-08-28 (`GEO-22` step 1, 07:30 implementer slot) — there is
> no floor, and no guard is possible: the failure is NON-MONOTONE in
> `resolution` on both geometries, deterministically so.** The bisection ran
> as commissioned and returned a measured negative. `probe_…_resolution.py`
> gained a leg C that sweeps the whole open interval `[0.008, 0.010]` on a
> uniform **2.5e-4** grid — nine rungs — on the example's geometry *and* the
> gate's, at `-n 1` (`20260828T123115Z_GEO-22-step1-bisect.log`, `Status 0`,
> **23 s**; repeat `20260828T123205Z_GEO-22-step1-bisect-repeat.log`,
> `Status 0`, **22 s**). A uniform sweep was run rather than a true bisection
> deliberately: it costs about what three bisection steps would and it is the
> only form of the measurement that can *see* non-monotonicity. It did.
>
> | `resolution` | example (L = 0.3, R = 0.04) | gate (L = 0.20, R = 0.030) |
> | --- | --- | --- |
> | 0.00800 | OK 21 830 | OK 8 262 |
> | 0.00825 | OK 18 745 | OK 8 004 |
> | 0.00850 | OK 17 644 | OK 7 755 |
> | 0.00875 | **FAIL** | **FAIL** |
> | 0.00900 | OK 14 709 | **FAIL** |
> | 0.00925 | **FAIL** | OK 6 894 |
> | 0.00950 | OK 17 683 | OK 6 768 |
> | 0.00975 | **FAIL** | OK 12 200 |
> | 0.01000 | **FAIL** | **FAIL** |
>
> Every failing cell is the same literal `Invalid boundary mesh (overlapping
> facets) on surface 1 surface 1`, in 0.2–0.3 s, as before.
>
> **Three findings, in order of consequence.**
>
> 1. **The failing set is interleaved, not a floor.** `h = 0.00875` fails on
>    both geometries while the *coarser* 0.00900 (example) and 0.00925 /
>    0.00950 / 0.00975 (gate) mesh. So "everything from 0.008 down works,
>    everything above fails" — the reading this entry has carried since
>    2026-08-25 — is **false**; it was an artefact of the old leg-A ladder
>    sampling only 0.010 and 0.008 and nothing between. There is no threshold
>    to encode, so `GEO-22` step 1's pre-registered stop condition fires and
>    **no guard was written.** A `resolution > RESOLUTION_FLOOR` guard at any
>    constant would either reject meshing rungs or admit failing ones.
> 2. **It is deterministic.** The two runs above are independent invocations
>    and reproduce **bit-identically** — same OK/FAIL at all 18 cells, same
>    cell count to the digit. So this is not run-to-run instability in gmsh's
>    randomised insertion; it is a reproducible function of `(geometry,
>    resolution)`. That matters for step 2: a retry-with-jitter fix would have
>    to *perturb* the request, not merely repeat it.
> 3. **The cell count is non-monotone in `h` too, and by a lot.** Example:
>    0.00900 → 14 709 but the *coarser* 0.00950 → 17 683 (+20%). Gate:
>    0.00950 → 6 768 but 0.00975 → **12 200**, a **1.80×** jump for a coarser
>    request. So the mesher's whole response to `resolution` is discontinuous
>    in this band, and the failures are the visible part of that.
>
> **Mechanism, localised but not diagnosed.** Every rung in the sweep — the
> meshing ones included — prints `[ 0%] NNN triangles are equivalent` on
> surface 1 (the wire cylinder) and then falls back
> `Frontal-Delaunay` → **`MeshAdapt`** for that surface alone. So
> Frontal-Delaunay is producing coincident triangles on the wire at every
> size in this band; whether gmsh's fallback then yields a boundary the 3D
> reconstruction accepts is what varies rung to rung. That is consistent with
> all three findings and with the wire-diameter suspicion being *near* the
> mark without being the mechanism (0.008 is 1.33× the 0.006 m diameter and
> also triggers the fallback — it just survives it). **Not chased in-slot:**
> `GEO-22` step 1's scope explicitly excludes diagnosing gmsh.
>
> **Not run, deliberately:** `mag:1` and the straight-wire gate ladders were
> the negative controls *for a guard*. No guard landed, no `src/` line
> changed, so there is nothing for them to control and spending 370 s on them
> would prove only that an unmodified generator is unmodified. The example's
> own 0.008 rung is reproduced inside this very sweep at **21 830 cells**,
> which is the `EX-30`/`mag:1` record to the digit — that is the control that
> was worth having, and it is free.
>
> **Retire-when — restated, because the old condition is now unreachable:** a
> *measured-threshold* guard cannot land. This entry retires when either (a)
> `straight_wire_domain` stops emitting the coincident-triangle surface mesh
> (an upstream image move, or a generator change that meshes the wire surface
> differently — e.g. an explicit size field on the cylinder rather than a
> global `resolution`), or (b) a `GEO-22` step 2 lands a guard of a *different
> shape* — a post-mesh validity check, or a documented allowlist of verified
> rungs — and a review rules that shape sufficient. **Owning chunk:**
> `GEO-22`, step 1 done as a measured negative, step 2 a review's call.
>
> **RULED 2026-08-28, 10:30 review — guard shape.** The allowlist is
> **rejected** (nine rungs on two geometries is a sample, not a truth). The
> post-mesh wrap is **adopted** and lands as part of `GEO-23` step 2a (§9
> item 1): `straight_wire_domain` gets the `birdcage_port_domain` raise path
> (catch on the building rank, `bcast`, raise on every rank) so a failing
> rung footers in seconds at `-n 2` instead of deadlocking, with a gate at
> `h = 0.00875` asserting the raise on every rank. The size field (branch
> (a) above) is the only candidate that could *fix* the fallback and would
> move `mag:1`'s 21 830 and the three ladder records — its *licence* is the
> 2026-08-30 weekly review's; its *measurement* is §9 item 5, a no-`src/`
> probe leg predicting 0 fallbacks / 18 of 18 OK. This entry retires with
> the step-2a wrap **only if** the review then rules the wrap sufficient;
> otherwise it stays open pointing at the size-field decision.
>
> **WRAP LANDED 2026-08-28 (`GEO-23` step 2a, 12:00 slot) — the adopted half is
> done; the entry stays OPEN.** `straight_wire_domain` now carries the shared
> `_raise_geometry_failure_on_every_rank` raise path, and the gate is
> `tests/mesh/test_geometry_failure_is_collective.py`: the `mag:1` example
> geometry at `h = 0.00875` raises on **every** rank (the caught flag is
> `allreduce`d, and rank 1's message is asserted to name both the generator and
> the resolution), `1 passed in 0.91s` at `-n 2` inside a `-k 30 60` window
> (`20260828T170254Z_GEO-23-step2a-gate-n2.log`, Status 0, 3 s; `-n 1`
> `20260828T170247Z_…-n1.log`). The wrap moved no mesh — `mag:1` re-reads
> **21 830 cells** and `B(3 mm) = 6.666667e-05 T`
> (`20260828T170414Z_GEO-23-step2a-control-mag1.log`). What is **not** done is
> the other clause of the restated done-when: the size-field probe table (§9
> item 5) is unrun, and no fallback line count changed, so the coincident-
> triangle emission this entry is about is untouched. Retirement still needs a
> review's ruling that the wrap is sufficient, or the size field.
>
> **SIZE-FIELD PROBE RUN 2026-08-29 (`GEO-22` step 2, 07:30 implementer slot) —
> the hypothesis is CONFIRMED: a wire-surface size field removes the fallback
> entirely and every rung meshes. The entry stays OPEN; nothing landed in
> `src/`.** `probe_straight_wire_mesh_resolution.py` gained a **leg D** that
> re-runs leg C's nine rungs on both geometries with a gmsh
> `Distance`/`Threshold` field anchored on the generator's own `wire_surface`
> physical group — `SizeMin = wire_radius = 0.003`, `SizeMax` = the rung's own
> `h`, `DistMin = 0.003`, `DistMax = 0.006` — installed by patching
> `gmsh.model.mesh.generate` for the duration of one call (so geometry,
> fragment, physical groups, the raise path and `_model_to_mesh` are all the
> shipped code) with `Mesh.MeshSizeFromPoints` /
> `…ExtendFromBoundary` / `…FromCurvature` off so the generator's
> `setSize(points, resolution)` cannot override the field.
> `20260829T123331Z_GEO-22-step2-sizefield.log`, `Status 0`, **33 s**, `-n 1`.
>
> | `resolution` | example, leg C | example, leg D | gate, leg C | gate, leg D |
> | --- | --- | --- | --- | --- |
> | 0.00800 | OK 21 830 | OK 19 823 | OK 8 262 | OK 10 196 |
> | 0.00825 | OK 18 745 | OK 18 807 | OK 8 004 | OK 9 596 |
> | 0.00850 | OK 17 644 | OK 17 563 | OK 7 755 | OK 9 248 |
> | 0.00875 | **FAIL** | OK 16 655 | **FAIL** | OK 8 892 |
> | 0.00900 | OK 14 709 | OK 15 909 | **FAIL** | OK 8 579 |
> | 0.00925 | **FAIL** | OK 15 464 | OK 6 894 | OK 8 144 |
> | 0.00950 | OK 17 683 | OK 14 980 | OK 6 768 | OK 7 918 |
> | 0.00975 | **FAIL** | OK 14 331 | OK 12 200 | OK 7 757 |
> | 0.01000 | **FAIL** | OK 13 837 | **FAIL** | OK 7 407 |
>
> **The two numbers the ruling asked for.** Leg D reads **18/18 OK** and
> **0/18 rungs with a `triangles are equivalent` line**; the whole log contains
> **zero** occurrences of that string and **zero** of `MeshAdapt`, against
> **18** occurrences (exactly one per rung) in both leg C runs. So
> Frontal-Delaunay now completes the wire surface unaided at every size in the
> band, and the seven step-1 failures are gone with it — including
> `h = 0.01000`, the rung that opened this entry on 2026-08-25.
>
> **Negative control, executed in its own process and reproduced
> bit-identically:** leg C re-run
> (`20260829T123413Z_GEO-22-step2-legC-control.log`, `Status 0`, **20 s**)
> returns step 1's table cell for cell — same OK/FAIL in all 18 cells, same
> cell counts to the digit (21 830 at the example's 0.008; the gate's 6 768 at
> 0.00950 and the 12 200 at the coarser 0.00975), same two `NON-MONOTONE`
> verdicts. Leg C and leg D are separate command-line modes and were run as
> two commands, so the control saw exactly the process history step 1 gave it
> (`GEO-23` finding F). The change is therefore the size field's and not the
> day's or the process's.
>
> **A third reading, free:** leg D's cell count is **monotone decreasing in
> `h`** on both geometries (example 19 823 → 13 837, gate 10 196 → 7 407),
> where leg C's jumps around (gate 6 768 at 0.00950 → 12 200 at the coarser
> 0.00975, 1.80×). So the discontinuous response to `resolution` recorded as
> step 1 finding 3 is *also* the wire surface, not the volume mesher.
>
> **Still not licensed.** The field is in the probe only; `src/` is untouched
> and no record moved. Landing it in `straight_wire_domain` would move
> `mag:1`'s **21 830** (leg D reads 19 823 at the same `h`) and the three
> straight-wire ladder records, so the re-record call is the 2026-08-30 weekly
> review's, per the 08-28 10:30 ruling. **Retire-when, unchanged in substance:**
> this entry retires when either a review rules the `GEO-23` step-2a wrap
> sufficient, or the size field lands in `straight_wire_domain` under that
> licence with the moved records re-recorded. **Owning chunk:** `GEO-22`, now
> **✅** — both clauses of its restated done-when are met (wrap + gate landed
> 08-28; this table recorded 08-29), and the size-field decision is the weekly
> review's, not a `GEO-22` step.
>
> **NOW GATED, ENTRY STILL OPEN (`GEO-22` step 2c, 2026-08-29 16:30 slot).**
> The two numbers above are no longer prose only:
> `tests/mesh/test_straight_wire_size_field_probe.py` builds the example
> geometry at `h = 0.008` twice in one process — under the probe's imported
> `_SizeFieldPatch` and without — and asserts **19 823 cells with 0
> fallbacks** patched against **21 830 cells with ≥ 1 fallback** unpatched,
> each count within ±1%. Both readings reproduce **exactly** at `-n 1`
> (`20260829T213132Z_GEO-22-step2c-n1.log`, 8 s) and `-n 2`
> (`…213148Z_…-n2.log`, 7 s). This changes nothing about the licence: the
> field is still probe-only, `src/` is still untouched, and `mag:1`'s 21 830
> is still the shipped record — the gate now *pins* both sides of the
> comparison, so a future landing of the field in `straight_wire_domain`
> must move this module's references deliberately rather than silently.

### ✅ RETIRED 2026-08-25 by `OPS-24` — `core/cavity.py` was **never migrated to dolfinx 0.11**: `assemble_matrix(..., diagonal=)` no longer exists, so the whole `TH-9` cavity + resonance-guard family was **non-executing on `main`** (`EX-30` leg (th), 2026-08-24)

**Retired.** The keyword was renamed `diagonal=` → `diag=` in 0.11 with unchanged
semantics (0.11 docstring: "Rows/columns that are constrained by a Dirichlet
boundary condition are zeroed, with the diagonal to set to `diag`"), verified by
introspecting the installed `dolfinx.fem.petsc.assemble_matrix` signature rather
than assumed. Both sites migrated; all four tests green at `-n 2` complex, and
every recorded figure reproduces the pre-0.11 record **to the printed digit**:
per-mode errors 0.0123 / 0.0153 / 0.0201 / **0.0436%** worst-mode against the
closed form on 720 cells / 5330 dofs, refinement 0.0436% → 0.0102% at fitted
rate 3.85, null cluster 8/8 with max |λ| = 5.560e-14, guard 137.554 (near-
resonant) vs 21.951 (clear) against the 50.0 threshold. `13 passed in 29.71s`
(with `tests/environment`), Status 0, 31 s harness —
`20260825T020157Z_OPS-24-green-quoted.log`; the red baseline was reproduced
in-slot first (`4 failed, 9 passed in 1.83s`,
`20260825T020052Z_OPS-24-red-baseline.log`). No band, tolerance or recorded
eigenfrequency was touched. Original entry below, for the audit trail.

**Test ids — four, all red on `main` with no local change:**

```
tests/validation/test_cavity_resonances.py::test_pec_cavity_resonances_match_closed_form
tests/validation/test_cavity_resonances.py::test_pec_cavity_resonances_improve_under_refinement
tests/validation/test_cavity_resonances.py::test_n1curl_gradient_modes_form_a_clean_zero_cluster
tests/validation/test_resonance_guard.py::test_energy_continuity_guard_fires_near_a_cavity_mode
```

and the two examples on the same code path, `th:2`
(`examples/time_harmonic/02_pec_cavity_resonances.py`) and `th:5`
(`examples/time_harmonic/05_resonance_guard_sweep.py`), which crash outright.

**Literal symptom**, identical at every site:

```
TypeError: assemble_matrix() got an unexpected keyword argument 'diagonal'
```

from `src/fem_em_solver/core/cavity.py:129`
(`A = assemble_matrix(stiffness, bcs=[bc], diagonal=bc_diagonal)`) and its
sibling `cavity.py:131` (`B = assemble_matrix(mass, bcs=[bc], diagonal=1.0)`),
reached through `_cavity_forms` from `cavity.py:229` (`solve_pec_cavity_modes`)
and `cavity.py:324`.

Gate probe, complex build, `FEM_EM_REQUIRE_COMPLEX=1`, `tests/environment`
first, `-n 2`: **`4 failed, 9 passed in 2.11s`**
(`docs/testing/logs/20260824T213908Z_EX-30-th-cavity-gate-probe.log`, Status 1,
4 s harness). Example crashes:
`20260824T213123Z_EX-30-th-run-1to4.log` (`th:2`) and
`20260824T213228Z_EX-30-th-run-5to8.log` (`th:5`).

**Verified at:** `main` @ `7529fa4` (2026-08-24), 0.11.0.post0 image.

**Cause — diagnosed, and it is ours.** `dolfinx.fem.petsc.assemble_matrix`
dropped the `diagonal=` keyword between 0.7.2 and 0.11. `OPS-18` step 2 migrated
the codebase to the 0.11 API but missed this module, and the miss was invisible
because **nothing scheduled runs these two test modules** — they are not in any
chunk's verification path, so the 0.11 merge (2026-08-23) landed on a green-
looking tree with a dead subsystem inside it. **All 9 `tests/environment` tests
pass in the same probe run**, so this is not an environment or complex-mode
regression.

**What this costs, stated plainly.** `TH-9`'s closed-form eigenfrequency
comparison and the energy-continuity resonance guard have produced **no number
since 2026-08-23**. Any reading of either as "gated" is unsupported until this
is fixed — per §9's standing rule, a status without a log reads "unknown".

**Retire when:** the two calls are migrated to the 0.11 signature and all four
tests above run green, with the closed-form eigenfrequency comparison quoted.
Scoped by `EX-30` leg (th) as an `OPS-18` follow-on for a review to queue; it
also unblocks 2 of the 6 `time_harmonic` artifacts that leg could not refresh.
**Commissioned as `OPS-24`** (2026-08-24 18:00 review, §9 item 2); §2.1 now
carries the non-executing caveat on the cavity figure until this retires.

### ✅ RETIRED 2026-08-25 by `OPS-25` — `th:7` calls `Function.interpolate(cells=)`, removed in 0.11 — the **only** such site in the repo, so the example has diverged from the gate it claims to import (`EX-30` leg (th), 2026-08-24)

**Retired by hoist, per the ruling — the divergence is gone, not just the
`TypeError`.** The five lines the example had re-derived (CG2 vector space →
`Function` → sphere-cell index array → restricted `interpolate`) now live once,
in the gate module, as `series_interior_function(series, msh, cell_tags)`
(`test_lossy_sphere_fullwave.py:367`); the gate's `_power_rung` and the example
both call it, so there is no second copy left to rot. The example's private
`cells=` line is deleted, not repaired; the surviving call site is the gate's
already-migrated `cells0=`.

**Evidence the hoist is behaviour-preserving.** The gate's own power figures
reproduce the pre-refactor green log
(`20260822T123746Z_OPS-18-step3-th10-rerun.log`) **bit-identically to all ten
printed digits** — `P_series(meshed)` = 1.048951142e-07 W at the coarse rung and
1.066439173e-07 W at the fine rung, errors 8.387% / 3.629%, quadrature-16
recheck 1.24e-16 — and that is the *only* quantity the moved code produces.
`13 passed in 25.28s`, Status 0, 27 s harness, `-n 2` complex with
`tests/environment` first, covering `test_lossy_sphere_fullwave.py` **and**
`test_lossy_sphere_degree2.py` (`20260825T033221Z_OPS-25-gate-green.log`).

**`th:7` green end-to-end**, `./scripts/run_examples.sh -e th:7 -n 2 -t 300`,
Status 0, 14 s (`20260825T033152Z_OPS-25-th7-green.log`), asserting both
element-order records against their own 1% band: degree 1 relL2 8.1541%
(drift 4.00e-06) / power 8.3869% (1.18e-05), degree 2 relL2 0.1405%
(5.50e-05) / power 0.0058% (1.48e-03). The red was reproduced in-slot first
(`20260825T033114Z_OPS-25-red-baseline.log`, Status 1, `TypeError` at line 198).
No record, band or assertion moved anywhere — this was a hoist. Original entry
below, for the audit trail.

**Test id:** none — no test asserts this. The failing artifact is the example
`examples/time_harmonic/07_element_order_lossy_sphere.py` (`th:7`), which cannot
run at all. `tests/validation/test_lossy_sphere_degree2.py`, the gate it builds
on, does **not** exercise this call and is not implicated by this entry.

**Literal symptom**
(`docs/testing/logs/20260824T213804Z_EX-30-th-run-7to8.log`, Status 1, 2 s,
`-n 2`, complex build):

```
File "/workspace/examples/time_harmonic/07_element_order_lossy_sphere.py", line 198, in _row_and_fields
  e_series_fn.interpolate(_series_interior_interpolant(series), cells=sphere_cells)
TypeError: Function.interpolate() got an unexpected keyword argument 'cells'
```

**Verified at:** `main` @ `7529fa4` (2026-08-24), 0.11.0.post0 image.

**Cause — diagnosed.** 0.11 renamed the cell-restriction argument of
`Function.interpolate`. A repo-wide grep for `interpolate(...cells=)` across
`src/`, `tests/` and `examples/` returns **exactly one hit**: that line. So this
is not a migration class, it is a single site — and the reason it is a *lone*
site is the interesting part. The example's own banner says its fixture is
"imported wholesale from tests/validation/test_lossy_sphere_degree2.py and the
TH-10 module it builds on", but this interpolation step is the example's own
code, not imported. The gate is green and the example is dead, which is exactly
the drift the `ANS-1` rule (records and machinery live in the gate, examples
import them) exists to prevent.

**Retire when:** the call is migrated *or*, preferably, the interpolation is
hoisted into the gate module and imported — a review should decide which, since
repairing it in place preserves the divergence. Unblocks 2 of the 6
`time_harmonic` artifacts `EX-30` leg (th) could not refresh.
**Ruled and commissioned as `OPS-25`** (2026-08-24 18:00 review, §9 item 3):
hoist and import — in-place repair is rejected because it preserves the
divergence this entry documents.

### ✅ RETIRED 2026-08-25 by `EX-30` leg (th) — `th:6`'s **128 MHz** interior relL2 does not reproduce the `TH-10` record on the 0.11 image (1.76864% vs 1.826%, 3.14% drift) while **64 MHz reproduces to 4.04e-05 on the same mesh** (`EX-30` leg (th), 2026-08-24)

**Retired by the licensed version-tagged re-record — the diagnosis below was
right and needed no new measurement.** The example's two restated 128 MHz
constants now carry the 0.11 digits from `TH-10`'s own gate re-run
(`20260822T123746Z_OPS-18-step3-th10-rerun.log`): `RECORD_INTERIOR_L2[128 MHz]`
0.01826 → **0.01769** and `RECORD_SEPARATION[128 MHz]` 57.31 → **59.16**, with
the 0.7.2 digits and their 55 251-cell mesh kept beside them in-comment. The
1% reproduction band did **not** move, and the 64 MHz constants were not
touched.

`th:6` runs green end-to-end, `-n 2`, complex, `20260825T050232Z_EX-30-th-run-5to6.log`
(Status 0, 55 s for `th:5` + `th:6`): 128 MHz fine rung **relL2 1.769% against
1.769% (drift 2.02e-04)**, **separation 59.16× against 59.16× (drift
5.45e-05)** at 55 241 cells, and 64 MHz unmoved at 3.643% / 18.67× (drifts
4.04e-05 / 2.96e-04) — the licensed pair now reproduces three decades inside
its own band, and the frequency asymmetry that made this entry is gone because
it was never physics. Original entry below, for the audit trail.

**Test id:** the assertion is in the example,
`examples/time_harmonic/06_larmor_lossy_sphere.py:186` (`_check_record`), which
gates against a 1% reproduction band. The owning gate module for the record
itself is `TH-10`'s; **it has not been re-run on 0.11**, which is the open
question below.

**Literal symptom**
(`docs/testing/logs/20260824T213236Z_EX-30-th-run-6to8.log`):

```
[64 MHz]  h_sphere = 0.00833 ( 17667 cells): relL2 = 3.643%, separation 18.67x
[64 MHz]  vs the TH-10 record: relL2 3.643% against 3.643% (drift 4.04e-05),
          separation 18.67x against 18.68x (drift 2.96e-04) — band 1%
[128 MHz] h_sphere = 0.00833 ( 17667 cells): relL2 = 3.302%, separation 31.75x
[128 MHz] h_sphere = 0.00556 ( 55241 cells): relL2 = 1.769%, separation 59.16x
AssertionError: [128 MHz] fine-rung interior relL2: this run measured 0.0176864
against the `TH-10` record 0.01826, a drift of 3.14% outside the 1% reproduction band
```

**Verified at:** `main` @ `7529fa4` (2026-08-24), 0.11.0.post0 image, `-n 2`,
complex build.

**Cause — NOT diagnosed. One thing is excluded by measurement: the mesh.** Every
0.11 record motion recorded in this file so far has been a moved mesh underneath
a converged solve. This one is not: the 128 MHz fine rung meshes to **55 241
cells, which is `TH-10`'s own re-recorded count**, and the coarse rung to 17 667,
also on record. Same code, same mesh, same rung — 3.14% different answer at
128 MHz and 4.04e-05 at 64 MHz. The frequency asymmetry is the whole finding;
128 MHz is the harder-conditioned rung (`|m|k₀a` = 1.374 vs 0.850, series N = 8
vs 7, last-term bound 7.2e-16 vs 8.1e-16, so the series itself is not the
suspect).

**Why this matters more than an example red.** 3.643% / 1.826% is the pair
CLAUDE.md and PROJECT_PLAN §2 quote as `TH-10`'s close — the Larmor-frequency
validation gate. The 64 MHz half reproduces; **the 128 MHz half is currently
unreproduced on the image `main` boots.**

**Nothing was re-recorded and no band was moved** — the assertion's own message
and §9 item 4's negative-result clause both forbid it, and the drift is 3× the
band on a quantity §2 depends on.

**The next measurement, and it is one standard-tier command:** re-run `TH-10`'s
own gate module on 0.11. If the gate reproduces 1.826%, this is an example/gate
path divergence (cf. the `th:7` entry above, same family, same slot). If the gate
also measures ~1.7686%, it is a real 0.11 motion in a §2 figure and the §2
sentence needs revising. Until one of those is done, this is undiagnosed.

**DIAGNOSED 2026-08-24, 18:00 review — from documentation; the measurement
already existed.** `TH-10`'s gate module *was* re-run on 0.11, on 2026-08-22,
by `OPS-18` step 3 attempt 1: green log
`20260822T123746Z_OPS-18-step3-th10-rerun.log` (11 passed, exit 0) prints the
128 MHz fine rung at **relL2 1.769%, separation 59.16×, 55 241 cells** — the
re-record 1.826% → 1.769% is explicit in §7 `OPS-18` ("*with its mesh*,
55 251 → 55 241"). `th:6` measured 1.76864% / 59.16× on 55 241 cells: the
gate's own 0.11 digits to 2e-4, against its never-updated restated constants
(`RECORD_INTERIOR_L2[128 MHz]` 0.01826, `RECORD_SEPARATION[128 MHz]` 57.31).
So this is the **example/gate-divergence branch** — same class as the `th:7`
entry — not a physics motion; the "mesh did not move" observation above was
correct and is exactly why: the mesh had already moved *at the re-record*,
and the record moved with it while the example's copy did not.

**Retire when:** `th:6`'s two 128 MHz constants are re-recorded
version-tagged from the `20260822T123746Z` log (0.7.2 digits kept beside)
and the example runs green — licensed to `EX-30` leg (th)'s re-run
(§9 item 4, 2026-08-24 18:00 review). §2 and CLAUDE.md now quote the
version-tagged pair.

**Also on that log — the `Status: 124` is a teardown hang, not a compute
overrun.** After the assertion fires (~40 s of real work), MPI deadlocks in
`mpi4py.MPI.commlock_free_cb` during interpreter shutdown (`SystemError: …
returned a result with an exception set`); the container-side `timeout -k 30 300`
fired and PETSc reported signal 15. The `-k 30` worked as designed —
`docker compose ps` read Up and `pgrep -c python3` read **0** immediately after,
no wedge and no force-recreate. Worth knowing: an assertion failure in this
example does not exit cleanly under `mpiexec`, so budget for the full timeout
when re-running it red.

### 🚫 OPEN — the gapped birdcage's **open-limit (1e6 Ω) driven self-impedance `Z₁₁` is not mesh-converged**: it moves ~40% under a 0.24% cell-count change, while the terminated column moves 1.9e-02 (`GEO-19` step B attempt 2, 2026-08-24)

**Test id:** `tests/validation/test_port_birdcage_termination_probe.py::test_the_open_control_reproduces_leg_c_before_the_knob_turns`
(and, on the same fixture,
`tests/validation/test_port_birdcage_lumped_column.py::test_adjacent_ports_of_the_driven_leg_agree_and_the_opposite_one_does_not`).
**Neither is red on `main`, and neither can be: step B landed 2026-08-25
under ruling (6\*) and both open-limit record assertions are gone with it**
(the Z-column reproduction retired, the degeneracy ordering assertion
retired; both quantities are still solved and printed as diagnostics, with
their digits kept in-comment as mesh-tagged history). `19 passed` twice from
`main` at 116 085 cells — `20260825T003622Z_GEO-19-stepB-port9-run1.log`,
`20260825T003832Z_...-run2.log`. This entry is no longer about a red; it is
the standing record of the **conditioning finding itself**, which is
unmeasured and unfixed. The attempt branch it once pointed at is deleted;
the content is on `main`.

**Literal symptom**, `20260824T183519Z_GEO-19-stepB-port9-measure.log`
(`3 failed, 16 passed` / 117.80 s / Status 1), the open (1e6 Ω) column at
116 085 cells against its record at 116 368:

```
Z_11 +9.201557829e+02-4.718342449e+03j  vs record +7.111692404e+02-3.351665665e+03j
Z_21 +1.390012417e+01-1.872224592e+03j  vs record +1.224919287e+01-1.878346946e+03j
Z_31 +1.322525314e+01-1.872769896e+03j  vs record +1.193721196e+01-1.878700877e+03j
Z_41 +1.465032447e+01-1.872096207e+03j  vs record +1.231338434e+01-1.878312313e+03j
```

`|Z₁₁|` goes 3.42e+03 → 4.81e+03 Ω, a **40.6%** move; the three mutuals move
0.3%; the driven current moves 1.381e-03. On the *terminated* (50 Ω) fixture
the same mesh change moves `Z₁₁` by 1.852e-02 and `Z₄₁` by 5.9e-04.

**Cause — measured, and it is not a defect in step B.** The mesh moved for the
reason ruling (4\*) already adjudicated (the local-frame construction is
exact-onto at the four axis azimuths but not bit-identical to the old one;
gmsh tie-breaking turns ~5 ulps into 116 368 → 116 085 cells). What is new is
the *sensitivity*: at `Z_p = 1e6 Ω` the port is very nearly open, so `I₁` is a
near-cancellation residual (~1e-9 A) and `Z₁₁ = V₁/I₁` inherits its
conditioning. The same fixture's degeneracy margin flips in step with it —
leg (c)'s magnitude-only reading 5.0594× → **0.7906×**, and the complex form
6.9398× → 1.5951×, both already below leg (d0)'s 10× floor *before* step B.
The terminated fixture shows the opposite behaviour and gets **better**:
margin 253.2002× → 2256.9707×, class separation 150.3584× → 166.6766×, every
intra-class spread down (0.0617/0.0359/0.0237% → 0.0553/0.0353/0.0214%).

**Why this is not disposed of by a re-record.** §9 item 2 licensed a
mesh-tagged re-record of the moved records and a pre-registered disposition for
the degeneracy gate. It did not anticipate a 40% move, and pinning `Z₁₁` at a
1e-9 print band on a quantity with no demonstrated mesh stability would record
noise as a fact. The reading this entry offers the review: **the open-limit
column is a diagnostic, not a record-bearing fixture**, and the anti-degeneracy
role it was carrying is already carried, with two decades more margin, by leg
(d0)'s terminated discrimination gate and leg (d)'s 4×4 class separation —
both gated on `main`, both green, both improved by step B.

**Flagged to the weekly review** (§10 Phase 6): if the open-limit column is
retired as a record, `PORT-9` leg (c)'s reproduction anchor needs a replacement
on the terminated fixture, and leg (d1′) should be re-scoped to match.

**Ruled 2026-08-24, 18:00 review — (6\*), option (A): the open-limit column
is retired as a record-bearing fixture; step B lands with the retirement
(§9 item 1), leg (c)'s anchor re-sites on its driven `I₁` + the terminated
fixture, (d1′) re-scoped.** The entry stays OPEN as the record of the
conditioning finding itself. **Retire when:** an h-refinement rung measures
the open column's conditioning, or Phase 6 adjudicates that no open-limit
quantity is record-bearing for the tuning workflow — whichever a review
commissions first. The Phase 6 flag above stands.

**Executed 2026-08-25 (§9 item 1, 19:30 slot).** The retirement is in code
on `main` and the three modules are green twice in-slot. Nothing about the
*finding* changed: `|Z₁₁|` at `Z_p = 1e6 Ω` is still unconverged, still
undiagnosed beyond the near-cancellation argument above, and no h-refinement
rung has been run. What changed is that no record now rests on it. The two
gates that absorbed the anti-degeneracy duty read **2256.9707×** (leg (d0),
floor 10×) and **166.6766×** (leg (d) class separation, floor 10×) on step
B's mesh, both improved. Retire-when is unchanged.

**Verified at:** `cc4ab78` (`main`) + `6c1f54e`
(`attempt/GEO-19-stepB-20260824T183000Z`), 2026-08-24; re-verified on `main`
2026-08-25 with the retirement landed.

### ✅ RETIRED 2026-08-25 (`GEO-19` step C, 07:30 implementer slot) — `birdcage_port_domain(emit_port_sheets=True)` **cannot build any birdcage with more than four legs**: the mid-plane sheet is an axis-aligned rectangle (`GEO-19` attempt 1, 2026-08-23)

**Retired on the run this entry named as its retire-when.** Step B's
local-frame construction landed on `main` 2026-08-25, and step C built the
16-leg fixture from `main`: **307 296 cells / 74.18 s of mesh time**, all 16
sheets at `dx·g` = 1.000000000000 with a C16 area spread of **1.331e-15** and
out-of-plane extents ≤ 1.736e-17 m in each port's own frame, 32 half-boxes at
0.500000000000, `GEO-9` partition 1.000000000000
(`20260825T124357Z_GEO-19-stepC-run1.log`, `-n 2`, 114 s). The
`NotImplementedError` is unreachable: ports P2/P4/… sit at 22.5° + 45k and
build. What step C found instead is a *band-domain* question on gate (ii)'s
equality half, filed as its own entry below — the capability limit this entry
described is gone.

**Test id:** no test asserts this on `main` — the module that hits it,
`tests/mesh/test_birdcage_port_scaleup.py`, is parked on
`attempt/GEO-19-20260823T214500Z` rather than landed red.

**Literal symptom**, at `leg_count = 16` with `leg_gap_length = 8e-3`,
`emit_port_sheets = True`:

```
NotImplementedError: emit_port_sheets builds axis-aligned rectangles, so
every leg must sit on a coordinate axis; port P2 is at 22.500 degrees
```

raised from `src/fem_em_solver/io/mesh.py:3189`, `-n 2`, 1.4 s,
`docs/testing/logs/20260823T213546Z_GEO-19-step1.log`.

**Verified at:** `main` @ the `GEO-19` blocker-A commit (2026-08-23), on the
0.11.0.post0 image.

**Cause — diagnosed, not a mystery.** The sheet is entered into the OCC
fragment as an axis-aligned dim-2 tool, and the half-assignment that follows
tests a *single Cartesian centroid coordinate* against the plane's offset
(`mesh.py:3270-3278`). Both steps assume the leg's radial direction is `x̂`
or `ŷ`, which holds only for `leg_count <= 4`. Any other count puts legs at
intermediate azimuths and the construction has no rectangle to place. This is
a genuine capability limit, not a regression: nothing above four legs had ever
been sheeted, so it had never been reached.

**Not to be confused with** the `100+i`/`110+i` tag collision in the same code
path, which was the *outer* guard (`leg_count <= 9`) and **is fixed** — the
upper base is now `200+i`, verified inert against `GEO-18` step 1/2 at
`3 passed` / 116 368 cells / C4 spread 6.050e-16, digit-identical to the
pre-change run (`20260823T213647Z_GEO-19-tagfix-regression.log`).

**Retire when:** the sheet is built in the leg's local `(r̂, ẑ)` frame with the
half test taken along the leg's radial normal, and `GEO-19`'s gates (i)–(v)
run at 16 legs. **Fix scoped 2026-08-23 18:00 review as `GEO-19` step B
(§9 item 3, rotated construction + 4-leg invariance control); the 16-leg
gates are step C (§9 item 5). This entry retires with step B's commit** —
the gates run is a separate deliverable and does not hold it open.

> **Step B attempt 1, 2026-08-24 03:30Z implementer slot — the rewrite exists,
> is green, and is parked rather than landed.** `attempt/GEO-19-stepB-`
> `20260824T034500Z` (`12737a8`) carries it: box and sheet both built at
> azimuth 0 and taken to the leg's azimuth by one snapped rotation about `ẑ`,
> half-assignment by signed projection on the plane's own normal, the raise
> deleted. The `GEO-18` step-1 + step-2 invariance control is `3 passed` /
> Status 0 **twice in-slot** (90.08 s / 88.97 s,
> `20260824T033811Z_GEO-19-stepB-snapped-run1.log`,
> `20260824T033956Z_…-run2.log`), reproducing the record's terminal ratios
> (0.988616 × 4) and C4 sheet spread (**6.050e-16**, exactly) with every
> analytic identity exact and the CAD digit-identical.
> **What holds it back is not the geometry but its consumers:** the mesh cell
> count moves (116 368 → **116 085** sheeted, 114 855 → **114 655** gapped),
> and on that moved fixture three `PORT-9` birdcage assertions go red
> (`20260824T034214Z_GEO-19-stepB-port9-regression.log`, `3 failed, 16 passed`
> / 124.68 s): leg (c)'s driven current deviates 1.376e-03 from record, leg
> (d0)'s `Z_11` 1.840e-02 against a 1e-9 print band, and leg (c)'s
> class-degeneracy gate **flips** — the opposite port sits 0.0321% from the
> adjacent pair's mean against the pair's own 0.0407% spread, i.e. inside it.
> Re-recording those digits is §9 item 4's licence, and the flipped gate is a
> ruling, so this entry stays open until a review disposes of it.

> **Ruled 2026-08-24 03:00 review — ruling (4\*), full text in §9.** The
> rewrite is adjudicated correct; the cell-count digit-for-digit expectation
> was unsatisfiable (the old construction sat ~5 ulps off exact positions and
> gmsh tie-breaking amplifies that to ~1e-3 in cell count; CAD and every
> analytic identity reproduce digit for digit). Sequencing: `PORT-9` leg
> (d3b) re-records the birdcage class on the **unmoved** mesh first (§9
> item 1), then step B lands with a mesh-tagged re-record (§9 item 2), whose
> licence includes the pre-registered degeneracy-gate disposition. **This
> entry retires with §9 item 2's commit.**

Blocked `GEO-19` until step C ran; never blocked `GEO-20` (ring-gap ports
sit at different azimuths and are scoped to their own local frame from the
start). Related and separate: the layout clearance floor independently caps
this geometry at `N <= 25` legs — see the `GEO-19` §7 entry.

---

### ✅ RETIRED 2026-08-25 (`GEO-19` step C, 12:00 implementer slot) — `GEO-18` step 1's **1e-5 terminal-equality band is a C4 band, not a C_N one**: at 16 legs the terminal disks spread **8.434e-04**, two decades wide of it, while every ratio stays inside the closed form's [0.95, 1.0] (`GEO-19` step C, 2026-08-25)

**Test id:** `tests/mesh/test_birdcage_port_scaleup.py::`
`test_sixteen_leg_identity_family_and_cost_rung`, parked on
`attempt/GEO-19-stepC-20260825T125000Z` (`e7a3926`) rather than landed red.

**Literal symptom**, at `leg_count = 16`, `-n 2`
(`docs/testing/logs/20260825T124357Z_GEO-19-stepC-run1.log`, 114 s):

```
AssertionError: 16 legs: the 16 terminal areas differ by 8.434e-04 relative
against the pre-stated 1e-05; the ports are not the same disk under a rotation
assert np.float64(0.0008433598402112139) < 1e-05
```

**Verified at:** `main` @ `d74c7a5`, 0.11.0.post0 image, step B's local-frame
construction.

**Cause — diagnosed, and it is arithmetic rather than geometry.** The 16
meshed terminal ratios take **three** values, and they sort by azimuth:

| azimuth | ratio to `2·π·r_leg²` | ports |
|---|---|---|
| 0/45/90/…/315° | 0.988615667 … 0.988615857 | P1 P3 P5 P7 P9 P11 P13 P15 |
| 22.5/157.5/202.5/337.5° | 0.989367491 … 0.989367549 | P2 P8 P10 P16 |
| 67.5/112.5/247.5/292.5° | 0.989449699 … 0.989449760 | P4 P6 P12 P14 |

Within each class the spread is ≤ 2e-7 — *tighter* than the 1e-5 band. The
band was measured at C4, where the four ports are related by exact 90°
coordinate permutations, so their inscribed triangulations are the same
arithmetic and agree to 3.2e-08 (this run's control reproduces that:
**3.184e-08**). At 22.5° there is no coordinate permutation; the disk's
inscribed polygon lands on different nodes, and an inscribed triangulation
under-reads a circle by ~1.1% to begin with. The observed 8.4e-04 spread is
**thirteen times smaller than that under-read** — it is the discretization
error's own azimuthal variation, not a broken port.

**Not a widening candidate in-slot.** The `GEO-19` §7 entry's negative-result
clause is explicit ("a gate red at 16 legs is a generator finding at the new
count — known-issues + §7 annotation, stop; never widen a `GEO-18` band"), so
the band is untouched and the module is parked. Everything else step C
pre-stated is green and is recorded in the §7 entry.

**Retire when:** a review rules on which of these the equality gate is asserting
— exact C_N symmetry of the *construction* (in which case the reading is
per-azimuth-class and the gate becomes an intra-class one at ~1e-6, tighter
than today's) or agreement of the *discretization* across azimuths (in which
case the band is h-dependent and wants a refinement rung, not a constant). Both
readings are consistent with the measurement; choosing between them is a
ruling, not an implementer judgement.

**RULED 2026-08-25, 10:30 review: construction symmetry.** The ≤ 2e-7
intra-class tightness says the construction is exactly C_N-covariant, and the
inter-class 8.4e-04 is the inscribed triangulation's azimuthal variation
(13× below its own ~1.1% under-read scale) — gating it at 1e-5 gates the
mesh, not the generator. The reading becomes per-azimuth-class: intra-class
equality asserted at **1e-6** (tighter than today; basis ≤ 2e-7), inter-class
spread asserted under a coarse **5e-3** discretization ceiling (basis
8.434e-04; half the under-read scale) so a broken port cannot hide, the
absolute [0.95, 1.0] band and every C4 module's 1e-5 unmoved. Full landing
instructions in the `GEO-19` §7 entry. **This entry now retires with the
commit that lands the ruled module green from `main`** (§9 item 1,
2026-08-25 10:30 queue).

**RETIRED 2026-08-25, 12:00 slot — the ruled module is green from `main`,
and the class table above reproduces port for port.**
`20260825T170316Z_GEO-19-stepC-ruled.log` (`2 passed` / **117 s**, Status 0)
and the record run `20260825T170523Z_GEO-19-stepC-ruled-record.log`
(`2 passed` / **115 s**, Status 0, `-s`). The partition is taken from the
mesh's own coordinate mirrors (`_azimuth_class`), not from the measured
areas, and it lands on exactly the three classes tabulated above:

| class | ports | meshed/analytic | intra-class spread (band 1e-6) |
|---|---|---|---|
| aligned (0/45/…/315°) | 8 | 0.988615772 | **1.923e-07** |
| 22.5/157.5/202.5/337.5° | 4 | 0.989367514 | **5.849e-08** |
| 67.5/112.5/247.5/292.5° | 4 | 0.989449735 | **6.144e-08** |

Inter-class spread **8.431e-04** against the 5e-3 ceiling. The four-leg
control returns **one** class at **3.184e-08** — the back-compat identity the
ruling asked for, i.e. the reading reduces to the old flat gate exactly — with
116 085 cells (delta **0**) and C4 sheet spread 6.050e-16. No band outside
`tests/mesh/test_birdcage_port_scaleup.py` moved; the C4 modules keep their
1e-5 and `TERMINAL_AREA_BAND` keeps [0.95, 1.0].

---

### ✅ RETIRED 2026-08-24 (`PORT-9` leg (d3c), 12:00 implementer slot) — two birdcage **reproduction controls** were red on `main`: the 0.11 image meshes the gapped birdcage at **116 368** cells, the records were taken at **116 416** (`PORT-9` leg (d3b), 2026-08-24)

**Test ids** (both `@complex_only`, both failed on `main` with no local change):

```
tests/validation/test_port_birdcage_termination_probe.py::test_the_open_control_reproduces_leg_c_before_the_knob_turns
tests/validation/test_port_birdcage_four_port.py::test_the_driven_column_reproduces_leg_d0
```

**Literal symptom**, `-n 2`, complex build, `2 failed, 17 passed`:

```
AssertionError: the open solve's driven current +9.992781266e-07+3.346865998e-09j A
deviates 6.829e-06 from leg (c)'s recorded +9.992734880e-07+3.351870842e-09j A
AssertionError: Z_11 = +2.172952668e+01+7.461413742e+00j Ohm deviates 1.449e-04 from
leg (d0)'s recorded +2.173224483e+01+7.459491479e+00j Ohm against the 1e-09
print-precision band
```

`docs/testing/logs/20260824T093133Z_PORT-9-step3d3b-run1.log` and
`…T093526Z_…-run2.log` — both runs identical in every Z digit.

**Verified at:** `main` @ `082e30f` (2026-08-24), 0.11.0.post0 image.

**Cause — measured, not a mystery: the mesh moved, and it is not the route.**
All three modules printed `116368 cells (record 116416, ratio 0.999588)`. The
`PORT-9` leg (c)/(d0)/(d) records were taken 2026-08-22/23 **before** the
`OPS-18` step 3b merge put main on dolfinx/gmsh 0.11, and 0f8ea96 already
measured 116 368 on 2026-08-23 *both before and after* its own tag change, so
the tag encoding is excluded. This is the same 1e-4 record motion the retired
0.11 entry below recorded for the two-torus family, recurring for the birdcage
family, which nothing re-gated on 0.11. The `PORT-9` leg (d3) route change
cannot be the cause: it touched only `_assemble_sparameter_matrix`, and these
two modules never call the sweep's S assembly at all. **Every physics identity
still held** on the moved mesh — sheet area `5.930614898e-05 m²`, `h` exactly
`8.000000000e-03 m`, out-of-plane `8.882e-19 m`, all four sheets identical, C4
class spreads 0.0617 / 0.0359 / 0.0237% and the (d0) discrimination margin
253.2002× against a 10× floor.

**Retired by:** ruling (5\*) (2026-08-24 10:30 review) granted the image-caused
re-record; `PORT-9` leg (d3c) executed it in the 12:00 slot. The two controls
are now recorded image-tagged at 116 368 — leg (c) `I_1` =
+9.992781266e-07 + 3.346865998e-09j A, leg (d0) `Z_11` =
+2.172952668e+01 + 7.461413742e+00j Ω, both beside the pre-0.11 digits in the
modules' own comments — and both runs of the re-record read **19 passed** with
every edited constant reproducing to ≤ 2.4e-10 against its 1e-9 band
(`20260824T170332Z_PORT-9-step3d3c-run1.log`,
`20260824T170544Z_PORT-9-step3d3c-run2.log`). No band was moved.

### ✅ RETIRED 2026-08-23 (`OPS-18` step 3b merge) — the two-torus port fixtures **SIGABRT'd in `gmsh.model.mesh.generate` only in the 0.11 image**: numpy 2 renders `!r` of a numpy scalar as `np.float64(…)` inside a gmsh `MathEval` string (`OPS-18` step 3 attempt 2, 2026-08-22; entered by the 10:30 review)

> **RETIRED 2026-08-23, 15:00 implementer slot.** The entry's own retirement
> condition is met: the fixing commit `445a3ea` (`float()` coercion at the
> four `MathEval` sites, attempt 3) reached `main` with the `OPS-18` step 3b
> merge, and `main` now boots the 0.11 image the defect was scoped to. The
> two-torus fixtures the SIGABRT killed are green on that image at
> `19 passed` / exit 0 twice (step 3a attempt 8,
> `20260823T170403Z_OPS-18-step3a-leg1-run1.log`,
> `20260823T170821Z_…-run2.log`). Original entry follows.
>
> **Where this fires.** `tests/validation/test_port_package_sparameters.py`
> and `tests/validation/test_port_lumped_two_torus.py` (every test that
> builds `two_torus_domain`), on the `attempt/OPS-18` worksite only. `main`
> boots 0.7.2 with numpy 1.x and is unaffected.
>
> **Literal symptom** (`20260822T140912Z_OPS-18-step3-port1-rerun.log`,
> `Status: 134` at 12 s, `-n 2`, complex build):
>
> ```
> Error   : Error [mathex::parseatom()]: invalid token on expression
> terminate called after throwing an instance of 'std::runtime_error'
> ```
>
> **Cause, measured by two probes.** gmsh in the 0.11 image is
> 4.15.2-git-657c8e9 and parses the exact gap-arc expression when its numbers
> are plain floats (`20260822T141005Z_…-gmsh-mathex-probe.log`); the image's
> numpy 2.4.6 renders a numpy scalar's `repr` as `np.float64(0.00591…)`
> (`20260822T141027Z_…-numpy-repr-probe.log`). `two_torus_domain` builds its
> `MathEval` size field by f-string `!r` interpolation (`io/mesh.py:1550`–
> `1557`) of `arc_half_y`, a numpy scalar, so the string literally contains
> `np.float64(`. Image debt of ours that numpy 1.x masked — not an upstream
> regression, not a gated number moving; no band, assertion or record touched.
>
> **Fix owner:** §9 item 3a — `float()` coercion at the sites plus a `src/`
> sweep for `!r` in any string handed to gmsh, PETSc options or a shell (the
> birdcage fixtures are predicted to carry siblings). This entry leaves with
> that commit.
>
> **FIXED on the branch 2026-08-22, 12:00 implementer slot (`445a3ea`,
> `attempt/OPS-18`) — this entry retires when that branch merges (§9 item
> 3b (iii)).** `arc_half_y`, `major_radius` and `z_c` are coerced to plain
> `float` before the f-strings. Negative control discharged against the red
> baseline quoted above: the same batch now meshes and runs to a footer,
> `17 passed / 2 failed` in 260.93 s
> (`20260822T170346Z_OPS-18-step3-port1-coerced.log`) — the SIGABRT is gone
> and the two remaining failures are the moved reproduction records in the
> next entry, a different defect. **Sweep result, measured:** `src/` carries
> **53** `!r` interpolations; the **4** two-torus `MathEval` sites are the
> only ones handed to a foreign parser (the other 49 are Python exception
> messages, which is what `!r` is for), and `MathEval` has exactly **one**
> call site in all of `src/` (`io/mesh.py:1568`). The prediction that the
> birdcage fixtures carry siblings is **wrong, by measurement** — they build
> no `MathEval` field. The class is closed at one instance.

### ✅ RETIRED 2026-08-23 (`OPS-18` step 3b merge) — two two-torus **reproduction records** moved in the 0.11 image at 1e-4 while every physics identity held (`OPS-18` step 3 attempt 3, 2026-08-22)

> **RETIRED 2026-08-23, 15:00 implementer slot.** The entry's stated closing
> condition — "this entry closes with step 3b's merge commit, which is what
> carries these branch-only writes to `main`" — is met: `5df1e39` (step 3a
> attempt 8) is on `main` with this merge, and the four re-records plus the
> two the same assertion loop unmasked are all written version-tagged, no
> band moved. See the attempt-8 resolution block at the end of this entry
> for the digits. Original entry follows.
>
> **Where this fires.** `tests/validation/test_port_package_sparameters.py::test_sanity_report_reproduces_the_gated_metrics_on_the_field_route`
> and `tests/validation/test_port_lumped_two_torus.py::test_step_1_measurements_reproduce`,
> on the `attempt/OPS-18` worksite only. `main` boots 0.7.2 and is unaffected.
> These are the two failures left in the log that discharged the SIGABRT
> above; they are a **different defect** from it, and they only became
> visible once the mesh built again.
>
> **Literal symptom** (`20260822T170346Z_OPS-18-step3-port1-coerced.log`,
> `2 failed, 17 passed` in 260.93 s, `Status: 1`, `-n 2`, complex build,
> both rank footers identical):
>
> ```
> passivity_max_sigma 0.861356895 does not reproduce the step-4 record
>   0.861449 within 1.0e-06   (moved 9.210529e-05)
> gap ratio: 0.894141 against step 1's record 0.894310 — moved by 1.69e-04,
>   above 1e-04
> ```
>
> and, printed but not asserted in the same test's stdout:
> `||S-S^T||/||S|| = 3.112128e-05` against the record `2.5494e-05`
> (band 5.0e-07).
>
> **What did *not* move.** Every gate that scores physics rather than a
> recorded digit string passes, in the same run: reciprocity at
> 3.112128e-05 is 32× inside the `PORT-1` band of **1e-3**; passivity holds
> (σ_max 0.8614 < 1, column power sum 0.7411 < 1); the open-limit reduction
> to the sheet average and the cross-route transverse-average identity both
> PASS. 17 of 19 tests pass.
>
> **Cause, not diagnosed — one hypothesis, and it is testable.** gmsh moved
> 4.11 → 4.15.2 with the image, and the meshes it emits move with it: the
> straight-wire fixture in the entry below went 145 900 → **147 235** cells
> on the same requested `h`. A two-torus mesh perturbed at that level moves
> a solved S-matrix at 1e-4, which is exactly the size of both misses and
> ~7× the tightest band (1e-6). The alternative — that 0.11 changed an
> assembly or interpolation the port route depends on — is not excluded by
> anything measured here. Deciding between them needs the two-torus cell
> count printed on both images; nobody has printed it.
>
> **Update, 2026-08-22 (`OPS-18` step 3 attempt 4): the mesh did move, and
> by 24× more than the records did.** `tests/mesh/probe_two_torus_cell_count.py`
> builds this exact fixture — every argument imported from `_build` in the
> test that owns the record — and prints the reduced global counts:
>
> | | dolfinx 0.7.2 / gmsh 4.11.1 | dolfinx 0.11.0.post0 / gmsh 4.15.2 | Δ |
> |---|---|---|---|
> | cells | 184 919 | 184 176 | **−743, −4.017e-03** |
> | vertices | 31 676 | 31 550 | −126, −3.978e-03 |
> | wire tags `1`/`2` | 9 463 / 9 380 | 9 556 / 9 448 | +0.98% / +0.72% |
> | gap halves `101`/`102`/`111`/`112` | 13 627 / 13 599 / 13 763 / 13 771 | 13 661 / 13 648 / 13 658 / 13 694 | ≤ 0.8% |
>
> Logs `20260822T183313Z_OPS-18-step3-twotorus-cells-072.log` (Status 0, 33 s,
> `main` source on the 0.7.2 image) and
> `20260822T183626Z_OPS-18-step3-twotorus-cells-011.log` (Status 0, 34 s,
> `attempt/OPS-18` source on the 0.11 image), both `mpiexec -n 2`. The
> 0.7.2 run had to be taken on `main`'s source: the branch's `io/mesh.py`
> imports `dolfinx.io.gmsh`, which 0.7.2 does not have, so the two runs
> differ by the step-2 migration as well as the image — a caveat on
> attribution, not on the counts.
>
> **So the mesh hypothesis is *consistent* here**: a 4.0e-03 mesh
> perturbation moving two solved records by 9.2e-05 and 1.7e-04 is a 24-40×
> attenuation, which is what a converged quantity on a perturbed mesh does.
> It is still not a proof — the same slot **refuted** the mesh explanation
> for the straight-wire entry below, where the counts moved by < 0.16% —
> so the two failures should not be assumed to share a cause. **The
> re-record decision remains the review's**; what this update supplies is
> the evidence it asked for.
>
> **No band, assertion or record was touched**, and none should be until
> the cause is decided: re-recording a solved S-matrix to make a version
> bump land is how a version bump hides a physics change. §9 item 3a's
> negative-result clause fired on this and stopped the leg.
>
> **Ruling, 18:00 review 2026-08-22 — re-record licensed, narrowly.** The
> three numbers (`passivity_max_sigma` at 1e-6, the gap ratio at 1e-4, the
> reciprocity record at 5e-7) are reproduction records of a solved field on
> a named mesh, every physics gate in the same run holds, and the mesh
> moved 4.017e-03 — the same grounds on which `TH-10`'s 55 251 → 55 241
> re-record was granted. Conditions: version-tagged (0.7.2 value + 184 919
> cells stay beside the new value + 184 176 cells + `0.11.0.post0 / gmsh
> 4.15.2`), bit-identical across two runs in the slot before the digit
> string is written, no band moves, branch-only until 3b merges. Queued as
> §9 item 4; this entry closes with that commit. Full text in the §7
> `OPS-18` entry.
>
> **Update, `OPS-18` step 3a attempt 7 (2026-08-23, 06:00 slot) — the three
> licensed records are written and green, and writing them surfaced a
> fourth and a fifth of the same kind.** On `attempt/OPS-18` at `44b5600`,
> image `v0.11.0`, complex, `-n 2`, two same-slot runs
> (`20260823T110726Z_OPS-18-step3a-leg1-confirm.log`, `1 failed / 18
> passed` / 234.88 s, and `20260823T112102Z_…-leg1-confirm-rerun.log`,
> same counts / 226.36 s). `passivity_max_sigma` 0.861356895, `‖S−Sᵀ‖/‖S‖`
> 3.11213e-05 (six digits per (b′)) and the gap ratio 0.894141 all
> reproduce as written in both runs; physics green in both (reciprocity
> 2.679e-05 inside 1e-3, σ_max 0.861357 < 1).
>
> The remaining failure is **not** a regression: `test_step_1_measurements_
> reproduce` checks three records in one loop, and the gap ratio was the
> first, so fixing it unmasked the other two.
>
> | record | 0.7.2 | 0.11.0 | move | band | run-to-run move |
> |---|---|---|---|---|---|
> | `STEP1_LUMPED_RATIO_RECORD` | 0.829782 | 0.828893 | 8.89e-04 | 1e-4 | 6.6e-10 (6.6e-06 of band) |
> | `STEP1_CROSS_ROUTE_RECORD` | 0.077095 | 0.077431 | 3.36e-04 | 1e-4 | identical to 6 printed digits |
>
> Both are step-1 reproduction records of the *same* solved field on the
> *same* fixture whose mesh moved 184 919 → 184 176 cells — the class
> ruling (1) licensed — and both satisfy (b′)'s reproduction condition on
> this slot's two runs. But ruling (1) enumerates **three** numbers, and an
> implementer does not extend a review ruling in-slot, so **neither was
> written**. What is owed is one review decision: extend ruling (1) to
> these two, or rule them differently. Nothing else in leg 1 is open.
>
> **Resolved, `OPS-18` step 3a attempt 8 (2026-08-23, 12:00 slot) — the
> 10:30 review's class ruling (1\*) admitted both, they are written, and
> leg 1 is green.** On `attempt/OPS-18` (`main` merged at `070b1b5`),
> image `v0.11.0`, complex, `-n 2`, two same-slot runs both **`19 passed`**
> / exit 0 (`20260823T170403Z_OPS-18-step3a-leg1-run1.log`, 238.64 s;
> `20260823T170821Z_OPS-18-step3a-leg1-run2.log`, 238.73 s), where attempt
> 7 read `1 failed / 18 passed`. `STEP1_LUMPED_RATIO_RECORD` **0.828893**
> and `STEP1_CROSS_ROUTE_RECORD` **0.077431** reproduce identically to six
> printed digits in both runs — (b′) arithmetic: the lumped route's
> `Im Z12` moves 1.029281339 → 1.029281338 Ω (1e-9 absolute, 1e-5 of the
> 1e-4 band once divided through by ωM₁₂), the cross-route print does not
> move at all. Physics green in both: reciprocity 2.679e-05 inside 1e-3,
> σ_max 0.861357 < 1, open-limit and cross-route decomposition PASS, the
> 5% cross-route MISS unchanged and still pre-stated. The fixture meshes
> to 184 176 cells in both runs. **The loop unmasked no further record**,
> and the only other consumer of these constants,
> `test_port_lumped_narrowed_sheet.py`'s `f = 1.0` negative control, is
> green on the new values in the same slot (`12 passed` / 142.72 s / exit
> 0, `20260823T171239Z_OPS-18-step3a-narrowed-sheet.log`; that rung prints
> 7.7431%, gap 0.894141, lumped 0.828893 — the identical digits). No band
> moved. **This entry closes with step 3b's merge commit**, which is what
> carries these branch-only writes to `main`.

### ✅ RETIRED 2026-08-23 (`MAG-18` re-gate, 19:30 implementer slot) — `test_straight_wire_b_field` failed **only in the 0.11 image**: the discretization error moved 12.75% → 15.3848% against a 15% band, on a mesh that grew 145 900 → 147 235 cells (`OPS-18` step 3 attempt 3, 2026-08-22)

> **Closing note (2026-08-23, 19:30 slot).** This entry stayed open after
> step 3b only because the `MAG-18` `E_Ω` ladder was unobserved on 0.11
> (see the scope update below). It has now been observed, on `main`, on
> the image the project boots, twice in the same slot: `7 passed` /
> exit 0 at `-n 2` (`20260824T003059Z_MAG-18-regate-run1.log` and
> `20260824T003650Z_MAG-18-regate-run2.log`, 296 s each), plus a `-n 4`
> record probe (`20260824T003606Z_MAG-18-regate-n4.log`, 32 s). The mesh
> growth this entry is about is *real and unchanged* — the h = 0.0025
> rung still meshes to **147 235** cells on 0.11 — but in the `MAG-18`
> norm it costs the gate nothing: `E_Ω` = 25.2868 → 10.6172 → 6.6458%,
> monotone, fitted rate **1.6854** against 0.7.2's 1.6842 (7e-04 of
> move), cross-width agreement 4.86e-07 ≤ 1e-6, natural-BC ratio 0.3285.
> The 10-point number this entry names is still 15.3848% on 0.11 — it is
> printed, reproduced under the version-keyed control row to 2.7e-06,
> and gates nothing. Nothing was re-recorded and no band moved. Retired,
> not merely superseded.

> **Where this fires.** `tests/validation/test_straight_wire.py::TestStraightWire::test_straight_wire_b_field`,
> real build, on the `attempt/OPS-18` worksite only. `main` boots 0.7.2 and
> is unaffected.
>
> **Scope update, `OPS-18` step 3b (2026-08-23, 15:00 slot) — read this
> first.** `main` now boots the 0.11 image, so the "worksite only" clause
> above is spent. The failure it names, however, **can no longer fire**: the
> 15% band is retired by `MAG-18` (`d494d81`, on `main` since 2026-08-22) —
> `test_straight_wire_b_field` now *prints* the 10-point number as
> "[reported, not gated]" and gates nothing, and the replacement gates are
> `TestStraightWire::test_domain_l2_*` on the sampler-free `E_Ω` and its
> convergence rate. This entry is therefore **superseded, not resolved**: it
> stays open because the thing it is really about — that the 0.11 image's
> gmsh moves the wire mesh (145 900 → 147 235 cells) and the solved error
> with it — has **not** been re-measured in the `MAG-18` norm on 0.11.
> Step 3b did not run the real-mode `MAG` leg (its anchor is the environment
> + mesh-tag family and the two collects), so **the `E_Ω` ladder and its
> rate band on 0.11 are owed and unobserved**; the numbers on record
> (25.3787 / 10.7288 / 6.6708%, rate 1.6842) are 0.7.2 numbers. A review
> should queue that leg before reading any `MAG` figure as re-gated.
>
> **Literal symptom** (`20260822T171401Z_OPS-18-step3-real-mag2.log`,
> `1 failed, 17 passed, 4 skipped` in 272.43 s, `Status: 1`, `-n 2`, both
> rank footers identical):
>
> ```
> Cells: 147235
> Relative L2 error: 15.3848%
> AssertionError: Relative error 15.3848% exceeds 15%
> ```
>
> **What did *not* move.** The rest of the `MAG` family passes on 0.11 in
> the same run: `test_straight_wire_convergence`,
> `test_analytic_bc_improves_on_natural_bc` (the `MAG-13` claim itself),
> both `test_circular_loop` gates, and all 7 `test_mutual_inductance_reference`
> tests. The failure is one number, on the one test whose band was set from
> a measured h-error ladder.
>
> **Cause, measured in part.** The 15% band is not a physics tolerance: the
> comment at `tests/validation/test_straight_wire.py:174`–`186` records it
> as the measured error of *this mesh* — `h=0.0025`, **145.9k cells**,
> **12.75%** on an O(h^1.2) ladder that has no plateau. The 0.11 image's
> gmsh (4.15.2-git-657c8e9 vs 4.11) meshes the same requested `h` to
> **147 235** cells, and this test's error is what a still-converging
> discretization does when its mesh changes — the number was always
> mesh-specific, and 15% was 1.18× a measurement rather than a bound with
> headroom.
>
> **Not diagnosed:** whether 15.3848% is *only* the mesh change. A 1.9%
> cell-count change producing a 21% error change is steeper than the
> recorded ladder (38.8k→145.9k cells for 22.19%→12.75%), so the mesh
> hypothesis is **not sufficient on its own** and something else may be
> contributing. Re-running the recorded ladder's other two rungs on 0.11
> would settle it; that is a slot's work and was not done here.
>
> **Update, 2026-08-22 (`OPS-18` step 3 attempt 4): the ladder was re-run on
> both images, and the mesh explanation is refuted.**
> `tests/validation/probe_straight_wire_ladder.py` drives the recorded rungs
> through the same `_solve_straight_wire` / `_sample_radial` / `ErrorMetrics`
> the gated test uses (imported, not restated), `mpiexec -n 2`, real build:
>
> | h | cells 0.7.2 | error 0.7.2 | cells 0.11 | error 0.11 | Δcells | Δerror |
> |---|---|---|---|---|---|---|
> | 0.0040 | 38 750 | **22.1925%** | 38 740 | **21.8417%** | −0.13% | −1.6% |
> | 0.0025 | **145 884** | **12.7485%** | 147 235 | **15.3848%** | **+0.93%** | **+20.7%** |
> | 0.0018 | 383 248 | **9.2568%** | 383 146 | **4.4605%** | −0.03% | **−51.8%** |
>
> Logs `20260822T184158Z_OPS-18-step3-wire-ladder-072.log` (Status 0, 98 s),
> `20260822T183710Z_OPS-18-step3-wire-ladder-011.log` (Status 0, 105 s) and,
> for the gated rung's 0.7.2 control,
> `20260822T185944Z_OPS-18-step3-wire-h0025-072.log` (Status 0, 27 s); the
> 0.11 `h=0.0025` row is quoted from the two runs above, which agree.
>
> **The 0.7.2 column is a clean control on all three rungs**: the July
> record reproduces to **+0.011%**, **−0.012%** and **−0.035%**, so the
> ladder is not stale and the deltas are the image.
>
> **And the outlier is not rank-dependent.** The gated rung re-run on 0.11
> at `-n 4` is **bit-identical** to the `-n 2` result — 147 235 cells,
> 15.3848% (`20260822T184951Z_OPS-18-step3-wire-h0025-n4.log`, Status 0,
> 28 s). Serial (`-n 1`) is a **sizing** finding, not a result: exit 124 at
> the 400 s ceiling (`20260822T185030Z_…-n1.log`), not retried. So the
> mesh count 147 235 and the 15.3848% are both stable and reproducible
> across rank widths, and partitioning is excluded as the cause.
>
> **What it shows.**
> 1. **Not the mesh.** Both probed rungs mesh to within 0.13% of their
>    recorded cell counts on 0.11, and their errors move by −1.6% and
>    −51.8%. A mesh that does not move cannot explain an error that halves.
> 2. **The convergence *rate* moved.** Fitted over the same two endpoints,
>    0.7.2 gives ln(22.1925/9.2568)/ln(0.004/0.0018) = **1.10** — the
>    recorded O(h^1.2) — and 0.11 gives ln(21.8417/4.4605)/ln(2.2222) =
>    **1.99**. At the fine end 0.11 is **2.1× more accurate**, not less.
> 3. **The gated rung is an outlier on its own ladder.** The 0.11 fit
>    predicts 21.8417% · (0.0025/0.004)^1.99 = **8.6%** at h = 0.0025;
>    it measures 15.3848%, **1.8×** that. It is also the only rung whose
>    cell count moved appreciably (+0.92%, 6-30× the others).
>
> **Consequence for the band.** 15% was set as 1.18× a 12.75% measurement on
> a still-converging ladder. On 0.11 that ladder converges at ~O(h²) and the
> h = 0.0018 rung already reaches 4.46% — inside the 5% target `MAG-13`'s
> comment calls out of reach at ~1.1M cells. So the honest disposal is
> probably *not* "loosen 15%": it is to find why h = 0.0025 sits off its own
> ladder on 0.11, since two rungs either side of it behave better than the
> record. **Nothing was touched here** — no band, no assertion, no record.
>
> **What is left to test.** Rank dependence and mesh instability are both
> excluded by the `-n 4` re-run above, so the remaining candidates are
> (a) a genuine non-monotonicity of this discretization near h = 0.0025
> that 0.11's slightly different mesh happens to land on, and (b) something
> in the sampling / point-location path that is sensitive to where a
> 1e-3-perturbed mesh puts cell boundaries relative to the 10 sample radii.
> (b) is the cheaper to test: re-run the gated rung on 0.11 with a
> different `n_points` (8 and 20) and see whether 15.3848% moves toward the
> ~8.6% the 0.11 fit predicts. If it does, the band was measuring the
> sampler as much as the solve.
>
> **No band was touched.** Loosening 15% to accommodate a version bump
> would erase the only instrument that shows the ladder moved. §9 item 3a's
> "a moved gated physics number is a known-issues entry and a stop" clause
> fired on this.
>
> ---
>
> **Update, `OPS-18` step 3 attempt 5 (2026-08-22, 15:00 slot) — candidate
> (b) is answered, and it answers more than it was asked.** The probe now
> solves each rung once and samples the *same* field at every requested
> `n_points`, so a spread within a row is the sampler's alone. Errors at
> n_points **8 / 10 / 20**, `-n 2`, both images
> (`20260822T200411Z_…-wire-h0025-npoints.log` Status 0 31 s,
> `20260822T200503Z_…-wire-ladder-npoints-011.log` Status 0 106 s,
> `20260822T201014Z_…-wire-ladder-npoints-072.log` Status 0 126 s):
>
> | h | 0.7.2: 8 / 10 / 20 | 0.11: 8 / 10 / 20 |
> |---|---|---|
> | 0.0040 | 18.6850% / **22.1925%** / 20.9923% | 18.5328% / **21.8417%** / 22.0704% |
> | 0.0025 | **15.8028%** / **12.7485%** / 11.4984% | 16.6033% / **15.3848%** / 13.6986% |
> | 0.0018 | 11.5626% / **9.2568%** / 7.5722% | 4.9201% / **4.4605%** / 4.8086% |
>
> Every n_points = 10 column still reproduces its record (bold, ≤ 0.035%
> on 0.7.2), so the sweep is anchored rather than a new measurement.
>
> 1. **The metric is sampler-fragile on *both* images, and worse on the
>    old one.** The 10-point radial L2 spans 34% of its own value on
>    0.7.2's gated rung and 43% on its fine rung, versus 21% and 10% on
>    0.11. This is a property of a 10-sample radial estimator, not of the
>    upgrade.
> 2. **The 15% band already fails on 0.7.2 at n_points = 8** — 15.8028%,
>    on the image the record was taken on. The gate's 1.18× headroom is
>    *inside* the statistic's own sampler spread, so it was passing on a
>    sampler choice rather than on a margin. That is the more important
>    finding here than anything version-specific.
> 3. **The outlier survives the control.** At fixed n_points the 0.11
>    gated rung is worse at every count (8: 15.80 → 16.60; 10: 12.75 →
>    15.38; 20: 11.50 → 13.70), and no n_points brings it near the 0.11
>    fit's 8.6%. Candidate (b) is therefore **excluded** as the *cause* of
>    the outlier, alongside partitioning and mesh instability; candidate
>    (a) — a real non-monotonicity near h = 0.0025 — is what remains.
>
> **Still nothing touched** — no band, no assertion, no record. But the
> disposal question has changed shape: it is no longer only "may this
> record move", it is "is a 10-point radial L2 a gateable statistic at
> all". A band 1.18× a number that swings 34% under its own sampler is
> not measuring the discretization. The review owns that call; a
> defensible fix (raise `n_points`, or gate a sampler-independent norm)
> is a `MAG` chunk, not an `OPS-18` clause.
>
> **Ruling, 18:00 review 2026-08-22 — the gate is replaced, not
> re-banded.** "Loosen 15%" refused (standing rule; and 0.11 is the more
> accurate solver on this ladder, so a loosened band would record the
> wrong fact). "Chase the 0.11 non-monotonicity" refused as an `OPS-18`
> clause: the statistic it would chase swings 34% under its own sampler on
> the image that recorded it, so it cannot adjudicate a version bump either
> way. **`MAG-18`** is commissioned (§7; §9 item 1): an annulus-restricted
> domain L2 of `|B_h| − |B_ana|`, assembled not sampled, gated on a
> pre-registered rate ≥ 0.7 plus rank-independence and the natural-BC
> control, measured on 0.7.2 / `main` first; the 10-point number becomes
> reported-not-gated. `OPS-18` then re-measures leg 2 in that norm on 0.11
> (§9 item 4). **This entry stays open**: the h = 0.0025 non-monotonicity
> on 0.11 is observed and unexplained, and `MAG-18` does not claim to
> resolve it — it leaves only when someone explains or retires it with a
> commit.
>
> ---
>
> **Update, `MAG-18` executed 2026-08-22 (log
> `20260823T003518Z_MAG-18-full.log`, `7 passed` / 270.64 s / `-n 2`,
> 0.7.2 / `main`) — the ruling is implemented, and the symptom at the top
> of this entry can no longer fire.** `rel_error < 0.15` is gone from
> `test_straight_wire_b_field`; the number is printed, and reproduced
> under assertion at `n_points` 8 / 10 / 20 in
> `test_domain_l2_record`. So on 0.11 that test will now *pass* — the
> 15.3848% it used to fail on is still there, still unexplained, and this
> entry stays open for it, but a run hitting it will see a printed line
> rather than a red assertion. **Do not read the green as an explanation.**
> The gate is now `E_Ω` = 25.3787 / 10.7288 / **6.6708%** on the recorded
> ladder, rate **1.6842**, monotone, with the natural-BC control at
> 32.3117% vs 10.7288%.
>
> **Update, `OPS-18` step 3a attempt 7 (2026-08-23, 06:00 slot) — leg 2 is
> green on 0.11 and the entry still stays open.** On `attempt/OPS-18` at
> `44b5600`, real, `-n 2`, `20260823T111216Z_OPS-18-step3a-leg2-confirm.log`:
> **`11 passed, 4 skipped`** / 293.59 s / exit 0, against attempt 6's `1
> failed / 10 passed / 4 skipped`. `E_Ω` = 25.2868 / 10.6172 / 6.6458% on
> the recorded ladder, rate **1.6854**, monotone, natural-BC 32.315493% vs
> 10.617170% (ratio 0.3285). The `E_Ω` h = 0.0025 record is now written
> version-tagged as 1.061717e-01 at 147 235 cells and measures
> 1.0617170177e-01; the retired sampler control is keyed by image and
> reproduces the 0.11 triplet 16.603276 / 15.384842 / 13.698645% to
> ≤ 3.3e-06. **The 15.3848% non-monotonicity is exactly that middle
> number** — it is now recorded and asserted rather than failing, which is
> what "reported-not-gated" means. Still unexplained; this entry stays
> open until someone explains or retires it.

### `MAG-18` anchor (ii) is unreachable as pre-registered: the magnetostatic solve's own cross-width floor is ~1e-7, not 1e-10 (2026-08-22)

> **Not a failing test** — no assertion is red. This records a
> pre-registered done-when clause that measurement showed could not be met
> by any statistic, so the next reader does not spend a slot re-measuring
> it.
>
> **The clause.** `MAG-18` anchor (ii), PROJECT_PLAN §7 and §9 item 1: "the
> h = 0.0025 value at `-n 2` and `-n 4` agree to **1e-10 relative** — a
> reduced integral has no sampler; this is the control that the new
> statistic lacks the defect the old one had."
>
> **Measured** (`20260823T003327Z_MAG-18-record-probe.log`, `-n 2`, 31 s;
> `20260823T003406Z_MAG-18-record-n4.log`, `-n 4`, 26 s; same 145 884-cell
> mesh in both, `Status: 0`):
>
> | statistic | `-n 2` | `-n 4` | relative |
> |---|---|---|---|
> | `E_Ω` (new) | 1.0728835983e-01 | 1.0728836764e-01 | **7.28e-08** |
> | 10-point, n_points = 8 (retired) | 15.802788% | 15.802785% | 1.9e-07 |
>
> **Cause: the linear solve, not the statistic.** `MagnetostaticSolver`
> runs `ksp_type=preonly, pc_type=lu` — a *direct* factorization, whose
> pivot/elimination order follows the mesh partition, so the computed `A`
> itself differs at roundoff amplified by the gauge-penalty system's
> conditioning. The retired sampled statistic moves the same way on the
> same two runs, which is the discriminator: a defect of the *sampler*
> would not appear in an assembled integral, and this appears in both.
> ~1e-7 is therefore the solve's cross-width reproducibility floor and no
> functional of this field can read below it.
>
> **What it does and does not mean.** It does **not** revive the sampler
> objection: anchor (ii) existed to show `E_Ω` has no sample-count
> dependence, and it has none — the 34% swing the old statistic showed
> under `n_points` has no counterpart here. It **does** mean the 1e-10
> number was written without knowing the solver's floor.
>
> **Nothing was loosened in-slot.** `E_OMEGA_RECORD_BAND` is the
> separately pre-registered **record** band 1e-4, not a relaxed 1e-10.
> Re-registering (ii) at the measured floor (1e-6 would be 100× the
> observation and still 1e5× tighter than the record band) is a review
> decision; `MAG-18` stays 🟡 until it is made. A cheap alternative the
> review may prefer: assert cross-width agreement *directly* by running
> the record test at both widths in one harness invocation rather than
> against a hard-coded constant.
>
> **✅ RESOLVED 2026-08-23 (03:00 review) — (ii) re-registered at ≤ 1e-6
> relative**, 14× the measured 7.28e-08 and five orders below the 34%
> sampler swing it was commissioned to exclude; the logged `-n 2`/`-n 4`
> pair satisfies it and `MAG-18` is ✅ (PROJECT_PLAN §7). The
> pre-registration error was in the clause, not the solver. Entry kept
> for the floor figure: ~1e-7 cross-width on a direct-LU magnetostatic
> solve is now a *known* floor for any future rank-independence clause,
> and the 2026-08-23 run-to-run entry below puts the single-width floor
> at ~1e-9–1e-10.
>
> **The floor confirmed on 0.11 (2026-08-23, 19:30 slot).** The re-gate
> re-measured the same pair on the image `main` now boots: `-n 2`
> 1.0617170177e-01 vs `-n 4` 1.0617175341e-01, **4.86e-07 relative** —
> 6.7× the 0.7.2 observation, still inside the re-registered 1e-6, and
> the two same-width runs agree to 1.86e-08. So the floor is a property
> of the direct-LU-under-partition solve and not of one image, and the
> 1e-6 clause has ~2× headroom on 0.11, not 14×. A future clause tighter
> than 1e-6 on this fixture would be pre-registering against the solver
> again.

### ✅ RESOLVED 2026-08-23 (`OPS-18` step 3b) — `test_region_resolution_policy_refines_the_tagged_volumes_toward_cad` failed **only in the 0.11 image**: the uniform-sizing meshed volume moved 4.251e-04 relative against its `OPS-17` record (`OPS-18` step 2, 2026-08-22)

> **RESOLVED 2026-08-23, 15:00 implementer slot (`OPS-18` step 3b), by
> re-record under the class ruling (1\*)** — the disposition the entry
> below asked step 3 to make, made by comparison rather than argument.
> The image's gmsh moves three of the four uniform-sizing volumes;
> `UNIFORM_VOLUMES_RECORD` in `tests/mesh/test_mesh_tag_integrity.py` now
> carries the v0.11.0 values version-tagged beside the v0.7.2 ones —
> tag 1 1.191750413e-04 → **1.192257046e-04** (+4.251e-04 relative),
> tag 2 1.188402981e-04 → **1.185069486e-04** (−2.805e-03), tag 3
> 4.943767949e-04 **unmoved**, tag 4 1.143560787e-02 → **1.143589055e-02**
> (+2.472e-05). **The 1e-9 band is untouched**, as are the `GEO-17` sign
> and CAD-recovery gates, which stay green on their own digits (policy /
> uniform recovery 0.833417 / 0.755006 and 0.835563 / 0.750454, phantom
> 0.992751 / 0.983531). The identity the drift could have broken still
> closes exactly: the tagged-volume partition ratio is
> **1.000000000000** on both sizings and on the plain integrity mesh.
> Condition (b′) is met with room to spare — **every printed digit is
> identical across the two `-s` confirming runs of the slot**, run-to-run
> move 0.0 (`20260823T200533Z_OPS-18-step3b-confirm-run2.log`,
> `20260823T200550Z_OPS-18-step3b-confirm-run3.log`, both `7 passed,
> 4 skipped` / exit 0 / `-n 2`, both rank footers identical), against the
> red baseline `1 failed, 6 passed, 4 skipped` reproduced this same slot
> on the rebuilt image (`20260823T200356Z_OPS-18-step3b-confirm.log`,
> Status 1). Original entry follows.
>
> **Where this fires.** `tests/mesh/test_mesh_tag_integrity.py::test_region_resolution_policy_refines_the_tagged_volumes_toward_cad`,
> on the `attempt/OPS-18` worksite branch only. `main` boots 0.7.2 and is
> unaffected — this is not a failure on `main`, and no `main` run should ever
> see it.
>
> **Literal symptom** (`20260822T110624Z_OPS-18-step2-shim-runtime.log`,
> `1 failed, 6 passed, 4 skipped` in 15.85 s, `-n 2`, real build, both rank
> footers identical):
>
> ```
> AssertionError: uniform sizing moved tag 1 (coil_1) by 4.251e-04 against its
> OPS-17 record: 1.191750413e-04 -> 1.192257046e-04 m^3
> ```
>
> **Verified at** `cc431c9` + the step-2 shim, i.e. the first commit at which
> `io/mesh.py` imports under 0.11 at all — the `gmshio` collect error masked
> every runtime number before it, so this could not have been observed earlier.
>
> **Cause: the image's gmsh, not the migration.** The failing quantity is a
> *meshed volume* of a fixed CAD region under fixed sizing — a mesh-generator
> output, not a solved one. The 0.7.2 → 0.11 image change carries a new gmsh
> along with it, and the §9 item-3 trap clause anticipates exactly this class
> ("the new image carries a new gmsh — a moved *cell count* with identities
> intact is re-recorded with a note; a moved gated *physics* number is a
> finding"). The three identity-shaped assertions in the same file — tag
> integrity and the region-resolution policy pair — **pass unchanged**, so the
> tagging and the sizing policy are intact; only the record's last digits moved.
> The drift is 4.3e-04 relative, four orders below any gated physics band.
>
> **Not diagnosed further, and deliberately not fixed here.** `OPS-18` step 2's
> done-when is collect-level, and the re-record/finding disposition belongs to
> **step 3**, which owns §5.3's environment table and every gated band. No
> assertion, band or record was touched by step 2 — the record moving is
> evidence about the image, and re-recording it before the re-gate leg has run
> would spend the trap clause's discrimination for nothing.
>
> **For step 3:** this is the first observed instance of the predicted gmsh
> drift and it is in the *re-record* category on its face. Expect siblings in
> other volume/cell-count records; a gated *physics* number moving is the
> different animal the clause stops on.

### ✅ FIXED 2026-08-19 (`OPS-22`) — the magnetostatic loop-drive fixtures were complex-hostile: `ufl.max_value` / `<=` geometry predicates in the current-density callable (`OPS-17` leg (b2), 2026-08-19)

> **FIXED 2026-08-19, 04:30 implementer slot (`OPS-22` step 1).** All three
> files repaired; nothing marked `@real_only`. The complex build now runs
> `test_circular_loop.py`, `test_helmholtz_magnitude.py` and
> `test_helmholtz_v2.py` as one command — **5 passed in 412.12 s, exit 0**,
> both ranks identical (`20260819T094710Z_OPS-22-step1-complex-all.log`) —
> and the printed digits equal the real-mode record to the last figure
> (loop relL2 7.0658% / max 13.8212%; Helmholtz centre 0.728%, mean 0.644%,
> CV 0.1602%). Real mode is unmoved: identical digits in
> `20260819T093105Z` (before), `20260819T093529Z` (after the predicate fix)
> and `20260819T095414Z` (after the real-part fix, 5 passed / 199.91 s).
> The 5 tests are unblocked for `OPS-17` leg (b2).
>
> **The fix had two layers, and the second was not predicted here.**
> (1) As diagnosed: `ufl.max_value(rho, 1e-12)` → `ufl.sqrt(x²+y²+1e-24)`,
> and `(...) <= a²` → `ufl.le(ufl.real(...), a²)`. (2) With the form
> compiling, the complex run reached the *assertions* and failed at
> `ValueError: Unknown format code '%' for object of type 'complex'`:
> `evaluate_vector_field_parallel` returns the complex scalar type even for
> a real-valued magnetostatic solution. Both comparing tests now assert
> `max|Im B_z| ≤ 1e-12·max|B_z|` and compare on `np.real` (a no-op in real
> mode). **`OPS-20` should expect the same second layer** once its
> predicate is fixed, as should
> `examples/magnetostatics/02_circular_loop.py:173` and
> `04_helmholtz_analytic_comparison.py:79`, which still carry the idiom and
> are unexercised in complex mode (follow-up, not done in this slot).
>
> The **poisoned-stub trap** documented below stands unchanged and is
> independently useful; the sweep was clean before and after this work.
>
> *(Diagnosis, retained as the record of how this was found:)*
> **CAUSE DIAGNOSED 2026-08-19, 22:30 slot (attempt 2).** The heading below
> originally read "cannot JIT-compile one form … cause not diagnosed". Two
> `--tb=long` runs on a **verified-stub-free** cache localized it, and the
> repo already half-knew the answer. Both failure modes come from the same
> place — the **load form `L`** built at `src/fem_em_solver/core/solvers.py:385`
> (`LinearProblem(a, L, …)`) from the test's `current_density` callable, which
> encodes "inside the wire" with ordering comparisons that UFL forbids on
> complex-typed operands:
>
> ```python
> in_wire_1 = ((rho - MAJOR_RADIUS) ** 2 + (x[2] - z1) ** 2) <= MINOR_RADIUS**2   # ordering
> rho_safe  = ufl.max_value(rho, 1e-12)                                            # max on complex
> ```
> (`tests/validation/test_helmholtz_magnitude.py:83–87`, same shape at
> `test_circular_loop.py:54` and `test_helmholtz_v2.py:46`.)
>
> **Two distinct symptoms, one cause.** Which one you see depends on whether
> UFL's comparison checker catches it before FFCx starts:
>
> | file | symptom | cost |
> |---|---|---|
> | `test_helmholtz_magnitude.py` | `ComplexComparisonError: Ordering undefined for complex values.` (`ufl/algorithms/comparison_checker.py:49`) — raised in UFL, **before** compilation; the form repr shows `Conditional(OrCondition(LE(Sum(Power(…SpatialCoordinate…)))))` | **13.10 s**, then the ~300 s non-collective exit hang (3b-xiii family) |
> | `test_circular_loop.py` | passes the checker, then `RuntimeError: Failed just-in-time compilation of form: Compilation failed on root node.` — the compiler's own message is swallowed by FFCx | **113.38 s**, nearly all in the doomed compile |
>
> **The codebase already carries the workaround** and its rationale, in
> comments written by earlier chunks: regularise *inside* the `sqrt` instead of
> with `ufl.max_value` — see `tests/validation/test_dodd_deeds_impedance.py:237–239`,
> `test_port_reaction_impedance.py:200–202`, `tests/mesh/test_two_torus_conforming.py:164`,
> all of which say in so many words that "the magnetostatic loop fixture's
> `max_value` form does not compile here". Those files were made complex-safe;
> these three (plus `examples/magnetostatics/02_circular_loop.py:173` and
> `04_helmholtz_analytic_comparison.py:79`, unexercised in complex mode) were
> not. So this is **fixture debt, not a solver defect** — no `src/` magnetostatic
> path is implicated, and real mode is green throughout.
>
> **Same family as the `test_coil_phantom_magnetostatics` entry below** (`You
> can't compare complex numbers with max.`), whose "cause not diagnosed / the
> comparison most likely enters through a DolfinX/UFL helper" line is now
> **superseded**: it enters through the drive callable, exactly as here.
> `OPS-20`'s step-1 diagnostic should start from that hypothesis.

**Verified at `c612920`, 22:30 implementer slot** — `20260819T033938Z_OPS-17-step3g-helmholtz-magnitude-isolated.log`
(exit 124 at the 300 s ceiling, but the full `--tb=long` traceback and the
`1 failed … in 13.10s` footer print before the hang) and
`20260819T034936Z_OPS-17-step3g-circularloop-onaxis-clean.log` (**exit 1**,
115 s, `1 failed, 2 deselected in 113.38 s`, both ranks). The cache was swept
with `find /root/.cache/fenics -name '*.c' -size 0` and the one stub deleted
**before** these runs, so neither reading is a stub artifact.

*(Prior text of this entry, from attempt 1 on 2026-08-19 at `e2295bf`, three
independent runs; the poisoned-stub trap below stands unchanged and is
independently useful.)*
Real mode is unaffected — these files are green in the real-mode leg (a) sweep.

| | |
|---|---|
| **Tests** | `tests/validation/test_circular_loop.py::TestCircularLoop::test_circular_loop_on_axis` (FAILED) and `::test_circular_loop_field_symmetry` (never returns; takes the window to `exit 124`); `tests/validation/test_helmholtz_magnitude.py::test_helmholtz_centre_field_magnitude` (FAILED, `ComplexComparisonError`); `tests/validation/test_helmholtz_v2.py::test_helmholtz_field_uniformity_two_torus` (never returns — it carries the same `max_value` idiom and was the test hanging batch A). **5 tests**, complex build only |
| **Symptom** | `RuntimeError: Failed just-in-time compilation of form: Compilation failed on root node.` on rank 0 (`dolfinx/jit.py:91`); rank 1 raises the same `RuntimeError` with `JIT compilation timed out, probably due to a failed previous compile. Try cleaning cache (e.g. remove /root/.cache/fenics/libffcx_forms_3b01242391fa699f45d97f502c916e1a1c96c1e6.c)`. Teardown then emits `AttributeError: 'LinearProblem' object has no attribute '_solver'` (a secondary, not the fault). The call is **109.07 s** — nearly all of it in the failing compile. |
| **Evidence it is not a cache artifact** | Three runs, same commit. (i) In a mixed batch: FAILED at 31%, then the next test in the file hung to `exit 124` (`20260819T021242Z_OPS-17-step3f-complex-validation-subset2.log`, 481 s). (ii) Isolated, `--tb=long`: `1 failed, 2 deselected in 109.58 s` (`20260819T022120Z_OPS-17-step3f-complex-circularloop-onaxis.log`, exit 1). (iii) **After deleting every 0-byte stub in `/root/.cache/fenics`**, the same test FAILED again and **re-created the identical hash `3b01242…` at 0 bytes** (`20260819T022356Z_OPS-17-step3f-complex-circularloop-repaired.log`, exit 124, 421 s). A cache artifact does not survive its own repair, and does not regenerate the same hash at zero length. |
| **Cause** | ~~Not diagnosed.~~ **Diagnosed 2026-08-19 attempt 2 — see the block at the top of this entry.** The complex-hostile geometry predicate (`ufl.max_value` / `<=`) in the fixture's `current_density` callable. FFCx still swallows the root-node compiler message for `test_circular_loop`, so the *compiler's* words remain unrecovered; the offending construct does not. |
| **Second-order damage — the poisoned-stub trap** | A 0-byte stub left by any killed compile makes **every later run that needs that form** fail this way rather than recompiling, and the message blames the cache, not the form. A stale stub from **2026-08-18 14:02** (leg (b1) attempt 2's era) was still sitting in the cache when this slot started — i.e. this has been silently mis-attributed before. Sweep with `find /root/.cache/fenics -name '*.c' -size 0` before trusting any "JIT compilation timed out" message; that check is cheap and should precede any cache-clear. Note this cuts **against** reflexively clearing `~/.cache/fenics`: the targeted delete is the diagnostic, and here it *exonerated* the cache. |
| **Not** | Not the `>12× real` cost rule (withdrawn 2026-08-18) and not a solve cost — 109 s of compile, 0 s of setup. Not a physics or tolerance failure: no assertion is ever reached. Not a real-mode issue. |
| **Fix** | Not attempted — `OPS-17` is a bookkeeping leg and does not touch `tests/`. The fix is mechanical and already precedented in this repo: regularise inside the `sqrt` (`test_dodd_deeds_impedance.py:237`, `test_port_reaction_impedance.py:200`) instead of `ufl.max_value`, and express the wire predicate without an ordering comparison on complex-typed operands. Whoever takes it should decide per file whether the complex build needs the magnetostatic path at all — `@real_only` is a legitimate, cheaper disposition (same call `OPS-20` faces). Do **not** conclude the forms are un-compilable: the sibling files prove the same physics compiles once the predicate is complex-safe. |
| **Resolves with** | **`OPS-22`** (commissioned 2026-08-19 03:00 review; §7 entry with the full rubric): per-file fix-or-mark of the three fixtures, real-mode records asserted unmoved, complex run completing with a footer. `OPS-20` stays a separate chunk (same family, different file) and its step 1 is re-pointed at the drive callable. Blocks 5 tests in `OPS-17` leg (b2) from being observed in a completed leg until it lands. |

### 1. ✅ RETIRED 2026-07-31 — stale test double, `DummyMagnetostaticSolver`

The two phantom tests
(`tests/materials/test_phantom_material_model.py::test_phantom_material_assignment_and_time_harmonic_pipeline_wiring`,
`tests/post/test_phantom_field_metrics.py::test_phantom_field_metrics_and_exports_are_finite`)
failed with `AttributeError: 'DummyMagnetostaticSolver' object has no attribute
'last_solve_diagnostics'`. No fix ever landed: `TH-1` steps 1–3 deleted the
`last_solve_diagnostics` read from the time-harmonic path, so the failing code
path went away under the entry.

Re-verified through the harness at `424faed`:
`20260731T170152Z_KI-1-retire-gate.log` — complex build, `FEM_EM_REQUIRE_COMPLEX=1`,
`-n 2`, **10 passed in 4.6 s**; and `20260731T170140Z_KI-1-real-mode-iomatpost.log`
— real build, the CI `validation` job's exact command with the `--deselect`s
removed, **15 passed, 2 skipped in 0.5 s**. Both `--deselect`s are gone from the
`validation` job and both files are now listed in `validation-complex`, which is
where the two `@complex_only` tests actually execute. The test-side
`ComplexWarning` casts were fixed in the same commit; the remaining one at
`post/phantom_fields.py:88` was recorded under `POST-1` in `PROJECT_PLAN.md` §7
and is **fixed as of 2026-08-04** (`POST-3` step 4 — both cast sites removed,
statistics taken on the phasor magnitude, gated by
`tests/post/test_phantom_phasor_semantics.py`). `POST-1` stays ⚠️ for the
interface-guardrail machinery, which is unrelated to the cast.

The heading is kept (rather than deleted with the entries renumbered) so the
numbering of entries 2–6 stays stable — several commits and CI comments refer to
them by number.

### 2. ~~Residual-trend classifier disagrees with its test~~ — RESOLVED 2026-08-08 (`OPS-12`)

Both failures were on the **code** side, and they were two different defects,
not one:

1. `classify_residual_trend()` carried undocumented thresholds
   (`f >= 0.75` ⇒ `mostly-decreasing`, `f >= 0.5` ⇒ `mixed`, where `f` is the
   fraction of non-increasing steps). Nothing — not the docstring, not the
   label names — licensed that asymmetry: it gave increases a band of width
   0.5 and decreases 0.25, so a history that decreased on two of every three
   iterations was reported `mixed`, and **no history of four or fewer samples
   could reach `mostly-decreasing` at all**. The labels now partition by the
   sign of `f - 0.5`, which is what their names mean, and the docstring states
   the table. The test's `[1.0, 0.4, 0.45, 0.1] -> mostly-decreasing`
   (`f = 2/3`) was right and is unchanged.
2. The second failure was never `assert diagnostics is not None` — the
   recorded symptom was wrong. It was `assert diagnostics.converged`, with
   `converged_reason = -3` (`KSP_DIVERGED_ITS`): the fixture asked for
   gmres+jacobi at `ksp_rtol = 1e-8` with `ksp_max_it = 300`, and that solve
   needs **1409** iterations on the 1405-cell fixture. The cap was
   under-resourced; the assertion was not wrong and was not touched.

A third defect fell out of the diagnosis: the time-harmonic path never called
`ksp.setConvergenceHistory()` (the magnetostatic path always has), so
`residual_history` came back **empty** and `residual_trend` was permanently
`unavailable` — the classifier was unreachable in production and the test's
membership assertion passed vacuously. Armed, and the test now gates
`len(history) == iterations + 1` and `trend == classify_residual_trend(history)`.

| | |
|---|---|
| **Fixed in** | `OPS-12`, 2026-08-08 — `src/fem_em_solver/core/solvers.py`, `src/fem_em_solver/core/time_harmonic.py`, `tests/solver/test_convergence_diagnostics.py` |
| **Gate** | 18 passed at `-n 2` under the complex build in 0.93 s (`20260808T050622Z_OPS-12-gate-final.log`); the classifier identity is asserted with `==` on an 11-row parameterized family spanning both sides of `f = 0.5` and of the retired `f = 0.75`, with negative controls |
| **CI** | `tests/solver/test_convergence_diagnostics.py` is now in the `validation-complex` job, which is what this entry's old status line named as its exit condition |

### 3. Port tests assert a non-zero power wave where the placeholder's fake makes it exactly zero (re-dated 2026-08-28 by `OPS-28`)

> **Re-dated 2026-08-28 (`OPS-28`, 22:30 slot) — still open, and the
> *reason* is confirmed while the entry's old one-line statement was
> imprecise for one of the two names.** With the `_DummyComm` double
> repaired, `…::test_port_orientation_flip_changes_off_diagonal_sparameter_sign`
> reaches its S-matrix assertion for the first time since `OPS-14` and dies
> at `tests/ports/test_port_orientation_sensitivity.py:115`,
> `assert aligned_s21.real > 0.0` → `assert np.float64(0.0) > 0.0`. On that
> fixture the **diagonal is not zero at all** — the log prints
> `S11 = 9.047e-01 − 1.289e-02j, S22 = 9.047e-01 − 1.289e-02j` — it is the
> **off-diagonal** that vanishes, because the placeholder gives the
> *undriven* port `V = 5.000000e-02 V`, `I = 1.000000e-03 A` at
> `Z₀ = 50 Ω`, i.e. `V = Z₀I` exactly, so `b = (V − Z₀I)/(2√Z₀) = 0` and
> `S21 = S12 = 0` identically. Same mechanism as the 3-port diagonal case
> below, different matrix entry, so the entry's title is corrected above
> and both names stay filed. `OPS-28`'s scope was the double only — no
> assertion moved, no `sparameters.py` edit, `git show -- src/` empty.
> Log: `20260828T033055Z_OPS-28-gate.log` (`2 failed, 15 passed in 0.79s`,
> Status 1, elapsed 2 s, `-n 2`, real build, smoke). Verified at the
> `OPS-28` commit. Disposition unchanged: `PORT-0`/`PORT-1` own it.

| | |
|---|---|
| **Tests** | `tests/ports/test_sparameter_assembly.py::test_n_port_sweep_assembles_finite_matrix_with_expected_shape` (zero **diagonal**, 3-port fake)<br>`tests/ports/test_port_orientation_sensitivity.py::test_port_orientation_flip_changes_off_diagonal_sparameter_sign` (zero **off-diagonal**, 2-port fake — measured 2026-08-28, see the note above) |
| **Symptom** | `assert np.all(np.abs(diagonal) > 0.0)` fails on `array([0.+0.j, 0.+0.j, 0.+0.j])`; on the orientation test, `assert aligned_s21.real > 0.0` fails on `np.float64(0.0)` |
| **Cause** | The fakes set `current = voltage / port.z0_ohm` — a perfectly matched port. The power wave `b = (V − Z₀I)/(2√Z₀)` is then `0` exactly, so the corresponding S entry is *legitimately* zero and the assertion cannot hold: on the 3-port fake that is every diagonal term, on the 2-port orientation fake it is the off-diagonal terms (the undriven port is the matched one there). |
| **Fix** | **Deliberately not fixed.** These exercise the placeholder coupling model's arithmetic (see `PORT-0`). Repairing them means tuning assertions to match a heuristic that `PORT-1` deletes. Resolve them there. |
| **Verified pre-existing at** | `53f6428` and earlier |
| **Progress 2026-08-04** | `PORT-1` step 3b-ii, the step that would replace these fakes with a driven gap port, was **attempted and parked** (`attempt/PORT-1-step3bii-20260804T141200Z`). The drive works — reciprocity `2.2840e-04`, undriven port open at `2.32e-03` — but `Im Z₁₂` is +72.12% off `ωM₁₂`, traced to the gap box's 1.83×-oversized cross-section rather than to the solve. These two tests stay red and unchanged; see PROJECT_PLAN §7 `PORT-1` step 3b-ii for the measurement and the ranked successor. |
| **Progress 2026-08-04 (2)** | Step 3b-iii tested that diagnosis and **refuted it** (parked on `attempt/PORT-1-step3biii-20260804T173000Z`; logs `20260804T170301Z_PORT-1-step3biii-costprobe.log`, `20260804T170439Z_PORT-1-step3biii-sweep-o5e4.log`). Shrinking only the transverse overhang gives `Im Z₁₂/ωM₁₂` = `+1.7210` (fringe 0.4546), `−0.2391` (0.3509), `+0.3317` (0.2739) — non-monotone and **sign-changing**, so a box-volume average is not a port voltage at any overhang. The shadow-restricted average is stable at `0.687–0.814 ×` across the same three geometries. The replacement route is now the facet-integral voltage (§7 step 3b-v on 3b-iv's tags); these two tests stay red and unchanged. |
| **Progress 2026-08-06** | Step 3b-v ran that facet-integral route and it is **also excluded** (parked on `attempt/PORT-1-step3bv-20260806T004500Z`; log `20260806T003559Z_PORT-1-step3bv-gate.log`, 3 failed / 7 passed, 67.6 s at `-n 2` — no hang, 3b-iv's hoisted `create_entity_permutations()` held). `V = −⟨E·ŷ⟩_{terminal discs, gap side}·L` gives `\|Im Z₁₂\|/ωM₁₂` = **4.845** (+384.54%) against the full-box `0.332` and tube-shadow `0.763 / 0.814` **on the same solve**, with reciprocity degrading `1.15e-4 → 1.79e-2`. Cause: `E·ŷ` on a terminal is the surface-charge-dominated *normal* component (measured gap/wire jump ratio 2.9e-5–4.6e-5), so a two-endpoint trapezoid samples exactly where the integrand peaks. Both the box family and the terminal-facet route are now excluded by measurement; a successor must integrate the *tangential* component along the whole gap path. `MUTUAL_TOLERANCE` unmoved. These two tests stay red and unchanged. |
| **Progress 2026-08-06 (2)** | Step 3b-vi ran the tangential path integral — `V = −∫E·t̂ dl` along the torus centreline arc through the gap, Gauss–Legendre nodes strictly interior to the arc, sampled via `post.evaluation.evaluate_vector_field_parallel` — and it is **unresolved, not refuted** (parked on `attempt/PORT-1-step3bvi-20260806T094500Z`, `ee5f0cb`; logs `20260806T093603Z_PORT-1-step3bvi-gate-n2.log` and `20260806T093808Z_PORT-1-step3bvi-quadrature-sweep-n2.log`, 4 failed / 4 passed, 136.13 s at `-n 2`). Value, off one solve: path **0.468933 / 0.499728** × ωM₁₂ against facet `4.802 / 4.889`, full-box `0.332`, tube-shadow `0.763 / 0.814` — a *third* distinct answer, below the shadow family, at −51.6% with reciprocity `6.3e-2`. But the plan's own quadrature precondition fails first: the proposed `(33, 65)` node pair disagrees by `1.07e-1`, and the sequence extended to 4097 nodes converges only at `O(1/n)` to a `~1e-3` plateau — because N1curl makes only the *facet*-tangential component continuous, the arc's tangent is not facet-tangential, and with `h_wire = 2.5e-3` against arc length `a·g = 1.2e-2` only ~5 cells span the path. Four estimator families now give four answers spanning a factor 15 on one solved field. The successor is **arc refinement, not more quadrature nodes**; if `~0.48` survives it, the family question is closed negatively and the suspects become finite-σ terminal penetration or the `ωM₁₂` reference. `MUTUAL_TOLERANCE` unmoved. These two tests stay red and unchanged. |
| **Progress 2026-08-06 (3)** | Step 3b-vii ran that arc refinement and **the family question closes negatively** (parked on `attempt/PORT-1-step3bvii-20260806T170000Z`, `bc8c04e`; probe `20260806T170559Z_PORT-1-step3bvii-probe.log`, gate `20260806T170835Z_PORT-1-step3bvii-gate-n2.log`, 2 failed / 10 passed, 165 s at `-n 2`). A coordinate-defined `MathEval`+`Threshold` size field on the fragmented model put `h_gap = 3e-4` — 40 cells across `a·g` — in a tube around each gap arc: 124 753 → 178 055 cells (1.427×), gap-tagged cells 1569 → 24 430 per port. It fixed the discretization and not the answer. Reciprocity **6.3e-2 → 3.8823e-3** (inside the 1e-2 band for the first time) and the fixed-order quadrature residual improved ~3×, but (129, 257) still disagree by `1.1444e-2` and the converged path value is **0.493653 / 0.491744** × ωM₁₂ (0.4808 at 4097 nodes) against 3b-vi's 0.468933 / 0.499728 — a discretization-level shift, `Im Z₁₂` at −50.73%. The built-in control holds: facet `5.165/5.169`, box `0.3496/0.3492`, shadow `0.8566/0.8386` all moved only a few % off the refined solve, so the solve did not change underneath the estimator. Four sampling geometries, four answers, and the ~0.48 survives refinement: **the deficit is not the sampling geometry**. Remaining suspects are finite-σ terminal penetration at `δ = 1.125 r_wire` and the filamentary `ωM₁₂` reference itself — a review's adjudication. `MUTUAL_TOLERANCE` unmoved. These two tests stay red and unchanged. |
| **Progress 2026-08-07** | Step 3b-viii audited the **`ωM₁₂` reference** — the first of the two remaining suspects — in closed form, no solve and no mesh (`tests/validation/test_mutual_inductance_reference.py`, on `main` and green; log `20260807T020314Z_PORT-1-step3bviii-gate.log`, 7 passed in 0.43 s at `-n 1`, smoke). **The suspect is retired.** (i) The vector-potential route the gates use and an independent elliptic-integral reimplementation (`M = μ₀√(ab)[(2/k − k)K − (2/k)E]`, `m = k²`) agree to **1.5e-15** at the fixture's `d`, and to ≤ 7.5e-14 across `d/4 … 4d`; `ω·M` reproduces the logged `1.241755 Ω` to 3.1e-7. A vacuity control confirms the identity has teeth — feeding SciPy the modulus where the parameter belongs moves `M` by **140%**, eleven orders above the 1e-9 gate. (ii) The finite-cross-section correction at `r/a = 0.125`, the filament kernel averaged over both minor discs at uniform current density (Gauss–Legendre × periodic trapezoid, converged to 6.7e-16 between orders), is **`M_tube/M_fil = 1.004809992`, i.e. +0.481%** — and it has the *wrong sign* to help, since a larger reference makes the deficit slightly worse (0.4937 → 0.4914 × ωM). A 0.5% correction cannot produce a factor 2, consistent with step 2's field-level agreement at −9.35%. **The reference is exonerated; finite-σ terminal penetration (step 3b-ix) is now the only named suspect.** `MUTUAL_TOLERANCE` unmoved. These two tests stay red and unchanged. |
| **Progress 2026-08-07 (2)** | Step 3b-ix closed the loop and **found the cause of the factor 2 — it is not physics, it is the estimator's integration limits.** Parked on `attempt/PORT-1-step3bix-20260807T050000Z` (`6caec85`); log `20260807T050654Z_PORT-1-step3bix-gate-n2.log` on that branch, 178 055 cells, `-n 2`, 227 s. Faraday on the closed centreline circle, tiled into four segments each verified against the DG0 material indicator before any solve (0 misassigned of 5392 nodes), gives on the undriven port: `V_gap = 0.493653 / 0.491744`, **`V_buried = 0.399972 / 0.402239`**, `V_wire = 0.002394 / 0.002316`, **sum = 0.896019 / 0.896299 × ωM₁₂** — inside the pre-set `1 ± 0.15` band and matching step 2's independent reaction route (−9.35%, of which −9.36% is the PEC box at padding 0.08). **Finite-σ terminal penetration is retired**: at `σ × {1, 2, 4}` (δ/r_wire 1.125 → 0.796 → 0.563) `V_wire/ωM` = 0.002394 → 0.001856 → 0.000727 — the signature is real and 200× too small to matter — while `V_gap/ωM` = 0.493653 → 0.490837 → 0.485059, i.e. it *falls*. The missing half is the **buried** dielectric: `GAP_BURIAL` puts the gap region out to `±arcsin(half_y/a) = ±0.175335` rad while `_gap_arc_quadrature` integrates only the nominal `±GAP_ANGLE/2 = ±0.15`, so 1.013 mm of arc per side — 0.8% of the loop's length, and exactly where the terminal fields live — carries 45% of its EMF. **Terminal to terminal the gap-port voltage is 0.8936 × ωM₁₂, not 0.4937.** Both suspects the 2026-08-06 review named are now dead. Successor **step 3b-x** (correct the limits off the port facet tags, then a box-padding sweep — the residual −10.6% is the PEC box's, and a `MUTUAL_TOLERANCE` edit is *not* the remedy) is written into PROJECT_PLAN §7 for a review to scope. `MUTUAL_TOLERANCE` unmoved at 0.10; nothing under `src/` changed. These two tests stay red and unchanged. |
| **Progress 2026-08-07 (3)** | Step 3b-xii ran the pre-decided box discriminator and it lands on **disposition (ii): the residual is a real estimator bias, not the PEC truncation box.** Parked on `attempt/PORT-1-step3bxii-20260807T170000Z` (`87bf35d`, carrying the full 3b-ix → 3b-x-b lineage); probe `20260807T170143Z_PORT-1-step3bxii-probe.log` (59 s), gate `20260807T170430Z_PORT-1-step3bxii-disc-n2.log` (`-n 2`, standard, **353 s**, 5 passed + the discriminator red). The gapped fixture was rebuilt at `air_padding = 0.10` — nothing else moved, and the same `_solve_gap_ports` the 0.08 gates use — at 194 985 cells (1.0951× the 178 055 at 0.08, under the plan's 230 000 stop rule; padding 0.08 re-meshed at **exactly** 178 055, so the fixture identity holds). All four route values: at padding 0.08 estimator `0.894543 / 0.894022`, control `0.922423`, deviation `−3.0224e-02`; at padding 0.10 estimator **`0.924103 / 0.923075`**, control **`0.952868`**, deviations **`−3.0188e-02 / −3.1267e-02`**. The box moved the estimator **+2.956 pp** and the control **+3.045 pp** — i.e. it moved *both routes together* — leaving their difference at 3.02–3.13% against the pre-decided 2.5% threshold, a move of **−0.104 pp**: the wrong direction, and 5× smaller than the 0.5 pp (i) required. That the box itself behaved normally is corroborated independently: this fixture's σ = 0 control reads `0.952868` at padding 0.10 against 3b-xi's *ungapped* reaction route at `0.949744`, and `0.922423` against `0.919676` at 0.08 — a stable `+0.27/+0.31` pp gapped/ungapped offset under enlargement. Negative control, recomputed against this box's own reference: the uncorrected wedge-only estimator gives ratio `0.5181`, deviation `−0.4819`, 15× the threshold. **`REACTION_CONSISTENCY_TOLERANCE` stays at 0.03** — the review's authorized re-size to 0.05 was conditional on convergence, which did not happen, so it is not taken, and nothing under `src/` changed. What this leaves open, for a review: the corrected terminal-to-terminal estimator and the σ = 0 reaction control differ by ~3% *for a reason that is not truncation and not the wedge limits* — the two problems differ in that the production loop is gapped and σ = 800 S/m while the control's is closed and lossless, and that difference is now the named suspect rather than an assumed nuisance. `MUTUAL_TOLERANCE` unmoved at 0.10. These two tests stay red and unchanged. |
| **Scoped 2026-08-07 (03:00 review)** | Both successors are now full §7 plans and queued (§9 items 1–2). **3b-x**: correct `_gap_arc_quadrature` to terminal-to-terminal limits read off the port facet tags, gate the corrected estimator against the *same-fixture* reaction-route `Im Z₁₂` (≤ 3%; the ωM₁₂ comparison stays printed and tracked here, expected ~−10.6%), delete the σ-monotonicity test whose premise 3b-ix refuted, and land the branch. **3b-xi**: padding sweep {0.08, 0.10, 0.12} on the ungapped fixture — if the deficit does not shrink monotonically with padding, the PEC-box attribution dies and this entry escalates to the weekly review. `MUTUAL_TOLERANCE` untouched by either. |
| **Progress 2026-08-08** | Step 3b-xiii ran that σ ladder and lands on **disposition (mixed) — but the informative result is that the experiment's premise is disproved, not that the bands were missed.** Parked on `attempt/PORT-1-step3bxiii-20260808T005500Z` (`82bfb40`, carrying the full 3b-ix → 3b-xii lineage); log `20260808T004346Z_PORT-1-step3bxiii-ladder-b-n2.log` (`-n 2`, standard, **344.6 s**, 20 passed + the known consistency gate red). Fixture identity first and it byte-reproduces the branch's record **exactly** — estimator `0.894543 / 0.894022`, control(σ = 0) `0.922423`, deviation `−3.0224e-02` — so nothing geometric moved. The ladder, σ on the wire ∪ gap-box footprints of both loops through the same DG0 material map the production solves use: `control(σ=0) = 0.922423`, `control(σ=200) = 0.496614`, `control(σ=800) = 0.107556` × ωM₁₂. It is **monotone decreasing** (the new ordering gate — the intermediate rung must lie between the endpoints, or the ladder measures noise rather than σ — passes) but lands nowhere near either 0.7 pp band: the σ = 800 rung sits **78.7 pp** from the estimator and **81.5 pp** from control(σ = 0), on a 2.81 pp endpoint spread. **Why:** a *closed* lossy loop is a shorted turn. The induced circulating current reaches `|I_cond/I′| = 0.412` at σ = 200 and **0.865** at σ = 800, and its back-field cancels most of the mutual EMF the reaction integral reads. σ and closed-vs-gapped are therefore **not separable on this control** — the knob the review believed independent is confounded with the very difference it was meant to isolate. The ~3% deviation is **untouched**: the loss-vs-gap question stays open and now needs a *gapped* control (the production loop driven at σ → 0), not a lossy closed one; that escalation is the weekly review's. **Not tuned:** `REACTION_CONSISTENCY_TOLERANCE` stays 0.03, nothing re-pointed, `MUTUAL_TOLERANCE` unmoved at 0.10. One `src/` change, unrelated to `PORT-1` and parked with the branch: `_validate_material_map_tags` tested rank-local `cell_tags.values`, so a material map over the two 1 mm gap boxes — globally valid — raised on one rank of two while the other entered the solve and hung in the first collective until the ceiling (`20260808T003238Z_PORT-1-step3bxiii-ladder-n2.log`: 16 errors, a 246 s session costing 601 s). The tag set is now reduced with `mesh.comm.allgather`. These two tests stay red and unchanged. |
| **Scoped 2026-08-07 (18:00 review)** | 3b-xii's disposition (ii) successor is now a full §7 plan and queued (§9 item 1): **step 3b-xiii**, the σ ladder {0, 200, 800} S/m on the closed-footprint control — nothing geometric moves, so σ becomes the only difference between the routes and the ~3% deviation gets an owner: loss or gap. Landing the parked branch (`attempt/PORT-1-step3bxii-20260807T170000Z`) is pre-authorized only under the (loss) disposition with the consistency bound unchanged at 0.03; the (gap) and (mixed) outcomes park and escalate to the weekly review. `attempt/PORT-1-step3bxb-…` was deleted this review as strictly superseded by content (+852/−3, verified — the ancestry test returns false only because the 12:00 run squashed the lineage). `MUTUAL_TOLERANCE` untouched regardless of outcome. |
| **Scoped 2026-08-08 (03:00 review)** | 3b-xiii's successor is now a full §7 plan and queued (§9 item 1): **step 3b-xiv**, the non-degenerate half of the same sweep — hold the **production gapped** fixture fixed and run its σ down {800, 200, 0}; a lossless *gapped* loop has no shorted-turn current, so σ and gap separate in this direction. **Measurement only: every disposition parks and reports** — branch landing and any gate re-pointing stay with the weekly review (2026-08-10), per 3b-xiii's escalation; this step exists so that review adjudicates with the ladder in hand. Branch hygiene: `attempt/PORT-1-step3bxii-20260807T170000Z` deleted this review (verified strict ancestor of the 3b-xiii branch); `attempt/PORT-1-step3bxiii-20260808T005500Z` (`82bfb40`) is the one live lineage. The rank-safety `_validate_material_map_tags` fix that rode along is separately scoped for `main` as `OPS-13`. |

### 4. ✅ RETIRED 2026-08-08 — coil+phantom B-field symmetry exceeded tolerance (`MAG-6` step 3)

**Resolution.** The estimator, not the physics, owned every number below. Both
sampled metrics in the test now go through **DG0** instead of CG1, and the
fixture is refined one rung to `resolution = 0.010` m; **no tolerance moved**
(`PHANTOM_SYMMETRY_REL_TOL = 0.35` and `PHANTOM_CENTERLINE_JUMP_RATIO_MAX =
0.60` are untouched, and the symmetry assertion was *tightened* — the
permissive `or max_abs_diff < …` escape is gone). Red first at `-n 1`
(`max_rel_diff=0.728`, `20260808T170126Z_MAG-6-step3-redbaseline-n1.log`);
green at `-n 1/2/4` with `max_rel_diff` = **0.323844 / 0.302661 / 0.308407**,
three-way spread **7.00%** against the pre-registered ≤ 10%, the `-n 1`
value byte-reproducing the step-2 record
(`20260808T170549Z_MAG-6-step3-gatefinal-n1.log`,
`…170529Z_…-n2.log`, `…170515Z_…-n4.log`).

**What this test now gates: discretisation symmetry, not phantom physics.**
`mu` is uniform, so the phantom is invisible to the solve and the exact
mismatch is 0 by construction. The fixture caveat below is preserved in the
test's module docstring; it was not "fixed", it was made explicit.

**Carried forward, not closed:** the centerline smoothness metric is *also*
CG1-owned and was re-pointed at DG0 in the same commit (CG1 read 0.705 and
0.732 on two identical `-n 4` runs against a 0.60 bound — rank-dependent and
not run-to-run reproducible; DG0 reads 0.227869 on the same solve). DG0 leaves
it passing at all three rank counts but still **88%** rank-scattered
(0.473300 / 0.268765 / 0.251746 at `-n 1/2/4`) — no rank-stability claim is
made for it, and sizing that second estimator is unscoped work for a review.
Related: the DG0 symmetry metric moved 6.8% between two identical `-n 2` runs
(meshing is not bit-reproducible), inside the spread gate but relevant to any
future tightening.

<details>
<summary>Historical record (the failing entry as it stood)</summary>


| | |
|---|---|
| **Test** | `tests/validation/test_coil_phantom_bfield_metrics.py::test_coil_phantom_bfield_metrics_are_finite_smooth_and_symmetric` |
| **Symptom** | **Rank-dependent** (`MAG-6` step 1, 2026-08-08). `max_rel_diff` reads **0.727907 at `-n 1` (fails)**, 0.240541 at `-n 2` (passes), 0.321468 at `-n 4` (passes), against the same `0.350` tolerance on the same 19 792-cell mesh. Historical record: 0.557 against 0.350, with `max_abs_diff=7.090e-07` against `6.523e-08`. |
| **Cause** | **The test's estimator, partially diagnosed** (`MAG-6` step 1). `curl A` for N1curl degree 1 is cell-wise constant, and the test interpolates it into **CG1** before sampling — a nodal value where the field jumps, supplied by whichever cell the partition happens to give. Sampling the same field at the same points through **DG0** is rank-stable (0.513648 / 0.534746 / 0.538472 at `-n 1/2/4`, 4.8% spread) where CG1 swings **3.03×**; the assembled `‖B‖_L2` moves 1.84% through CG1 but only **0.09%** through DG0, so the solve is not the suspect. What the ~0.53 rank-stable residual itself *is* was answered by step 2 (row below): **coarse-mesh discretisation**, falling at p ≈ 1.07 under refinement. Tracked as `MAG-6` (legacy A1). |
| **Do not read the green `-n 2` run as a fix** | The test passes in CI (which runs `-n 2`) for a non-physical reason. The rank-stable estimate 0.51–0.54 is close to the historical 0.557 and **above** the 0.350 tolerance; the record was not wrong, the estimator drifted into a lucky partition. Retiring this entry on the strength of a green `-n 2` run would bury a real finding. |
| **Ruled out** (`MAG-6` step 1) | **Boundary-mirror artifact:** on the rank-stable DG0 path, growing `air_padding` 1.5× moves the metric 0.534746 → 0.534772, a **0.005%** move against the "≥ 2× drop" the hypothesis predicted. **Gauge penalty:** the test solves at `gauge_penalty=1e-3`, 1000× below `DEFAULT_GAUGE_PENALTY = 1.0` and the source of the 9 `GaugeContaminationWarning`s per run, but re-solving at 1.0 moves `max_rel_diff` 0.240541 → 0.241846 (`-n 2`) and `‖B‖_L2` by 0.016% — `MAG-10`'s catastrophe needs degree 2, this fixture is degree 1. |
| **Fixture caveat** | `MagnetostaticProblem` is built with a **uniform** `mu = MU_0`, so the phantom is physically invisible — the test's off-centre-phantom asymmetry control moves only the mesh, and on the rank-stable path it *decreases* the metric (0.476684 vs 0.534746) instead of increasing it. Any symmetry claim on this fixture is a claim about discretisation, not about the phantom. |
| **Note** | The coil+phantom fixture uses a single global `setSize` and tight air padding — the same pattern that cost **20% error** on Helmholtz until `air_padding` was decoupled (see `docs/validation/helmholtz.md`). Kept for the air-box generalisation follow-up; it is *not* the owner of this metric. |
| **Verified pre-existing at** | `ce92e8c` and earlier (0.559 at `HEAD`, 0.557 after the gauge change — the gauge default is not the cause). Reproduced 2026-08-08 at `ed2d7e5` in the rank-dependent form above: `20260808T033401Z_MAG-6-step1-rankcheck.log`, `20260808T034013Z_MAG-6-step1-sampling.log`, `20260808T033802Z_MAG-6-step1-gauge.log`. Probe: `scripts/probes/mag6_step1_probe.py`. |
| **What the ~0.53 is** (`MAG-6` step 2, 2026-08-08) | **Coarse-mesh discretisation, measured.** On the fixture's own resolution knob with the probe grid frozen, the DG0 metric falls **monotonically**: 0.534746 (h = 0.015 m, 19 792 cells) → 0.312197 (h = 0.010, 55 784) → 0.255165 (h = 0.0075, 124 179) at `-n 2`, total ratio **2.0957**, observed rate **p = 1.067** — the O(h) that N1curl degree 1 allows. Independently at `-n 4`: 0.537750 → 0.304356 → 0.292706, ratio 1.8372. Rung 1 byte-reproduces step 1 (0.534746 at `-n 2`, 0.513648 at `-n 1`). **Caveat, load-bearing:** the finest rung is **void by its own rank control** — 14.71% spread between `-n 2` and `-n 4` against the ≤ 10% band — while its assembled `‖B_dg0‖_L2` moves only **0.0079%** across the same ranks, so the sampling, not the solve, destabilises as cells shrink under a fixed grid. The band holds on the two controlled rungs alone (4.69% and 6.40% spread; 1.713× drop across a 1.5× refinement). |
| **CG1 does not converge either** (`MAG-6` step 2) | On the identical solves, the test's own CG1 path reads 0.240541 → 0.760519 → 0.723637 at `-n 2` — **non-monotone and mostly rising** under refinement where DG0 falls. Step 1 showed CG1 owns the rank-dependence; refinement does not rescue it. |
| **The number the tolerance question was waiting on** | The DG0 metric meets the **unmodified 0.350** at **h = 0.010 m** (0.312197 at `-n 2`, 0.304356 at `-n 4`) for 55 784 cells, 6.4 s mesh + 2.0 s solve at `-n 2` — standard tier. So candidate (i) (re-point the estimator at DG0) plus one refinement rung gates green **without raising 0.350**. The choice is still a review's; nothing was re-pointed and the tolerance is untouched. |
| **Verified at** (step 2) | `20260808T123206Z_MAG-6-step2-meshprobe.log` (cell counts), `20260808T123245Z_MAG-6-step2-hconv-n2.log` (35 s), `20260808T124355Z_MAG-6-step2-hconv-n4.log` (32 s), `20260808T123335Z_MAG-6-step2-hconv-n1.log` (**exit 124** — sequential LU 13.0 s → 132.4 s over rungs 1–2, rung 3 past the 600 s ceiling; that rung's `-n 1` control was dropped on cost per §7, not retried longer). |
| **Estimator adjudicated 2026-08-08 (10:30 review)** | Candidate (i) is taken on step 2's licensed numbers: `MAG-6` step 3 (§7, queued §9 item 1) re-points the test's sampling at DG0 and refines the fixture to h = 0.010 m, gating against the **untouched** 0.350 with a ≤ 10% three-way rank-spread gate (6.40% on record). Candidate (ii) — real material contrast — is rejected for this chunk: it changes the physics under the metric; the uniform-μ caveat transfers into the test docstring instead. **This entry retires with step 3's landing commit.** |
| **Superseded next step scoped 2026-08-08 (03:00 review)** | `MAG-6` step 2 (§7, queued §9 item 3): measure the **DG0 metric's `h`-convergence** on a three-rung refinement ladder — the one measurement that decides whether ~0.53 is coarse-mesh discretisation (it falls with `h`) or a mesh-independent defect (it plateaus). Candidates (i) re-point the estimator at DG0 and (ii) give the phantom real material contrast are deliberately deferred behind it: (i) would flip the test hard-red today with no licensed number to gate against, and (ii) changes the physics under the metric. The 0.350 tolerance stays untouched until step 2's bands read out. |

</details>

### 5. ✅ RETIRED 2026-08-06 — domain sizing heuristic, off-centre phantom

| | |
|---|---|
| **Test** | `tests/mesh/test_domain_sizing_heuristics.py::test_coil_phantom_domain_sizing_accounts_for_off_center_phantom_extent` |
| **Symptom** | `assert 0.09 > 0.09` |
| **Was pre-existing at** | `794d2f1` (pre-session); reproduced one last time 2026-08-06 at `d4e278d` (`20260806T033155Z_GEO-4-step1-precontrol.log`, 1 failed 3 passed in 1.31 s) |
| **Diagnosis** (`GEO-4` step 1) | **The test's assertion, not the arithmetic.** The air box is centred on the origin, so its half-width is `max(coil_major + coil_minor, |offset| + phantom_radius) + padding` — the off-centre phantom enters through the second term of the max. `coil_phantom_domain` rejects any placement with `|offset| + phantom_radius >= coil_major - coil_minor` (the `radial_clearance <= 0` guard), so the phantom's outer radius is **always** strictly below the coil's outer radius and the max is always won by the coil. The property "an offset phantom grows the box" is therefore unattainable for every meshable configuration, not merely unexercised by the chosen 0.03 m offset (phantom reaches 0.07 m vs the coil's 0.09 m). Test and code landed together in `2c52f05`; the test never passed. |
| **Resolution** | The strict `>` was **not** relaxed. The test now gates the containment identity with the clearance term explicit — `half_width == max(coil_outer, |offset| + r_phantom) + padding` for both presets, and `clearance(centered) - clearance(shifted) == 0.03` exactly (the whole offset is spent out of the phantom's wall clearance). Two tests added: the phantom-governed branch of the max keeps a strict `>` alive where it exists (arithmetic only, outside the meshable envelope), and a zero-padding negative control still detects an undersized domain. `coil_phantom_domain_sizing_diagnostics` gained `phantom_outer_radial_extent_m`, `phantom_boundary_clearance_m`, `phantom_offset_radius_m`, `phantom_governs_radial_extent`; **no sizing number changed**, so no meshed fixture moved. |
| **Verified at** | `20260806T033316Z_GEO-4-step1-gate.log` (6 passed, 1.36 s, `-n 2`) and `20260806T033327Z_GEO-4-step1-mesh-regression.log` (whole `tests/mesh`, no `--deselect`, **27 passed 1 skipped in 85.3 s**) |
| **Back in CI** | The `OPS-11` `--deselect` was removed in the same commit; the `Mesh generation suite` step now excludes nothing. |
| **Cited wrongly as "known-issues 6"** | Commit `3ac025c` and `docs/testing/attempts.md:1903,1907` call this entry 6. **It was entry 5.** Entry 6 is the rank-dependent single-port excitation test in `tests/solver`, unrelated to `tests/mesh`. |

**Open follow-up for a review (not a failing test):** because the overlap guard
is z-blind, a *short* phantom that would clear the torus tubes in z is rejected
just the same. If off-centre placements that radially govern the box are ever
wanted, that guard — not the sizing heuristic — is what must change.

### 6. Rank-dependent: single-port excitation

| | |
|---|---|
| **Test** | `tests/solver/test_single_port_excitation.py::test_single_port_excitation_returns_finite_estimates` |
| **Symptom** | Passes at 1 rank, fails at `mpiexec -n 8` — **verified 2026-08-08**, and the failure is a `ValueError` raised out of `src/`, not a test assertion: `missing required port tags: [21, 22]` / `[12, 21, 22]` from `ports/definitions.py:99`, on 8/8 ranks. Also red at `-n 4` (`missing required port tags: [22]`, 4/4 ranks) — the entry's `-n 8` is the count that was tried, not the threshold. |
| **Cause** | **Diagnosed 2026-08-08 (09:00 run) by `OPS-14` — two independent defects, and neither one alone explains the red.** See the diagnosis row below. *(Original, superseded:)* Not diagnosed. Two rank-local bugs of this family were already fixed on 2026-07-27 (`tests/solver/test_two_torus.py` asserted on rank-local `cell_tags.values`; `test_helmholtz_v2.py` did a per-rank collision search). Suspect the same pattern — a quantity that is rank-local being treated as global. |
| **Tool** | `tests/mesh/helpers.py::global_cell_tag_set()` exists for the tag case. `post.evaluation.evaluate_vector_field_parallel()` for the point-location case. |
| **Verified pre-existing at** | `ce92e8c` and earlier |
| **Scoped 2026-08-08 (03:00 review)** | `OPS-14` (§7, queued §9 item 4) owns the diagnosis — the last never-diagnosed entry in this file. **Treat the symptom line above as unverified:** the last two never-diagnosed entries both turned out to be misrecorded (entry 2's assertion was wrong; entry 4's green CI signal was a partition artifact), so the first step is a three-way `-n 1/2/8` reproduction that captures the *actual* failure. Prime suspect: the fixture's `tags[cell_indices % 4]` over rank-local indices on a 12-cell cube — at `-n 8` ranks see strict subsets of the tag set. Pre-registered disposition: a defect wholly inside the `PORT-0` placeholder is **not fixed** (entry 3's "resolve in `PORT-1`" logic) — this entry would then be re-pointed at `PORT-1` rather than retired. |
| **Diagnosed 2026-08-08 (09:00 run, `OPS-14`)** | **Two defects, independent, and each is individually sufficient to keep this red at `-n 4` and `-n 8`.** Measured with `scripts/probes/ops14_rank_probe.py` at `-n 1/2/4/8` (logs `20260808T140412Z`/`140424Z`/`140426Z`/`140427Z_OPS-14-table-n{1,2,4,8}.log`; reproduction `20260808T140044Z`/`140055Z`/`140056Z_OPS-14-repro-n{1,2,8}.log`). **(1) The fixture** (`tests/solver/test_single_port_excitation.py:21-26`) builds `tags[cell_indices % 4]` over **rank-local** indices, so the *global* tag set is itself rank-count dependent: `{11,12,21,22}` at `-n 1/2`, **`{11,12,21}` at `-n 4`** (per-tag global cell counts `4/4/4/0`), **`{11,12}` at `-n 8`** (`8/4/0/0`). Tag 22 exists on no rank at `-n 4`, so the `ValueError` is *correct behaviour* — the mesh really lacks the tag. The same defect makes the placeholder's own output rank-dependent while green: `P1.I` = `3.000000e-03+4.263898e-04j` at `-n 1` against `4.000000e-03+5.685197e-04j` at `-n 2` (+33.3%), because `support` counts tagged cells. **(2) `ports/excitation.py:249`** hands rank-local `problem.cell_tags.values` to `validate_required_port_tags_exist`, so the check is not collective — a rank owning no cell of a terminal region raises while others return. Counterfactual B (fixture tags taken over *global* cell numbering — global per-tag counts then exactly `3/3/3/3` at every rank count) still raises on 4/4 ranks at `-n 4` and 8/8 at `-n 8`, which isolates (2) from (1). Counterfactual A (collective validator argument, fixture untouched) still raises at `-n 4/8`, which isolates (1) from (2). **Anchor — the cross-rank identity:** under counterfactual B the estimates are **byte-identical** at `-n 1` and `-n 2` (`P1.I = 3.000000000000e-03+4.263897544510e-04j`, `P2.V = 5.000000000000e-02`, coupling `1.000000000000e-01`), where production diverges by 33.3% across the same two rank counts. |
| **Defect (2) fixed 2026-08-13 (13:30 run, `PORT-1` step 4) — entry stays red** | `run_placeholder_port_coupling_case` now reduces the tag set with `comm.allgather` before `validate_required_port_tags_exist`, exactly as that function's docstring prescribes. Not a courtesy: step 4's negative control runs the retiring heuristic on the two-torus fixture at `-n 2`, where each rank owns one port's cells, and defect (2) made that call raise on one rank while the other returned. Verified by the control's own green run (`20260813T183606Z_PORT-1-step4-packagegate.log`, 7 passed 153.9 s). **Defect (1) — the fixture tagging over rank-local cell indices — is untouched, so this entry stays open and the test stays red at `-n 4`/`-n 8`.** |
| **Disposition 2026-08-08 — not fixed, re-pointed at `PORT-1`** | The pre-registered rule applies as written: both defects are wholly inside the `PORT-0` placeholder that `PORT-1` deletes — (2) is a line of `run_placeholder_port_coupling_case`, and (1) is a fixture that exists only to exercise it. A shared-machinery survey found no other non-collective tag read left in `src/`: `core/time_harmonic.py:162` was fixed by `OPS-13`, `post/sar.py:184` already reduces with `allreduce(..., op=MPI.MAX)`, `io/mesh.py:1711` with `SUM`. The only change landed is a hazard warning in `validate_required_port_tags_exist`'s docstring (behaviour unchanged) so `PORT-1`'s real caller does not repeat (2). **This entry leaves with `PORT-1`, like entry 3.** |

### 8. ✅ RETIRED 2026-08-05 — magnetostatic energy raised `TypeError` in the complex build

**Fixed 2026-08-05 (16:30 run) by `MAG-16`.** Both tests pass at `-n 2` under
`dolfinx-complex-mode` with their identity assertions untouched
(`20260805T213601Z_MAG-16-gate-complex-final.log`, 10 passed in 4.9 s with
`tests/environment` first), and the complex-mode `tests/solver` sweep went from
4 standing failures to 2 — the remaining two are **entry 2**, unrelated
(`20260805T213408Z_MAG-16-regress-complex.log`, 2 failed 34 passed in 28.3 s).

`compute_magnetic_energy` now takes `np.real` of the reduced scalar and raises
if `abs(Im W)/abs(Re W)` exceeds `ENERGY_IMAG_RTOL = 1e-8`; `abs()` was
rejected on purpose, since it would swallow a genuine imaginary part *and* a
negative real one. The suspicion recorded below — that the imaginary part is
round-off — was **too pessimistic**: it is **exactly 0.0** in both gauges,
because the magnetostatic load is real and `ufl.inner` conjugates its second
argument, so the assembled integrand is `μ⁻¹|curl A|²/2` and the complex build
merely stores a real number in a complex slot.

The value had indeed never been compared across builds, so it was pinned before
being trusted: the real-build energies were captured *pre-fix*
(`20260805T213144Z_MAG-16-probe-real.log` — `1.121469318858e-08 J` penalty,
`1.121466766900e-08 J` Lagrange) and the complex build reproduces them to
`2.9e-07` and `1.3e-13` respectively. The penalty gauge's run-to-run wander
(`1.9e-08…2.9e-07`) is its κ ~ 1e10 operator, not the reduction.

The file is now listed in the `validation-complex` CI job, which is what stops
this from recurring — nothing had ever run it under the complex build until a
`POST-3` step-5 regression sweep did by hand. Original entry follows.

| | |
|---|---|
| **Tests** | `tests/solver/test_energy_and_point_evaluation.py::test_energy_matches_explicitly_reduced_assembly`<br>`tests/solver/test_energy_and_point_evaluation.py::test_energy_satisfies_discrete_work_energy_identity` |
| **Symptom** | `TypeError: float() argument must be a string or a real number, not 'complex'` at `src/fem_em_solver/core/solvers.py:661` (`MagnetostaticSolver.compute_magnetic_energy`) |
| **Cause** | Not diagnosed beyond the mechanism: in the complex build every `fem.Function` is complex, so the assembled energy scalar is complex-typed (with a round-off imaginary part) and the unconditional `float(...)` refuses it. The magnetostatic energy is real by construction, so the fix is presumably `np.real(...)` before the cast — but that is `MAG` work and the value has never been checked against the real-build number, so it is recorded rather than patched in passing. Both tests pass in the real build. |
| **Verified pre-existing at** | `aabb0a7` — reproduced with the `POST-3` step-5 diff stashed: `2 failed, 2 passed in 4.46 s` (`20260805T003945Z_POST-3-step5-preexisting.log`, `-n 2`, complex build). Found by that step's regression sweep, which is the first time this file was run under `dolfinx-complex-mode`. |

Owned by chunk `MAG-16` (§7, written by the 2026-08-05 10:30 review); this
entry leaves with `MAG-16`'s fixing commit — which is the commit carrying the
retirement header above.

### 9. ✅ RETIRED 2026-08-05 — `-n 2` hang on `two_torus_domain`'s port facets

**Diagnosed and fixed 2026-08-05 (12:00 run); `tests/mesh/test_two_torus_port_facets.py`
is on `main` and green at `-n 2` in 20 s
(`20260805T171107Z_PORT-1-step3biv-parallel-gate-fixed.log`, 2 passed).**

**Cause: a lazy collective, reached on only one rank.** An interior-facet
(`dS`) assembly requires `Topology::create_entity_permutations()`, and the
dolfinx assembler calls it *lazily* — only once a rank finds integration
entities for the form's subdomain id. Under this fixture's partition each rank
owns the facets of exactly one port (rank 0 → tag 201, rank 1 → tag 202), so
assembling tag 201 put rank 0 inside that collective while rank 1, with no
201 facets, sailed past it into the next one. Hence the two ranks' *different*
SIGTERM stacks (`create_entity_permutations` vs mpi4py `MPI_Comm_dup`) — a
mismatched collective, not a slow one. The fix is one hoisted line in
`_facet_group_area`: call `create_entity_permutations()` unconditionally on
every rank before building the form.

**What the discriminating run was.** The same computation, marker-instrumented,
ran to completion as a *script* at `-n 2` (exit 0, 12 s,
`20260805T170545Z_PORT-1-step3biv-dS-localise.log`) while the pytest gate hung
— and the script's only extra call was the explicit
`create_entity_permutations()`. Markers inside the gate then pinned the hang to
`_facet_group_area` at tag 201
(`20260805T170743Z_PORT-1-step3biv-pytest-localise.log`, exit 124).

**The ghost-mode hypothesis was necessary but not sufficient.** The
`shared_facet` partitioner now plumbed into `two_torus_domain` does what the
entry below predicted — `cells_ghost` 0 → 239/231 per rank
(`20260805T170109Z_PORT-1-step3biv-ghostprobe.log`, 14 s) — but the gate still
hung with it alone (`20260805T170140Z_…-parallel-gate.log`, exit 124, 181 s).
Both changes are kept: an interior-facet integral does need both cells of every
facet, and the fixture's docstring records the requirement.

**Generalisation, untested elsewhere:** any `dS` integral over a subdomain that
some rank does not touch is exposed to this. Only this fixture is fixed.

#### Superseded diagnosis, 2026-08-05 (22:30 run)

**Retitled and half-refuted 2026-08-05 (22:30 run).** The mesh is innocent: with
the gmsh dim-2 physical groups removed entirely and the identical facet set
rebuilt on the dolfinx side from the distributed cell tags, `model_to_mesh`,
`create_entities(fdim)` and `create_connectivity(fdim, tdim)` all return at
`-n 2` on the gate's own mesh in **14 s** (marker probe
`20260805T034007Z_PORT-1-step3biv-hang-localise-fine.log`, exit 0; 39578/39956
cells per rank, 116 interface facets found per port). The `-n 2` gate still
times out, so *something* on this path hangs — but it is downstream of the tags,
in the `dS` facet-area assembly, and the paragraph below misattributes it.

**Leading hypothesis for the next attempt, measured not guessed:**
`gmshio.model_to_mesh` passes no partitioner, so the mesh is built with the
default ghost mode and the probe measures `cells_ghost=0` on **both** ranks. An
interior-facet (`dS`) integral needs both cells behind every facet, which a mesh
with no ghost cells cannot supply on a partition-boundary facet. First move:
hand `model_to_mesh` a `shared_facet` partitioner and re-measure. Second
observation from the same probe, relevant either way: with the current
partition each rank sees exactly **one** port (rank 0 tag 201, rank 1 tag 202),
so any per-port assertion is rank-local until it is reduced.

The original entry follows, kept because its serial measurements stand.

#### Original entry, 2026-08-05 (21:00 run) — the `model_to_mesh` attribution is superseded above

| | |
|---|---|
| **Tests** | `tests/mesh/test_two_torus_port_facets.py` (both tests) — **not on `main`**; the file and the mesh change were parked *because* of this, so nothing on `main` is red. *(The branch this row named, `…021000Z`, was deleted by the 2026-08-05 10:30 review; the current code is on `attempt/PORT-1-step3biv-20260805T034500Z`.)* |
| **Symptom** | With `PORT-1` step 3b-iv's dim-2 physical groups `201`/`202` (the gap↔conductor shared surfaces, which are **interior** facets) added to the gapped fixture, `mpiexec -n 2` hangs inside `gmshio.model_to_mesh` and is killed by `timeout` at the 180 s ceiling. Both ranks' loguru stacks are identical and spinning in `MPI_Testall` ← `MPI::compute_graph_edges_nbx` ← `IndexMap::index_to_dest_ranks` ← `Topology::create_entity_permutations` ← `create_entities`. gmsh finishes (`Done optimizing mesh (Wall 7.14s)`) ~10 s in; the remaining ~168 s is the hang. No test code runs — the hang is before `model_to_mesh` returns. Log: `20260805T020301Z_PORT-1-step3biv-costprobe.log`, exit 124. |
| **Cause** | Not diagnosed. Bounded from two sides by measurement: `-n 1` completes the identical case in 22.5 s with correct areas (`20260805T020843Z_PORT-1-step3biv-serial-gate.log`, 2 passed), and `-n 2` on the same fixture **without** the new facet groups is green today (`tests/mesh/test_two_torus_gapped.py`). So it is neither cost nor the gapped geometry: it is the distribution of facet tags whose facets are interior to the partitioned mesh. The `2xx` groups are the fixture's first interior dim-2 groups — the only pre-existing one is the outer boundary. |
| **Verified pre-existing at** | Not pre-existing — introduced by the parked branch, which is why it is parked. Recorded here so the next attempt starts from the stack trace instead of re-deriving it. |

### 10. ✅ RETIRED 2026-08-06 — `two_torus_domain`'s outer-boundary facet group never reached the dolfinx facet tags (`GEO-10`)

The group was never *declared*, so nothing downstream could lose it. gmsh
inflates an OCC entity's bounding box by its geometric tolerance — measured at
exactly **`1.000e-07`** on all six walls of this box
(`20260806T050143Z_GEO-10-probe.log`) — and the fixture's flat-against-wall
test used `tol = 1e-9`. All six walls failed it, `boundary_surfaces` came out
empty, and the `if boundary_surfaces:` guard silently skipped
`addPhysicalGroup`. The chunk's prime suspect, fragment renumbering, is
**refuted**: the group is re-derived from bounding boxes after `fragment` +
`synchronize`, so renumbering never reaches it.

Fixed by widening that one tolerance to `1e-6` — 10× above the measured
padding and four orders below the nearest interior face's `2.000e-02`
residual, so the interior-face protection the tight test existed for is
intact. ~~No other fixture is affected: the rest of `io/mesh.py` uses a
`< resolution` wall test (loose by ~4 orders), and only `two_torus_domain` had
tightened it.~~ **Corrected 2026-08-06 by `GEO-11` measurement:** two other
fixtures had also tightened it to `1e-9` and have the identical defect —
`loop_over_half_space_domain` and `sphere_in_box_domain`, see entry 12. This
retirement stands (its own gate is unaffected); only the generality claim was
wrong.

Gated by `tests/mesh/test_two_torus_outer_boundary.py`: tag sets exactly `{1}`
ungapped and `{1, 201, 202}` gapped, and the assembled `ds` area over tag `1`
equals the analytic box surface `2(LW+LH+WH) = 3.220000000000e-02 m²` at
ratio **`1.000000000000000`** (`-n 2`,
`20260806T050313Z_GEO-10-gate-n2.log`, 25 s) and `1.000000000000001` (`-n 1`,
`…050350Z_…-n1.log`, 24 s) — planar walls, so this is an identity at `1e-9`,
not a band.

The open question the entry recorded is now answered: **neither Helmholtz
consumer depends on tag `1`.** Both were re-run with the group present and
their gated numbers are digit-identical — `MAG-14`'s centre-field error is
still `0.728%` (`…050656Z_GEO-10-helmholtz-regression.log`, 2 passed, 11 s).
The port-facet gate likewise reproduces `A_201 = A_202 = 1.563786482e-04 m²`
at `0.974490841` of analytic (`…050620Z_GEO-10-portfacet-digits.log`), so
adding a boundary group moved no interface tag. Full `tests/mesh` at `-n 2`:
**29 passed, 1 skipped, 107.64 s** (`…050421Z_GEO-10-mesh-regression.log`).

### 11. `two_torus_domain` gap-box terminal facet tags include lateral strips below `gap_overhang ≈ 6e-4`

| | |
|---|---|
| **Test** | `tests/validation/test_port_gap_voltage_impedance.py` disc-area band (on `attempt/PORT-1-step3bv-20260806T004500Z`, not on `main`) — and any future test that gates on the `201`/`202` facet areas at small overhang |
| **Symptom** | Measured facet-group area `1.643447371e-04 m²` per port at `gap_overhang = 2e-4` — `1.0241 ×` the exact oblique cut `1.604721580e-04 m²`, i.e. **above** a value an inscribed linear-tet section must sit below |
| **Cause** | Measured, not guessed (`PORT-1` step 3b-v, `20260806T003559Z_PORT-1-step3bv-gate.log`): at overhang 2e-4 the tube protrudes 0.2018 mm through the gap box's `−x` face over `2.821 mm < \|y\| < 3.989 mm` (box `min x` = 1.480000e-02, tube `min x` at `y = half_y` = 1.459821e-02), so the fragment-boundary intersection that defines tags `201`/`202` picks up the arc-end disc pair **plus two lateral strips**. The "gap box contains the arc ends" invariant fails below overhang ≈ 6e-4. 3b-iv's disc-area band was measured at overhang 1e-3, where the tube clears the face by 0.598 mm — it does not transfer to small overhang, and the mesh is not what is wrong. |
| **Verified at** | `main` fixture geometry as of `7747999`; the failing band assertion lives only on the parked branch |
| **Fix options, neither taken in-slot** | Raise `GAP_OVERHANG` back above ~6e-4 (changes the comparison geometry all 3b measurements share), or make the band overhang-aware (the strip area is computable from the same arithmetic above). A per-geometry decision for whoever next gates on these tags. |
| **Owned by** | `PORT-1` steps 3b-vi/3b-vii note it as a trap (do not gate on the 2xx areas at overhang 2e-4); entry leaves with the commit that restores an exact terminal-area anchor at the geometry it is asserted on |
| **Second measurement, 2026-08-07 (`PORT-1` step 3b-x)** | The strips bias *any* facet average, not just the area. Reading the terminal angle as `arcsin(⟨y⟩/a)` over tags `201`/`202` gives **0.173852206 rad against the exact 0.175335123** — 1.48e-3 short, because the strips sit at `\|y\| < half_y` (`20260807T093604Z_PORT-1-step3bx-gate-n2.log`). The workaround that step took, and the one to reuse: gate the interface's **extreme** reach (`max \|y\|` over the tagged facets' nodes, exact to 5.6e-17 rad), since every strip point lies inside the box while the box face is a plane its nodes sit on exactly. Print the mean beside it — it is this entry's magnitude on the live fixture. |

### 12. ✅ RETIRED 2026-08-06 — `loop_over_half_space_domain` and `sphere_in_box_domain` never declared their `outer_boundary` group (`GEO-12`)

Fixed by widening both `tol` from `1e-9` to `1e-6` (`io/mesh.py`, the two sites
below) — exactly `GEO-10`'s fix, for the identical measured cause. Post-fix
(`20260806T183203Z_GEO-12-probe.log`): the loop fixture accepts **10 of 12**
dim-2 entities (the cube's four `z = 0`-split sides plus top and bottom; the
two rejected are the torus surface at `9.000010e-02` and the air/slab interface
at `1.000001e-01`) and the sphere fixture **6 of 7** (the sphere surface is
rejected at `1.500001e-01`). Both land on wall ratio
`1.0000000000287557e-01` — the same `1e-7/1e-6 = 0.1` `GEO-10` designed — so
`tests/mesh/test_boundary_classification_margins.py` now *asserts* the
two-sided margin for them instead of pinning a defect; the two `pytest.skip`s
are gone.

The group was invisible because nothing gated it, so the tolerance landed with
a meshed gate: `tests/mesh/test_wall_boundary_tag_areas.py` asserts per fixture
that facet tag `1` exists, carries an allreduced facet count > 0, and that its
assembled `ds` area equals the analytic cube surface `6(2W)² = 2.4e-01 m²` —
an identity on planar walls, gated at `1e-9` relative. Measured at `-n 2`
(`20260806T183328Z_GEO-12-gate.log`, 3.2 s): loop **1958 facets, ratio
1.000000000000000**; sphere **988 facets, ratio 0.999999999999999**.

The latency claim is now measured, not assumed. All six downstream callers plus
`tests/post/test_drop_set_semantics_sphere.py` were re-run and **no landed
number moved a digit**: `MAT-6` step 3 `dR` rel. error `1.5834%` / `dX` ratio
`0.9200`; step 4 `1.5763%` / `0.9849` (projected) and `1.5713%` / `0.8740`
(pinned), identical to `20260805T200455Z`/`20260805T200938Z`; `TH-8`/`MAT-4`
mass-averaged SAR ratio `0.999846` and the `POST-1` sphere table `4.2530%`
(`20260806T183745Z_GEO-12-callers-A.log`, 24 passed 210 s;
`20260806T184151Z_GEO-12-callers-B.log`, 8 passed 574 s). Whole `tests/mesh` at
`-n 2`: **35 passed, 2 skipped, 118.29 s**
(`20260806T183404Z_GEO-12-mesh-regression.log`).

Entry 13 is **not** covered by this fix and stays open — `cylindrical_domain`'s
margin is a different mechanism (tolerance coupled to `resolution`).

| | |
|---|---|
| **Test** | None fails. Measured and pinned by `tests/mesh/test_boundary_classification_margins.py` (`GEO-11`), which **skipped** the margin assertion for these two after pinning their numbers |
| **Symptom** | Both fixtures' wall test classifies **zero** surfaces — 0 of 12 and 0 of 7 dim-2 entities — so `boundary_surfaces` is empty and the `if boundary_surfaces:` guard silently skips `addPhysicalGroup`. Facet tag `1` does not exist in the returned `facet_tags` |
| **Cause** | Measured, not guessed (`20260806T140325Z_GEO-11-probe.log`): identical to retired entry 10. Both use `tol = 1e-9` (`io/mesh.py` ~lines 1384 and 1532) against gmsh's OCC bounding-box padding, which is the same **`1.000e-07`** `GEO-10` measured on `two_torus_domain` — the tolerance sits **100× below** the padding it must clear. Retired entry 10's closing claim that "no other fixture is affected" was wrong: it checked the `< resolution` fixtures and missed these two, which had also tightened the test |
| **Live impact** | **None — latent.** Every caller of both generators discards the facet tags (`msh, cell_tags, _ = MeshGenerator...`) in `test_dodd_deeds_impedance.py`, `test_dodd_deeds_projected_drive.py`, `test_dodd_deeds_reactance_box_size.py`, `test_dielectric_sphere.py`, `test_lossy_sphere_sar.py`, `test_mass_averaged_sar.py`, and imposes its wall condition geometrically instead. No landed `MAT-6`, `TH-8` or `MAT-4` number reads the missing group, so none of them is wrong |
| **Verified at** | `main` as of `2cad984` |
| **Fix, not taken in-slot** | Widen both to `1e-6`, exactly as `GEO-10` did — the nearest interior faces sit at `9.000e-02` and `1.500e-01`, so `1e-6` keeps 5 orders of interior-face protection. `GEO-11`'s plan reserves any tolerance change for a review with the numbers in hand, which these are. Whoever takes it must add a facet-tag assertion at the same time: the defect was invisible precisely because nothing gates the group |
| **Owned by** | `GEO-12` (commissioned by the 2026-08-06, 10:30 review — §9 item 2, with the tolerance decision taken); **discharged 2026-08-06, 13:30 implementer slot** — see the retirement note above |

### 13. ✅ RETIRED 2026-08-07 — `cylindrical_domain`'s classification margin was 4.50× its tolerance (`GEO-13`)

The tolerance was the *mesh size*: `abs(r_max - outer_radius) < resolution`. It
is now `0.01 × (outer_radius - inner_radius)` — a fraction of the radial gap,
so the margin is a ratio of geometry to geometry and no longer moves when a
caller coarsens the mesh. Measured across all four argument sets the repo calls
the generator with (`20260807T033127Z_GEO-13-probe.log`): the fraction window
where **both** sides of the `GEO-11` identity hold is `[1e-4, 0.05]`, and `0.01`
sits in the middle of it. At defaults the interior margin goes
**`4.499995×` → `99.99989×`** (floor `10×`) with the accepted side at
`1.111111e-04×` (ceiling `0.1×`), and the classification itself is **unchanged**
— still 3 of 6 surfaces, on every one of the four geometries.

The failure mode the entry named is reproduced in the probe before the fix: at
`resolution = 0.09` (the gap) the old predicate accepts **6 of 6** surfaces, the
inner cylinder swept whole into `outer_boundary`.

`tests/mesh/test_boundary_classification_margins.py` now **asserts** the
two-sided margin for this fixture instead of pinning it — the pin and its skip
are gone, and the file reads the fraction from the generator so the two cannot
drift apart. All four fixtures in that file are now live: **5 passed in 1.05 s**
(`20260807T033236Z_GEO-13-margins.log`, `-n 1`). Regression: whole `tests/mesh`
**36 passed, 1 skipped in 110.34 s** (`20260807T033250Z_GEO-13-mesh-regression.log`,
`-n 2`) — one skip fewer than the 35/2 on record, which is this fixture. Callers
green at `-n 2`: `4 passed, 1 skipped in 0.97 s`
(`20260807T033454Z_GEO-13-callers.log`; the skip is the complex-mode PEC test).

**Live precondition, new:** the tolerance scales with the gap, so a gap below
~`1e-4` m stops clearing the `1.000e-07` gmsh OCC bounding-box padding by 10×.
Recorded at the use site in `io/mesh.py`; no caller is near it (smallest gap in
the repo is `0.07` m).

<details>
<summary>Original entry</summary>

| | |
|---|---|
| **Test** | None fails. Measured and pinned by `tests/mesh/test_boundary_classification_margins.py` (`GEO-11`), which skips the margin assertion after pinning the ratio |
| **Symptom** | The nearest surface the wall test *rejects* sits at residual `8.999990e-02` = **`4.499995 ×`** `tol`, below the `10×` floor `GEO-11` asserts. The accepted side is fine (`5.000e-06 × tol`) |
| **Cause** | Measured (`20260806T140325Z_GEO-11-probe.log`): the test is `abs(r_max - outer_radius) < resolution` with `tol = resolution = 0.02` at defaults. The inner cylinder's surface and end caps sit at `r_max = inner_radius = 0.01`, a residual of `0.09`. The margin is a ratio of geometry to *mesh size*, so it shrinks as either radius gap narrows or `resolution` coarsens — at `resolution ≥ 0.09` the inner cylinder would be swept into `outer_boundary` |
| **Live impact** | **None at defaults.** `tests/mesh/test_cylindrical_domain.py` passes; the classification is correct today, only under-separated |
| **Verified at** | `main` as of `2cad984` |
| **Fix, not taken in-slot** | Either decouple the tolerance from `resolution` (a geometric fraction of `outer_radius - inner_radius` is the natural choice) or document the sizing precondition. A per-fixture decision for a review, per the `GEO-11` plan |
| **Owned by** | `GEO-13` (filed 2026-08-06, 18:00 review, with the geometric-fraction fix and the un-skip of the margin assertion; was `GEO-11`, whose sweep found it); **discharged 2026-08-07, 22:30 implementer slot** — see the retirement note above |

</details>

### 7. ✅ RETIRED 2026-08-03 — birdcage mesh fails to generate (`GEO-9`, steps 1 + 2a + 2b)

All three tests are green and the whole of `tests/mesh` less known-issues 5 is
`20 passed, 1 skipped, 1 deselected in 42.15 s`, exit 0
(`20260803T200504Z_GEO-9-step2b-gate.log`, `-n 2`) — the CI command verbatim,
with the birdcage `--ignore` removed in the same commit. **Step 2b** replaced the
`occ.cut(..., removeTool=False)` with a single `occ.fragment` of the air box
against every tool, so the legs and rings that pierce each other by construction
are booleaned into conforming pieces instead of being meshed twice; the physical
groups are re-derived from the fragment out-map (26 volumes, 20 of them
conductor) and the port boxes get the 3-D groups they never had. Measured:
`V_mesh/V_box = 1.000000000000` and `Σ(tagged)/V_mesh = 1.000000000000`, both
gated to `1e-9`, and every port box exact to `1e-9` of `dx·dy·dz`. The
rank-local `set(np.unique(cell_tags.values))` was fixed to `global_cell_tag_set()`
in the same commit — it was real and it fired: at `-n 2` rank 0 reported P2/P3
missing and rank 1 reported P1/P4 missing on an otherwise correct mesh
(`20260803T200151Z_GEO-9-step2b-probe.log`).

The history below is kept because several commits and the `GEO-9` §7 entry refer
to it, and because the diagnosis — one poisoned generator hanging every later
mesh in the process — is the reusable part.

<details>
<summary>Original entry (steps 1 and 2a)</summary>

#### Birdcage mesh fails to generate *(coil+phantom half resolved 2026-08-03, `GEO-9` step 2a)*

| | |
|---|---|
| **Tests** | ~~`tests/mesh/test_birdcage_port_tags.py::test_birdcage_like_mesh_has_core_and_port_tags`~~ — the "still red" note here is **historical**; the overlapping-facets geometry was fixed by `GEO-9` step 2b and the test itself no longer exists: `OPS-17` step 2 (2026-08-17) removed it as finiteness-only, its mesh-side content having been subsumed by `test_birdcage_volumes_partition_the_box` in the same file<br>~~`tests/mesh/test_coil_phantom_mesh.py::test_coil_phantom_mesh_generates_required_tags_centered_preset`~~ **passes since 2026-08-03**<br>~~`tests/mesh/test_coil_phantom_mesh.py::test_coil_phantom_mesh_off_center_preset_moves_phantom_without_overlap`~~ **passes since 2026-08-03** |
| **Symptom** | `gmsh.py:2006: Exception: Invalid boundary mesh (overlapping facets) on surface 3 surface 49` (birdcage) and `dolfinx/io/gmshio.py:118: AssertionError` ×2 (coil+phantom) — the meshes never reach dolfinx |
| **Cause** | **Diagnosed 2026-08-03 by `GEO-9` step 1, and it is a single cause, not two.** `birdcage_port_domain` raises inside its `comm.rank == rank` block (the overlapping-facets error) and therefore never reaches its `gmsh.finalize()`. The process is left with gmsh initialised and mid-command, so the *next* generator in the same pytest process gets `Warning : Gmsh has aleady been initialized` and `Info : I'm busy! Ask me that later...`, every subsequent `occ` call is silently refused, and `model_to_mesh` reads the stale birdcage model — whose mixed element types are what `gmshio.py:118` asserts on. **The coil+phantom generator is innocent:** in a fresh process all three of its tests pass in 4.8 s (`20260803T033050Z_GEO-9-before.log`), and they fail again the moment the birdcage file runs first (`20260803T033119Z_GEO-9-order-probe.log`, 3 failed 2 passed in 3.47 s — the same two failures). Found 2026-08-01 by the `GEO-8` run, which ran `tests/mesh` as a regression sweep; the whole directory is in no CI job, which is why these were invisible. Both fixtures are untouched by `GEO-8` (it changed `two_torus_domain` only). |
| **Verified pre-existing at** | `63c94f2` — the `GEO-8` diff touches neither generator; log `20260801T004839Z_GEO-8-unrelated-failures.log`, 3 failed 2 passed in 3.5 s at `-n 2` |
| **Note** | ~~Likely the same overlapping-geometry family `GEO-8` just fixed for `two_torus_domain`: `coil_phantom_domain` and the birdcage fixture should be audited for missing `occ.fragment`.~~ **Half wrong — corrected 2026-08-02, 18:00 review, by code reading (not by execution).** `coil_phantom_domain` **already fragments** (`io/mesh.py:1616`), so its cause is downstream of fragment; the visible fragility is the group re-derivation at `io/mesh.py:1622-1634`, which assumes fragment returns exactly four volumes and leaves any extra piece with no physical group — which is what `gmshio.py:118` asserts on. The **birdcage** does match the family, differently: it uses `occ.cut(..., removeTool=False)` (`io/mesh.py:1970`), so the conductors, phantom and port boxes are never booleaned against *each other* and the port boxes overlap the legs by construction — hence "overlapping facets". The birdcage's port boxes also receive no 3-D physical group (`io/mesh.py:1985-1988`). |
| **Owned by** | `GEO-9` (created 2026-08-02): step 1 coil+phantom, step 2 birdcage. Two of the four §10 Target criteria route through these two fixtures. **Step 1 landed 2026-08-03** — the coil+phantom half is now gated by `tests/mesh/test_coil_phantom_conforming.py` (volume-partition identity, `20260803T033659Z_GEO-9-step1-gate.log`, 8 passed 1 skipped in 22.25 s) and the generator raises with the volume count and per-volume masses if fragment ever does return other than four grouped volumes. **All three tests above still fail in a shared process** and will until step 2 fixes the birdcage: `20260803T033733Z_GEO-9-order-probe-after.log` shows the new guards do *not* fire (gmsh is already busy, so they never execute), still `gmshio.py:118`. **Step 2's first action is the cheap half of this — wrap the birdcage's rank-0 block in `try/finally: gmsh.finalize()`**, which stops one broken generator from poisoning every later mesh in the process, independently of fixing the geometry. Split out as **`GEO-9` step 2a** at the 2026-08-03 03:00 review, with step 2b holding the `occ.fragment` geometry rewrite. |
| **A poisoned process hangs — added 2026-08-03, 03:00 review** | Both `GEO-9` order probes report pytest finishing (3.47 s and 3.29 s) but the **harness** exits **124 at the 180 s ceiling**, with `Loguru caught a signal: SIGTERM` (`docs/testing/test-results.md:136,139`; logs `20260803T033119Z_GEO-9-order-probe.log`, `…033733Z_GEO-9-order-probe-after.log`). The step-1 prose quotes only the pytest wall time and does not say this. Two consequences: `tests/mesh` cannot enter CI with the birdcage in it (`OPS-11`) because the job would burn its whole `timeout-minutes` rather than fail fast; and `GEO-9` step 2a gets a sharper anchor than "the tests pass" — harness exit **124 at 180 s → 0 in seconds**. If a `try/finally` does not fix it, suspect an MPI collective the raising rank never reaches, not gmsh state. |
| **Excluded from CI, and the reason has changed — `OPS-11`, 2026-08-03** | The `validation` job's `Mesh generation suite` step `--ignore`s `test_birdcage_port_tags.py`. The exclusion no longer rests on the hang or the budget: post-2a the file fails **promptly** (the unexcluded-directory control `20260803T170132Z_OPS-11-fullsweep.log` is 2 failed 18 passed 1 skipped in 31.85 s, harness exit 1 in 33 s, where the pre-2a probes exited 124 at the 180 s ceiling). It is ignored because it is deliberately red until `GEO-9` step 2b, and a permanently-red test in CI hides regressions behind an expected failure. **Remove the `--ignore` in the commit that fixes the geometry.** The same control also shows the coil+phantom tests now passing *with the birdcage in the same process* — the step-2a poisoning fix holding under the condition that used to break it. |
| **✅ Two-thirds resolved 2026-08-03 by `GEO-9` step 2a — and the hang was *both* causes, not one** |<!-- retired: see the summary above --> The review's warning was right: `try/finally` alone would not have fixed the hang. Rank 0 raised and skipped the collective `gmshio.model_to_mesh`, so rank 1 blocked in it forever — that is the exit 124, and gmsh contamination is a second, independent defect. `birdcage_port_domain` now builds its model in `_build_birdcage_port_model`, calls `gmsh.finalize()` (guarded by `gmsh.isInitialized()`) when that raises, and `comm.bcast`es the failure so **every** rank raises before any enters `model_to_mesh`. The birdcage still fails loudly with the original message. **Before** (`20260803T123116Z_GEO-9-step2a-before.log`, re-run at the working commit, not quoted): 5 failed 2 passed in 3.16 s of pytest, harness **exit 124 at 180 s**. **After** (`20260803T123549Z_GEO-9-step2a-after.log`, same command): **1 failed 6 passed in 12.10 s, harness exit 1 at 13 s** — only the birdcage test itself. Gated by `tests/mesh/test_birdcage_finalize_isolation.py` (`20260803T123657Z_GEO-9-step2a-gate.log`, 1 passed in 5.30 s, **exit 0**), which runs the two generators in the poisoning order in one process and asserts `V_mesh/V_box = 1.000000000000` and `Σ(tagged)/V_mesh = 1.000000000000` to `1e-9` afterwards. `tests/mesh` less the birdcage file is now 17 passed 1 skipped, 1 failed in 28.46 s (`20260803T123714Z_GEO-9-step2a-sweep.log`) — the single failure is **entry 5**, unrelated. |

</details>

---

## Non-test issues

### `check_example_doc_references.py` exit codes: 0 clean, 1 real defect, 2 staleness only (`OPS-19`, 2026-08-16 — contract, not an issue)

**Resolved 2026-08-16 (`OPS-19` step 1).** Staleness no longer owns the exit
code, so a chunk touching examples can read its companion docrefs log by its
status alone:

| code | meaning | who caused it |
|---|---|---|
| 0 | every reference resolves, every artifact fresh, guide pass green | — |
| 1 | **hard** violation: dead reference, missing guide, missing heading | usually the chunk in the slot |
| 2 | staleness only: references resolve, guides green, some artifact older than `--max-age-s` | the backlog — nobody has re-run those examples |

The last line of the checker's output states the split for a caller that does
not want to parse the body: `RESULT: dead=<n> guide=<n> stale=<n>
stale_severity=<fail|report> exit=<code>`. `--stale-severity fail` restores
the pre-`OPS-19` all-or-nothing reading (staleness exits 1); the default is
`report`. `--max-age-s` (`OPS-15`'s 48 h) did **not** move.

**On `main` at the time of the split**: `dead=0 guide=0 stale=24
stale_severity=report exit=2` — the 24 stale `paraview_output/` files (aged
105–141 h, magnetostatics/MRI examples) are still there, and regenerating
them is still compute rather than a documentation fix. What changed is that
they no longer show up as a failure. Guide pass green at 21/21 examples,
0 pending. Verified in `20260816T213312Z_OPS-19-step1-rerun.log` (8 passed,
1.91 s); the contract is pinned by `tests/unit/test_doc_reference_exit_codes.py`,
whose negative control is a guide naming an artifact no run ever wrote — that
must still exit 1 after the split, or the checker was switched off rather than
sharpened.

*(History: the pre-split behaviour — exit 1 on every invocation, "gate on the
guide-pass violation count, not on exit 0" — cost `EX-20` and `ANS-3` a
red-but-benign companion log each on 2026-08-16, which is what commissioned
`OPS-19`. The `EX-18` heading violations once filed here, three missing
headings in `examples/ports/01_two_torus_port_pair.md`, were fixed 2026-08-16.)*

### ~~`check_example_doc_references.py` freshness-gates only 5 of 27 examples — every `stale=24, none of them mine` line is not an all-clear~~ — RESOLVED 2026-08-24 (`EX-29`; found by the weekly review 2026-08-23)

**Found by the 2026-08-23 weekly examples audit (read-only, not a test
failure).** The checker's `--output-dir` defaults to the single repo-root
`paraview_output/` (`scripts/testing/check_example_doc_references.py:241-242`),
and its `in_tree_artifacts` exemption (`:276-298`) treats any referenced
artifact whose basename also appears anywhere under `examples/` as
"committed next to its own case — existence is enough". Only
`mag` 1/2/4/5/6 and `mri:1` write to the repo-root directory; the other
**22 of 27** runnable examples write `Path(__file__).parent/"paraview_output"`,
so they get an existence-only check and are **never** freshness-gated. The
exemption's premise is false: `.gitignore` ignores `paraview_output/` at
every depth and `git ls-files examples/ | grep paraview_output` returns
nothing — no artifact under `examples/` is committed evidence. That is why
the stale count has read exactly 24 on every docrefs log since `OPS-19`
and always names the same set.

**Consequence.** On 2026-08-23 the artifacts the checker cannot see are
10–17 days old for 13 examples (`mesh:1` ~17 d, `mesh:2` ~16 d, `mri:2`
~15 d, `mat:1` / `th:1`–`th:4` / `ans:1` ~14 d, `th:5` ~13 d, `ports:1` /
`th:6` ~10 d), all predating `OPS-17`'s test replacement; no EX chunk's
"none of them mine" reading ever covered them. A second, smaller finding:
`examples/magnetostatics/paraview_output/` (2026-08-03/04 `circular_loop_*`
files) is an orphan — `02_circular_loop.py` has written to the repo root
since `EX-17`, and nothing regenerates that directory.

**RESOLVED 2026-08-24 by `EX-29`** (`tests/unit/test_doc_reference_exit_codes.py`,
15 tests, green twice in-slot; logs `20260824T110512Z_EX-29-unit.log` /
`20260824T110540Z_EX-29-unit-run2.log`). The checker now resolves each
referenced artifact in the citing guide's own `paraview_output/` first and the
shared `--output-dir` second, and exempts only paths `git ls-files` reports as
tracked. Measured on the same tree, same slot: **pre-fix `stale=24`**
(`20260824T110150Z_EX-29-prefix-control.log`) → **post-fix `stale=55`**
(`20260824T110531Z_EX-29-census.log`, `dead=0 guide=0 exit=2`), with
**32 of 58** resolved artifact references sitting outside the repo-root
directory — the set the old exemption hid. The orphaned
`examples/magnetostatics/paraview_output/` is deleted. `EX-30` refreshes the
now-visible stale set and is re-sized from 55 by a review.

Two corrections to this entry's own text, both measured: (a) the tracked set
is **not** empty — `git ls-files` reports three committed artifacts under
`examples/` (`ansys_benchmarks/*/metrics.json` ×2,
`magnetostatics/straight_wire_validation.png`), which are exactly the
"committed next to its own case" exemption the rule was written for and are
pinned by path in the test; (b) `git` inside the `fem-em-solver` container
fails with `fatal: detected dubious ownership in repository at '/workspace'`
(root over a host-owned bind mount), which would have silently emptied the
exemption and reported the two tracked `metrics.json` as **dead references** —
the checker passes `-c safe.directory=` for both the repo root and the docs
root. Any future in-container `git` call needs the same.

### The container-side `timeout` in the standard harness recipe does not reliably stop an `mpiexec` job, and an overrun can wedge the container (`MAT-6` step 10, 2026-08-12)

**Verified at `648b216`, 00:00 implementer slot.** The recipe every heavy
chunk uses — `... bash -lc 'source ... && timeout <s> mpiexec -n <N> python3
...'` — was run with `timeout 590`. It should have fired at 05:11:23Z. The
ranks were still burning 8–12 cores at 05:31Z, ~1 700 s into a solve, and the
harness never wrote a footer
(`20260812T050133Z_MAT-6-step10-probe.log`). **Treat the container-side
`timeout` as best-effort, not a guaranteed stop**; the recipe had no
`-k`/kill-after, so a job that ignores or outlives SIGTERM keeps the cores.
Repair landed 2026-08-12 (03:00 daily review): the canonical recipes in
CLAUDE.md, PROJECT_PLAN §5, and docs/automation/ now read
`timeout -k 30 <s>`. This entry stays for the container-wedge behavior and
its recovery below, which the `-k` reduces but does not provably eliminate.

**The overrun then wedged the container**, and the usual levers failed in
order: `docker compose exec` hung twice with no output (>2 min each);
`docker compose restart` and `docker compose kill` both returned
`Error response from daemon: ... tried to kill container, but did not receive
an exit event`; a later exec failed with `OCI runtime exec failed: ... error
executing setns process: exit status 1`. **What recovered it:**

```bash
docker compose -f docker/docker-compose.yml up -d --force-recreate
```

Verified clean afterwards — exec responds, `/sys/fs/cgroup/memory.max` still
`68719476736`, zero stray `python3`, host load 12.2 → 8.9 as the orphaned
ranks died. Reach for the force-recreate rather than repeating the
restart/kill pair. Not diagnosed: whether the wedge is specific to a job that
survived its `timeout`, or to any long `docker compose exec` under load.

### A killed `mpiexec` job leaks its `/dev/shm/mpich_shm_*` segment, and once the container's 64 MB `/dev/shm` fills, **every** later run dies with `EXIT CODE: 135` (interactive session, 2026-08-28)

**Verified at `15e596f`, interactive session.** An `examples/run_examples`
invocation was interrupted by the human operator mid-run. Every subsequent
`mpiexec` — including ones that had been green minutes earlier — then aborted
immediately with

```
=   BAD TERMINATION OF ONE OF YOUR APPLICATION PROCESSES
=   PID <pid> RUNNING AT <container-id>
=   EXIT CODE: 135
=   CLEANING UP REMAINING PROCESSES
```

**135 = 128 + 7 = SIGBUS**, raised when MPICH touches a shared-memory page it
cannot back. `df -h /dev/shm` inside the container read **64M used, 0 avail,
100%**, holding **28** orphaned `mpich_shm_*` segments dated 2026-08-27 through
2026-08-28 — three of them 16.9 MB, from the interrupted run. No MPI process
was alive; nothing owned them. **Recovery is cheap** — no force-recreate, no
container restart:

```bash
docker compose -f docker/docker-compose.yml exec -T fem-em-solver \
  bash -lc 'rm -f /dev/shm/mpich_shm_*; df -h /dev/shm'
```

Verified clean afterwards: shm 0%, and `mpiexec -n 2 python3 -c "from mpi4py
import MPI; c=MPI.COMM_WORLD; print(c.rank, c.allreduce(1))"` returns `2` on
both ranks, exit 0.

**The segment size is a pure function of local rank count**, ~1.06 MB/rank,
independent of problem size or mesh — measured live, and the 16-rank row is not
extrapolation (it is the size of the orphans the interrupted run left):

| ranks | segment | orphaned runs before `/dev/shm` is full |
|---|---|---|
| 1 | 1.06 MB | 60 |
| 2 | 2.12 MB | 30 |
| 8 | 8.46 MB | 7 |
| 12 | 12.69 MB (measured live at `15e596f`) | 5 |
| 16 | 16.92 MB | 3 |

So a *single* run of any legal width fits comfortably; what kills the container
is **accumulation**. A clean exit releases its segment, so this is purely a
kill/timeout aftermath — and each kill permanently burns a slot until someone
clears it. At the project's `-n 12` ceiling the **sixth** killed run poisons the
box; the standard `-n 2` recipes give 30. Note that `timeout -k 30` firing
(exit 124) is itself a kill and leaks a segment like any other.

**Do not read a post-kill `EXIT CODE: 135` as a regression** — same discipline
as the FFCx JIT-cache entry below, and the two compound: a killed run can leave
*both* a poisoned JIT cache and a leaked shm segment, so clear both before
trusting any failure that follows a kill. Suspect this whenever a previously
green command fails instantly with 135 and no Python traceback.

**Not fixed, and one-line to fix:** `docker/docker-compose.yml` sets no
`shm_size`, so the container is on Docker's 64 MB default. `shm_size: 2gb`
would raise the orphan headroom to ~120 sixteen-rank runs and costs nothing
unused (`/dev/shm` is tmpfs — RAM is consumed only by pages actually touched).
Deliberately left unapplied here; it needs a container re-create to take effect.
Related: the **12-rank ceiling is not enforced against an interactive session** —
`scripts/automation/hooks/bash_guard.py:36-43` is a PreToolUse hook, so it
denies `mpiexec -n >12` only from agent sessions. The 16.9 MB orphans above are
what an unguarded human-typed `n` looks like.

### A killed harness run poisons the FFCx JIT cache, and the *next* run fails unrelated forms with "JIT compilation timed out" (`OPS-17` step 3 attempt 3, 2026-08-18)

**Verified at `2f97048`, 00:00 implementer slot.** Two complex-mode legs were
killed at their ceilings by `timeout -k 30 570` (exit 124,
`20260818T050123Z_OPS-17-step3c-complex-portgap.log` and
`20260818T051115Z_OPS-17-step3c-complex-remainder.log`). In the *second* of
those, `tests/solver/test_coil_phantom_magnetostatics.py::test_coil_phantom_magnetostatics_matches_the_two_loop_closed_form`
FAILED at 67% — a test that is green in real mode and whose gated quantity
(17.1233% L2 against a 30% band, `OPS-17` step 2) has nothing to do with the
build mode. Re-run alone it fails in **14.09 s** with

```
RuntimeError: Failed just-in-time compilation of form: JIT compilation timed
out, probably due to a failed previous compile.
Try cleaning cache (e.g. remove /root/.cache/fenics/libffcx_forms_<hash>.c)
or increase timeout option.
```

(`20260818T052132Z_OPS-17-step3c-coilphantom-complex.log`, exit 1, 15 s.) The
form's compile was interrupted mid-flight when the first leg was killed; the
lock file it left in `/root/.cache/fenics/` makes every later process wait out
the JIT timeout and raise. **The failure is an artifact of the kill, not a
regression** — do not open a chunk against the test on this evidence, and do
not trust *any* failure in a run that follows a killed one until the cache is
cleared. Suspect this whenever a fast, previously-green test fails in seconds
with a `dolfinx/jit.py` `RuntimeError` rather than an assertion.

**⚠️ PARTLY SUPERSEDED 2026-08-18 (`OPS-17` step 3 leg (b1), 07:30 slot).** The
cache-poisoning mechanism above is real and confirmed: `rm -rf
/root/.cache/fenics` is sufficient (no force-recreate needed), and the JIT
`RuntimeError` message does change with cache state. But the **conclusion drawn
about this particular test was wrong**. On a genuinely cold cache the test does
*not* return to green — it fails in **5.58 s** with a real complex-mode defect
(`ComplexComparisonError`, next entry). The poisoned cache was masking a
pre-existing failure, not creating one. Read this entry as "a killed run makes
the *message* untrustworthy", not "a killed run makes the *failure* spurious":
after clearing the cache you must still re-run and read the new message.

Measured cache-state → message map for this one test, all at `-n 2` complex:

| Cache state | Result | Message |
|---|---|---|
| poisoned by a kill mid-compile | FAILED 14.09 s | `JIT compilation timed out, probably due to a failed previous compile` |
| warm from a *completed* prior leg | FAILED 13.92 s | `Failed just-in-time compilation of form: Compilation failed on root node.` |
| cold (`rm -rf /root/.cache/fenics`) | FAILED **5.58 s** | `ComplexComparisonError: You can't compare complex numbers with max.` |

**Sizing corollary, measured 2026-08-18 (leg (b1) attempt 2, 09:00 slot).**
Clearing the cache is correct but it is not free, and it is the dominant cost
of a complex leg — not the solves. Same commit, same command shape, complex
`-n 2`: `tests/solver` on a **cold** cache exhausted a 480 s window at 61%
(`20260818T140137Z_OPS-17-step3e-complex-solver-tail.log`, exit 124), while on
a **warm** cache the same directory (minus the coil-phantom file) is
**46 passed / 2 xfailed in 111.22 s**
(`20260818T141104Z_OPS-17-step3e-complex-solver-warm.log`, exit 0) — ~2.7× the
41 s real-mode number, i.e. the recorded 2.6× rule holds. The file the cold leg
died in, `test_gauge_penalty.py`, is 8 passed in 20.33 s standalone warm
(`20260818T141020Z_OPS-17-step3e-complex-gaugepenalty.log`), so a cold-leg
death location says nothing about which test is expensive. **Never infer a
per-test cost from a cold-cache run, and never let compilation and measurement
share one window** — size the first post-clear command as a throwaway warm-up.

### ~~`test_coil_phantom_magnetostatics` fails in the complex build on a cold FFCx cache: `ComplexComparisonError`~~ **RESOLVED 2026-08-19 (`OPS-20`, 06:00 implementer slot)** (`OPS-17` step 3 leg (b1), 2026-08-18)

> **Resolved 2026-08-19, `OPS-20` step 1 — fixed, not marked.** The Cause row
> below is wrong and the 03:00 review's re-pointing was right: the `max` never
> entered through a DolfinX/UFL helper. It came from the test's **imported**
> drive callable — this file uses
> `tests/validation/test_circular_loop.azimuthal_current_density`, whose
> `ufl.max_value` `OPS-22` had already replaced with a regularise-inside-the-
> `sqrt` form at the 04:30 slot. So the commissioned defect was **already dead
> on arrival** and a free grep of the import line localized it; no cold-cache
> window was spent. What remained was the *second layer* `OPS-22` warned
> `OPS-20` to expect: with the form compiling, the complex run reached the
> print block and died at
> `ValueError: Unknown format code '%' for object of type 'complex'`
> (`test_coil_phantom_magnetostatics.py:145`) — `evaluate_vector_field_parallel`
> returns the complex scalar type although this magnetostatic solution is
> real-valued. Note the **rank split** that message produces: only rank 0
> executes the print block, so the diagnosis run read `1 failed` on rank 0 and
> `1 passed` on rank 1 in the same command. Fixed with the `OPS-22` idiom —
> assert `max|Im B_z| ≤ 1e-12·max|B_z|`, then compare on `np.real` (a new
> complex-mode assertion; exactly zero and a no-op in real mode). The
> non-collective ~300 s exit hang is gone with the raise: every run in this
> slot returned a footer in ≤ 8 s.
>
> **Numbers** (`-n 2`, all four runs footered, exit 0 except the diagnosis):
> real-mode control before any edit `20260819T110051Z` — 1 passed / 5.81 s,
> L2 **17.1233%**, the `OPS-17` step-2 record to the digit; complex diagnosis
> `20260819T110111Z` — 1 failed (rank 0) / 6.19 s, the `ValueError` above with
> a user frame under `--tb=long`; complex after the fix `20260819T110144Z` —
> **1 passed / 5.11 s, L2 17.1233%**, both ranks identical, i.e. the complex
> build passes the *same* 30% gate at the *same* digits; real-mode re-run
> `20260819T110156Z` — 1 passed / 3.36 s, **17.1233%** unmoved, so the fix
> moves no real-mode digit. No `@real_only` marker anywhere, so the complex
> collect count is **unchanged at 49** and `OPS-17`'s bookkeeping does not
> move. Stub sweep `find /root/.cache/fenics -name '*.c' -size 0` clean before
> and after.
>
> **For `OPS-17` leg (b1):** the coil-phantom exclusion recorded when that leg
> closed is now discharged in principle — the file is green in the complex
> build. A whole-`tests/solver` complex batch attempted as confirmation in this
> slot **timed out at 89%** (`20260819T110220Z`, exit 124, 481 s) and is
> therefore **uncounted** — no footer, no count claim. The coil-phantom test
> itself is visible PASSED on both ranks at 10% in that log. Separate finding
> for the review: complex `tests/solver` fit 111.22 s warm on 2026-08-18 and no
> longer fits a 480 s window, which points at cold forms added since (`POST-5`
> step 2 is the candidate), not at this fix.

**Verified at `93fc531`, 07:30 implementer slot,
`20260818T124742Z_OPS-17-step3d-coilphantom-complex-cleancache.log`**, `-n 2`,
complex build + `FEM_EM_REQUIRE_COMPLEX=1`, `/root/.cache/fenics` removed
immediately before the run.

| | |
|---|---|
| **Test** | `tests/solver/test_coil_phantom_magnetostatics.py::test_coil_phantom_magnetostatics_matches_the_two_loop_closed_form` |
| **Symptom** | `ufl/algorithms/comparison_checker.py:66: ufl.algorithms.comparison_checker.ComplexComparisonError: You can't compare complex numbers with max.` — **1 failed in 5.58 s**, raised during form compilation, before any assertion runs. |
| **Mode** | Complex build **only**. Real mode is green and gates 17.1233% L2 against a 30% band (`OPS-17` step 2). Nothing about the gated quantity is complex-valued; this is a UFL-level rejection of a `max`-style comparison in a form that is assembled with a complex scalar type. |
| **Cause** | **Not diagnosed.** The run used `--tb=line`, which printed only the UFL frame and no user frame, so the offending expression is not localized. `grep` for `max_value`/`min_value`/`conditional(` across `src/` finds exactly one hit (`src/fem_em_solver/post/sar.py:286`), which this test does not exercise — so the comparison most likely enters through a DolfinX/UFL helper (a cell-size or clamp expression) rather than a literal `ufl.max_value` call. **One command settles it:** re-run this file alone on a cleared cache with `--tb=long`. |
| **Not** | Not the cache artifact the previous entry claimed, and not a regression from any recent chunk — no completed complex leg had ever reached this file before today, so it has no known-green complex history. |
| **Scope** | `OPS-17` is test-hygiene bookkeeping and deliberately did not fix it. Whoever fixes it should record whether the complex build ever needs this magnetostatic path at all — if not, an explicit `@real_only` marker is a legitimate disposition and is cheaper than making the form complex-safe. |
| **Resolves with** | `OPS-20` (commissioned 2026-08-18 10:30 review): one `--tb=long` cold-cache diagnosis, then fix-or-mark, real-mode record 17.1233% re-asserted unmoved either way. **Re-pointed 2026-08-19 03:00 review:** the Cause row's "DolfinX/UFL helper" hypothesis is disfavoured — every other instance of this error class was a fixture-side `max`/ordering predicate in the test's own drive callable (see the `OPS-22` entry above); start the diagnosis by grepping this test's drive construction. |

### The complex-power identity reads 3–5e-9 at degree-2 N1curl on the coil fixture, against a 1e-9 family bound — and the quantity it gates is 99.6% spurious electric energy (`TH-12` step 2, 2026-08-18)

**Verified at `92fc3e7`, 15:00 implementer slot,
`20260818T200059Z_TH-12-step2-full.log`** (exit 1, 546 s, `-n 8`, complex
build, `TH12_STEP2_MODE=full`, 138 619 cells at 10 MHz).

| | |
|---|---|
| **Tests** | `tests/validation/test_coil_loading_degree2.py::test_complex_power_identity_holds_at_this_order[loaded-2]` and `[free-2]` |
| **Symptom** | `AssertionError: complex-power identity broken on the loaded solve at degree 2: reaction -2.117210e+03 Ohm vs energy -2.117210e+03 Ohm, relative 4.5931e-09` (free: 3.0030e-09). The degree-1 rows of the same run, same mesh, same process are green at **8.0743e-15 / 8.7088e-15** — three orders of magnitude *inside* the bound, so this is an order effect, not a fixture or reduction defect. |
| **Cause** | Diagnosed by inspection of the printed energies, not fixed. `Im Z = 4ω(W_m − W_e)/I′²` is exact for the discrete solution, so the residual is arithmetic cancellation — and at degree 2 the cancellation is catastrophic because `W_e` explodes. Degree 1: `W_m` 3.04e-08 J, `W_e` **2.03e-13 J** ⇒ `Im Z` = **+9.02 Ω**, the physical loop reactance. Degree 2: `W_m` 3.13e-08 J (unmoved, 3%), `W_e` **7.16e-06 J** — 3.5e7× larger — ⇒ `Im Z` = **−2.117e+03 Ω**. The ungauged curl-curl operator's gradient null space is vastly richer at second order (882 296 DOFs vs 162 710) and the penalty-free formulation lets irrotational content sit in `E` at an amplitude that swamps the magnetic term. |
| **What it does and does not invalidate** | The spurious term is **common-mode**: it cancels in the loaded−free difference, so `ΔX` moves only −0.5666 → −0.5625 Ω (0.7%) and `ΔR` is unaffected. `TH-12` step 2's `ΔR` reading is therefore not contaminated by this. What is destroyed is the **identity's discriminating power at degree 2 on this fixture**: it now gates a number that is 99.6% non-physical, so passing it would mean little and failing it at 5e-9 means only that 2 117 Ω minus 2 117 Ω leaves 1e-5 Ω of round-off. |
| **Not** | **Not** to be fixed by widening `IDENTITY_TOLERANCE` — the bound is the `TH-11` step-2f family's, it is met at 1e-14 at degree 1 in the very same process, and widening it would hide the `W_e` explosion that is the actual finding. Not the magnetostatic degree-2 null-space failure either (different formulation, barred by `TH-12`'s scope guard) — though the two rhyme, and that rhyme is the hypothesis worth testing. |
| **Fix** | Not attempted; `TH-12` step 2 is a reading with no gate. The candidate dispositions, cheapest first: (a) re-anchor the identity at degree ≥ 2 on the **difference** `Im ΔZ` rather than the absolute `Im Z`, which is the quantity every downstream claim actually uses; (b) measure the gradient content of `E` directly (Helmholtz split, or `‖∇·(εE)‖` against a null-space projector) and report it as the degree-2 cost line; (c) treat it as a formulation defect and price a gauged/regularised second-order path. (a) is a test change, (b) is a measurement, (c) is a chunk. |
| **Resolves with** | `TH-12` **step 3** (commissioned 2026-08-18 18:00 review): the affordable form of disposition (b) — measure whether the `W_e` explosion is generic to incompatible drives (smoke fixture, `J·n ≠ 0`) or coil-feed-specific, at degrees 1/2 on the smoke + sphere fixtures at smoke cost. Dispositions (a)/(c) stay contingent on its reading — both need the 62 GiB coil solve to verify at degree 2. Until then this file **fails by default** (`TH12_STEP2_MODE` defaults to `full`), and `probe`/`calibrate` modes remain green. |
| **Step-3 reading (2026-08-19, `20260819T183425Z_TH-12-step3-warm.log`, `tests/validation/test_degree2_energy_mechanism.py`, 8 passed / exit 0 / 10 s at `-n 2`)** | **COIL-SPECIFIC** at the pre-registered ≤ 10×-on-both band. Cross-order move in `W_e/W_m`: smoke fixture (incompatible axial drive, `J·n ≠ 0` on the end caps, 1 405 cells) **1.155×** (2.164348 → 2.499688); lossy sphere (imposed field, 5 866 cells) **1.015×** (1.068190 → 1.052552); this coil **3.426e+07×** (6.677632e-06 → 2.287540e+02). So **`J·n ≠ 0` is not sufficient** — the incompatible-drive hypothesis in the "Cause" row above is refuted as *stated*, and the ungauged-gradient explanation now has to say why only this fixture displays it. **Confound the step could not separate, measured:** the fixtures' baseline `W_e/W_m` spans **2.16 / 1.07 / 6.7e-6**, so a contamination of fixed *absolute* size moves the quasi-static coil's ratio ~1e6× more than either cheap fixture's; "the coil's feed model injects it" and "only a `W_m ≫ W_e` fixture can display it" both survive the reading. Splitting them needs a magnetically-dominated fixture with a compatible drive, or the absolute gradient content of `E` (disposition (b) proper, unscoped). **This entry stays open**; the two degree-2 identity tests stay failing at the unloosened 1e-9 bound, and no coil number moved. |
| **`TH-13` step-1 reading (2026-08-30, `20260830T020301Z_TH-13-step1.log`, `tests/validation/test_degree2_gradient_discriminator.py`, 1 failed / 12 passed / 1 skipped, exit 1, 36 s at `-n 2`)** | **The discriminator did not discriminate — a pre-registered negative result on both of its clauses, and the failing precondition assert is a deliberate red on `main`.** The fixture was `POST-5` step 2's closed azimuthal loop (`div J = 0`, `J·n = 0`) on the smoke box's own 1 405-cell mesh at 10 MHz, the missing magnetically-dominated-plus-compatible-drive cell of the step-3 table. (i) **Precondition failed:** degree-1 `W_e/W_m` = **1.952350e-02** against the pre-registered ≤ 1e-2 — a factor of 1.95 miss, so the fixture is *not* magnetically dominated and is not that cell. The number is unsurprising in hindsight: `W_e/W_m ~ ω²` at fixed impressed current, and the smoke box's own 2.164348 at 127.74 MHz scaled by (10/127.74)² predicts 1.33e-2. (ii) **Verdict IN-BETWEEN:** the loop's cross-order move is **5.156e+01×**, between the pre-registered 10× (FEED) and 1e3× (CLASS), so the reading is recorded and no band was invented in-slot (test skips, per §7). What the run *does* establish: **both step-3 controls reproduced to the digit on this code path** — smoke 1.155× (2.164348 → 2.499688) and sphere 1.015× (1.068190 → 1.052552) at the 1% band — so nothing has drifted since 2026-08-19, and `|Im P|/Re P` = 0.000e+00 at both orders on the loop. The suggestive part of the in-between number: degree 2 lifts the loop's `W_e` 63.7× (5.621559e-19 → 3.579741e-17 J) while `W_m` moves 1.23×, landing `W_e/W_m` at **1.006682** — i.e. at the same O(1) equipartition the smoke (2.50) and sphere (1.05) fixtures already sit at, and nowhere near the coil's degree-2 **229**. That is consistent with an absolute gradient contamination that saturates at equipartition, which neither band was written to catch. **This entry stays open**; nothing is fixed, no coil number moved, the two degree-2 identity tests stay failing at the unloosened 1e-9 bound. **Rescope hypothesis for the review** (not executed in-slot — §7 pins 10 MHz): the ω² scaling puts the precondition in reach at ≤ 7 MHz and puts it at ~2e-4 at 1 MHz, which is also far enough below equipartition that a 1e3× move is *representable* — at 1.95e-2 a CLASS reading was arithmetically capped at ~50× before the run started, so the fixture could not have returned CLASS whatever the physics. |

### ✅ RETIRED 2026-08-11 — "unexplained" mid-command termination of the logging harness was the background-and-end-turn trap (2026-08-08, 15:00 and 19:30 implementer slots)

**Retired by the 2026-08-11 10:30 review — cause named, with wrapper-log
evidence; nothing host-side ever killed anything.** Both slots' automation
wrapper logs end with the session announcing it is waiting on a
*backgrounded* harness run, then `exit=0` at the exact minute the harness
log stops: `logs/automation/20260808T200001Z_implementer.log` ends "Stage 2
is running … I'll report when the monitor fires", `exit=0` 20:16:37Z
(death ~20:15Z); `logs/automation/20260809T003001Z_implementer.log` ends
"Waiting on the background solve … I'll report when it lands", `exit=0`
00:33:04Z (the log's last flushed write, to the minute). A headless
`claude -p` session that ends its turn exits the CLI and SIGKILLs its
process tree — harness included: footerless log, no journal, dirty tree.
This is the same mechanism, established the same way, as the three `MAT-6`
step 7 deaths root-caused by the 2026-08-11 03:00 review (attempts.md
2026-08-11T08:00Z). It explains every anomaly this entry catalogued: the
6.7× spread in time-to-death (it is when the session chose to end its turn,
not a resource ceiling), the never-restarted container, the missing
attempts.md entries (the session died with its journal unwritten), and the
stage-uncorrelated kills (MESH_ONLY ran clean *foreground*). The fix is the
foreground recipe already landed in implementer-run.md and the §9 rubric
trap list (03:00 review commit `bc86367`); this commit names the cause,
which is the condition this entry set for leaving. **The standing
instruction below is lifted**: `MAG-13` step 2 is retryable under the
foreground recipe (re-queued §9 item 3, 2026-08-11 10:30), and the
operator's host-observables ask (`dmesg`, `journalctl`, WSL2 reclaim) is
withdrawn from Waiting-on-you. Original record retained below.

**Observed twice — the standing instruction below has fired; `MAG-13` step 2
is escalated, not retryable.** The second occurrence is recorded after the
first-occurrence text; the two are compared at the end of this entry.

Observed first during `MAG-13` step 2's stage-2 solve
(`timeout 1200 mpiexec -n 4 python3 scripts/probes/mag13_step2_probe.py`,
started 20:04:51Z), the harness died ~660 s in — the log
(`20260808T200451Z_MAG-13-step2-solve-n4.log`) ends mid-Netgen with **no
`## Exit` block** and no `test-results.md` row. That is not the command
exiting: `run_and_log.sh` writes an Exit block even on non-zero status (it
did so for the same slot's stage-1 run forty minutes earlier), so the
harness process itself was killed from outside. The kill fell well inside
the command's own `timeout 1200` and well before the slot's 65-minute hard
kill (21:05Z). Not a container-cgroup OOM signature either — those
manifest as the *command* dying with signal 9 / exit 137 and an Exit block
written (see `MAT-6` step 6's two on-record examples). The session died
with its harness: no attempts.md entry, nothing committed or parked
(journaled by the 16:30 slot; artifacts landed by the 18:00 review,
`8b8a706`).

**Second occurrence — 2026-08-08, 19:30 slot.** The same command on the same
probe (`timeout 1200 mpiexec -n 4 python3 scripts/probes/mag13_step2_probe.py`,
started 00:31:25Z) died again, log
`20260809T003125Z_MAG-13-step2-solve-n4-cap16G.log`: 43 437 B, 627 lines, no
`## Exit` block, no `test-results.md` row, stopping mid-Netgen volume
optimisation (`Total badness = 1.36536e+06`). Last flushed write 00:33:04Z —
**≈ 99 s after start**, versus ~660 s for the first occurrence. That slot also
left no attempts.md entry; its tree was journaled by the 21:00 slot and parked
by the 22:30 slot on `recovered/20260809T033023Z`. The log's one durable
measurement: `CGROUP_MEMORY_MAX=17179869184` (16 G) confirmed at the kernel
before any solve, so `MAT-6` step 6's cap no longer rests on a compose-file
read.

**Common factors, and the ones ruled out (22:30 slot, 2026-08-09):**

| | 15:00 slot | 19:30 slot |
|---|---|---|
| log | `…200451Z_…-n4.log` | `…003125Z_…-cap16G.log` |
| died after | ~660 s | ~99 s (flushed-output bound) |
| stage reached | `Done optimizing mesh (Wall 149.77s)` | mid-volume-optimisation |

Shared: same probe, same `-n 4`, same `run_and_log.sh` → `docker compose exec`
path, both truncated with no Exit block, neither at its `timeout`, neither at
its session hard kill, neither with a kernel OOM signature. **Ruled out — the
container did not restart.** `docker inspect` at 03:30Z reports
`StartedAt = 2026-08-08T20:00:21Z`, `RestartCount = 0`; the container has been
continuously Up across **both** deaths (20:15Z and 00:33Z). So the cause is not
a container/cgroup restart, and it is not inside Docker's lifecycle — the
host-side process tree is being killed. The 6.7× spread in time-to-death also
argues against a deterministic per-run resource ceiling, which would land at a
repeatable point on a fixed fixture.

**MESH_ONLY discriminator executed — 2026-08-09, 07:30 slot; the physics is
exonerated and the kill is *not* stage-correlated.** The queued next step ran
(`20260809T123053Z_MAG-13-step2-meshonly-diag.log`, exit 0, 188 s harness-wall,
668 lines, `## Exit` block present, `test-results.md` row written): the same
probe, same `-n 4`, same harness path, `MAG13_STEP2_MESH_ONLY=1`, FFCx cache
cleared first. It **reproduced the mesh rung exactly** — **1 097 873 cells**,
equal to the 2026-08-08 record digit for digit, in 185.7 s (record 192.7 s,
−3.6%); the log is structurally identical to the record's, both with their two
`Done optimizing mesh` lines at the same line numbers (486 / 663; fine
volume-optimisation wall 142.4 s here vs 147.8 s on record). Container state
before and after: `StartedAt = 2026-08-08T20:00:21Z`, `RestartCount = 0`, Up
17 h — unchanged across this run and both deaths.

**What that rules out, and the part that contradicts the pre-decided reading.**
Branch (a) of the §7 plan fired literally — MESH_ONLY completes — but its
inference ("the kill is specific to the longer/heavier solve stage") does **not
survive this run's own comparison**: the 19:30 death stopped mid-Netgen *volume
optimisation* of the fine mesh (`Total badness = 1.36536e+06`, before any
`Done optimizing mesh (Wall 14x s)` line and before any solve), i.e. inside the
very phase MESH_ONLY has now completed **twice** at the same rank count and
resolution. So no stage owns the kill: one death is in the mesh phase, one past
it in the solve, and the mesh phase runs clean on demand. Combined with the
6.7× spread in time-to-death and the never-restarted container, the surviving
hypothesis is a **non-deterministic host-side kill of the process tree,
uncorrelated with the computation** — WSL2 memory reclaim / a host session
supervisor are the live candidates, and none of it is observable from inside
the container.

**Standing instruction (unchanged in force):** a run that finds its log
truncated this way should treat the measurement as *unobserved*, not failed.
Do **not** spend a slot on the `MAG-13` step 2 solve — the stage-2 attempt
stays blocked pending a review, and the diagnostic budget for it is spent
(three data points, physics exonerated). What is left needs the **human
operator**: host-side observables at the timestamps of the two deaths
(20:15Z and 00:33Z on 2026-08-08/09) — `dmesg -T`, `journalctl -k`, WSL2
`vmmem` reclaim, any host cron/session supervisor. On the dashboard's
Waiting-on-you as of this slot. Cause unknown; this entry leaves only with a
commit that names and fixes it.

### ✅ RETIRED 2026-08-09 — "rank-dependent DG0 centerline sample" was the probe's own bug (`MAG-6` step 4, second pass)

**There is no rank-safety defect.** The 00:00 slot completed step 4's missing
rungs and the claimed defect is **refuted with its own signature measured**:
the probe's `instrumented_eval` inflated `|B|` by exactly **√3** at any point
whose claiming rank held *only that one point*. `Function.eval` squeezes its
return to shape `(3,)` for a single point, so `rank_vals[k]` was the scalar
x-component and `values[i] = rank_vals[k]` broadcast it across all three
components. Measured ratio at the two affected points
(`20260809T050838Z_MAG-6.log`, `WRITECHECK` lines):
`4.852607687905e-07 / 2.801654354883e-07 = 1.7320508` and
`2.853753669222e-07 / 1.647615449126e-07 = 1.7320508` — √3 to 8 digits. The
production path `post/evaluation.py::evaluate_vector_field_parallel` is
**immune by construction**: it assigns `values[rank_indices] = rank_values`, and
numpy broadcasts a `(3,)` row into a `(1, 3)` slice correctly. Nothing under
`src/` was ever wrong; the one-line fix is in the probe
(`scripts/probes/mag6_step4_probe.py`, `.reshape(-1, 3)`).

**The rank-invariance identity holds.** On the gate's own evaluation path at
the validated `gauge_penalty=1.0`, the centerline jump ratio reads
**0.251272 / 0.250416 / 0.250453** at `-n 1 / -n 2 / -n 4` — a three-way spread
of **0.341%**, against the ≤ 10% band, with the mirror-symmetry control on the
same solves at 0.311226 / 0.311166 / 0.311157 (**0.022%**). Logs
`20260809T050259Z` (`-n 1`, 152 s), `20260809T050621Z` (`-n 2`, 10 s),
`20260809T050202Z` (`-n 4`, 12 s), all `_MAG-6.log`.

**So step 3's 88% scatter is gauge contamination after all** — the mechanism
the first pass believed it had refuted. It "refuted" it by comparing 0.250406
at `-n 2` against 0.328496 at `-n 4`, but that `-n 4` number was a probe
call-1 value carrying the √3 bug; the same run's library-path value is
0.250417. At the sub-floor `gauge_penalty=1e-3` the gate fixture uses, the
scatter is real; at 1.0 it is 0.341%. **A fix chunk on the DG0 evaluation path
is not needed and must not be scoped.** Whether the *gate fixture* should stop
solving below the validated gauge floor is a separate, live question for a
review — `MAG-6` stays ✅ either way, passing its untouched 0.60 bound at every
rank count measured. Confirming run after the probe fix:
`20260809T050930Z_MAG-6.log` — all four evaluations in one process bitwise
identical, zero `WRITECHECK` DIFF, metric 0.250457 at `-n 4`.

*Original entry, retained for the record:*

**One cell's `B` value depends on the rank count, on a mesh and an owning cell
that are provably identical.** Diagnosing `MAG-6` step 3's 88% rank scatter in
the centerline jump-ratio metric, step 4 instrumented the point evaluation
(`scripts/probes/mag6_step4_probe.py`; no `src/` change) and eliminated both
mechanisms step 3 had proposed:

- **Not mesh noise.** `MESH_FINGERPRINT` (global cell count plus reduced
  midpoint moments) is `cells=55784 m1=-4.9768680987…e+00 m2=7.977798997317e+02`
  in **every** run — `-n 2`, `-n 4`, and a fixed-rank repeat — agreeing to 12
  significant digits (the last digit of `m1` moves with reduction order alone).
  The mesh is reproducible run to run; step 3's 6.8% "mesh drift" attribution
  does not survive.
- **Not partition-owned sampling.** `CENTERLINE_MULTICLAIM = 0/9` and
  `CENTERLINE_MULTICELL = 0/9` at both rank counts: every centerline point is
  claimed by exactly one rank and collides with exactly one cell, so the
  `links[0]` / rank-order-overwrite ambiguity in
  `post/evaluation.py::evaluate_vector_field_parallel` never fires here. The
  **chosen cell midpoints are identical across `-n 2` and `-n 4` for all nine
  points**, printed to 9 decimals.
- **Not gauge contamination.** The fixture solves at `gauge_penalty=1e-3`,
  below the validated floor of 1, and raises `GaugeContaminationWarning`. Re-run
  at `gauge_penalty=1.0` the scatter persists: jump ratio 0.250406 at `-n 2`
  vs 0.328496 at `-n 4` (31%).

**What is left.** At `gauge_penalty=1.0`, eight of the nine centerline points
are rank-invariant to ~5 significant digits between `-n 2` and `-n 4`. The
entire metric spread is set by **one point, i=1 at z = -0.0225 m**, whose
sampled `|B|` reads `2.813455e-07` at `-n 2` and `4.852531e-07` at `-n 4` —
**72% apart, in the same cell** (midpoint
`(-1.204260909e-03, +4.174143551e-03, -2.041163735e-02)` in both). Same mesh,
same cell, same field definition, different rank count. That is a rank-safety
defect in the solve/interpolation path, not in the metric's reduction and not
in the sampling.

**A second, possibly related signal, not yet diagnosed:** the probe evaluates
the same `Function` at the same points twice in one run — once instrumented,
once through the library — and compares them exactly. They agree at `-n 2`
(`LIB_AGREES_WITH_INSTRUMENTED = True`) and **disagree at `-n 4`** (`False`)
in the same process, on the same unchanged `b_dg0`. Two identical evaluations
inside one run should be bitwise equal. Whether this is the same defect or an
independent one is unmeasured — the probe prints only the boolean, not the
magnitude of the difference.

**Impact and scope.** No gate is affected today: `MAG-6` stays ✅, the
centerline jump ratio passes its untouched 0.60 bound at every rank count
measured (0.250406–0.328496), and the ≤ 10% rank-stability claim belongs to the
mirror-symmetry metric alone — which on these same solves reads
0.306591 / 0.309126 / 0.310501 / 0.311161 / 0.311162, a **0.15% spread**, and is
therefore the in-fixture control showing the defect is localised to the
centerline sample rather than global to the solve. No fix is attempted here:
step 4 is diagnosis-only and a fix is a review-scoped chunk, not an in-slot
improvisation. Logs: `20260809T033322Z`, `…033350Z`, `…033403Z`, `…033514Z`,
`…033555Z`, `…033608Z`, all `_MAG-6.log`.

### ✅ RETIRED 2026-08-04 — reaction Z-matrix diagonal is negative where it must be inductive

**Fixed by `PORT-1` step 2f**: `TimeHarmonicSolver.solve()` now drives with the
CG1-weakly-solenoidal part of the prescribed current by default
(`project_source=True`, helper
`src/fem_em_solver/core/source_projection.py`), and the diagonal of
`test_port_reaction_impedance.py` is **gated**, not printed. Gate
`20260804T111102Z_PORT-1-step2f-gate.log`, 12 passed 1 deselected in 58.9 s at
`-n 2`, on the same fixture every measurement below was taken on:

| quantity | production path, projected | this entry's unprojected number |
|---|---|---|
| `Im Z₁₁`, reaction / energy routes | **`+7.437243e+00 Ω`** (both) | `−4.108550e+01 Ω` |
| `Im Z₂₂`, reaction / energy routes | **`+7.436633e+00 Ω`** (both) | `−4.092413e+01 Ω` |
| ratio to Grover `ωL = 6.818343 Ω` | **1.090770 / 1.090680** | −6.03 |
| complex-power identity residual | `4.0412e-11` / `9.1813e-11` (gated `< 1e-9`) | `1.8128e-10` |
| driven current | `I′ = 0.969001 A` | `I = 0.969009 A` |

The three gates are `test_projected_port_diagonal_is_inductive` (sign, a
priori, both ports, both routes), `..._satisfies_the_complex_power_identity`
(bookkeeping, `< 1e-9`) and `..._matches_grover` (the independent physics
anchor, band `(1.042, 1.140)` carried over from step 2e's measurement, which
the production path reproduced to 2e-5). The number reproduced step 2e's
hand-rolled `+7.437243e+00 Ω` to all seven printed figures — same physics,
now on the path callers actually use.

Nothing was widened to retire this: the diagonal moved from *ungated* to
gated, and the three files that pin the unprojected numbers (steps 2b, 2d, 2e)
now pass `project_source=False` explicitly and reproduce them unchanged
(`20260804T111221Z_PORT-1-step2f-regress-diagnosis.log`,
`20260804T111607Z_PORT-1-step2f-regress-remainder.log`). The original entry
follows, unedited, because the diagnosis chain in it is the reason the fix is
believable.

---

Found 2026-08-02 by `PORT-1` step 1; **diagnosed 2026-08-03 by step 2b to the
electric energy — see the update at the end of this entry — and still not
fixed.** The diagonal remains ungated. Recorded here because the number is wrong
in a way a later run would otherwise re-discover from scratch.

On the two-torus air fixture (a = 0.04 m, r_wire = 0.005 m, d = 0.04 m,
f = 10 MHz), the reaction integral `Z_i1 = −(1/(I₁Iᵢ))∫E₁·Jᵢ dV` returns
`Im Z₁₁ ≈ −40.9 Ω` (`-4.069329e+01j` at
`20260802T183226Z_PORT-1-step1-solve008.log:442`, and −41.09 / −40.97 at the two
boxsens configurations). A lossless loop must be inductive, `+ωL`; a Grover
estimate `ωL ≈ μ₀ωa(ln(8a/r_wire) − 2) ≈ 6.8 Ω` — **hand-evaluated, in no log**.
So the diagonal is wrong in sign and ~6× in magnitude, while the *off*-diagonal
on the same solve is right in sign and within 5–9% of its closed form. That
contrast points at the self-term (the source's own singular field inside the
driven wire entering `∫E·J` over the source region) rather than at a global
convention error, but nothing has been measured to confirm it.

**Consequence:** no input impedance and no `S₁₁` derived from this path means
anything yet. `PORT-1` step 2 therefore leaves the diagonal **ungated** —
deliberately, and *not* by widening a bound. `PORT-1` step 2b (§7) owns the
diagnosis, and its anchor is the complex-power identity
`Im Z₁₁ = 4ω(W_m − W_e)/|I₁|²` as an independent second derivation.

**Update 2026-08-03 — step 2b executed; the reaction integral is exonerated and
the anomaly is localised to the electric energy.**
`tests/validation/test_port_self_impedance_energy.py`, 3 passed in 43.5 s at
`-n 2` (log `20260803T050252Z_PORT-1-step2b-gate.log`), one mesh at padding
0.08 / h_far 0.03 and one solve:

| quantity | value |
|---|---|
| `Im Z₁₁`, reaction integral | `−4.108550e+01 Ω` |
| `Im Z₁₁`, complex-power route `4ω(W_m−W_e)/I²` | `−4.108550e+01 Ω` |
| relative disagreement | **1.8128e-10** (gated `< 1e-9`) |
| `4ωW_m/I²` (inductive part) | `+7.437 Ω` vs Grover `ωL = 6.818 Ω`, **ratio 1.0908** |
| `4ωW_e/I²` (capacitive part) | `+48.52 Ω` |
| `W_e/W_m` | 6.524 |

So the guess above — that the self-term of `∫E·J` is the bug — is **wrong**. The
two derivations agree to 1.8e-10, and the magnetic half is the physical loop
inductance to 9.1% of Grover, which is within what the PEC box at this padding
can plausibly account for. The whole of `−40.9 = 7.44 − 48.52` is an *electric*
energy excess in the solved field.

**Leading hypothesis, not yet measured:** low-frequency breakdown of the
curl-curl formulation. At ω → 0 the operator acts on the gradient subspace as
`−k₀²ε_c`, so any residual non-solenoidal component of the discretised impressed
current — the analytic azimuthal `J` is exactly divergence-free and tangent to
the torus surface, but the *faceted* meshed boundary is only approximately so —
is amplified into a spurious electrostatic field that contributes to `W_e` and to
nothing else.

**Correction 2026-08-03 (03:00 review): the ω-sweep named here as "the
discriminating measurement" does not discriminate.** Restricting the solved
equation to the gradient subspace gives `E_g = jωμ₀J_g/k₀² = jJ_g/(ωε₀) ∝ 1/ω`,
hence `W_e ∝ ω⁻²` and `4ωW_e/I² ∝ ω⁻¹` — **the same `1/(ωC)` a physical
capacitance gives.** Gradient-space contamination *is* a spurious electrostatic
response, so it necessarily scales like one, and the sweep separates only the
capacitive family (`ω⁻¹`) from an induction-driven `E = −jωA` (`4ωW_e/I² ∝ ω³`).
It is a cheap sanity check, not the discriminator; do not spend a run on it
expecting an answer.

What does settle it, and why this fixture makes it decisive: the two-torus
fixture has **no conductors** — the tori are tagged *air* subdomains carrying an
impressed `J`, the only metal is the outer PEC wall, and `∇·J = 0` analytically
means no charge. There is therefore **no physical capacitance available to
find**, so the open question is quantitative: does the gradient content of the
load account for all 48.52 Ω? Because the N1curl/CG1 discrete sequence is exact,
that is answerable by two assemblies and no extra solve —
`∫E_h·∇q dV = (j/(ωε₀))∫J·∇q dV` must hold for every `q ∈ CG1 ∩ H¹₀` — with the
energy share following from one cheap scalar Poisson solve. `PORT-1` step 2d in
`PROJECT_PLAN.md` §7 carries the plan; `tests/validation/test_current_divergence.py`
(`POST-3` step 3) is the second, structural route to the same question.

**Update 2026-08-03 — step 2d executed; the answer is "all of it", and the cause
is now measured rather than hypothesised.**
`tests/validation/test_port_gradient_load.py`, 7 passed in 41.5 s at `-n 2` (log
`20260803T183556Z_PORT-1-step2d-gate.log`), same mesh, one curl-curl solve and
one CG1 Poisson solve:

| quantity | value |
|---|---|
| identity `∫E_h·∇q = (j/ωε₀)∫J·∇q`, relative residual | **4.4916e-09** (gated `< 1e-7`) |
| blind control, `j` dropped | 1.4142e+00 = `√2`, as the identity implies |
| `‖P_G J‖²` | `2.534713e-02` (two routes agree to 7.9e-15) |
| `4ωW_e^spur/I² = ‖P_G J‖²/(ωε₀I²)` | **`4.852262e+01 Ω`** |
| measured `4ωW_e/I²` | `4.852271e+01 Ω` |
| **ratio** | **0.999998** |

So the "leading hypothesis" above is confirmed *quantitatively*: the gradient
content of the **discretised** impressed current, amplified by `1/(ωε₀)` on the
subspace where the operator acts as `−k₀²ε_c`, is two-parts-in-a-million the
entire electric-energy excess. Nothing is left for a second mechanism. The
negative diagonal is an artifact of the current representation — not the
reaction integral (step 2b), not physical capacitance (none exists here).

The identity's bound was raised 1e-9 → 1e-7 after a first run measured
4.4916e-09 and failed the plan's house guess; the gate reproduced 4.4916e-09
bit-for-bit. It is a solve-accuracy number, not a physics one — a rank-count,
mesh or solver change that moves it is information, so re-measure rather than
widening again. PROJECT_PLAN §7 `PORT-1` step 2d carries the full reasoning.

**Step 2e executed 2026-08-04 — the fix works, and this entry still stays
open.** `tests/validation/test_port_solenoidal_drive.py` drives the same mesh
with `J′ = J − P_G J` and gets the prediction to three figures
(`20260804T050616Z_PORT-1-step2e-gate.log`, 9 passed in 41.8 s at `-n 2`):

| quantity | projected drive | unprojected (this entry) |
|---|---|---|
| `Im Z₁₁`, both routes | **`+7.437243e+00 Ω`** | `−4.108550e+01 Ω` |
| ratio to Grover's `ωL = 6.818343 Ω` | **1.090770** | −6.03 |
| `4ωW_e/I′²` | `8.761041e-05 Ω` | `4.852271e+01 Ω` |
| `‖P_G J′‖²/‖J′‖²` | `4.5758e-33` | `8.175e-06` |
| complex-power identity residual | `1.6242e-14` | `1.8128e-10` |
| meshed current | `I′ = 0.969001 A` | `I = 0.969009 A` |

`4ωW_m/I′² = 7.4373 Ω` is step 2b's number unchanged, as it must be — the
projection moves `W_e`, not `W_m` — so the fixture's inductance was physical
throughout and the sign is now explained *and* demonstrated, not just
diagnosed.

The entry stays open because **the production driver still builds the
unprojected load**: `TimeHarmonicSolver.solve()` assembles
`−jωμ₀∫J·v̄` from the caller's `current_density` with no projection, so the
diagonal in `test_port_reaction_impedance.py` is still negative and still
ungated. Making the projection the port-excitation default is its own step.

**Consequence, unchanged:** no input impedance and no `S₁₁` off this path means
anything. The off-diagonal is unaffected — `PORT-1` step 2 gates `Im Z₁₂` to
9.35% of `ωM₁₂` and that number does not go through `W_e`.

Remove this entry with the commit that explains the sign.

*(That step is 2f and it landed 2026-08-04 — see the retirement header at the
top of this entry. The off-diagonal did move slightly, as the projection
changes the field and not only its gradient part: `Im Z₁₂` went from
`+1.125614e+00 Ω` (−9.35% of `ωM₁₂`) to `+1.142011e+00 Ω` (**−8.03%**), toward
the closed form, under the unchanged 10% gate.)*

### ✅ RESOLVED 2026-08-03 — "birdcage suite is over the compute budget" was the hang, not meshing cost

The 10:30 review's reinterpretation was right and `GEO-9` step 2b's cost probe
settles the figure. The claim was that
`tests/mesh/test_birdcage_port_tags.py` takes **~10 minutes** on its own and
that a full `tests/mesh` run exceeded a 700 s bound. **Measured at the fixed
geometry, default parameters, no coarsening:** the file is **8.95 s** of pytest,
harness 10 s (`20260803T200151Z_GEO-9-step2b-probe.log`), and the whole
directory at `-n 2` is **42.15 s**, exit 0
(`20260803T200504Z_GEO-9-step2b-gate.log`). The old number was a poisoned
process burning the harness `timeout` — pytest reported in ~3 s while the run
exited 124 at 180 s — so `resolution` never had to be coarsened from 0.015 and
the file needs no exclusion from routine runs. It is in CI as of this commit.

The **latent rank-local tag bug** recorded here is also fixed, and it was not
latent: `set(np.unique(cell_tags.values))` is per-rank, and at `-n 2` on the
newly-working mesh rank 0 reported P2/P3 missing while rank 1 reported P1/P4
missing. `GEO-9` step 2b switched the test to
`tests/mesh/helpers.py::global_cell_tag_set()` — the fix that was written and
reverted on request pending exactly this rework. The assertion content (core +
per-port tags all present) is unchanged.

### The gauge penalty is a workaround, not a gauge — closed by decision (2026-07-28)

`DEFAULT_GAUGE_PENALTY = 1.0` prices the curl-curl operator's gradient null space
rather than removing it (`PROJECT_PLAN.md` §7 `MAG-10`). This was previously the
highest-risk open item; the decision is recorded here so it is not reopened:

- `MAG-15` landed `GaugeMethod.LAGRANGE` — an (A, p) saddle point that removes the
  null space with no parameter — as a cross-check and diagnostic
  (`tests/solver/test_gauge_lagrange.py`). The penalty at 1.0 stays the production
  default on cost grounds (~2× at degree 1, ~7.5× at degree 2).
- Tree-cotree gauging is rejected: `TH-1`'s E-field formulation has no static null
  space at ω > 0 (the operator acts as −k₀²ε_c on the gradient subspace), so deeper
  magnetostatic gauge machinery has no Phase-2 payoff.
- The risk does **not** transfer to `TH-1` as gauge cancellation. The Phase-2
  silent-failure analog is *near-resonance ill-conditioning*, tracked in the
  `TH-1` formulation notes in `PROJECT_PLAN.md` §7.

### ✅ RESOLVED 2026-07-30 — truncation-wall modeling floor on the wire/loop fixtures (MAG-13)

The natural BC `n×H = 0` on a truncation wall contradicts Ampère's law for any net
enclosed current (`∮H·dl = I` vs `H_φ(R) = 0` forced at the wall), so it puts a
floor under these fixtures that no refinement removes.

**Straight wire: fixed 2026-07-30** (`MAG-13` steps 1–3). `test_straight_wire.py`
now imposes the analytic `A_z` on the exterior via
`core.solvers.exterior_dirichlet_bc`; measured 35.13% → 22.19% at h=0.004 on the
same mesh, and 22.19% → 12.75% → 9.26% across h = 0.004/0.0025/0.0018, i.e. still
converging at ~O(h^1.2) with no plateau. `J·n ≠ 0` at the end caps remains (the
`MAG-15` multiplier spread measures it) but is not what was dominating.

**Loop: fixed 2026-07-30** (`MAG-13` steps 4–5). `test_circular_loop.py` now
imposes the Jackson 5.37 off-axis `A_φ` on the outer sphere through the same
helper, and `test_convergence.py::test_h_refinement_straight_wire` fits the rate
over three resolutions (**1.10**, bound `[0.7, 1.5]`) instead of two.

One measurement worth keeping: on the *loop*, the analytic wall is ~20% **worse**
at fixed h than the natural one (16.23% vs 14.98% at h=0.0035; 10.37% vs 8.86% at
h=0.0025, on-axis `B_z` over `|z| ≤ 0.4 R`). Unlike the wire's Ampère-law
contradiction, the loop's natural-BC bias is a PMC image term of order
`(a/R)³ ≈ 3.7%`, which is *smaller* than the O(h) error that degree-1
interpolation of `A_φ` injects through the boundary data. What the Dirichlet wall
buys is the limit: 16.23% → 10.37% → 7.07% at h = 0.0035/0.0025/0.002 converges
monotonically to the analytic field (fitted ~1.4), where the natural wall
converges to a different field. The loop tolerance is therefore tightened
10% → 8% *at h = 0.002* (411k cells) rather than at the old h = 0.0025 — no
assertion was loosened to accommodate the better boundary condition.

Remaining, not blocking: `J·n ≠ 0` at the wire end caps, and the < 5% wire target
needs h ≈ 0.00125 (~1.1M cells, > 5 min at `-n 2`) — graded refinement (`MAG-9`),
not more uniform h.

### ✅ RESOLVED 2026-08-01 — `two_torus_domain` was not a conforming mesh (`GEO-8`)

The fixture added two tori and `occ.addBox` over them and never fragmented, so
gmsh meshed a solid box plus two torus islands: total mesh volume exceeded the
analytic box by exactly the two torus volumes (ratio `1.002633`), and driving
torus 1 with a tag-restricted source gave `∫|E|² dV` over tags (1, 2, 3) =
`2.0537e-04, 0, 0` — the field could not leave the driven island, which is why
`PORT-1` measured `Z₁₂ ≡ 0`.

Fixed by `occ.fragment` plus centroid/mass re-derivation of the physical
groups. Both signatures are now gated by
`tests/mesh/test_two_torus_conforming.py`: volume ratio `1.000000000`
(log `20260801T003528Z_GEO-8-after.log`) and air/driven `∫|E|²` ratio
`1.4118`, undriven/driven `5.2088e-08` (log
`20260801T003600Z_GEO-8-field-gate-numbers.log`). The Helmholtz users improved
rather than regressed: centre-field error `1.731% → 0.728%`.

### Air-box sizing is not generalised

Only `two_torus_domain` has `air_padding` and graded sizing. Every other fixture in
`io/mesh.py` — including the coil+phantom geometry all MRI work depends on — still
uses a single global `setSize` with padding tied to feature size. On Helmholtz that
pattern produced a **20.4% error that did not improve across a 7× refinement**, and it
was invisible until an analytic comparison existed. Coil+phantom has no analytic
reference yet. See `PROJECT_PLAN.md` §9.


### ✅ RETIRED 2026-08-10 (`EX-17`) — `02_circular_loop.py` never wrote its VTX/`.bp` output

Fixed by the one-file port of the `EX-14` diff: the writers now take the
`A_lag`/`B_lag` Lagrange interpolants the example already builds, each under
its own `try`, and `_check_vtx_roundtrip()` reads `circular_loop_B.bp` back
through ADIOS2 — in-memory and read-back max |B| both **7.756122914931e-05 T**,
relative difference **0.000e+00** vs the 1e-10 tolerance
(`20260810T200154Z_EX-17-gate-mag2.log`, exit 0, 124 s, `-n 2`). The pre-fix
state on record: `⚠ VTX output failed (ADIOS2 may not be available): Only
(discontinuous) Lagrange functions are supported` once per rank, and
`paraview_output/circular_loop_A.bp` opening with zero ADIOS2 variables.

### Every XDMF/VTX export of a Nédélec or DG field ships a Lagrange-P1 interpolant that disagrees with the solved field at O(20–52%) — everywhere in the cell, not only at vertices (`POST-4` step 4, 2026-08-12)

**What this affects.** Eleven interpolation sites in `examples/` build a
`("Lagrange", 1, (3,))` (or scalar `("Lagrange", 1)`) function for export;
**ten** of them are fed by a source that is not continuous in that space —
N1curl (`A`, `E`) or DG (`B`):

| file | line | source |
| --- | --- | --- |
| `examples/mri/01_coil_phantom_fields.py` | 413 | `A` N1curl, `B` DG1, `E` N1curl |
| `examples/magnetostatics/01_straight_wire.py` | 185 | `B` DG1 — **evaluated, not only exported** (see below) |
| `examples/magnetostatics/02_circular_loop.py` | 259 | `A` N1curl, `B` DG1 |
| `examples/magnetostatics/04_helmholtz_analytic_comparison.py` | 136 | `A` N1curl, `B` DG1 |
| `examples/magnetostatics/05_gauge_cross_check.py` | 198 | `A` N1curl, `B` DG1 (both gauges) |
| `examples/time_harmonic/01_lossy_plane_wave.py` | 109 | `E` N1curl |
| `examples/time_harmonic/02_pec_cavity_resonances.py` | 145 | eigenmode, N1curl |
| `examples/time_harmonic/03_dielectric_sphere_in_uniform_field.py` | 258 | `E` N1curl |
| `examples/time_harmonic/04_evanescent_waveguide_decay.py` | 246 | `E` N1curl |
| `examples/time_harmonic/05_resonance_guard_sweep.py` | 127 | `E` N1curl |

`examples/magnetostatics/06_h_convergence_rate.py:164` is the exception that is
*safe by construction*: it exports the CG1 function it also asserts on, so the
asserted field and the exported field are the same object.

**Measured magnitude** (`examples/mri/01` debug preset, 9261 cells, `-n 2`,
400 cell midpoints + 400 vertices, `20260812T003454Z_POST-4-step4-anchor-n2.log`,
exit 0, 4 s). Pointwise relative median of |P1 − source| / |source|:

| field | midpoints | vertices | scaled median (mid / vtx) |
| --- | --- | --- | --- |
| `A` (N1curl) | **51.17%** | 27.33% | 0.1032 / 0.0432 |
| `B` (DG1) | **52.47%** | 38.39% | 0.1590 / 0.0766 |
| `E` (N1curl) | **20.18%** | 15.79% | 0.1633 / 0.1116 |

**Two things this measurement settled, both against the prior expectation.**
(1) The artifact is *not* localized at shared vertices — the midpoint
disagreement is **larger** than the vertex disagreement in all three fields
(separation 0.4185× / 0.4818× / 0.6835×, where the step-4 entry predicted
O(50×) the other way). The wrong vertex dofs define the P1 interpolant over
the whole cell, so the interior inherits them; a vertex sample can also, by
chance, draw the same cell trace on both paths, which is why vertices read
*quieter*. (2) None of it is interpolation error. Interpolating the same three
sources onto a **DG1** target — same degree, no dofs shared between cells —
reproduces them to round-off (scaled median 3.25e-17 / 0.0 / 0.0), because all
three are degree-1 discontinuous polynomials and are represented exactly. The
entire disagreement is the P1 continuity constraint. Negative control: a
conforming P1 source round-tripped through the same machinery agrees to
**0.000e+00** against a 1e-10 bound.

**Consequences.** ParaView renderings of `A`, `B`, and `E` from these exports
are a continuous *approximation* of a field that is not continuous, off by tens
of percent pointwise at debug resolution; they are qualitative pictures, not
data. No gate cites them. The one case that goes beyond visualization is
`examples/magnetostatics/01_straight_wire.py:185`, which interpolates `B` to P1
and then **evaluates the radial profile from the interpolant** — that printout
carries this artifact and should be read as indicative only; the `MAG-13`
convergence numbers do not come from it.

**Scope of this entry.** Measurement only — no export code was changed, and no
ParaView claim elsewhere in the repo is withdrawn by it. Whether to export DG1
instead (faithful, larger files, discontinuous rendering) or to keep P1 with
this caveat is a review decision, not this step's. Probe:
`scripts/probes/post4_step4_probe.py`.

### ✅ RETIRED 2026-08-11 (`POST-4` step 3) — `examples/mri/01` centerline samples were rank-dependent at ~23%, at and below the gauge floor

**Closed by sampling the source fields.** The example's centerline table now
evaluates `E`/`B` **as solved** through `evaluate_vector_field_parallel`,
instead of the `("Lagrange", 1, (3,))` interpolants it builds for the XDMF
export — the locus the step-1 revision below attributed the spread to. Measured
across `-n 1/2/4` on the post-fix example:

```
                            max rank spread over the -n 1/2/4 pairs
  |E| centerline                     0.000000%   <- every printed digit
  |B| centerline                     0.008613%   <- magnetostatic solve noise
  collapse from the 23.5539% record  2735x       (anchor demanded >= 235x)
```

plus faithfulness — the printed values now equal step 1's measured source
values (|E| to 3.1e-7, |B| to 7.6e-5, the |B| leg's own floor); `|E|` at
z = −0.045 m reads **1.368268e+02** where the interpolant printed
**7.670127e+03**, the 56× artifact — and non-regression: the phantom-region
aggregates reproduce their `EX-16` record to 0.005745% (`-n 2`) and 0.002218%
(`-n 4`), inside the phantom path's own 0.007326% floor.

**Verified at:** `a34c3e6` + the `POST-4` step-3 diff, logs
`20260811T183229Z_POST-4-step3-n1.log`,
`20260811T183211Z_POST-4-step3-n2.log`,
`20260811T183222Z_POST-4-step3-n4.log`, anchor
`20260811T183503Z_POST-4-step3-anchor.log` (PASS, 1 s),
`scripts/probes/post4_step3_spread.py`.

**What is NOT closed by this.** The exported XDMF/VTX fields are still P1
interpolants of Nédélec/DG sources and still carry the vertex-convention
artifact — the fix moved the *printout* off that path, it did not repair the
path. `POST-4` step 4 bounds that residue on the export paths and is open. And
rank-invariance is not physics: `examples/mri/01` is ungated by design
(`WF-1` 🧪), so a faithful printout of an ungated proxy field is still ungated.

*The original entry and its two cause revisions are retained below for the
audit trail.*

#### Original entry (opened `EX-13`, 2026-08-10)

**Test id:** none — `./run_examples.sh -e mri:1 -n 2` vs `-n 4` (the example
is ungated by design, `WF-1` 🧪).
**Symptom:** the five printed centerline `(z, |E|, |B|)` pairs differ between
rank counts far beyond sampling noise. Worst pair at the validated gauge floor
(`gauge_penalty=1.0`), z = +0.0225 m:

```
-n 2:  z=+0.0225 m -> |E|=2.708874e+02, |B|=4.055231e-07
-n 4:  z=+0.0225 m -> |E|=2.592948e+02, |B|=5.304733e-07
```

— **23.5545%** max relative spread across the five pairs (|E| alone: 15.6832%
at z = +0.0450 m). The phantom-region aggregates are stable to ~0.1%, so this
is specific to the centerline point samples.

**Verified at:** `3c9c0bf`, logs `20260810T050150Z_EX-13-floor-n2.log` /
`…-floor-n4.log` (floor) and `…050120Z_EX-13-subfloor-n2.log` /
`…050133Z_EX-13-subfloor-n4.log` (sub-floor `1e-3`), spread computation
`20260810T050319Z_EX-13-spread.log`.

**Cause:** partly diagnosed, and *not* the gauge. Sub-floor spread is
**23.3010%** — 0.9892× the floor value, i.e. indistinguishable — and the |E|
legs are bit-identical between the two settings because
`TimeHarmonicSolver.solve` ignores `gauge_penalty`
(`src/fem_em_solver/core/time_harmonic.py:351`). The leading suspect is the
unconverged frequency-domain solve: GMRES stops at `ksp_max_it=180` with
`converged=False (reason=-3)` and `residual_norm=1.684628e+00` (identical at
both rank counts), so the returned iterate — not a converged solution — is
partition-dependent. The magnetostatic |B| leg moves < 0.6% with the gauge, so
it cannot account for a 23% spread either. Not confirmed: no run yet with a
converged KSP. *(That suspect was tested and refuted on 2026-08-10 — see the
revision below.)*

**Cause, revised 2026-08-10 (`EX-16`) — the convergence suspect is refuted
and the sampling path is confirmed as the owner.** The demo now solves
direct (`ksp=preonly, pc=lu, converged=True (reason=4)` at both rank
counts) at `gauge_penalty=1.0`, and the spread **does not move**:

```
                       unconverged (EX-13)   converged (EX-16)
max spread, all pairs        23.5545%             23.5539%
  |B| leg (magnetostatic)    23.5545%             23.5539%
  |E| leg (time-harmonic)    15.6832%             13.4499%
```

The anchor's own max is carried by the **magnetostatic |B|** leg, which the
frequency-domain fix cannot touch and which reproduces the unconverged
record to 1.0000×. Converging the KSP bought only 15.68% → 13.45% on the
|E| leg. **Positive control, same two runs, same fields:** the 493-point
phantom-region sampling path agrees across rank counts to **0.007326%**
(|B| mean and all three |E| stats bit-identical) — **3215×** tighter than
the centerline path. Same solve, same field, two samplers: the defect is in
the **centerline point-evaluation path**, not in the solve, the gauge, or
the KSP. Leading (undiagnosed) mechanism: the centerline points sit at
x = y = 0, on mesh edges of the axis, so ownership in
`evaluate_vector_field_parallel` is partition-dependent — the mechanism
`MAG-6` step 4 already characterised for its own centerline metric.

**Verified at (revision):** `34f18de` + the `EX-16` diff, logs
`20260810T170234Z_EX-16-direct-n2.log`, `20260810T170309Z_EX-16-direct-n4.log`,
spread computation `20260810T170457Z_EX-16-spread-v2.log`.

**Not fixed here:** both `EX-13` and `EX-16` were scoped as example/hygiene
chunks with a < 5% rank-stability anchor and an explicit report-and-stop
clause for a converged solve that still spreads. Repairing on-axis point
evaluation is solver-side work on `post.evaluation`, not an example edit.
**Resolved by:** assigned to `POST-4` (2026-08-10, 18:00 review) — step 1
diagnoses the ownership mechanism on the `EX-16` fixture (claim multiplicity,
per-claiming-cell disagreement, `valid_mask`, and an off-axis ε-nudge
discriminator); step 2, conditional on step 1 confirming, replaces
last-writer-wins with a minimum-global-cell-index tie-break in
`evaluate_vector_field_parallel` (`MAG-6` step 4 is the precedent read
first — it measured 0/9 multi-claims on *its* fixture, so the mechanism is
unproven here until step 1 measures it). Entry leaves only with a `POST-4`
step 2 commit whose collapse anchor lands (23.5539% → ≤ 0.1% across
`-n 1/2/4`); stays open on any other outcome.

**Cause, revised 2026-08-11 (`POST-4` step 1) — the ownership tie-break is
refuted; the locus is the interpolation into Lagrange P1, upstream of
`evaluate_vector_field_parallel`.** The probe rebuilt this exact fixture and
solved it at `-n 1/2/4` on a **byte-identical mesh** (9261 cells, coordinate
moments identical to 12 digits at all three rank counts), then instrumented the
point evaluation: it evaluated at *every* colliding cell, not just `links[0]`,
and reduced the claiming `(rank, global cell)` sets across ranks. The
mechanism's necessary condition is simply absent —

```
rows (5 points x 4 fields x 2 point sets x 3 rank counts): 120
MULTI_RANK_CLAIMS   = 0/120
MULTI_CELL_CLAIMS   = 0/120   (links[0] can only bite here)
MASK_INVALID        = 0/120   (silent zero-fill candidate)
CROSS_CELL_DISAGREE = 0/120
```

— every centerline point is claimed by exactly one cell on exactly one rank,
every mask is full, and the ε-nudge to x = y = 1e-6 m does **not** collapse the
spread (97.9755% on axis → 97.9754% nudged, 1.00×) where the chunk's anchor
demanded ≥ 235×. Both candidate mechanisms — partition-dependent cell choice and
silent zero-fill — are therefore dead on this fixture, matching `MAG-6` step 4's
0/9 rather than contradicting it.

**Where the spread actually lives.** The probe sampled four fields at the same
points on the same solves: the Lagrange-P1 interpolants the example prints
(`E_lag`, `B_lag`) and the fields they were interpolated *from* (`E_src`,
`B_src`).

```
                     max rank spread over -n 1/2/4 pairs, on axis
  E_lag (P1 interp)                 97.975464%
  B_lag (P1 interp)                 49.126566%
  E_src (source field)               0.000000%   <- bit-identical
  B_src (source field)               0.008426%
  separation, same points/solves     1.163e+04x
```

The solve is rank-invariant to round-off — `E_src` is bit-identical across all
three rank counts and `B_src`'s 0.008426% sits at the phantom-path control's
0.007326% scale. The 23% enters at `fem.Function.interpolate` into
`("Lagrange", 1, (3,))`: the P1 vertex dof of a field that is not continuous
there is written from whichever adjacent cell writes last locally, which is a
property of the partition. The `-n 2` vs `-n 4` per-point table reproduces
`EX-16`'s record exactly (`B_lag` 23.5539% at z = +0.0225 m), confirming the
probe re-created the fixture rather than a neighbour of it. The `-n 1` leg,
unmeasured before now, is the worst: `E_lag` at z = −0.045 m reads
**7.670127e+03** against 1.5646e+02 / 1.5528e+02 at `-n 2` / `-n 4` and against
the source field's 1.368268e+02 — a 56× interpolation artifact at a single
vertex, present at *every* rank count and merely varying with it.

**Verified at (second revision):** `1c1dc13` + the `POST-4` step-1 diff, logs
`20260811T140414Z_POST-4-step1-n1.log`,
`20260811T140345Z_POST-4-step1-n2.log`,
`20260811T140402Z_POST-4-step1-n4.log`, attribution
`20260811T140549Z_POST-4-step1-attribution.log` (anchor PASS).

**Resolved by (re-pointed):** `POST-4` step 2 as scoped — a min-global-cell
tie-break in `evaluate_vector_field_parallel` — **cannot fix this** and is
skipped per its own conditional clause. The owner is the P1 interpolation of a
non-P1-conforming field (or the example's decision to sample the interpolant
rather than the source field at all); re-scoping that is the next review's.
This entry stays open, with its exit condition unchanged in kind: it leaves with
a commit whose fix collapses the on-axis spread across `-n 1/2/4`, wherever that
fix turns out to live. *(That exit condition was met by `POST-4` step 3 on
2026-08-11 — the second option, the example sampling the source field; see the
retirement block at the top of this entry.)*

---

### Latent (has not fired): rank-local ladder-budget break in `test_birdcage_conductor_sizing.py` can desync collectives

**Found:** 2026-08-16, 10:30 review audit of `GEO-15` step 1 (subagent
auditor), at commit `94becb5`. **Not a failure yet** — recorded because the
mode it enables is a wedge, not a wrong number.

**Symptom (potential):** `tests/mesh/test_birdcage_conductor_sizing.py`
lines ~149–158 break out of the sizing ladder when
`remaining < 2 × previous_rung_time`, using per-rank `time.perf_counter()`
with **no reduction**. If ranks ever straddle the threshold, one rank
`break`s while the other enters a collective mesh call — deadlock until the
container-side `timeout -k 30` kills the job. It cannot corrupt a reported
number (all rungs completed in the closing run, 41 s against a 300 s
budget), but a slower box or a bigger ladder could fire it.

**Cause:** wall-clock is rank-local state used in a collective control-flow
decision — the same class as the `cell_tags.values` rule in CLAUDE.md.

**Resolves with:** any commit that next touches this test — reduce the
decision (`comm.allreduce(remaining, MPI.MIN)` or decide on rank 0 and
`bcast`). `EX-21` must not copy the pattern into the example.

---

### Four defects surfaced by replacing finiteness-only tests with real anchors (`OPS-17` step 2, 2026-08-17)

**Found:** 2026-08-17, `OPS-17` step 2, at commit `197142f`. All four were
invisible until the tests that exercise these paths were given quantitative
anchors — which is the whole premise of the chunk. **None is being fixed here:**
`OPS-17` is test hygiene, and each of these belongs to the subsystem it lands
in. The first three are carried in the tree as `pytest.mark.xfail(strict=True)`
with the measurement in the docstring, so a fix reports as XPASS rather than
silently passing; the fourth is worked around in one test.

**1. ~~`coil_phantom_domain` region-resolution policy shrinks the meshed coil
volumes by ~22% while asking for a *finer* mesh.~~ ✅ RESOLVED 2026-08-20
(`GEO-17` step 1, 06:00 implementer slot) — the per-region sizes were never
applied at all: `coil_phantom_domain` walked volume → surfaces → curves →
points through `gmsh.model.getBoundary` with its default `combined=True`,
whose result for a volume's closed shell of surfaces is empty, so every region
collected zero CAD points and `mesh.setSize` was never called
(`20260820T110127Z_GEO-17-step1-diag.log`: `air: 0 pts -> NO SIZE SET` for all
four regions at both sizings). Only the global `CharacteristicLengthMin/Max`
clamps survived — uniform `[0.015, 0.015]`, policy `[0.010, 0.020]` — so the
policy run meshed the coil at the *air's* 0.020 ceiling. **The hypothesis
below is refuted:** no field won the interface, because no field existed. The
sizes are now carried by a `Min` over per-volume `Constant` size fields, and
the volumes move the way refinement requires (final log
`20260820T110549Z_GEO-17-step1-final.log`, `-n 2`, 13 s): coil_1
1.191750413e-04 → **1.319468693e-04 m³** (+10.72%, meshed/CAD 0.754685 →
**0.835563**), coil_2 → 1.316573175e-04 (+10.79%, 0.752565 → 0.833730),
phantom → 4.990112950e-04 (+0.94%, 0.983531 → 0.992751), and the air — the one
region the policy *coarsens* — is the one region that loses volume (−0.26%).
The uniform column reproduces the table below to every printed digit, gated in
the test as the negative control. The test is a plain gate again, renamed
`test_region_resolution_policy_refines_the_tagged_volumes_toward_cad`; its 5%
band was replaced with the sign-of-refinement identity and the meshed/CAD
recovery bounds, because the old band's premise (region sizing "must not move
the geometry") is false for a curved region — see that test's docstring.**
`tests/mesh/test_mesh_tag_integrity.py::test_region_resolution_policy_does_not_move_the_tagged_volumes`
(xfail). Measured at `-n 2`, `20260817T111054Z_OPS-17-step2-mesh-n2.log`,
uniform `h = 0.015` against `coil_resolution=0.012, phantom_resolution=0.010,
air_resolution=0.020`:

| tag | uniform [m³] | policy [m³] | Δ |
| --- | --- | --- | --- |
| 1 `coil_1` | 1.191750413e-04 | 9.333354960e-05 | −21.68% |
| 2 `coil_2` | 1.188402981e-04 | 9.195675344e-05 | −22.62% |
| 3 `phantom` | 4.943767949e-04 | 4.880940997e-04 | −1.27% |
| 4 `air` | 1.143560787e-02 | 1.149461560e-02 | +0.52% |

CAD torus volume is `2π²Rr² = 1.579137e-04 m³`, so uniform recovers 75.5% of
each coil and the policy mesh 59.1%. **The sign is the defect:** a linear-tet
mesh inscribes a curved surface, so refining can only move meshed volume *up*
toward CAD. Every region given a finer size lost volume, and the air took up
exactly what the curved regions lost. **Cause: not diagnosed.** Hypothesis —
the region size fields replace rather than refine the surface sizing on shared
curved interfaces, so the coarse air field (0.020) wins on the coil and phantom
boundaries. **Resolves with:** a `GEO` chunk on `coil_phantom_domain`'s sizing
path. Both meshes still partition their own volume to 1e-9, so this is fidelity,
not conformity.

**2. ~~The Coulomb-gauge Lagrange multiplier does not vanish for a
divergence-free source.~~ ✅ RESOLVED 2026-08-20 (`MAG-17` step 1, 07:30
implementer slot) — candidate (a) confirmed, candidate (b) excluded: **the
anchor was wrong, not the constraint block.** The h-ladder ran
(`20260820T123307Z_MAG-17-step1-ladder.log`, `-n 2`, 95 s), reproducing the
record at its own mesh and refining twice:

| h | cells | multiplier spread |
| --- | --- | --- |
| 0.0050 | 29 190 | 7.836781e+00 |
| 0.0035 | 82 819 | 3.052022e+00 |
| 0.0025 | 208 049 | 1.438617e+00 |

Fitted log-log rate **2.4476** (pairwise 2.645 / 2.234) against the
pre-registered bands rate ≥ 0.7 ⇒ DISCRETE-SOURCE, |rate| < 0.3 ⇒
ASSEMBLY-DEFECT. The verdict is DISCRETE-SOURCE with four sigfigs of margin,
and superlinearly so: `p` is absorbing the interpolated `J`'s discrete
divergence, which is a mesh residual that converges away, not a defect in how
the constraint is assembled. The consequence is that the `OPS-17` anchor
("spread → 0 to solver tolerance") **cannot hold on any single mesh** — the
right anchor is a convergence rate. The strict xfail is retired and the claim
moved to
`tests/solver/test_gauge_multiplier_convergence.py::test_multiplier_spread_converges_for_a_divergence_free_source`,
a plain gate on the ladder at the unmoved pre-registered 0.7 (band deliberately
not tightened to the measurement — it stays the discriminator it was designed
as). The negative control holds in the same run: the incompatible straight
wire stays at its recorded 2.083064e+02 scale, > 10× the loop's base-h spread
(recorded separation 26.6×), so the multiplier has not stopped discriminating
compatible from incompatible sources. Final run
`20260820T123823Z_MAG-17-step1-final2.log`, 6 passed, 97 s.**
`tests/solver/test_gauge_lagrange.py::test_gauge_multiplier_vanishes_for_a_divergence_free_source`
(xfail). Measured at `-n 2`, `20260817T111217Z_OPS-17-step2-solver-n2.log`:
spread **7.836781e+00** on a closed current loop (azimuthal J: `div J = 0`
inside, `J·n = 0` on both the torus surface and the outer sphere) against the
solver-tolerance residual the theory requires. The multiplier is not dead — it
reads **2.083064e+02** on the deliberately incompatible straight wire, 26.6×
larger — but "vanishes for a compatible source" is false as written.
**Cause: not diagnosed.** Two candidates, separable with one h-ladder:
(a) benign — the source enters through an interpolated `J` whose discrete
divergence is O(h), and the fixture is coarse (h = 0.005 against a 0.003 wire
radius), in which case the spread falls with refinement; (b) a real defect in
how the constraint is assembled, in which case it is h-independent.
**Resolves with:** a `MAG`/`OPS` chunk on the gauge formulation. Note `max|A|`
is not a usable normaliser here — `test_lagrange_removes_the_null_space`
requires the LAGRANGE `max|A|` to sit six orders below the penalty solve's.

**3. ~~Real Poynting power does not balance on the time-harmonic smoke fixture,
and the boundary flux has the wrong sign.~~ ✅ RESOLVED 2026-08-19 (`POST-5`
step 4, 15:00 implementer slot) — see the closing block at the end of this
entry; the test is a plain gate again and passes.**
`tests/solver/test_time_harmonic_smoke.py::test_time_harmonic_smoke_solve_conserves_real_power`
(xfail). Measured at `-n 2`,
`20260817T112448Z_OPS-17-step2-th-smoke2-n2.log`: dissipated
`½∫σ|E|²dV = +1.199162e-06 W` against net inward flux
`−∮½Re(E×H̄)·n̂dS = −2.008179e-07 W`, relative imbalance **116.7465%** against
a pre-stated 25%. Power leaves through the boundary while the medium
dissipates, which the identity forbids for any solution of Maxwell's equations
regardless of boundary condition. **Cause: not diagnosed.** Candidates:
(a) resolution — 0.16 m domain at h = 0.03 m is ~9 cells per in-medium
wavelength (λ = c/(f√78) = 0.266 m), and the boundary leg is a curl trace, the
least accurate quantity a degree-1 N1curl solution carries;
`tests/validation/test_poynting_balance.py` needs a refined mesh to reach 5%
and gates the *convergence* of this imbalance for that reason; (b) the source —
an axial current terminating on the end caps, so `J·n ≠ 0` there, the same
incompatibility as defect 2. **Resolves with:** a `TH`/`POST` chunk; an
h-ladder on this fixture distinguishes the two in one command.

> **Sharpened 2026-08-18, `POST-5` step 1 — candidate (a) is excluded and so
> is a third candidate (c).** The h-ladder ran
> (`20260818T215101Z_POST-5-step1-ladder2.log`, `-n 2`, 5 s):
>
> | h | cells | dissipated [W] | net inward [W] | imbalance |
> |---|---|---|---|---|
> | 0.030 | 1 405 | 1.199162e-06 | −2.008179e-07 | 116.7465% |
> | 0.020 | 2 590 | 1.154337e-06 | −1.778362e-07 | 115.4059% |
> | 0.015 | 4 661 | 1.479920e-06 | −2.134447e-07 | 114.4227% |
>
> Fitted rate in h **0.0290** against the pre-registered ≥ 0.7, and the net
> inward flux is negative on every rung including the finest. **It is not
> resolution.** Candidate (c), a flipped outward measure, is excluded
> exactly: `∮x·n̂dS / 3|Ω| = 1.000000000000` on this fixture with the same
> `dx`/`ds` pair the balance uses
> (`test_smoke_fixture_boundary_measure_is_outward_oriented`). Candidate (b)
> — the drive's `J·n ≠ 0` on the end caps — is what remains, together with a
> defect in the boundary leg's assembly. The xfail is **not** rescoped to
> convergence; its reason string now carries these numbers. `POST-5` step 2
> in PROJECT_PLAN §7 scopes the next discriminator (a closed azimuthal
> source on the same fixture).

> **Sharpened again 2026-08-19, `POST-5` step 2 — candidate (b) is excluded
> too; the defect is in the boundary leg's assembly.** The closed-drive
> discriminator ran on the coarse rung
> (`20260819T051150Z_POST-5-step2-closed-drive2.log`, `-n 2`, **4 s**):
>
> | drive | dissipated [W] | net inward [W] | sign | imbalance | blind diss [W] |
> |---|---|---|---|---|---|
> | axial (record) | 1.199162e-06 | −2.008179e-07 | − | 116.7465% | 0.000000e+00 |
> | closed azimuthal | 4.778876e-09 | −2.849722e-10 | − | 105.9632% | 0.000000e+00 |
>
> The azimuthal drive `J = (−y, x, 0)/a` is a *closed* source on this fixture
> — `div J = 0` pointwise, `J·n = 0` on both end caps and on the rod's own
> lateral surface, so the tag restriction adds no surface divergence either —
> and it is P1-exact, so no interpolation error is folded in
> (`_azimuthal_current` in the smoke module). Both halves of the
> pre-registered SOURCE band fail: the imbalance moves only
> 116.7465% → **105.9632%** (a 10.8 pp move, against a band that required
> < 25%) and the flux **sign does not turn positive**. The axial drive re-run
> in the same session reproduces the step-1 record to `rtol=1e-6` on all
> three numbers (asserted, not eyeballed), so the drive is the only thing
> that changed between the two rows. **Verdict: ASSEMBLY.** The source's
> `J·n ≠ 0` incompatibility is real (defect 2 measures it) but it is not what
> makes this identity fail. **Resolves with:** the boundary-leg probe scoped
> as **`POST-5` step 3** (named in the step-2 §7 entry; queued 2026-08-19
> 03:00 review) — scoring the curl trace `−∮½Re(E×H̄)·n̂dS` against the
> `TH-6` lossy plane wave, where both legs have closed forms, which separates
> a wrong `H = ∇×E/(−jωμ)` reconstruction from a wrong facet assembly. The
> xfail keeps its 25% band and `strict=True`.

> **Resolved as a defect in the *identity*, not the code — 2026-08-19,
> `POST-5` step 3.** Step 2's ASSEMBLY verdict is **overturned by direct
> measurement**: the boundary leg is sound, and what is wrong is that
> `poynting_power_balance` scores the **source-free** identity on a
> **driven** fixture.
>
> *Leg 1 — the boundary leg against its own closed form*
> (`20260819T123438Z_POST-5-step3.log`, `-n 2`;
> `test_each_leg_scored_against_its_own_closed_form`). On the `TH-6` lossy
> plane wave both legs have closed forms —
> `P_flux = ½βL²(1−e^{−2αL})/(ωμ₀μᵣ)`, `P_diss = ½σL²(1−e^{−2αL})/(2α)`,
> equal identically because `k² = k₀²ε_c` gives `2αβ = ωμ₀σ`
> (asserted separately at `rtol=1e-12`: both sides 7.060162290693e+02;
> analytic value 1.241101e-04 W):
>
> | rung | cells | flux leg [W] | flux err | volume leg [W] | volume err |
> |---|---|---|---|---|---|
> | 12³ | 10 368 | 1.140318e-04 | 8.1205% | 1.241984e-04 | 0.0711% |
> | 24³ | 82 944 | 1.190042e-04 | **4.1141%** | 1.241317e-04 | 0.0174% |
>
> The boundary leg is inside the pre-registered 10% band on the fine rung and
> falls at rate `log₂(8.1205/4.1141) = 0.981` — clean O(h) for a degree-1
> N1curl curl trace. `H = ∇×E/(−jωμᵣμ₀)` and the facet assembly are
> **correct**; there is no factor and no conjugation error to find.
>
> *Leg 2 — the full three-term balance on this fixture*
> (`20260819T124405Z_POST-5-step3-source.log`, `-n 2`, 4 s;
> `test_the_missing_impressed_source_term_accounts_for_the_smoke_imbalance`).
> With an impressed `J`, Poynting's theorem reads
> `−∮½Re(E×H̄)·n̂dS = ½∫σ|E|²dV + ½Re∫E·J̄dV`, and the helper omits the
> second term:
>
> | drive | dissipated [W] | net inward [W] | source ½Re∫E·J̄ [W] | two-term | three-term |
> |---|---|---|---|---|---|
> | axial | 1.199162e-06 | −2.008179e-07 | −1.199162e-06 | 116.7465% | **16.7465%** |
> | azimuthal | 4.778876e-09 | −2.849722e-10 | −4.778876e-09 | 105.9632% | **5.9632%** |
>
> Both inside the pre-registered 25% band (the xfail's own), so the omitted
> term **is** the imbalance. **Read the third column carefully**: the source
> term equals `−dissipated` to all seven printed digits on both drives. That
> is not a coincidence and not evidence about the flux — under the *natural*
> boundary condition this fixture uses (`TimeHarmonicBoundaryCondition.NATURAL`,
> the default; the `TH-6` fixture is PEC-with-Dirichlet-data and source-free,
> which is why its 5% gate is honest) the weak form tested with `v = Ē` has no
> boundary term, so `½∫σ|E|² + ½Re∫E·J̄ = 0` holds *algebraically* in the
> discrete solution. The three-term residual is therefore exactly the boundary
> flux over the scale — i.e. 16.7% / 6.0% is the discretisation error of the
> curl trace on a ~9-cells-per-wavelength gmsh mesh, entirely consistent with
> leg 1's 8.1% at 10 368 cells on a *structured* box.
>
> **Consequence.** The wrong sign is not forbidden: `−∮½Re(E×H̄)·n̂dS` alone
> has no sign law when a source is present inside — only the three-term sum
> does. The original entry's "which the identity forbids for any solution of
> Maxwell's equations regardless of boundary condition" is **wrong as
> written**; it is true only for a source-free domain. **Resolves with:**
> `POST-5` step 4 (scoped, not executed) — teach `poynting_power_balance` the
> impressed-source term and re-gate. Nothing was changed in this step: the
> xfail keeps its 25% band and `strict=True` and still XFAILs.

> **✅ CLOSED 2026-08-19, `POST-5` step 4 (15:00 implementer slot).** The fix is
> in the helper, not in the solve: `poynting_power_balance` now accepts the
> impressed `current_density` (and the `source_measure` it was assembled on),
> assembles `source_power_w = ½Re∫E·J̄dV`, and scores `relative_imbalance` on
> the three-term statement when a drive is given. Omitting the drive changes
> nothing — the source-free two-term identity is still what a source-free
> domain is scored against, and it stays reachable in both cases as
> `two_term_relative_imbalance` / `two_term_power_scale_w`, so the step-1
> h-ladder journal above keeps reconciling.
>
> `test_time_harmonic_smoke_solve_conserves_real_power` is a **plain gate**
> again — the `xfail(strict=True)` is gone and it PASSES against the *unmoved*
> 25% band (`20260819T201005Z_POST-5-step4-smoke-final.log`, `-n 2`, complex
> build, 12 passed / exit 0 / 8 s):
>
> | reading | value |
> |---|---|
> | dissipated ½∫σ\|E\|²dV | 1.199162e-06 W |
> | net inward −∮½Re(E×H̄)·n̂dS | −2.008179e-07 W |
> | source ½Re∫E·J̄dV | −1.199162e-06 W |
> | three-term residual (gated, band 25%) | **16.7465%** |
> | two-term reading (step-1 record 116.7465%) | 116.7465% |
> | σ-blind three-term control | 83.2535% |
>
> Every one of these reproduces the step-3 record; the test asserts them at
> `rtol=1e-6` (powers) and `atol=1e-6` (the two imbalances, which the record
> carries only to 4 decimals as a percentage) rather than printing them.
> The σ-blind control is now scored on the three-term residual too, where its
> arithmetic ceiling is `1/0.167465 = 5.97×`; the pre-registered replacement
> for the old (never-met) 10× factor is **3.0×**, and it must also be *rejected*
> by the very band the honest solve passes — 83.2535% is 4.97× the honest
> reading and well outside 25%.
>
> **Negative control, on the fixture where J = 0**
> (`20260819T200651Z_POST-5-step4-negcontrol.log`, `-n 2`, 15 passed / exit 0 /
> 152 s): `test_zero_impressed_current_leaves_the_source_free_balance_untouched`
> solves the `TH-6` plane wave at 12³ and scores it twice — with no drive and
> with `J = fem.Constant(msh, [0,0,0])` (a `Constant` rather than a literal, so
> the integral is genuinely *assembled* rather than folded away). The source
> term is **exactly `0.0` W**, asserted `== 0.0`, and all seven other returned
> quantities are asserted **bit-identical** between the two calls: 8.185716%
> both ways, which is the step-3 12³ rung's 8.1857% unmoved. All the `POST-3`
> gates in that file (5% MVP, piecewise σ, μᵣ-field, and the three blind
> controls) are green in the same log.

> **JIT trap, 2026-08-19 (`POST-5` step 2).** The step's first window
> (`20260819T050314Z`, exit 124 at 400 s) died with rank 1 parked in
> `MPI_Bcast` — the dolfinx cold-JIT signature — and left **one 0-byte
> `.c` in `/root/.cache/fenics`** (created 7 s into the run, i.e. long
> before the form that was waiting on it was reached). Removing that single
> entry (`rm /root/.cache/fenics/*<hash>*`) and re-running the identical
> command took **2.94 s of pytest**. So a 0-byte cache entry is not only the
> *symptom* of a killed compile, it is a live lock the rest of that same run
> can block on: when a run stalls in `MPI_Bcast`, look for `find
> /root/.cache/fenics -size 0` **before** concluding the case is too big for
> the window or that a form's quadrature degree is unpinned.

**4. ~~`poynting_power_balance` raises on a scalar `sigma=0.0`~~ — FIXED
2026-08-18 (`POST-5` step 1).** The scalar branch is now wrapped in
`fem.Constant(msh, dolfinx.default_scalar_type(σ))`, so the integral keeps
its domain and `sigma=0.0` assembles to **exactly 0.000000e+00 W** (verified
at three mesh sizes, `20260818T215101Z_POST-5-step1-ladder2.log`; asserted
`== 0.0`). The `SIGMA_BLIND = 1e-12 * SIGMA` workaround is deleted and the
control is now a real zero. `tests/validation/test_poynting_balance.py` is
unmoved by the wrap — 8 passed, scalar-vs-DG0-field paths still equal at
`rtol=1e-12` (`20260818T215117Z_POST-5-step1-negcontrol.log`). Original
report follows.

**`poynting_power_balance` raises on a scalar `sigma=0.0`, the σ-blind
negative control its own docstring advertises.**
`src/fem_em_solver/post/power_balance.py:137`. `0.5 * 0.0 * ufl.inner(E, E)`
folds to a domain-less UFL zero and `* ufl.dx` then raises
`ValueError: This integral is missing an integration domain`. First hit at
`20260817T112414Z_OPS-17-step2-th-smoke-n2.log`. **Cause:** the scalar branch
passes a bare Python float rather than wrapping it in `fem.Constant(msh, ...)`,
so UFL constant-folds the whole integrand away. `sigma=0.0` is an intended
input — the module docstring calls it "what makes the σ-blind negative control
possible". Existing callers pass a non-zero scalar or a `sigma_field`, so
nothing was previously red. **Worked around**, not fixed: the smoke test above
uses `SIGMA_BLIND = 1e-12 * SIGMA`. **Resolves with:** wrapping the scalar in
`fem.Constant` — a one-line `POST` fix plus a re-run of
`tests/validation/test_poynting_balance.py`.

### `PORT-1` step 4's `allgather` reduction broke `_DummyComm`, and one orientation test regressed silently on 2026-08-13 (`OPS-17` step 3, 2026-08-17)

**Found:** 2026-08-17, `OPS-17` step 3, at commit `e211356`, in the first
*completed* real-mode suite leg since 2026-08-13
(`20260817T201248Z_OPS-17-step3-real-nonvalidation-n2.log`, `-n 2`, 218 s,
3 failed / 134 passed / 32 skipped / 2 xfailed, both ranks identical).

| | |
|---|---|
| **Tests** | `tests/ports/test_port_orientation_sensitivity.py::test_port_orientation_flip_changes_induced_voltage_sign` — **not previously known-red**<br>`tests/ports/test_port_orientation_sensitivity.py::test_port_orientation_flip_changes_off_diagonal_sparameter_sign` — known-red under entry 3, but **not for entry 3's recorded reason** |
| **Symptom** | `AttributeError: '_DummyComm' object has no attribute 'allgather'` raised out of `src/fem_em_solver/ports/excitation.py:258`. The failure is inside `src/`, *before* any test assertion executes. |
| **Cause** | Diagnosed, one line. `PORT-1` step 4 (2026-08-13) added `problem.mesh.comm.allgather(...)` at `excitation.py:258` to reduce the tag set before `validate_required_port_tags_exist` — the documented fix for entry 6 defect (2). The file's test double (`tests/ports/test_port_orientation_sensitivity.py:16`) implements only `rank` and a static `allreduce`, so the new collective call has nothing to dispatch to. |
| **Why it went unseen for four days** | `PORT-1` step 4's own gate ran the *two-torus* negative control, not this file, and every slot since has used targeted per-file runs. No completed suite leg was paid for until this one. The `--ignore=tests/validation` leg above is the cheapest thing that catches this class (218 s). |
| **Two separate consequences** | (i) `test_port_orientation_flip_changes_induced_voltage_sign` is absent from entry 3's list of two tests, so it was green before 2026-08-13 — this is a **silent regression**, not a pre-existing red. (ii) Entry 3's symptom line (`assert np.all(np.abs(diagonal) > 0.0)` on a zero diagonal) is **stale for the orientation test**: that assertion is now unreachable. It still describes `tests/ports/test_sparameter_assembly.py::test_n_port_sweep_assembles_finite_matrix_with_expected_shape` correctly (`test_sparameter_assembly.py:104: AssertionError: assert False`), which is the third failure in the same leg. |
| **Fix** | **Deliberately not fixed by `OPS-17`** — that chunk is test hygiene, and entry 3's standing disposition is that these tests live and die with `PORT-1`'s retirement of the `PORT-0` placeholder. The mechanical repair is two lines in the test double (`allgather = staticmethod(lambda v: [v])`, or use a real `MPI.COMM_SELF`); whoever retires `PORT-1` should decide whether the double survives at all. Do not read the `AttributeError` as evidence about the placeholder's arithmetic — it never runs. |
| **Resolves with** | `PORT-1`'s retirement commit, or any earlier commit that repairs the double. **Entry 3 must be re-symptomed in the same commit**, since its recorded cause now applies to only one of its two tests. |

### ✅ RESOLVED 2026-08-23 (`OPS-18` step 3a `5df1e39`, landed on `main` by 3b) — the two-torus and straight-wire solves are run-to-run non-deterministic at ~1e-10 relative, so "bit-identical reproduction" is not an achievable criterion (`OPS-18` step 3a attempt 6, 2026-08-23)

**Found:** 2026-08-23, on `attempt/OPS-18` at `9b3c9e2`, image
`0.11.0.post0` / gmsh 4.15.2 / numpy 2.4.6, `-n 2`, in two back-to-back
runs of the *same* command on an *unchanged* tree
(`20260823T050426Z_OPS-18-step3a-leg1-run1.log`,
`20260823T050903Z_OPS-18-step3a-leg1-run2.log`).

| | |
|---|---|
| **Tests** | `tests/validation/test_port_package_sparameters.py::test_sanity_report_reproduces_the_gated_metrics_on_the_field_route`, `tests/validation/test_port_lumped_two_torus.py::test_step_1_measurements_reproduce` (both already red on 0.11 for the *moved-record* reason); the same effect is visible in real mode in `test_straight_wire.py`. |
| **Symptom** | Repeating one command reproduces every *outcome* and every band, but not every digit: `passivity_max_sigma` 0.8613568946068969 → 0.86135689450373 (1.2e-10 rel), two-torus gap ratio 0.8941410489050936 → 0.8941410492011536 (3.3e-10), `‖S−Sᵀ‖/‖S‖` 3.112128e-05 → 3.112131e-05 (1.0e-06 rel, 3e-11 abs). In one real-mode run `E_Ω` at h = 0.0025 printed 1.0617170184e-01 (ladder) and 1.0617170177e-01 (record test) — 7e-10 apart, same field, same run. |
| **Cause** | Not separated further in-slot; the signature (same mesh, same tree, same image, ~1e-10) is floating-point summation/factorisation order inside MPI-parallel assembly and the direct solve, i.e. the same class as `MAG-18`'s 7.28e-08 `-n 2` vs `-n 4` floor. It is **not** the version bump: both runs are on one image. |
| **Consequence** | Any acceptance criterion phrased as "reproduces bit-identically" — including `OPS-18` ruling (1) condition (b), 2026-08-22 18:00 review — cannot be met by these fixtures. Records whose written precision is coarser than ~1e-9 relative are unaffected in practice (0.861356895 and 0.894141 both reproduce as written); the `‖S−Sᵀ‖/‖S‖` record at 7 significant digits does **not**, and would have to be written as 3.11213e-05. |
| **Not a band question** | Every physics band in the same runs is orders of magnitude above the wobble (reciprocity 2.679e-05 vs 1e-3; the symmetry record's own band is 5e-7 absolute vs a 3e-11 move). Nothing here licenses loosening anything. |
| **Resolves with** | A review restating the reproduction criterion at a stated tolerance (proposal in attempts.md 2026-08-23T05:25Z: agreement to ≤ 1e-9 relative across two runs, record written only to digits both runs share). No code fix is implied. |
| **Ruling, 2026-08-23 03:00 review** | Restated as **(b′)**, per-record rather than one relative number — the proposed "≤ 1e-9 relative" would itself reject `‖S−Sᵀ‖/‖S‖` (1.0e-06 relative, cancellation-amplified): *the move across two same-slot runs must be ≤ 1% of the record's own unmoved band, and the value is written only to the digits both runs share, never fewer than the band resolves.* All four records pass (1.2e-4, 3.3e-6, 6e-5 and 7e-6 of their bands); the symmetry record is written as 3.11213e-05. Full text in PROJECT_PLAN §7 `OPS-18`. **This entry closes with the `OPS-18` 3a commit that writes the records** (§9 item 2). |
| **Closed, `OPS-18` step 3b (2026-08-23, 15:00 slot)** | The stated condition is met: the records-writing commit is **`5df1e39`** (3a attempt 8), on `main` with this step's merge. The criterion that replaces "bit-identical" is (b′), quoted verbatim from the ruling above: *"the move across two same-slot runs must be ≤ 1% of the record's own unmoved band, and the value is written only to the digits both runs share, never fewer than the band resolves."* Every record written under it since — the four of attempt 7, the two of attempt 8 (1.2e-4 / 3.3e-6 / 6e-5 / 7e-6, then 6.6e-6 and below the printed digits, all as fractions of their own bands), and step 3b's four `UNIFORM_VOLUMES_RECORD` volumes (move 0.0 across two runs) — satisfies it with no band moved anywhere. **The underlying wobble is not fixed and is not a defect**: it is the ~1e-10 assembly/factorisation-order floor named in the Cause row, the same class as `MAG-18`'s 7.28e-08 cross-width floor, and it stays the reason no criterion in this project may say "bit-identical" of a *solved* number. |

### ✅ RETIRED 2026-08-25 — Gate (iii) is blind to a broken C4 on the *opposite* class, and the lumped-sheet 4-port sweep loses reciprocity by 223× on an asymmetric layout (`PORT-9` step 3 leg (d1), 2026-08-23)

**Retirement evidence (leg (d1′), 06:00 slot, `20260825T110438Z_PORT-9-step3d1.log`,
`13 passed 106.64 s`; confirmed by `20260825T110643Z_PORT-9-step3d1-consumers.log`,
`24 passed 222.15 s`).** Both findings are disposed on `main`, and the module that
carried them is now on `main` and green rather than parked:

* **Finding 1 (gate blindness) — disposed by tightening, not by widening.** Gate
  (iii)'s 5% became **(iii′) 0.5%** at its single source with all three consumers
  re-run green under it (leg (c) 0.0407%, leg (d0) 0.0040%, leg (d) 0.0553 /
  0.0353 / 0.0214%). Under (iii′) the 22.5° rotation breaks **all three** classes,
  not two: self **6.2219%**, adjacent **7.1142%**, and the opposite class — the
  one this entry named as blind at 1.6476% against 5% — **2.8474%**, an amplifi­
  cation of 133.11× over the symmetric rung. The 08-23 10:30 review's open
  question about whether the opposite class belongs in the geometric control is
  therefore answered affirmatively by measurement.
* **Finding 2 (reciprocity) — disposed by the (d3) power-wave assembly.** On the
  same displaced fixture the route now reads `‖S−Sᵀ‖/‖S‖` = **2.259e-14** against
  the unmoved 1e-3, versus this entry's **5.57e-03**: a **2.466e+11×** separation
  against the (d3) ruling's ≥ 100× bar, and the first test of that fix on a
  fixture that is both 3D and asymmetric. Per (d3c) the reading is an order of
  magnitude only (the confirm run read 6.846e-14).

`PORT-9` ✅ 2026-08-25 at 10 MHz; the branch
`attempt/PORT-9-d1-20260823T124500Z` is deleted. Original text kept verbatim
below.

---

Two findings from one run, both **measured, neither disposed** — the leg's own
negative-result clause (§7 `PORT-9` step 3 leg (d1)) sends both to the review.
The tests are **not on `main`**: they are parked on
`attempt/PORT-9-d1-20260823T124500Z` at `bbe657f`, so nothing here is red in CI.

| | |
|---|---|
| **Tests** | `tests/validation/test_port_birdcage_leg_offset_sweep.py::test_gate_iii_detects_the_broken_c4`, `::test_the_displaced_rung_stays_reciprocal` (parked branch only) |
| **Log** | `docs/testing/logs/20260823T140422Z_PORT-9-step3d1.log` — `2 failed, 7 passed` / 119 s / `-n 2`, complex build, standard tier |
| **Fixture** | `GEO-18`'s gapped, sheeted birdcage, two rungs of the same code path: `leg_azimuth_offsets_rad` all zero (116 416 cells) and leg 1 alone at **+22.5°** (116 944 cells); four driven lumped-sheet solves per rung at `Z_p = z0 = 50 Ω`, 10 MHz, `f = 0.5`, `w = A/h`. |
| **The comparison is controlled** | The zero rung reproduces leg (d)'s recorded 4×4 **entry by entry** to ≤ **2.969e-10** relative against the 1e-9 print-precision band (worst of sixteen), with `‖S−Sᵀ‖/‖S‖` = 2.495292352e-05 and `σ_max` = 0.862659137 identical to nine digits. The offset knob and the frame-aware sheet narrowing this leg added do not move the solve, so every difference below belongs to the displacement. |
| **Finding 1 — symptom** | Displaced, gate (iii)'s three class spreads read **self 5.1819%**, **adjacent 7.1147%**, **opposite 1.6476%** against the unmoved 5% band (symmetric rung: 0.0199 / 0.0180 / 0.0108%; amplifications 260.89× / 395.76× / 152.49×). The adjacent class detects the broken C4 by 1.42×; the **opposite class does not** — it is inside the band it passes on a symmetric layout. The leg's anchor required **both** off-diagonal classes to exceed the band. |
| **Finding 1 — cause** | Geometric and expected in direction, not in size: rotating leg 1 by 22.5° moves the P1–P3 separation 180° → 157.5° while P2–P4 stays 180°, so the opposite class mixes two separations 22.5° apart, where the adjacent class mixes 67.5° / 90° / 112.5°. Leg (d0) measured only 5.9% between 90° and 180°, so a 22.5° perturbation of the *opposite* pair is a second-order effect on an already-flat part of the coupling curve. Not diagnosed further in-slot. |
| **Finding 2 — symptom** | On the displaced rung `‖S−Sᵀ‖/‖S‖` = **5.570640234e-03** against step 2c's unmoved **1e-3** band (`‖Z−Zᵀ‖/‖Z‖` = 7.440778193e-03) — a **223×** rise from the same code path's 2.495292352e-05 on the symmetric rung. `σ_max` = 0.865743230, still passive. Reciprocity is a property of the materials, so this is a systematic of the route or the discretisation, never of the physics. |
| **Finding 2 — cause** | Not diagnosed. The one measured asymmetry that tracks it: the midpoint interior-width filter keeps **26** facets on the rotated port's sheet against **27** on the other three, so P1's `w = A/h` is **7.272128105e-03 m** against 7.413268623e-03 m elsewhere — a 1.9% width difference entering `LumpedSheetPortSpec.sheet_width_m`, hence the V/I estimate, asymmetrically between driven and undriven readings. On the symmetric rung all four sheets are identical and the systematic cancels exactly. This is a hypothesis with a measurement attached, not a diagnosis. |
| **Not a mesh defect** | The negative control of the control is green on **both** rungs: every sheet is a full rectangle of the closed-form `dx·g` = 1.120000000e-04 m², meshed/analytic **1.000000000000** to the 1e-9 band, planar to ≤ 1.7e-17 m in its own port frame, and narrower than the full sheet after filtering. Both rungs' meshes are conforming and every `GEO-18` identity holds. |
| **Consequence** | `PORT-9` stays **🟡**: step 3's gate (iii) is validated as a symmetry gate on the adjacent class only, and the displaced spreads cannot be read as pure geometry while finding 2 stands. §2.2's "no coil has ports" sentence is **unmoved**. Nothing licenses widening (i)–(iii) or the 5% band. |
| **Resolves with** | A review ruling on both: whether gate (iii) is re-specified (a tighter band, an adjacent-class-only statement, or a different invariant), and how the reciprocity systematic is disposed — a per-port equal-facet-count narrowing rule is the obvious first probe, and is code work, not a band question. |
| **Ruling, 2026-08-23 10:30 review** | **The width hypothesis is refuted from the log's own Z** (`…step3d1.log:9327-9330`): a 1.9% readout-width asymmetry on P1 would put a common factor 0.981 on every `Z₁ⱼ/Zⱼ₁` and leave the other pairs at 1; measured `\|Z_ij/Z_ji\|` = 0.99589 / 1.00109 / 1.00625 on row 1 and 1.00523 / **1.01041** / 1.00515 on the pairs that do not involve P1 — the worst pair is **P2–P4, neither port moved**. The asymmetry is global, 0.2–1.6% per pair, the order of the discretisation on a mesh gmsh regenerated whole. Reading: the route's `V` readout is not the impressed source's adjoint, so `Z − Zᵀ` is a local-discretisation residual that cancels only when every port sees the same local mesh — which every fixture this route has been measured on provides (two identical tori, C4 birdcage). **Step 2c's 2.6e-11 is evidence of a symmetric fixture, not of a reciprocal discretisation.** Disposal: `PORT-9` leg (d2), an asymmetric two-torus (`f` = 0.5 / 0.735) with pre-registered predictions (A: O(1e-2); B: ≤ 1e-9), §9 item 2. **Gate (iii) re-specified as (iii′) ≤ 0.5%** (25× above the measured symmetric floor, 3.3× below the weakest displaced class; a tightening; leg (d) stays ✅ under it). The (d1) re-run is serial on (d2). This entry closes with the (d1′) commit. |
| **Finding 2 disposed — leg (d2), 2026-08-23** | **Hypothesis A is refuted and A′ stands: the readout *is* the source's adjoint; the asymmetry is the terminated-`Z` assembly.** `tests/validation/test_port_lumped_sheet_asymmetric.py`, `9 passed` / 198 s and 191 s at `-n 2`, complex, standard (`20260823T183434Z_PORT-9-step3d2.log`, `20260823T183823Z_PORT-9-step3d2-repeat.log`). Two sweeps on **one** 184 919-cell two-torus mesh — control `f` = 0.5/0.5 and asymmetric `f` = 0.5/0.735, `w₂/w₁` = 1.472822047, `Z_p` = 1e6 Ω. Control reproduces step 2c: `‖S−Sᵀ‖/‖S‖` = 2.574356760e-11, **1.078e-15** from the record (band 1e-9). Asymmetric: **8.255602536e-09** — 320.7× the control but **5 orders inside** the unmoved 1e-3, i.e. prediction **B** at the Frobenius grain, so A's O(1e-2) does not happen. Mechanism, asserted at a pre-stated 1e-6: (i) `I₁(drive 2)` = `I₂(drive 1)` to **1.33e-10** — the transadmittance is discretely symmetric, so the current readout **is** the impressed source's adjoint (same facet set `S_i`, same weighting `ĥ_i/(R_i h_i)`, same vector the source is built from, on a complex-symmetric operator); (ii) `Z₁₂/Z₂₁` = `I₁(d1)/I₂(d2)` to **1.33e-10** — `_assemble_impedance_matrix` divides column *j* by the **driven** port's own current, so what it calls `Z` is a *terminated* transimpedance, not the open-circuit matrix reciprocity makes symmetric, and `Z_ij/Z_ji` collapses exactly to the ratio of the two driven-port self-currents (1 for equivalent ports, nothing in particular otherwise). Both runs identical to 8–10 digits. **Read the per-pair number, not the Frobenius one:** here `\|Z₁₂/Z₂₁\|` = **0.997537168** (phase −0.020146017°), a **0.25%** per-pair asymmetry — the same order as (d1)'s 0.2–1.6% table — which the Frobenius ratio hides because at `Z_p` = 1e6 Ω the kΩ diagonal (6.21 − 2.93j / 3.73 − 3.28j) drowns the ~1.13 Ω mutuals, whereas the birdcage's 50 Ω termination puts `Z₁₁` ≈ 21.7 Ω beside 17 Ω mutuals and lets the same per-pair asymmetry surface as 5.57e-03. **So (d1)'s reciprocity miss is not a discretisation residual and not birdcage-specific: it is the assembly's per-column normalisation, made visible by a matched termination.** Not fixed in-slot per the leg's scope — the fix is an assembly change (an open-circuit `Z`, or `S` from power waves as `_assemble_sparameter_matrix` already does) and it **moves the 2b/2c/(c)/(d0)/(d) records**, which is a review's ruling. |
| **Ruling (2\*), 2026-08-23 18:00 review — fix scoped** | The fix is the **power-wave S assembly** on the gated routes (`S_ij = b_i/a_j`, `a_j` = `V_src/(2√z0)` at a matched drive — symmetric by mechanism identity (i)); the open-circuit-`Z` alternative is rejected on leg (c)'s near-degenerate 1e6 Ω column. The terminated `Z` stays as a documented diagnostic, never reciprocity-gated. Scoped as `PORT-9` legs **(d3)** (two-torus + class re-record under the (1\*) pattern, §9 item 2) and **(d3b)** (birdcage re-record, §9 item 4); **(d1′) serial on (d3b)**. This entry still closes with the (d1′) commit. |

### ✅ RETIRED 2026-08-29 (`GEO-24` step 2b, 06:00 implementer slot) — ~~the **32-port** ring-gap sheet reconstruction is rank-width dependent~~ ~~**`birdcage_port_domain` is built with no ghost layer (`GhostMode.none`), so interior port facets on a partition boundary are unclassifiable — at *every* leg count; it reaches the 4-leg fixture at `-n 12`**~~ — **fixed by the `shared_facet` plumb landed in `470f410` (`GEO-24` step 2a′) and cleared by the two-family re-read; the two-torus `-n 12` drift found inside this entry lives on as `PORT-12` below**

| | |
| --- | --- |
| **Test id** | `tests/mesh/test_birdcage_ring_gaps_scaleup.py::test_thirty_two_ring_ports_at_sixteen_legs` — **not on `main`**; parked on `attempt/GEO-20-step2-20260828T094500Z`. Nothing on `main` is red because of this; the entry exists so the next attempt does not re-derive the measurement. |
| **Verified at** | `e4510a5`, 0.11 image, real build, 2026-08-28. |
| **Symptom** | `birdcage_port_domain(leg_count=16, ring_gap_length=8e-3, emit_port_sheets=True)` — 265 621 cells, 48 ports — is **green at `-n 1`** (`20260828T093352Z_GEO-20-step2-probe1.log`, `1 passed` / 275 s) and **red at `-n 2` on the identical geometry** (`20260828T093839Z_GEO-20-step2-record.log`, Status 1 / 198 s). At `-n 2`, three of the 32 ring sheets do not reconstruct: **P30 and P37 return 0 facets** (meshed/analytic 0.000000000000 of `w²`) and **P45 returns 5 facets** (0.315302109223); the other 29 read **1.000000000000**. The gate that fires is P30's boundary closure, **0.981164653445** against 1e-9. A missing sheet also makes `_sheet_azimuth_deg` return NaN (`inf + -inf` bbox centre), which raises `ValueError: cannot convert float NaN to integer` inside `_azimuth_class` — caught by the module's `_report_safely` guard, so the run fails on the gate rather than hanging. |
| **Not the CAD, the cut, or the volume tagging** | At **both** widths: all 32 port volumes are 1.000000000000 of the analytic wedge, the `GEO-9` partition and air-box closure are 1.000000000000, the ring arcs satisfy Pappus at 1.000000000000, the conductor keeps 0.976465 of its CAD mass, no ring port touches the phantom, and all 32 terminals read 0.974454791–0.974455668 (spread 2.572e-07). The defect is confined to the facet-set reconstruction. |
| **Not the port count alone, and not the ring construction alone** | In the *same* `-n 2` run, the 4-leg ring-gapped fixture (8 ring ports, 110 786 cells) and the 16-leg **leg**-gapped fixture (16 ports, 307 296 cells, C16 sheet spread 1.331e-15) both reproduce their records digit for digit and are green. It takes 32 small port solids for the failure to appear. |
| **Cause** | **Not diagnosed.** Hypothesis with the signature attached: `_interface_facet_tags` matches a facet by the cell tags of its two adjacent **owned** cells, so a port whose `PORT_LOWER+i` and `PORT_UPPER+i` half-regions land on different ranks contributes no facet on either — which is exactly the 0-facet / partial-facet pattern. Discriminator that costs no `src/` change: re-run at `-n 4` / `-n 8` and see whether the broken port *set* moves with the rank count. |
| **Consequence** | `GEO-20` stays **🟡**; step 2 landed **no band and no record**. The 16-leg ring cost rung (110 786 → 265 621 cells, 2.3976×; mesh 23.30 → 72.23 s, 3.1003×) is measured and is safe to cite — it is a cell count and a wall time, not a reconstruction reading. Nothing licenses reading the 32-port fixture's sheets, or building a port model on it, until this is disposed. `GEO-19`'s 16-leg fixture passing at `-n 2` is luck of the partition, not immunity. |
| **Resolves with** | `GEO-20` step 2 attempt 2: confirm or refute the partition reading at `-n 4`/`-n 8` first. If confirmed, the fix is in `_interface_facet_tags` (ghost-layer-aware matching), which is `src/` work touching every module that reconstructs a sheet and could move existing records — a **review's ruling**, not an in-slot fix. |

> **✅ CONFIRMED CLOSED 2026-08-29, 09:00 implementer slot (`GEO-20` step 2
> attempt 2) — the fixture this entry is about now reads green in parallel and
> the module is ON `main`.** The "Test id" row above is superseded:
> `tests/mesh/test_birdcage_ring_gaps_scaleup.py` was restored from `31c08ed`
> and landed with this commit; `attempt/GEO-20-step2-20260828T094500Z` is
> deleted. Re-run on the plumbed tree (`470f410`) at both widths:
> `20260829T140037Z_GEO-20-step2-rerun-n2.log` (Status 0 / 188 s) and
> `…140402Z_…-rerun-n12.log` (Status 0 / 184 s), `1 passed` each. The
> **Symptom** row's three broken sheets are repaired at the identical 265 621
> cells — **P30 and P37 0 → 176 air facets**, **P45 5 facets /
> 0.315302109223 → 180 / 1.000000000000** — and all 32 sheets, all 32
> closures and all 32 `volume/analytic` read **1.000000000000** at `-n 2` and
> `-n 12` alike. The **Cause** row's "not diagnosed" hypothesis
> (`_interface_facet_tags`) is superseded by the `GhostMode.none` diagnosis
> and its one-keyword fix; `_interface_facet_tags` was never touched. The
> **Consequence** row's embargo is lifted: the 32-port fixture's sheets are
> licensed to read.

> **RULED 2026-08-28, 10:30 review — `GEO-20` step 2a queued (§9 item 3):**
> the `-n 4`/`-n 8` discriminator with a per-port print of which rank owns
> each `PORT_LOWER+i`/`PORT_UPPER+i` cell set, no `src/` change; the
> hypothesis predicts a *moving* broken-port set and exact agreement between
> "half-boxes on different ranks" and "sheet broken" across 32 × 3 ports. The
> `_interface_facet_tags` fix is withheld until a review holds that table.
> The attempt branch is kept as the fixture. Entry retires with the fix
> commit, whichever chunk lands it.

> **🔬 DIAGNOSED 2026-08-28, interactive session (at `883c52e`) — the
> hypothesis above is WRONG in its location, and the cause is now measured.
> The defect is not in `_interface_facet_tags`; it is that
> `birdcage_port_domain` never asks for a ghost layer.**
>
> Found by the human operator running
> `examples/meshing/07_birdcage_ring_gap_ports.py` at **`-n 12`**: `port P8
> closure 0.990103697427 on the doubly-gapped mesh`, on the **4-leg,
> 12-port** rung — the fixture `GEO-20` step 1 closed as exact. So the class
> is *not* confined to 16 legs / 32 ports.
>
> **The `-n 4`/`-n 8` discriminator the ruling asked for, answered on the
> small fixture** (probe: build the doubly-gapped rung, print every port's
> closure; logs `20260828T1727*`–`20260828T1730*Z_GEO-20-widthprobe-n{1,2,4,8,12}.log`,
> ~32 s each, **128 111 cells at every width**):
>
> | ranks | 1 | 2 | 4 | 8 | 12 |
> |---|---|---|---|---|---|
> | red ports | — | — | — | — | **P8** |
>
> Same geometry, same cell count; only the partition moves. The defect is a
> **partition-density** property, not a leg-count or port-count property —
> which is why 16 legs breaks at `-n 2` and 4 legs survives to `-n 8`.
>
> **The lost quantity is one facet.** P8 reads **175** air facets against 176
> on every other ring port; its conductor count (102) and terminal ratio
> (0.974454791) are identical to P7/P11/P12, i.e. the *sheet* reconstructs
> correctly and only the boundary partition loses area.
>
> **Mechanism, measured** (`20260828T173142Z`/`20260828T173221Z_GEO-20-facetprobe-n{1,12}.log`)
> — facets the rank **owns** whose second cell is not present locally, not
> even as a ghost:
>
> ```
> WIDTH  1: owned facets touching P8 = 1417, locally one-sided (counts==1) =  0
> WIDTH 12: owned facets touching P8 = 1417, locally one-sided (counts==1) = 19  (ranks 2 and 5)
> ```
>
> `_interface_facet_tags` selects `interior = counts == 2`, so all 19 drop out
> of every interface group. Most are sheet-plane facets that belong to none of
> the three groups anyway; exactly one faced air, and that is the missing
> 0.99%.
>
> **Cause — diagnosed, one line.** `birdcage_port_domain` calls
> `_model_to_mesh(gmsh.model, comm, rank, gdim=3)` (`io/mesh.py:3356`) with
> **no partitioner**, i.e. gmshio's default `GhostMode.none` — no ghost layer
> at all. `two_torus_domain` was given
> `create_cell_partitioner(GhostMode.shared_facet, 2)` in `PORT-1` step
> 3b-iv for exactly this reason, and that site's comment says so verbatim:
> the port facets are *interior*, classifying one needs the tag of the cell
> on both sides, and "`shared_facet` is what makes that cell present as a
> ghost … Plumbed here only, so no other fixture changes partition." The
> birdcage reconstructs interior port facets the same way and was never given
> the ghost layer that reconstruction requires.
>
> **Confirmed by construction, then reverted** (`20260828T173412Z_GEO-20-ghostfix-probe-n12.log`):
> with the same partitioner plumbed into `birdcage_port_domain`, `-n 12` reads
> **`1.000000000000` on all 12 ports**, P8 back to **176** air facets,
> **128 111** cells unchanged, mesh 26.08 s unchanged. The patch was **not
> landed** — it changes the partition of the fixture `GEO-19`, `GEO-20`,
> `PORT-9` and `PORT-11` all share, which is a re-record question. `GEO-24`
> owns it.
>
> **What this revises in the rows above.** "Resolves with" is superseded: the
> fix is **not** ghost-layer-aware matching inside `_interface_facet_tags`
> (no reconstruction logic changes), and it does **not** touch every module
> that reconstructs a sheet — it is one keyword at one call site. The
> ruling's predicted "moving broken-port set" is confirmed as *width*-moving;
> the per-rank ownership table it asked for is no longer needed to locate the
> cause, though `GEO-24` step 1 still owes the before/after readings.
>
> **A record this puts a caveat on** — ***caveat DROPPED 2026-08-29 by
> `GEO-24` step 2a′/2b; the plumb is landed and the reading is measured true
> at 12 ranks. Kept struck-through for the audit trail:*** ~~`GEO-20` step
> 1's "closure and volume/analytic `1.000000000000` on all 12" is
> **width-conditional** — true at ≤ 8 ranks, false at 12. Every reading taken
> through `_interface_facet_tags` on this fixture inherits that caveat until
> the plumb lands.~~ `GEO-19`'s own remark that passing at `-n 2` is "luck of the
> partition, not immunity" is now measured rather than suspected.

> **📐 `GEO-20` STEP 2a EXECUTED 2026-08-28 (15:00 slot, at `61e97f1`) — the
> ownership table, on the 16-leg / 32-port fixture itself. The set moves with
> the width and agrees with rank ownership port for port, 32 × 2 with no
> exception.** Logs `20260828T200204Z_GEO-20-step2a-n4.log` (Status 1 / 189 s)
> and `20260828T200524Z_GEO-20-step2a-n8.log` (Status 1 / 189 s), standard
> tier, real build, the parked module plus a per-port `allgather`ed count of
> owned `PORT_LOWER+i` / `PORT_UPPER+i` cells. No `src/` change.
>
> | ranks | broken sheets (of 32) | ports whose two half-boxes are not on one rank | sets agree |
> |---|---|---|---|
> | 2 (recorded 04:30) | P30, P37, P45 | *(not instrumented)* | — |
> | 4 | **P25, P29, P37, P41, P45** (5) | P25, P29, P37, P41, P45 | **yes**, ∅ either way |
> | 8 | **P17, P21, P26, P30, P37, P44, P48** (7) | P17, P21, P26, P30, P37, P44, P48 | **yes**, ∅ either way |
>
> The 4-leg / 8-ring-port control in the same runs is **0 broken, 0 straddling
> at both widths** — consistent with the width probe above, where the small
> fixture only breaks at `-n 12`. The set is not nested and not monotone in
> membership (P45 breaks at 2 and 4 but not 8; P30 at 2 and 8 but not 4), which
> is what a partition boundary sweeping through a fixed geometry looks like and
> what no geometry-deterministic defect can produce.
>
> **Failure shape, unchanged from `-n 2`:** a broken port loses its sheet
> **entirely** (0 facets) or keeps a fragment — P29/P45 at `-n 4` **5 facets /
> 0.315302109223** of `w²`, P26 at `-n 8` **6 facets / 0.449137697797** — while
> its *terminal* stays exact (0.974454791–0.974455668, the intact value) and
> its **volume/analytic is 1.000000000000**. Boundary closure drops only on the
> one port per run that also loses an **air** facet (P29 at `-n 4`,
> 0.991120008826, 179 vs 180; P44 at `-n 8`, 0.991064589826, 175 vs 176) —
> the same one-facet loss the 4-leg fixture shows at `-n 12`.
>
> **Negative controls, both widths, digit for digit:** all 40 port
> volume/analytic readings **1.000000000000**, `GEO-9` partition and air-box
> closure **1.000000000000**, ring arcs against Pappus **1.000000000000**,
> conductor 0.976465 / 0.969275 of CAD, kwarg-off at 16 legs **307 296** cells
> (ratio 1.000000) with C16 sheet spread **1.331e-15**, 4-leg ring rung
> **110 786** cells (ratio 1.000000). The volume identity does not route
> through `_interface_facet_tags` and did not move at any width — so the defect
> is confined to facet reconstruction, exactly as the ghost-layer diagnosis
> says.
>
> **Reading.** This is confirmation of the *phenomenology* the 10:30 ruling
> asked for, on the large fixture, and it is consistent with the ghost-layer
> cause rather than with the `_interface_facet_tags` location — ownership
> predicts breakage perfectly because a straddling port is precisely one whose
> interior sheet facets have a neighbour cell that `GhostMode.none` does not
> materialise. Per the ruling, **confirmed is stop**: no `src/` line moved, no
> band, no record. The instrumented module is
> `scripts/probes/geo20_step2a_ownership_scaleup.py` (the parked module verbatim
> plus the ownership print — the attempt branch still holds the uninstrumented
> original; see attempts.md 2026-08-28T20:40Z for why it did not go to the
> branch). The fix and the re-record sweep stay
> `GEO-24`'s, and `GEO-24` step 1 now owes only the before/after readings on
> the modules that already live on `main`.

> **📐 `GEO-24` STEP 1a EXECUTED 2026-08-28 (21:00 slot, at `deef8c5`) — the
> `main`-side "before" table for the seven `tests/mesh/` consumers, at `-n 2`
> and `-n 12`, no `src/` change. Every cell count is identical across widths;
> `-n 2` is green everywhere; two modules are red at `-n 12`, both by facet
> reconstruction.** Fourteen windows, one module per window, `-s`, standard
> tier, real build, `-k 30 400` (`-k 30 570` for `port_scaleup`);
> logs `20260829T0200*`–`20260829T0213*Z_GEO-24-step1a-*-n{2,12}.log`,
> **668 s of compute** in total.
>
> | module | cells (`-n 2` / `-n 12`) | `-n 2` | `-n 12` |
> |---|---|---|---|
> | `test_birdcage_port_sheets` | 116 085 / 116 085 (control 114 655) | ✅ 2 passed, 52 s | ✅ 2 passed, 50 s |
> | `test_birdcage_port_terminals` | 98 666 / 98 666 | ✅ 1 passed, 22 s | ❌ **1 failed**, 22 s |
> | `test_birdcage_ring_gaps` | 128 111 / 128 111 (control 98 666) | ✅ 2 passed, 74 s | ❌ **1 failed, 1 passed**, 74 s |
> | `test_birdcage_leg_gaps` | 114 655 / 114 655 (control 98 666) | ✅ 1 passed, 44 s | ✅ 1 passed, 44 s |
> | `test_birdcage_leg_offset` | 116 085 / 116 475 / 116 085, both widths | ✅ 6 passed, 76 s | ✅ 6 passed, 75 s |
> | `test_birdcage_port_sheet_prerequisite` | 98 666 / 98 666 | ✅ 1 passed, 22 s | ✅ 1 passed, 21 s |
> | `test_birdcage_port_scaleup` | 307 296 / 307 296 (control 116 085) | ✅ 2 passed, 109 s | ✅ 2 passed, 108 s |
>
> **Consumer list re-derived by construction, no difference:**
> `grep -rln birdcage_port_domain tests/ examples/` ∩ the
> `_interface_facet_tags` / `port_sheet` users is exactly these seven under
> `tests/mesh/` — the 18:00 review's list is correct as written.
>
> **The prediction from the diagnosis is confirmed digit for digit.**
> `test_birdcage_ring_gaps` fails at `-n 12` on
> `port P8 closure 0.990103697427` (assert `0.009896302572964588 < 1e-09`) —
> the exact digit the width probe recorded, on the exact port, at an
> unchanged **128 111** cells. Every other reading in that module is
> identical to its `-n 2` value: all 12 ports `volume/analytic
> 1.000000000000`, all 8 ring sheets `1.000000000000`, ring terminals
> 0.974454791 / 0.974454832, leg terminals 0.988615826–0.988615858, Pappus
> 1.000000000000 both gapped and uncut, kwarg-off control **98 666** cells
> at ratio 1.001950.
>
> **New information — the defect reaches a *second* surface, not only port
> sheets.** `test_birdcage_port_terminals` is red at `-n 12` on its
> **positive control**, the phantom↔air interface:
> `phantom surface measures 1.939344e-02 m^2, 0.935322 of the closed-form
> 2.073451e-02 m^2` against the `[0.95, 1.0]` inscribed band — **245 facets
> at `-n 12` against 255 at `-n 2`** (0.979885), i.e. **10** interface facets
> lost, the same one-cell-per-partition-boundary shortfall an order larger.
> All four port boxes in that module stay exact at both widths (air 24 facets
> / 5.200000e-04 m², closure 1.000000000000, conductor 0 facets). So the
> `GhostMode.none` reconstruction gap is **not** specific to port sheets:
> *any* interior material interface on this fixture inherits it. **Step 2a's
> gate must include this reading** — the plumb should return 255 facets /
> 0.979885 at `-n 12`, and if it does not, that is a finding.
> **⚠️ The 255 / 0.979885 in this paragraph is DEFECTIVE (annotated
> 2026-08-29, step 2a′): it is one facet short. `-n 1` on `main`, no plumb,
> reads 256 / 0.984183 (`…050535Z_…-terminals-n1-main.log`) — the serial
> truth, which needs no ghost layer — so step 1a's `-n 2` reading inherited
> the same `GhostMode.none` gap it was meant to be the reference for. The
> post-plumb reading is 256 / 0.984183 at `-n 1`, `-n 2` and `-n 12` alike.
> No test carried the 255 (the band is `[0.95, 1.0]`), so nothing in
> `tests/` moved. Ruled a defect repair, not a re-baseline, by the
> 2026-08-29 03:00 review.**
>
> **Negative control as pre-stated, both widths, digit for digit:** the
> terminal ratios and port-volume identities — neither of which routes through
> a facet reconstruction — are identical at `-n 2` and `-n 12` in every
> module, including the 16-leg scale-up's three azimuth classes
> (0.988615772 / 0.989367514 / 0.989449735, intra-class spreads
> 1.923e-07 / 5.849e-08 / 6.144e-08, inter-class 8.431e-04) and its C16 sheet
> spread (1.331e-15 at `-n 2`, 1.210e-15 at `-n 12` — the only digit that
> moves anywhere in the table, at the 1e-15 floor).
>
> **Cost finding: nothing was unmeasured.** `test_birdcage_port_scaleup` — the
> module the review flagged as most likely to overrun at `-n 12` — completed
> in **108 s**, well inside `-k 30 570`; `GEO-19` step C's exit 124 at 561 s
> was a *bundled* window, not this module's own price. `-n 12` costs the same
> wall clock as `-n 2` throughout (±2 s), since the mesh is built on rank 0
> either way.
>
> **Nothing on `main` is red at `-n 2`,** so CI is unaffected; the two reds
> above are `-n 12`-only and are the measurement `GEO-24` step 1a was
> commissioned to take.
>
> **📐 `GEO-24` STEP 1b EXECUTED 2026-08-29 (22:30 slot, at `d5b4586`) — the
> `main`-side "before" table for the five `tests/validation/` consumers, at
> `-n 2` and `-n 12`, complex build, no `src/` change. Every cell count is
> identical across widths, every module is green at *both* widths, and every
> printed S/Z identity is digit-identical — the validation family shows **no**
> `-n 12` red at all. The one red in the slot is the pre-stated negative
> control, and it is `-n 12`-only.** Thirteen windows, one module per window,
> `-s`, standard tier, `-k 30 480` (`-k 30 400` for the two cheapest,
> `-k 30 300` for the last control); logs
> `20260829T0331*`–`20260829T0342*Z_GEO-24-step1b-*.log`, **660 s of compute**
> in total (env gate + 10 module windows + 2 control windows).
>
> | module | cells (`-n 2` / `-n 12`) | `-n 2` | `-n 12` |
> |---|---|---|---|
> | `test_port_birdcage_lumped_column` | 116 085 / 116 085 | ✅ 2 passed, 33 s | ✅ 2 passed, 31 s |
> | `test_port_birdcage_four_port` | 116 085 / 116 085 | ✅ 5 passed, 51 s | ✅ 5 passed, 40 s |
> | `test_port_birdcage_larmor_probe` | 116 085 / 116 085 | ✅ 3 passed, 40 s | ✅ 3 passed, 32 s |
> | `test_port_birdcage_termination_probe` | 116 085 / 116 085 | ✅ 4 passed, 39 s | ✅ 4 passed, 32 s |
> | `test_port_birdcage_leg_offset_sweep` | 116 085 + 116 475, both widths | ✅ 5 passed, 96 s | ✅ 5 passed, 77 s |
>
> **Consumer list re-derived by construction, no difference:**
> `grep -rln birdcage_port_domain tests/ examples/` ∩ the
> `_interface_facet_tags` / `port_sheet` users is exactly these five under
> `tests/validation/` — the 18:00 review's list is correct as written. Note
> that only `_lumped_column` calls `birdcage_port_domain` directly; the other
> four reach the fixture through its `_build` helper and appear in the
> intersection through their own `_interface_facet_tags` / sheet imports.
> `test_port_birdcage_larmor_gate.py` and `_larmor_gate_128.py` are **not** in
> the intersection (they reconstruct nothing themselves) and were not read.
>
> **Digits, both widths, identical unless stated.** All four
> `Z_{11,21,31,41}` reproduce their `PORT-9` records at rel. deviation
> 1.07e-10 – 2.57e-10 in every module that gates them; 4×4 gates in
> `_four_port`: `||S−S^T||/||S||` **8.141422487e-15** at `-n 2` and
> **1.116856988e-13** at `-n 12` (band 1e-3, both PASS; `||Z−Z^T||/||Z||`
> 8.814400605e-05 vs …604e-05 reported), `sigma_max(S)` **0.999992805** and
> max column power sum **0.793823974** at both, C4 class spreads
> **0.0553 / 0.0353 / 0.0214 %** at both (band 0.5%), pooled off-diagonal
> 9.2115% and separation 166.6766×. `_lumped_column`: all four sheets 26
> facets / 5.835298880e-05 m² / `w = A/h` 7.294123600e-03 m, out-of-plane
> 0.000e+00 m, at both widths. `_larmor_probe`: `Z_11` +2.215494591e+01
> +7.460189773e+00j (10 MHz) and +2.647082952e+01+4.646185233e+01j (Larmor
> rung), identical at both. `_termination_probe`: margin **2256.9707×**,
> spread **0.0040%**, open control 1.5951× / 0.0407%, `I_1` reproducing at
> 5.9e-12 / 1.1e-11. `_leg_offset_sweep`: displaced rung 116 475 cells (ratio
> 1.003360) with class spreads **6.2219 / 7.1142 / 2.8474 %** vs the zero
> rung's 0.0553 / 0.0353 / 0.0214 %, `sigma_max` 0.999992337 vs 0.999992805,
> `||S−S^T||/||S||` zero 1.044255156e-14 → 6.958642293e-14 and displaced
> 2.009039801e-14 → 4.532499019e-13 across widths (band 1e-3).
>
> **⚠️ The pre-stated negative control did not hold, and it is the step's new
> information.** `tests/validation/test_port_lumped_two_torus.py` — the
> fixture that *already* has `create_cell_partitioner(GhostMode.shared_facet,
> 2)` (`PORT-1` step 3b-iv) — is **green at `-n 2`** and **red at `-n 12`**:
>
> ```
> gap ratio: 0.894274 against step 1's record 0.894141 — moved by 1.33e-04,
>   above 1e-04; step 2's reads changed step 1's solve
> ```
>
> (`20260829T034112Z_…-twotorus-control-n12.log`, `1 failed, 4 passed`,
> Status 1, 84 s; `20260829T034253Z_…-twotorus-control-n2.log`, `5 passed`,
> Status 0, 84 s, gap ratio **0.894141** = the record exactly.) The mesh does
> **not** move — **184 176 cells at both widths** — and the four other tests in
> the module pass at `-n 12`, so this is not the `GhostMode` reconstruction
> defect: it is a *solved* quantity (the gap-route `V` line integral,
> `Im Z12 = 1.110469250` at `-n 12` vs `1.110303775` at `-n 2`, 1.5e-4
> relative) drifting with partition count on an already-plumbed fixture, at
> the same order as the `OPS-18` step-3 re-record band it is gated against
> (1e-4). **Consequence for step 2b:** a `-n 12` *solved* digit that moves at
> 1e-4 after the birdcage plumb is not by itself evidence the plumb failed —
> the gate must distinguish facet-reconstruction readings (which must return
> exactly 1.000000000000) from solve-derived digits at 1e-4. Whether the
> two-torus 1e-4 band should be width-qualified is a **review's call**, not
> this chunk's; nothing was loosened here.
>
> **Nothing on `main` moved at `-n 2` in this family** — every `-n 2` reading
> matches its `PORT-9` / `PORT-11` record, so CI is unaffected and no record
> is owed a re-write from step 1b. Step 2b (the plumb re-read of this family)
> is unblocked.
>
> **📐 `GEO-24` STEP 2a EXECUTED 2026-08-29 (00:00 slot, at `169c28c`) — the
> plumb repairs both `-n 12` reds, every cell count and every other `-n 2`
> digit holds, and it moves *one* `-n 2` reading, which is §9 item 4's
> pre-stated stop. The plumb is REVERTED on `main` and parked on
> `attempt/GEO-24-step2a-20260829T052300Z` (`e1dede8`); nothing under `src/`
> landed.** Sixteen windows, one module per window, `-s`, standard tier, real
> build, `-k 30 400` (`-k 30 570` for `port_scaleup`); logs
> `20260829T0501*`–`20260829T0519*Z_GEO-24-step2a-*.log`, **≈ 870 s** of
> compute (14 table windows + 2 serial diagnostics + 1 control window).
>
> The patch is one keyword at `io/mesh.py:3356` —
> `partitioner=create_cell_partitioner(GhostMode.shared_facet, 2)`, the
> `two_torus_domain` site's kwarg and comment, nothing else in `src/`.
>
> | module | cells (`-n 2` / `-n 12`) | `-n 2` before → after | `-n 12` before → after |
> |---|---|---|---|
> | `test_birdcage_port_sheets` | 116 085 / 116 085 (control 114 655) | ✅ → ✅ 2 passed, 66 s | ✅ → ✅ 2 passed, 62 s |
> | `test_birdcage_port_terminals` | 98 666 / 98 666 | ✅ → ✅ 1 passed, 26 s **(digit moved, below)** | ❌ → ✅ 1 passed, 26 s |
> | `test_birdcage_ring_gaps` | 128 111 / 128 111 (control 98 666) | ✅ → ✅ 2 passed, 85 s | ❌ → ✅ 2 passed, 85 s |
> | `test_birdcage_leg_gaps` | 114 655 / 114 655 (control 98 666) | ✅ → ✅ 1 passed, 51 s | ✅ → ✅ 1 passed, 51 s |
> | `test_birdcage_leg_offset` | 116 085 / 116 475 / 116 085, both widths | ✅ → ✅ 6 passed, 84 s | ✅ → ✅ 6 passed, 83 s |
> | `test_birdcage_port_sheet_prerequisite` | 98 666 / 98 666 | ✅ → ✅ 1 passed, 23 s | ✅ → ✅ 1 passed, 23 s |
> | `test_birdcage_port_scaleup` | 307 296 / 307 296 (control 116 085) | ✅ → ✅ 2 passed, 118 s | ✅ → ✅ 2 passed, 117 s |
>
> **Gate clause 1 — every cell count identical: ✅.** All seven modules read
> the same counts as step 1a at both widths, and every kwarg-off control
> reproduces (98 666 at ratio 1.001950, 114 655, 116 085, the scale-up's
> `cells 116085 vs 116085 (delta 0, relative 0.000e+00)`). The plumb changes
> partitioning, not meshing, exactly as predicted.
>
> **Gate clause 3 — both previously-red `-n 12` readings now green: ✅.**
> `test_birdcage_ring_gaps` port P8 returns to **176 air facets, closure
> 1.000000000000** from 175 / **0.990103697427**, at an unchanged 128 111
> cells, with all 12 ports' `volume/analytic` and all 8 ring sheets still
> 1.000000000000. `test_birdcage_port_terminals`' phantom↔air control returns
> to **256 facets** from 245, and all four port boxes stay exact (air 24
> facets / 5.200000e-04 m², closure 1.000000000000, conductor 0).
>
> **Gate clause 2 — every `-n 2` digit identical: ❌ in one cell, and that is
> the stop.** `test_birdcage_port_terminals`' positive control reads
> **256 facets / 2.040655e-02 m² / 0.984183** of the closed-form
> 2.073451e-02 m² after the plumb, against step 1a's recorded **255 facets /
> 0.979885** at `-n 2`. The test passes either way (the band is [0.95, 1.0]),
> but the digit moved, and §9 item 4's negative-result clause is explicit:
> a moving `-n 2` digit stops the chunk for a review. Every *other* `-n 2`
> digit in all seven modules is identical to step 1a's — the C4 sheet spread
> 6.050e-16, leg terminals 0.988615825–0.988615858, ring terminals
> 0.974454791 / 0.974454832, Pappus 1.000000000000, and the scale-up's three
> azimuth classes 0.989367514 / 0.989449735 / 0.988615772 with intra spreads
> 5.849e-08 / 6.144e-08 / 1.923e-07, inter-class 8.431e-04, C16 sheet spread
> 1.331e-15 at `-n 2` and 1.210e-15 at `-n 12` (the 1e-15 floor, as before).
>
> **What the moved digit actually is — measured, not argued.** Two extra
> serial windows settle it. On the **plumbed** tree at `-n 1`:
> **256 facets / 0.984183**. On **`main`** at `-n 1`, plumb reverted:
> **256 facets / 0.984183** — identical (`…050500Z_…-terminals-n1-plumbed.log`
> and `…050535Z_…-terminals-n1-main.log`, Status 0, 26 s / 25 s, 98 666 cells
> both). A single rank has no partition boundary, so it needs no ghost layer
> and reads the true interface either way. **So 256 is the truth, and the
> recorded `-n 2` value of 255 / 0.979885 was itself one facet short from the
> same `GhostMode.none` gap** — the record was *defective at every parallel
> width*, not partition-dependent physics. After the plumb the reading is
> 256 / 0.984183 at `-n 1`, `-n 2` and `-n 12` alike, i.e. width-independent
> and equal to the serial truth. This is the fix working on a surface where
> step 1a had mistaken a short reading for the baseline.
>
> **Negative controls, pre-stated, with the plumb applied: green and
> unmoved.** `tests/mesh/test_two_torus_port_sheet.py` and
> `tests/mesh/test_cylindrical_domain.py` — untouched fixtures — are
> `4 passed` / Status 0 / 33 s with the `GEO-16` control at its usual
> **79 070** cells and tags `[1, 2, 3, 101, 102] / [1, 201, 202]`
> (`…051958Z_…-controls-n2.log`). No other fixture's partitioner was touched.
>
> **Cost: nothing unmeasured.** `-n 12` again costs the same wall clock as
> `-n 2` throughout (±2 s), the mesh being built on rank 0 either way;
> `port_scaleup` took 117 s at `-n 12` inside `-k 30 570`.
>
> **What a review owes this chunk.** The measurement says the plumb is safe
> and correct on the mesh family and that step 1a's 255 is a defective
> record to be re-written to 256 / 0.984183 with the `-n 1` provenance —
> but re-writing records is **step 3's**, and item 4's scope is explicit that
> no record moves in step 2a. So: rule on the 255 → 256 re-record, then the
> parked branch lands as-is. Step 2b (the validation family) is unaffected by
> this stop — it reads a family that showed no reconstruction red at all —
> but it should not run before the plumb's disposition is ruled, since it
> measures the same patch.
>
> **RULED 2026-08-29, 03:00 review — defect repair, not re-baseline; land
> the parked commit.** The `-n 1` control on `main` (no plumb,
> `…050535Z_…-terminals-n1-main.log`, 256 facets / 0.984183, 98 666 cells)
> is the serial truth: one rank has no partition boundary and reads the
> interface whole. Step 1a's `-n 2` **255 / 0.979885** was therefore one
> facet short from the same `GhostMode.none` gap — a *defective record*,
> not partition-dependent physics — and no test carries it
> (`test_birdcage_port_terminals` gates `[0.95, 1.0]`). Disposition:
> §9 item 1 (`GEO-24` step 2a′) cherry-picks `e1dede8`, re-reads
> `port_terminals` at `-n 1/2/12` and `ring_gaps` at `-n 2/12` on the
> landed tree, and annotates the 255 in this table as defective; §9 item 2
> (step 2b, the validation family) retires this entry on green; the
> two-torus `-n 12` finding above is **split out** as its own entry
> (`PORT-12`, below) so this entry can retire without losing it; `GEO-20`
> step 2 is re-run as §9 item 4 after the plumb lands. No band, tolerance
> or record in `tests/` moves under this ruling.
>
> **Step 2a′ ✅ 2026-08-29, 04:30 slot — the plumb is LANDED on `main` and
> the defective digit is disposed of.** `e1dede8` cherry-picked onto
> `31a4e0b` (`470f410`; `git diff HEAD~1 -- src/` is the one
> `io/mesh.py:3356` kwarg + comment hunk, working tree clean after). Re-read
> on the landed tree in six windows / **246 s** of container time:
> `test_birdcage_port_terminals` at `-n 1` / `-n 2` / `-n 12`
> (`…093031Z`, `…093103Z`, `…093130Z`, Status 0, 23 / 21 / 22 s) and
> `test_birdcage_ring_gaps` at `-n 2` / `-n 12` (`…093201Z`, `…093326Z`,
> Status 0, 75 s each), all prefixed `GEO-24-step2aP-`.
>
> **Every anchor met, digit for digit.** Phantom↔air positive control
> **256 facets / 2.040655e-02 m² / 0.984183 at all three widths** on
> **98 666** cells — the serial truth now reproduced in parallel, which is
> the repair. `ring_gaps` port P8 at `-n 12`: **176 air facets / closure
> 1.000000000000** (was 175 / 0.990103697427) on **128 111** cells, with all
> 12 ports' `volume/analytic` 1.000000000000 and all 8 ring sheets
> `meshed/analytic` 1.000000000000; the ring-gapped rung is **110 786**
> cells and Pappus reads 1.000000000000 gapped and uncut. Every other
> printed digit is identical to the step-2a table: leg terminals
> 0.988615826 / 0.988615832 / 0.988615854 / 0.988615858, ring terminals
> 0.974454791 / 0.974454832, the four leg port boxes air 24 facets /
> 5.200000e-04 m² / closure 1.000000000000 / conductor 0, and the kwarg-off
> control 98 666 cells / 0.966977. `-n 2` and `-n 12` agree everywhere.
>
> **Negative control, pre-stated: green and unmoved.**
> `test_two_torus_port_sheet` + `test_cylindrical_domain` `4 passed`,
> Status 0, 30 s, `GEO-16` control at **79 070** cells with tags
> `[1, 2, 3, 101, 102] / [1, 201, 202]` (`…093452Z_…-controls-n2.log`). No
> cell count moved anywhere, so the landed commit is the one that was
> measured. The `attempt/GEO-24-step2a-20260829T052300Z` branch is deleted.
>
> **This entry stays open**: step 2b (the validation family, §9 item 2)
> retires it. Nothing loosened, no band moved, no record in `tests/`
> touched.
>
> **✅ Step 2b 2026-08-29, 06:00 slot — the validation family re-reads clean
> on the plumbed tree at both widths, and THIS ENTRY IS RETIRED.** Eleven
> windows / **485 s** of container time at `470f410`, complex build,
> `FEM_EM_REQUIRE_COMPLEX=1`, `-s`, `-k 30 480`, one module per width per
> window, no `src/` change in the slot; logs
> `20260829T1100*`–`20260829T1108*Z_GEO-24-step2b-*.log`, all **Status 0**.
> Environment gate `11 passed` / 21 s first.
>
> | module | cells (`-n 2` / `-n 12`) | `-n 2` | `-n 12` |
> |---|---|---|---|
> | `test_port_birdcage_lumped_column` | 116 085 / 116 085 | ✅ 2 passed, 33 s | ✅ 2 passed, 30 s |
> | `test_port_birdcage_four_port` | 116 085 / 116 085 | ✅ 5 passed, 49 s | ✅ 5 passed, 39 s |
> | `test_port_birdcage_larmor_probe` | 116 085 / 116 085 | ✅ 3 passed, 38 s | ✅ 3 passed, 33 s |
> | `test_port_birdcage_termination_probe` | 116 085 / 116 085 | ✅ 4 passed, 38 s | ✅ 4 passed, 33 s |
> | `test_port_birdcage_leg_offset_sweep` | 116 085 + 116 475, both widths | ✅ 5 passed, 97 s | ✅ 5 passed, 74 s |
>
> **The gate was pre-stated in two classes, and both are met** (the 03:00
> ruling's lesson, and step 1b's).
>
> *(i) Reconstruction readings — required identical to the digit, and they
> are.* All four `_lumped_column` sheets **26 facets / 5.835298880e-05 m² /
> `w = A/h` 7.294123600e-03 m / out-of-plane 0.000e+00 m** at `-n 2` and
> `-n 12` alike (same in `_four_port`), full-sheet bbox 1.400000000e-02 m,
> filtered bbox 9.167340025e-03 m; every cell count identical across widths
> and equal to step 1b's records at ratio **1.000000** (the displaced rung
> 116 475, ratio 1.003360 against the shared record, exactly as before).
>
> *(ii) Solved digits — required inside each module's own in-file band, and
> every one passes at both widths.* `_larmor_probe`: `Z_{11,21,31,41}`
> reproduce their `PORT-9` records at rel. deviation **1.071e-10 –
> 2.568e-10** (`-n 2`) and **1.071e-10 – 2.566e-10** (`-n 12`), phantom
> `cells/delta` 5.9213 (10 MHz control 12.0002). `_four_port`:
> `sigma_max(S)` **0.999992805** and max column power sum **0.793823974** at
> both widths, C4 class spreads **0.0553 / 0.0353 / 0.0214 %** (band 0.5%) at
> both, pooled off-diagonal 9.2115% and separation 166.6766×,
> `||S−S^T||/||S||` 1.044255156e-14 (`-n 2`) / 1.897457072e-14 (`-n 12`),
> band 1e-3. `_termination_probe`: margin **2256.9707×** and spread
> **0.0040%** at both, open control 1.5951× / 0.0407%. `_leg_offset_sweep`:
> displaced rung breaking (iii′) at **6.2219 / 7.1142 / 2.8474 %** against
> the zero rung's 0.0553 / 0.0353 / 0.0214 %, amplifications 112.58× /
> 201.52× / 133.11×, at both widths. The only `-n 12` movement anywhere is
> in the last displayed digits of `Z_11` in `_lumped_column`
> (+9.201557829e+02−4.718342449e+03j → +9.201557791e+02−4.718342444e+03j,
> **4.1e-9** relative) and in the two Frobenius asymmetry residuals at the
> 1e-14 floor — reported, orders inside every band, and far below the 1e-4
> the `PORT-12` precedent set as the threshold worth reporting at all.
>
> **Negative control** (pre-stated: this family has no kwarg-off control, so
> the control is step 1b's own table): every `-n 2` digit reproduces step
> 1b's `main`-side reading, so the plumb changed nothing this family could
> see — which is the expected result, step 1b having shown the family took no
> damage from `GhostMode.none` in the first place. The two-torus control was
> **deliberately not re-run**: its `-n 12` red is `PORT-12`'s and is not
> moved by this patch.
>
> **Disposition.** `GEO-24` **✅** — the ghost layer is plumbed and both
> consumer families are re-read at `-n 2` and `-n 12`. `GEO-20` step 1's
> "closure and volume/analytic `1.000000000000` on all 12" loses its
> **width-conditional caveat** (above): it is now measured true at 12 ranks
> on the landed tree (`GEO-24` step 2a′, port P8 176 air facets / closure
> 1.000000000000). `GEO-20` step 2 remains 🟡 as a **re-run** of the parked
> 32-port module, now unblocked. Step 1a's `-n 2` **255 / 0.979885** stands
> annotated *defective* (one facet short; `-n 1` truth 256 / 0.984183).
> Nothing loosened, no band moved, no record in `tests/` touched.

### `PORT-12` — the two-torus gap-route reproduction record drifts with rank width on a fixture that already has the `shared_facet` ghost layer (found 2026-08-29 by `GEO-24` step 1b)

| | |
| --- | --- |
| **Test id** | `tests/validation/test_port_lumped_two_torus.py` — the `STEP1_GAP_RATIO_RECORD` reproduction assertion (`REPRODUCTION_BAND` 1e-4). Green at `-n 2`, which is what CI runs; **red at every parallel width above 2** (`-n 4`, `-n 8`, `-n 12` measured). |
| **Verified at** | `d5b4586`, 0.11 image, complex build, 2026-08-29 (`20260829T034253Z_GEO-24-step1b-twotorus-control-n2.log`, `5 passed` / 84 s; `20260829T034112Z_GEO-24-step1b-twotorus-control-n12.log`, `1 failed, 4 passed` / Status 1 / 84 s). Widths 4 and 8 added by `PORT-12` step 1 at `c4630ed` (`20260829T170059Z_PORT-12-step1-twotorus-n4.log`, `1 failed, 4 passed` / Status 1 / 87 s; `20260829T170240Z_PORT-12-step1-twotorus-n8.log`, `1 failed, 4 passed` / Status 1 / 81 s; env gate `20260829T170032Z_PORT-12-step1-env.log`, `11 passed` / 21 s). |
| **Symptom** | `gap ratio: 0.894274 against step 1's record 0.894141 — moved by 1.33e-04, above 1e-04` at `-n 12`; `-n 2` reads **0.894141**, the record exactly. `Im Z12` 1.110303775 (`-n 2`) → 1.110469250 (`-n 12`), 1.5e-4 relative. The mesh does **not** move — **184 176** cells at both widths — and the other four tests in the module pass at `-n 12`. |
| **Four-width table** (`PORT-12` step 1, 2026-08-29) | All four widths on **184 176** cells. Gap route / lumped route / cross-route and `Im Z12`:<br>`-n 2` — gap **0.894141** (= record), `Im Z12(gap)` 1.110303775, `V_gap` +1.365256733e-02+1.079044036e+00j; lumped **0.828893**, `Im Z12(lumped)` 1.029281338; cross-route 7.743060e-02.<br>`-n 4` — gap **0.894274** (+1.33e-04), `Im Z12(gap)` 1.110469342, `V_gap` +1.368962224e-02+1.079204774e+00j; lumped **0.828893**, `Im Z12(lumped)` 1.029281337; cross-route 7.754834e-02.<br>`-n 8` — gap **0.894347** (+2.06e-04), `Im Z12(gap)` 1.110559796, `V_gap` +1.370291038e-02+1.079292623e+00j; lumped **0.828893**, `Im Z12(lumped)` 1.029281336; cross-route 7.761484e-02.<br>`-n 12` — gap **0.894274** (+1.33e-04), `Im Z12(gap)` 1.110469250, `V_gap` +1.373904726e-02+1.079204448e+00j; lumped **0.828893**, `Im Z12(lumped)` 1.029281338; cross-route 7.753298e-02. |
| **Negative control (held)** | Every reconstruction digit is **identical at all four widths**: 184 176 cells, sheet 212 **1583 owned facets**, meshed/CAD area **1.000000000000**, `w` 1.040000000e-02 m, `h` 1.395505060e-02 m, `w/h` 0.745249896 squares, out-of-plane spread **0.0e+00 m**, meshed/analytic gap volume **1.000000000000**. This is **not** the `GEO-24` class of defect on a plumbed fixture. |
| **Not the `GEO-24` defect** | `two_torus_domain` has carried `create_cell_partitioner(GhostMode.shared_facet, 2)` since `PORT-1` step 3b-iv; the quantity that moves is a *solved* line integral (`V = −∫E·dl` on the gap route), not a facet reconstruction. It was run as `GEO-24` step 1b's pre-stated negative control ("an already-plumbed fixture is width-independent") and the control **failed**. |
| **Cause** | **Classified, not yet root-caused. The drift is an evaluation-path effect confined to the gap route, and it is *non-monotone* in width.** The two pre-stated candidates separate cleanly: (a) a *solve-side* drift would move all three routes together — it does not. The **lumped route reads the same solved field through the sheet's own law and is flat to 2e-09** across all four widths (`Im Z12(lumped)` 1.029281338 / …337 / …336 / …338; `I_sheet` −4.122422e−08−1.000166e−06j at every width), and the step-2 *surface* read of the same field, `mean E.yhat over the sheet`, is **bit-identical to every printed digit at all four widths** (shadow −2.958541e+00−7.177866e+01j, fringe +8.607682e-03−1.009219e-02j, ratio 0.000185). So the solved field itself is width-independent to ~1e-9, five orders below the gap route's 1.3e-04–2.1e-04 motion. (b) The **gap route alone moves**, and not monotonically: +1.33e-04 at `-n 4`, +2.06e-04 at `-n 8`, back to +1.33e-04 at `-n 12` — `-n 8`, not `-n 12`, is the worst width, so this is not a "more partitions ⇒ more drift" law. The cross-route figure tracks the gap route exactly (it is derived from it), and the step-2 path/projection residual is likewise non-monotone: 0.0689 / 0.0632 / 0.0662 / 0.0836 pp at 2 / 4 / 8 / 12. One sub-shape worth the root-cause hunt: `Re V_gap` **is** monotone in width (1.365256733e-02 → 1.368962224e-02 → 1.370291038e-02 → 1.373904726e-02, 6.5e-03 relative from `-n 2` to `-n 12`) while `Im V_gap` is not — consistent with the `V = −∫E·dl` path picking up partition-dependent contributions where it crosses a partition boundary, rather than with a converged field being integrated correctly. |
| **Consequence** | The 1e-4 band is a `-n 2` statement until this is classified; every `PORT-1`/`OPS-18` two-torus record is quoted at `-n 2`. `GEO-24` step 2b (the birdcage validation family after the plumb) must not read a `-n 12` solved digit moving at ≤ 1e-4 as evidence the plumb failed. Nothing loosened, no record re-written. **Step 1 adds:** because the drift is on the evaluation path and not the solve, any *other* `V = −∫E·dl` gap-route reading in the package is suspect at parallel width in the same way — but no lumped-sheet port reading is, the lumped route being flat to 2e-09 here. |
| **Resolves with** | ~~`PORT-12` step 1~~ **✅ 2026-08-29** (the four-width table and the classification above). **Step 2 is the 2026-08-30 weekly review's call** with this table in hand: the drift is *not* monotone and *not* shared by all three routes, so the "solver-side fix" option in the original framing is off — the choices are (i) width-qualify `REPRODUCTION_BAND` as a `-n 2` statement, (ii) widen it to a pre-registered parallel band ≥ 2.1e-04 with the non-monotone table as the justification, or (iii) commission a root-cause step on the gap-route line integral's partition crossing. |
| **RULED 2026-08-30, weekly planning review — option (i) with a bounded envelope; option (iii) declined with an epitaph** | `REPRODUCTION_BAND` = 1e-4 stays what it is and is **stated as a `-n 2` record** (every `PORT-1`/`OPS-18` two-torus digit is quoted at that width; the constant's comment says so). At `comm.size > 2` the same assertion runs against a **separate pre-registered `PARALLEL_DRIFT_ENVELOPE = 3e-4`** whose provenance is the four-width table above (max observed +2.06e-04 at `-n 8`, 1.46× headroom), so the drift is *bounded on every width CI might run* rather than hidden by a skip; and the lumped route's width-flatness — `Im Z12(lumped)` within **1e-8** relative across widths, measured 2e-9 — is asserted as the module's new negative control, because that flatness is the reason the production port model is unaffected. **Not (ii)** as framed: widening the *record* band would let the `-n 2` record itself drift. **Not (iii):** the gap route is the two-torus `V = −∫E·dl` estimator, which no birdcage or Larmor quantity reads — `PORT-9`/`PORT-11` are lumped-sheet throughout and flat here to 2e-9 — so a root-cause hunt on a partition-crossing line integral is off the mission's shortest path; it re-opens the day a production quantity is read through a gap-route integral at parallel width. This is `PORT-12` **step 2**, scoped in §7 for the daily review to queue (smoke, real+complex, `-n 2` and one `-n > 2` window). This entry **retires with step 2's landing**. |

### `WF-6` — the first `|B₁⁺|` map is C4-covariant to only ~9%, against a 5% pre-registered discretisation band (found 2026-08-29 by `WF-6` step 1)

| | |
| --- | --- |
| **Test id** | `tests/validation/test_birdcage_b1_plus_map.py::test_b1_plus_map_is_c4_covariant_under_the_drive_rotation` — gate (ii). Red at `-n 2`, which is what CI runs. The module's other two tests, including **gate (i)**, the three-way power accounting, pass. |
| **Verified at** | `bea89f3` + this commit, 0.11 image, complex build, `-n 2`, 2026-08-29 (`20260829T183450Z_WF-6-step1.log`, `1 failed, 13 passed` / Status 1 / 89 s, with `tests/environment`; re-read with the ungated diagnostics at `20260829T183728Z_WF-6-step1-diagnostic.log`, `1 failed, 2 passed` / Status 1 / 87 s). |
| **Symptom** | `|B1+| from the P2 drive at the 90deg-rotated point disagrees with the P1 drive by 8.6516% in relative l2 over 51 phantom centroids, outside the pre-registered 5.0% discretisation band`. The sample set is the 51 tag-3 cell centroids with `r ≤ 0.02 m`, `|z| ≤ 0.02 m` on the 116 085-cell `GEO-19` step-B fixture; `|B₁⁺|` there reads mean 2.077398e-08 T, max 2.834980e-08 T, min 1.457925e-08 T at `V_src = 1 V`. |
| **The band is not passing on noise, and the estimator resolves azimuth** | The **180° negative control holds with room**: the P3 drive against the same 90°-rotated points reads **27.3161%**, 3.2× the failing reading and 5.5× the band. So the comparison is measuring the drive's azimuth, not returning scatter for everything. |
| **The miss is systematic, not a few outlier cells** | Printed and never gated: the pointwise `|B₁⁺|` deviation over the 51 points is median **6.7395%**, p90 **15.0357%**, max **17.5662%** — a broad distribution, so no handful of cells can be blamed. The **second instance of the same identity** — the P4 drive at −90°, which the module solves for exactly this purpose — reads **9.5808%**, alike to P2's 8.6516%. Both 90° instances agreeing rules out anything peculiar to P2 and points at the shared mechanism: `B` is DG0 on a gmsh mesh that is not itself C4-symmetric, so a sample point and its rotated image sit in *different* cells, and the DG0 cell-scatter of a curl is the floor of this comparison. |
| **Cause** | **Not root-caused; two candidates left open for a review.** (a) The pre-registered 5% band simply underestimated DG0 cell-to-cell scatter for a curl at this mesh resolution — the reading would then be an honest measurement of the estimator's floor, and the fix is a better estimator (a CG1 projection of `B`, or cell-volume-weighted comparison, or sampling on a rotation-invariant point set rather than on centroids) rather than a looser band. (b) A real C4 asymmetry in the solved field beyond what the terminal quantities show — but the same fixture's `Z` classes spread ≤ 0.5% (`PORT-9` gate (iii′)), which bounds the *terminal* asymmetry an order of magnitude below this. Nothing was widened, nothing was refitted, and both gates stand as pre-registered. |
| **Not a power-accounting problem** | Gate (i) closes at **9.795751e-03** of the supplied power at the P1 drive and **9.796209e-03** at P2, inside its 1e-2 band, with the shares 0.0008% phantom / 6.5374% conductor / 92.4822% sheets; its negative control (drop the conductor term) misses by 7.517001e-02, 7.7× the band. So the field is energetically accounted for at both drives that gate (ii) compares. |
| **Consequence** | `WF-6` stays **🧪** — step 1's `post/` helpers (`magnetic_flux_density_from_e`, `b1_plus`) are landed and exercised, gate (i) is closed, and **no B₁⁺ homogeneity, CV or absolute-accuracy claim exists**. `main` carries this one red deliberately, per the step's own pre-registered negative-result clause ("record the mismatch, keep the asserts, never widen either band in-slot"). |
| **Resolves with** | `WF-6` steps **1b** (CG1-projected `B` on the same 51 points, the 180° identity read for the first time) and **1c** (a 96-point rotation-invariant ring sample at DG0) — both scoped by the 2026-08-29 18:00 review and queued §9 items 1 and 3, independent of each other, measurement only. The 5% band must not be moved without their tables in hand; the review then either re-registers gate (ii) on the better estimator (candidate (a)) or commissions a field-side hunt (candidate (b)). Noted at scoping: 51 centroids in a 0.02 × 0.04 m cylinder means ≈ 1 cm phantom cells — the DG0 curl scatter candidate is the fixture's resolution, not a mystery. |
| **Step 1b executed 2026-08-29 19:30 — the estimator leg, verdict (a)** | `20260830T003238Z_WF-6-step1b.log`, `1 failed, 15 passed` / Status 1 / 98 s (the one failure is *this* entry's gate (ii), unchanged and deliberately red; both new tests pass). The DG0 `B_phasor` was L²-projected onto `("Lagrange", 1, (3,))` through a Hermitian mass-matrix `LinearProblem` (CG/Jacobi, `ksp_rtol` 1e-12 — never `interpolate`, which is ill-defined at vertices for a DG0 field), and `\|B_x + jB_y\|/2` formed from the projected vector at the *same* 51 points. Anchors all reproduced: DG0 P2-at-+90° **8.6516%**, gate (i)'s P1 residual **9.795751e-03**, both at rtol 1e-4; `valid` all-true, 51 of 51, on every rotated image. **The three-angle × two-estimator table:** <br>`P2 @ +90°` — DG0 **8.6516%** (med 6.7395, p90 15.0357) │ CG1 **2.1870%** (med 1.5240, p90 3.3040) <br>`P4 @ −90°` — DG0 **9.5808%** (med 5.1948, p90 13.4830) │ CG1 **2.1146%** (med 1.5757, p90 3.4706) <br>`P3 @ 180°` — DG0 **8.5970%** (med 5.1290, p90 13.6265) │ CG1 **1.8911%** (med 1.3170, p90 2.8471) <br>`P3 @ +90°` (mis-rotated control) — DG0 **27.3161%** │ CG1 **23.2642%**, both outside the 5% band, asserted. `\|B₁⁺\|` mean over the set 2.077398e-08 T (DG0) vs 2.069556e-08 T (CG1) — the projection moves the magnitude by 0.38%, not the map. |
| **What the table decides** | The pre-registered verdict is **(a) — the estimator floor**, unambiguously: CG1 is inside 5% at *all three* covariance angles, a factor 4–5 below DG0, while the mis-rotated control survives the projection at 23%, so the smoothing has not smoothed the map away. Read the 180° column, which step 1 never had: DG0 gives **8.5970%** there against 8.6516% at +90° — the *same* miss at both angles, which is the signature of a scatter floor and the opposite of what a C2-preserving, C4-breaking field asymmetry (candidate (b)) would produce. Candidate (b) is not supported by any reading on this fixture. **No band was moved:** re-registering gate (ii) on the CG1 estimator, with this table as the new band's provenance, is a **review's call** — the slot recorded and stopped, per the step's scope. `WF-6` stays 🧪 and the gate stays red until then. |
| **Step 1c executed 2026-08-29 22:30 — the sample-set leg, the set is not the mechanism** | `20260830T033147Z_WF-6-step1c.log`, `1 failed, 18 passed` / Status 1 / **97 s** (the one failure is again *this* entry's gate (ii), untouched). Estimator held at DG0, sample set replaced by one closed under the C4 rotation: rings at `r ∈ {0.005, 0.010, 0.015, 0.020}` m × `z ∈ {−0.015, 0, +0.015}` m × 8 azimuths in 45° steps, azimuth start jittered 3.7° off the coordinate planes — 96 points, every ±90° and 180° image a member of the set. Anchors: `valid` **96 of 96** on all four drives and every rotated image; centroid-set DG0 P2-at-+90° reproduced **8.6516%** and gate (i)'s P1 residual **9.795751e-03**, both rtol 1e-4; the mis-rotated control P3-at-+90° **25.8213%**, asserted outside the band. **Ring-set table (centroid-set figure, delta):** <br>`P2 @ +90°` **9.9271%** (med 6.9433, p90 16.2927) — centroid 8.6516%, **+1.28 pp** <br>`P4 @ −90°` **9.9519%** (med 7.3968, p90 16.4548) — centroid 9.5808%, **+0.37 pp** <br>`P3 @ 180°` **8.4706%** (med 5.7448, p90 13.5804) — centroid 8.5970%, **−0.13 pp**. `\|B₁⁺\|` over the ring set, P1 driven: mean 2.023327e-08 T, max 3.263326e-08, min 1.419703e-08. |
| **What the ring set decides** | The pre-registered verdict is **"sample set is not the mechanism"** — all three angles land within ±2 pp of the centroid set (max \|Δ\| 1.28 pp), so the centroid set's lack of closure under the rotation was not manufacturing the miss and the ~9% floor is the **DG0 scatter itself**. This is the one thing step 1b could not distinguish, and it corroborates 1b's verdict (a) from the opposite direction: 1b changed the estimator and the miss fell 4–5×; 1c changed the sample set and the miss did not move. The 180° column agrees with +90° on the ring set too (8.47 vs 9.93%), so candidate (b) remains unsupported. **Per-ring structure, for the review to read against the coil geometry:** no monotone radial trend — 6.33…11.65% at `r = 0.010`, 4.61…12.63% at `r = 0.020`, the single lowest ring being the outermost top one (`r = 0.020, z = +0.015`, 4.61 / 6.21 / 3.96%) and the highest an inner one (`r = 0.005, z = −0.015`, 11.25 / 12.27%); ring-to-ring spread of the same order as the overall figure is what a per-cell scatter looks like. **No band was moved**; gate (ii) stays red, `WF-6` stays 🧪, and re-registering the gate on the CG1 estimator remains the review's call. |
| **RULED 2026-08-30, weekly planning review — gate (ii) is re-registered on the CG1-projected estimator; the DG0 5% assertion is replaced, not loosened** | The two legs read as a pair: change the estimator and the miss falls 4–5× (1b); change the sample set and it does not move (1c). That is the pre-registered candidate (a), and the 180° column (DG0 8.60% ≈ +90° 8.65%) rules out candidate (b) on this fixture. **Ruling:** (1) the production `|B₁⁺|` map estimator for gates and examples is `b1_plus` of the **L²-projected CG1 `B`** (mass-matrix `LinearProblem`, never `interpolate`), with the DG0 field kept as the raw curl; (2) gate (ii) becomes the CG1 covariance identity at **all three angles** (+90°, −90°, 180°) on the 51 centroids, band **5%** unchanged in value but now with a *measured* provenance — CG1 reads 2.19 / 2.11 / 1.89%, p90 ≤ 3.47%, so the band carries 2.3× headroom and is a discretisation floor someone has measured; (3) the mis-rotated 180°-vs-90° control stays asserted **> 5%** under CG1 (23.26%); (4) the DG0 readings are **printed and recorded**, not gated — the old DG0 assert is removed with its record (8.6516 / 9.5808 / 8.5970%) cited in-comment, because gating a curl at DG0 on a non-symmetric mesh gates the mesh, not the map (the `GEO-19` step-C precedent). No CV, homogeneity or absolute-accuracy claim follows from (ii) closing — it is a symmetry identity. This is **`WF-6` step 1d** (§7), one smoke/standard slot on the existing fixture; steps 2–3 stay serial on it. This entry **retires with step 1d's landing**; `main`'s deliberate red retires with it. |

## Recording a new entry

Add an entry when you find a failure you are **not** fixing. Include: the test id, the
literal symptom, the commit you verified it against, the cause (or an explicit "not
diagnosed" — an honest gap is more useful than a guess), and which chunk resolves it.

Remove the entry in the same commit that fixes the test.
