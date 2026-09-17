# Surface-Fit Patch — camera-grip-voronoi-adjustable

You **do not need to delete or re-extract the entire adjustable repository**.

This ZIP is an overlay patch. Extract it into the **parent directory that already contains**:

```text
camera-grip-voronoi-adjustable/
```

and allow the folders to merge.

## Mac/Linux

If the patch ZIP is in `~/Downloads` and the repo is in `~/Projects/`:

```bash
cd ~/Projects
unzip -o ~/Downloads/camera-grip-voronoi-adjustable-surface-fit-patch.zip
```

The archive already contains the top-level `camera-grip-voronoi-adjustable/` folder, so it merges into the existing repository.

## What this patch adds

```text
camera-grip-voronoi-adjustable/
├── src/
│   └── surface_fit.py
├── config/
│   └── surface_fit.json
├── assets/
│   └── smooth/
│       ├── Camera_Right_Grip_SURFACE_FIT.step
│       ├── Camera_Right_Grip_SURFACE_FIT.brep
│       ├── Camera_Right_Grip_SURFACE_FIT_PREVIEW.stl
│       └── surface_fit_report.json
└── SURFACE_FIT.md
```

## Run it again

From the repo root:

```bash
python src/surface_fit.py
```

Adjust the patch layout:

```bash
python src/surface_fit.py --patches 10
```

Adjust fitting tolerance:

```bash
python src/surface_fit.py --fit-tolerance 0.25
```

Or edit:

```text
config/surface_fit.json
```

## What the resulting STEP is

The original grip remains an STL mesh and remains the canonical truth for the robust Voronoi/voxel pipeline.

The fitted STEP is a **smooth B-spline/NURBS reference** built from horizontal cross-sections of that STL. Instead of thousands of triangular CAD faces, the default reconstruction contains only:

```text
8 angular patches × 4 Z bands = 32 smooth faces
```

This gives CAD tools much more useful selectable topology:

- smooth faces,
- patch boundary edges,
- patch corner vertices,
- stable surfaces for sketches / external geometry / ShapeBinders.

It does **not** reconstruct the original feature history, and it should not replace the master STL for the printable Voronoi generation pipeline.
