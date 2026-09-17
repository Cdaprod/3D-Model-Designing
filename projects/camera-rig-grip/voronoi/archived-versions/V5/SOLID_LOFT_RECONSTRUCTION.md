# Solid Loft Reconstruction Patch

This replaces the disconnected 32-surface fitter.

## Apply
Do **not** delete the repo. Extract this ZIP over the directory containing
`camera-grip-voronoi-adjustable/` and allow overwrite:

```bash
unzip -o camera-grip-voronoi-adjustable-solid-loft-patch.zip
```

## Import into Onshape
Use:

`assets/smooth/Camera_Right_Grip_RECONSTRUCTED_SOLID.step`

Expected tree: **Parts (1)** rather than **Parts (0), Surfaces (32)**.

The legacy `Camera_Right_Grip_SURFACE_FIT.step` path is overwritten with the
same corrected one-solid STEP, so existing references can also be re-imported.

## Regenerate
```bash
python src/surface_fit.py
```

The reconstruction uses closed periodic B-spline section wires and an
OpenCascade through-sections solid loft. The canonical STL still remains the
source of truth for the Voronoi/voxel generation pipeline.
