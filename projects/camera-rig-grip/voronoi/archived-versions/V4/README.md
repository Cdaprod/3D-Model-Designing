# camera-grip-voronoi-adjustable

Canonical adjustable camera-grip project consolidating the V1-V3 experiments.

## Recommended files

**Print / visual mesh**
`assets/Camera_Right_Grip_ADJUSTABLE_DEFAULT_PRINT.stl`

**CAD-editable/selectable multi-body model**
`assets/step/Camera_Right_Grip_ADJUSTABLE_MULTIBODY_SELECTABLE.step`

Use the STEP file when you want to select faces, edges or vertices in Onshape/FreeCAD.

## Why both STL and STEP?

The source hand-grip geometry began as a triangulated STL. STL is only a mesh, so CAD systems do not expose the kind of BREP topology you expect from native CAD.

The STEP exports in this package convert coarser faceted proxies into explicit CAD faces/edges/vertices. They are not smooth reconstructed NURBS, but they are selectable and usable as CAD references.

## Separate bodies

Nothing is forced into one giant body in the selectable STEP output.

`assets/step/` contains:
- Cellular_Ribs_SELECTABLE.step
- Heel_Protected_SELECTABLE.step
- Top_Protected_SELECTABLE.step
- Rear_Spine_SELECTABLE.step
- Upper_Transition_SELECTABLE.step
- Electronics_Liner_OPTIONAL_SELECTABLE.step
- Electronics_Cavity_REFERENCE_SELECTABLE.step
- Camera_Right_Grip_ADJUSTABLE_MULTIBODY_SELECTABLE.step

The electronics liner is **not fused into the default print**. It is a separate optional body.

## Consolidated defaults

- master height: 98 mm
- seeds: 12
- rib width: 5.4 mm
- surface structural depth: 6.0 mm
- heel solid height: 10.0 mm
- top solid begins: Z=81.0 mm
- voxel pitch: 0.8 mm
- selectable STEP proxy pitch: 1.8 mm
- generic electronics liner fused into print: **disabled**

## Presets

- `config/presets/balanced.json`
- `config/presets/lightweight.json`
- `config/presets/reinforced.json`

## Adjustable configuration

The source of truth is `config/defaults.json`.

The generator is intentionally parameter-first so you can change the field without redesigning the grip:
- cell/seed count
- rib width
- structural depth
- top/heel protected regions
- spine width/position
- resolution
- optional electronics liner
- placeholder electronics envelope dimensions

## Important next evolution

The electronics cavity/liner remains a placeholder reference. The right next step is replacing it with the actual Lolin S2 Mini, joystick, button PCB/perfboard, battery and connector envelopes.
