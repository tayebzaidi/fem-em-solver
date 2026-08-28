# ParaView Visualization Guide

## Running the Example

```bash
./run_examples.sh -e 1 -n 2 -t 180
```

The example solves in the container; the host interpreter has no DolfinX. The
run creates a `paraview_output/` directory with the visualization files below.

---

## Output Files

### XDMF Format (Traditional)
- `magnetostatics_01_straight_wire_A.xdmf` + `.h5` - Vector potential A field
- `magnetostatics_01_straight_wire_B.xdmf` + `.h5` - Magnetic field B
- `magnetostatics_01_straight_wire_B_analytical.xdmf` + `.h5` - Exact analytical B field
- `magnetostatics_01_straight_wire_combined.xdmf` + `.h5` - mesh + CellTags + A + B + B_analytical on one grid

Every XDMF file above carries the mesh and a `CellTags` cell array (an
ordinary array like the fields, usable directly in Threshold), so there is no
separate mesh-only file to open.

### Matplotlib summary
- `magnetostatics_01_straight_wire_validation.png` - |B| vs r, numerical against analytic

A copy of this plot is checked in next to the example so it can be read
without running anything. **That checked-in copy is stale as of 2026-08-26**:
it is from 2026-08-09 and reads relative L2 error 65.8739%, max relative error
85.2498% (the last digit of the max moved between runs — 85.2499% was equally
on record), which are this example's numbers at its **old**
`resolution = 0.01 m`. That resolution no longer meshes on the dolfinx 0.11
image, so the example moved to `resolution = 0.008 m` (`EX-30` leg (root),
2026-08-26; see `01_straight_wire.md` and `docs/testing/known-issues.md`) and
now reads **51.9781% / 76.7330%** at 21 830 cells. A live run rewrites
`paraview_output/magnetostatics_01_straight_wire_validation.png` with the current numbers —
read that one, not the checked-in copy, until the copy is refreshed. The
error is large in either case because of the mesh, not because the comparison
is wrong.

### VTX Format (Modern, requires ADIOS2)

- `magnetostatics_01_straight_wire_A.bp/` - Vector potential A (Lagrange interpolant)
- `magnetostatics_01_straight_wire_B.bp/` - Magnetic field B (Lagrange interpolant)

Both are directories, not files. Repaired 2026-08-10 (`EX-14`): the writers
used to be handed the N1curl `A`, which `VTXWriter` cannot write, under a
single `try` that swallowed `B` with it, so no `.bp` was ever produced. They
now get the same `A_lag`/`B_lag` interpolants the XDMF path uses, and each
writer has its own `try`.

The run verifies the artifact rather than trusting it: `magnetostatics_01_straight_wire_B.bp` is
read back through the ADIOS2 Python bindings and its max |B| is compared with
the in-memory value, printed as the "VTX round-trip check" block. On record
(`docs/testing/logs/20260810T140337Z_EX-14-gate-mag1-v2.log`, `-n 2`) both read
**4.463805898300e-05 T**, relative difference **0.000e+00** against a 1e-10
tolerance. A mismatch raises.

`02_circular_loop.py` carried the identical defect and was repaired the same
way on 2026-08-10 (`EX-17`), so `magnetostatics_02_circular_loop_A.bp/` and `magnetostatics_02_circular_loop_B.bp/`
now exist too, with the same round-trip check — both **7.756122914931e-05 T**,
relative difference **0.000e+00** (`docs/testing/logs/20260810T200154Z_EX-17-gate-mag2.log`).

---

## Opening in ParaView

### Method 1: XDMF Files (Recommended for beginners)

1. **Open ParaView**
2. **File → Open**
3. Navigate to `paraview_output/`
4. Select `magnetostatics_01_straight_wire_B.xdmf` (the magnetic field)
5. In the dialog, choose **"Xdmf3ReaderT"** as the reader
6. Click **"Apply"** in the Properties panel on the left

You should now see the mesh loaded!

### Method 2: VTX Files (Modern)

1. **File → Open**
2. Navigate to `paraview_output/` and select the `magnetostatics_01_straight_wire_B.bp`
   **directory** itself (do not descend into it)
3. Choose the **"ADIOS2VTXReader"** when prompted
4. Click **"Apply"**

`magnetostatics_01_straight_wire_A.bp` opens the same way for the vector potential.

---

## Visualizing the Magnetic Field

### View Field as Colored Surface

1. After loading the data, in the **Properties** panel:
   - Under "Coloring", select **"B"** from the dropdown
   - This colors the mesh by magnetic field magnitude

2. Click the **"Rescale to Data Range"** button (⟳ icon) to adjust colors

### View Field Vectors (Glyphs)

1. With your data loaded, go to **Filters → Common → Glyph**
2. In Glyph properties:
   - **Glyph Type**: Arrow
   - **Orientation Array**: B
   - **Scale Array**: B
   - **Scale Factor**: Adjust to make arrows visible (try 0.001 to start)
   - **Glyph Mode**: All Points or Every Nth Point
3. Click **"Apply"**

This shows arrows indicating field direction and magnitude!

