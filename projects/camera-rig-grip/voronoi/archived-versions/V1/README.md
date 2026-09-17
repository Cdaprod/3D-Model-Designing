# Camera Right Grip — normalized + structural Voronoi prototype

This package derives all geometry from `Camera_Right_Grip_MASTER_98mm.stl`.
The master is kept untouched. Coordinates are millimeters, centered in X/Y, with the lowest point at Z=0.

## Generated design logic

- 98 mm real-world overall basic grip length.
- Internal slide-in electronics tunnel follows the grip's measured cross-section centerline.
- A larger protected keep-out surrounds that tunnel, leaving roughly 3 mm of liner before Voronoi cutters can reach it.
- Voronoi cells are generated in the broad YZ side profile and extruded through X.
- Cell interiors are inset so the remaining material forms ~5.2 mm nominal organic ribs.
- Bottom 10 mm stays solid for a future removable electronics cap / sled interface.
- Z >= 79 mm stays solid for the thumb/control/mount region.
- Voronoi openings may become true through-openings away from the tunnel, but stop at the electronics keep-out near the protected internal liner.

## Files

- `Camera_Right_Grip_MASTER_98mm.stl` — immutable normalized master.
- `Camera_Right_Grip_HOLLOW_98mm.stl` — master with slide-in electronics cavity.
- `Camera_Right_Grip_VORONOI_PROTOTYPE_98mm.stl` — cavity + protected structural Voronoi cuts.
- `Electronics_Cavity_Reference.stl` — negative volume for electronics placement.
- `Electronics_Keepout_Reference.stl` — region Voronoi cuts are prohibited from entering.
- `Voronoi_Cutters_Reference.stl` — actual grip-intersecting cutter geometry.
- `.scad` source files — editable/reproducible OpenSCAD Boolean construction.
- `process_parameters.json` — all key dimensions and deterministic seed.

## Important

This is the first structural-layout prototype, not a print-final grip. The exact joystick, buttons, fasteners, battery, and Lolin S2 Mini models have not yet been fitted, so the top control zone is intentionally kept conservative/solid.
