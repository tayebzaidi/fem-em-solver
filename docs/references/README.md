# References — operator-provided texts and cached upstream docs

This directory holds reference material for offline sessions. Two kinds:
**operator-provided texts** (gitignored — copyrighted material is never
committed or pushed; absent on a fresh clone until the operator restores
them, so a missing file is expected, not a dead reference) and **cached
public upstream documentation** (tracked, available on any clone).

## Tracked (cached public docs)

- **`dolfinx-0.11-migration/`** — the `OPS-18` migration pack, cached
  2026-08-18 from public release notes and demos because scheduled
  sessions have no network: distilled 0.7.2 → 0.11 API map with a
  repo-specific hit list, per-version release-note summaries (0.10 is a
  documented gap), and verbatim 0.11 idioms. The installed container
  API is ground truth over the pack.

## Available locally (gitignored)

- **`jin-fem-3e/`** — Jin, *The Finite Element Method in Electromagnetics*,
  3rd ed. (Wiley, ISBN 9781118841983), converted to per-chapter markdown
  from the operator's EPUB (`JianmingJinFiniteElemMethodElectro.epub`, kept
  beside it). Start at `jin-fem-3e/INDEX.md` for the chapter/section map.
  Conversion caveats: equations are placeholders like `[eq (8.12)]` keyed
  to the print numbering — the prose, definitions, and derivation structure
  are faithful and Grep-able, but for the mathematics itself cite the
  equation number and consult the EPUB/print copy. Figures are `[image: …]`
  placeholders. The book index (page-number based) was not converted.

  Regenerating after an EPUB update is mechanical: a stdlib-only Python
  pass (unzip, strip the XHTML per spine item, emit `#` headings, replace
  `eqN-M.gif` images with `[eq (N.M)]` placeholders, rebuild `INDEX.md`
  from the headings).

Consult these before re-deriving formulation, feed/port-model, boundary
condition, or solver theory — several PORT-1 questions (gap-source
impedance artifacts, voltage path dependence) are treated directly in Jin
chapters 5, 8, 9, and 12.