### View Field Lines (Stream Tracer)

1. With your data loaded, go to **Filters → Common → Stream Tracer**
2. In Stream Tracer properties:
   - **Vectors**: B
   - **Seed Type**: Point Cloud (or Line Source)
   - Adjust seed positions to interesting regions
3. Click **"Apply"**
4. Optionally add **Tube** filter to make lines thicker

This shows magnetic field lines flowing around the wire!

### View Cross-Section (Slice)

1. With your data loaded, go to **Filters → Common → Slice**
2. In Slice properties:
   - **Slice Type**: Plane
   - **Origin**: Center of your domain
   - **Normal**: [0, 0, 1] for XY plane, [0, 1, 0] for XZ plane, etc.
3. Click **"Apply"**
4. Color by **"B"** magnitude

This shows the field in a 2D slice through the domain!

---

## Viewing the Mesh

If you just want to see the mesh structure:

1. Open `magnetostatics_01_straight_wire_combined.xdmf`
2. In the toolbar, change representation from "Surface" to **"Wireframe"** or **"Surface with Edges"**

---

## Troubleshooting

### "Cannot find reader for XDMF file"
- Make sure you select **"Xdmf3ReaderT"** (note the "3" and "T")
- Not "XdmfReader" (old version)

### "Vectors not showing"
- Check that **Orientation Array** and **Scale Array** are both set to "B"
- Increase the **Scale Factor** if arrows are too small
- Try "Every Nth Point" with N=10 if there are too many glyphs

### "Field looks wrong"
- Click **"Rescale to Data Range"** button
- Check units - B field is in Tesla (very small values expected)
- For the straight wire, expect cylindrical symmetry

### "VTX files not created"
- A run prints `⚠ VTX output of A failed` / `... of B failed` if a writer
  raised; each writer is independent, so one can succeed alone
- If the round-trip check prints `read-back unavailable`, the ADIOS2 Python
  bindings are missing from the container — the `.bp` may still be fine
- Use the XDMF files meanwhile; they carry every field this example writes

### "ParaView crashes when opening file"
- Try opening a single-field file first: `magnetostatics_01_straight_wire_B.xdmf`
- If that works, then open the combined file
- Check ParaView version - need 5.10+ for best XDMF support

---

## Expected Physics for Straight Wire

For a straight wire carrying current I along the z-axis:

- **B-field pattern**: Circular/azimuthal around the wire
- **B-field magnitude**: Decreases as 1/r (where r = distance from wire)
- **Analytical**: B = μ₀I/(2πr) in the azimuthal direction
- **Symmetry**: Cylindrical symmetry about the wire axis

### What you should see:
- Field lines forming circles around the wire
- Strongest field near the wire surface
- Field decreasing with distance
- No field component along the wire axis (z-direction)

---

## Advanced Visualizations

### 1. Magnitude Contours
- **Filters → Common → Contour**
- **Contour By**: B_Magnitude (or magnitude of B vector)
- Creates iso-surfaces of constant field strength

### 2. Vector Field Animation
- Use **Calculator** filter to compute derived quantities
- Example: Compute |B| = sqrt(B_X^2 + B_Y^2 + B_Z^2)

### 3. Compare with Analytical Solution
- The combined file carries a `B_analytical` point array on the same grid
- **Filters → Calculator**, expression `mag(B - B_analytical)` → pointwise error
- Threshold on `CellTags` first to drop wire cells, where the filamentary
  analytical formula does not apply

---

## File Format Details

### XDMF Format
- **Pros**:
  - Widely supported, works on all platforms
  - Human-readable XML descriptor
  - Efficient HDF5 binary data storage
- **Cons**:
  - Limited to 2nd order geometry
  - Two files per dataset (.xdmf + .h5)

### VTX Format
- **Pros**:
  - Modern ADIOS2 backend
  - Supports arbitrary order elements
  - Better parallel I/O performance
  - Single directory per dataset
- **Cons**:
  - Requires ADIOS2 installation
  - Newer format, less widespread

**Recommendation**: XDMF for the combined tags+fields grid; VTX if you want
the ADIOS2 reader or parallel I/O. The example writes both.

---

## Additional Resources

**ParaView Documentation**:
- [Official ParaView Guide](https://docs.paraview.org/en/latest/)
- [ParaView Tutorial](https://www.paraview.org/Wiki/The_ParaView_Tutorial)

**FEniCSx + ParaView**:
- [FEniCSx Tutorial - ParaView Chapter](https://jsdokken.com/dolfinx-tutorial/chapter1/membrane_paraview.html)
- [DOLFINx I/O Documentation](https://docs.fenicsproject.org/dolfinx/main/python/generated/dolfinx.io.html)

**Understanding the Physics**:
- Magnetic field of current-carrying wires
- Biot-Savart law
- Magnetostatics and Maxwell's equations

---

## Questions?

If you encounter issues or want to visualize other quantities:
1. Check the ParaView built-in help (Help → Guide)
2. Try different filters and experiment!
3. Consult the FEniCSx documentation for other output options

Happy visualizing! 🎨🔬
