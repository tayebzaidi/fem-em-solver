# References — operator-provided texts

This directory holds reference texts the human operator provides locally.
The contents are **gitignored** (copyrighted material is never committed or
pushed); only this README is tracked. On a fresh clone the subdirectories
below are absent until the operator restores them — a missing file here is
expected, not a dead reference.

## Available locally

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
