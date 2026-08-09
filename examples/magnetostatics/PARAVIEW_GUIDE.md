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
- `straight_wire_A.xdmf` + `.h5` - Vector potential A field
- `straight_wire_B.xdmf` + `.h5` - Magnetic field B
- `straight_wire_B_analytical.xdmf` + `.h5` - Exact analytical B field
- `straight_wire_combined.xdmf` + `.h5` - mesh + CellTags + A + B + B_analytical on one grid

Every XDMF file above carries the mesh and a `CellTags` cell array (an
ordinary array like the fields, usable directly in Threshold), so there is no
separate mesh-only file to open.

### Matplotlib summary
- `straight_wire_validation.png` - |B| vs r, numerical against analytic

A copy of this plot is checked in next to the example so it can be read
without running anything. It is regenerated from a real run whenever the
example changes; the copy in the repo is from 2026-08-09 and reads relative
L2 error 65.8739%, max relative error 85.2498% (the last digit of the max
moves between runs — 85.2499% is equally on record) — the numbers for
this fixture, which is coarse on purpose (`resolution = 0.01 m`) so the
scheduled runs stay cheap. The error is large because of the mesh, not
because the comparison is wrong.

### VTX Format (Modern, requires ADIOS2) — **not currently produced**

The example attempts a VTX/ADIOS2 export and it fails every run, printing

```
⚠ VTX output failed (ADIOS2 may not be available): Only (discontinuous)
Lagrange functions are supported. Interpolate Functions before output.
```

`VTXWriter` is handed the N1curl potential `A`, which it cannot write, and the
one `try` block covers both writers, so no `.bp` directory is produced for `B`
either. See `docs/testing/known-issues.md`. Use the XDMF files above; if you
find a stale `.bp` directory in `paraview_output/`, it predates 2026-08-03
and is not from your run.

---

## Opening in ParaView

### Method 1: XDMF Files (Recommended for beginners)

1. **Open ParaView**
2. **File → Open**
3. Navigate to `paraview_output/`
4. Select `straight_wire_B.xdmf` (the magnetic field)
5. In the dialog, choose **"Xdmf3ReaderT"** as the reader
6. Click **"Apply"** in the Properties panel on the left

You should now see the mesh loaded!

### Method 2: VTX Files (Modern)

Unavailable — the VTX export fails on every run (see "Output Files" above).
XDMF is the only format the example writes.

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

1. Open `straight_wire_combined.xdmf`
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
- Expected: the export fails on every run, and not because ADIOS2 is missing
  (see "Output Files")
- Use XDMF files instead - they carry every field this example writes

### "ParaView crashes when opening file"
- Try opening a single-field file first: `straight_wire_B.xdmf`
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

**Recommendation**: XDMF, which is also the only format this example
successfully writes today.

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
