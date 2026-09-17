# CAD-selectable STEP outputs

The source ergonomic grip is an STL mesh, so it has no original analytic BREP/NURBS topology.

The files in `assets/step/` are faceted STEP/BREP surface representations.
They are exported specifically so CAD tools such as Onshape and FreeCAD can select:
- faces,
- edges,
- vertices.

The multi-body STEP keeps each functional component separate instead of fusing them:
- cellular ribs,
- heel,
- top,
- rear spine,
- upper transition,
- optional electronics liner,
- cavity reference.

These are still faceted approximations. A true smooth NURBS model requires reverse-engineering/surface fitting.
