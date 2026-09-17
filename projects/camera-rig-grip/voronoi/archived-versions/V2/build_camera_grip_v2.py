from __future__ import annotations

import json, math, shutil, subprocess, zipfile
from pathlib import Path
import numpy as np
import trimesh
from scipy.spatial import Voronoi
from shapely.geometry import Polygon, MultiPoint, Point, box
from shapely.ops import unary_union

ROOT = Path('/mnt/data/camera-grip-voronoi-v2')
ROOT.mkdir(exist_ok=True)
MASTER_SRC = Path('/mnt/data/Camera_Right_Grip_NORMALIZED_98mm.stl')
MASTER = ROOT / 'Camera_Right_Grip_MASTER_98mm.stl'
shutil.copy2(MASTER_SRC, MASTER)

mesh = trimesh.load(MASTER, force='mesh')
verts = np.asarray(mesh.vertices)
yz = verts[:, [1,2]]

# Approximate usable side silhouette from projected mesh points.
# Concave hull retains the organic grip outline better than a rectangular domain.
cloud = MultiPoint([tuple(p) for p in yz[::3]])
try:
    silhouette = cloud.concave_hull(ratio=0.20, allow_holes=False)
except Exception:
    silhouette = cloud.convex_hull
silhouette = silhouette.buffer(0)

# Protected zones follow the shape instead of a flat Z plane.
# Upper zone protects thumb shelf/control/mount geometry.
upper_keepout = unary_union([
    Point(1.0, 84.0).buffer(21.0, resolution=48),
    Point(-23.0, 73.0).buffer(13.5, resolution=48),
    Polygon([(-42,72),(-28,58),(-14,76),(3,98),(-42,105)])
]).buffer(0)
# Bottom keepout preserves cap/sled interface and heel strength.
lower_keepout = unary_union([
    Point(4.0, 5.0).buffer(13.0, resolution=48),
    box(-36,-4,36,8.5)
]).buffer(0)
protected_2d = unary_union([upper_keepout, lower_keepout])
usable = silhouette.difference(protected_2d).buffer(0)

# Sparse intentionally placed Voronoi seeds (Y,Z mm) for load-path-like cells.
seeds = np.array([
    [-28.0, 63.0],
    [-10.0, 65.0],
    [  9.0, 65.0],
    [ 25.0, 54.0],
    [-25.0, 47.0],
    [ -4.0, 49.0],
    [ 17.0, 43.0],
    [-18.0, 31.0],
    [  3.0, 31.0],
    [ 27.0, 25.0],
    [ -6.0, 17.0],
])

# Add guard points around domain to bound all seed regions.
mins = yz.min(axis=0)-30
maxs = yz.max(axis=0)+30
cy = (mins[0]+maxs[0])/2; cz=(mins[1]+maxs[1])/2
span_y=maxs[0]-mins[0]; span_z=maxs[1]-mins[1]
guards=[]
for ang in np.linspace(0,2*np.pi,24,endpoint=False):
    guards.append([cy + span_y*math.cos(ang), cz + span_z*math.sin(ang)])
pts=np.vstack([seeds,np.array(guards)])
vor=Voronoi(pts)

# Finite polygons helper adapted to SciPy Voronoi recipe.
def finite_polygons_2d(vor, radius=200):
    new_regions=[]; new_vertices=vor.vertices.tolist()
    center=vor.points.mean(axis=0)
    all_ridges={}
    for (p1,p2),(v1,v2) in zip(vor.ridge_points,vor.ridge_vertices):
        all_ridges.setdefault(p1,[]).append((p2,v1,v2))
        all_ridges.setdefault(p2,[]).append((p1,v1,v2))
    for p1, region_idx in enumerate(vor.point_region):
        vertices=vor.regions[region_idx]
        if vertices and all(v>=0 for v in vertices):
            new_regions.append(vertices); continue
        ridges=all_ridges[p1]
        new_region=[v for v in vertices if v>=0]
        for p2,v1,v2 in ridges:
            if v2<0: v1,v2=v2,v1
            if v1>=0: continue
            t=vor.points[p2]-vor.points[p1]; t/=np.linalg.norm(t)
            n=np.array([-t[1],t[0]])
            midpoint=vor.points[[p1,p2]].mean(axis=0)
            direction=np.sign(np.dot(midpoint-center,n))*n
            far=vor.vertices[v2]+direction*radius
            new_region.append(len(new_vertices)); new_vertices.append(far.tolist())
        vs=np.asarray([new_vertices[v] for v in new_region])
        c=vs.mean(axis=0)
        angles=np.arctan2(vs[:,1]-c[1],vs[:,0]-c[0])
        new_region=np.array(new_region)[np.argsort(angles)].tolist()
        new_regions.append(new_region)
    return new_regions,np.asarray(new_vertices)

regions, vertices = finite_polygons_2d(vor)

rib = 5.6
inset = rib/2
cells=[]
for i in range(len(seeds)):
    poly=Polygon(vertices[regions[i]]).buffer(0)
    poly=poly.intersection(usable)
    if poly.is_empty: continue
    # leave nominal ~5.6 mm between neighboring cell openings
    poly=poly.buffer(-inset, join_style='round')
    if poly.is_empty: continue
    # smooth polygon corners and slivers
    poly=poly.buffer(1.4, join_style='round').buffer(-1.4, join_style='round')
    if poly.is_empty: continue
    geoms=list(poly.geoms) if poly.geom_type=='MultiPolygon' else [poly]
    for g in geoms:
        if g.area >= 40.0:
            cells.append((i,g.simplify(0.25, preserve_topology=True)))

# Classification: a few true openings, rest alternating deep pockets.
# Cell IDs are based on seed index, not output order.
through_ids={0,3,7,9}
shallow_ids={1,8}

# Current V1 electronics path, retained as a placeholder until actual components are fitted.
cavity_pts=[[-5.5,10.0,2.0],[-5.0,10.5,18.0],[-3.5,7.0,36.0],[-1.0,1.5,52.0],[1.5,-7.0,68.0],[1.0,-9.0,75.0]]
cavity_r=[6.4,10.0,5.0]
keepout_r=[9.6,13.2,7.2]

# Emit OpenSCAD polygon point arrays and modules.
def scad_poly(g:Polygon):
    pts=list(g.exterior.coords)[:-1]
    return '['+','.join(f'[{p[0]:.4f},{p[1]:.4f}]' for p in pts)+']'

cell_defs=[]
cell_calls=[]
meta_cells=[]
for j,(sid,g) in enumerate(cells):
    name=f'cell_{j}'
    cell_defs.append(f'{name} = {scad_poly(g)};')
    if sid in through_ids:
        kind='through'; side=0; depth=60
    elif sid in shallow_ids:
        kind='shallow'; side=1 if sid%2==0 else -1; depth=8.5
    else:
        kind='deep'; side=1 if sid%2==0 else -1; depth=17.0
    cell_calls.append((name,kind,side,depth,sid))
    meta_cells.append({'seed_id':int(sid),'kind':kind,'side':int(side),'depth_mm':depth,'area_mm2':round(g.area,3)})

# Utility: rounded ellipsoid capsules along control points using hull of spheres scaled per axis.
def vec(v): return '['+','.join(f'{x:.4f}' for x in v)+']'

scad_header='''$fn=28;\nMASTER="Camera_Right_Grip_MASTER_98mm.stl";\n'''
scad_cells='\n'.join(cell_defs)

cavity_scad = scad_header + f'''\nmodule ellipsoid(c, r) {{ translate(c) scale(r) sphere(1); }}\nmodule cavity() {{\n'''
for p in cavity_pts:
    cavity_scad += f'  ellipsoid({vec(p)}, {vec(cavity_r)});\n'
for a,b in zip(cavity_pts[:-1],cavity_pts[1:]):
    cavity_scad += f'  hull() {{ ellipsoid({vec(a)}, {vec(cavity_r)}); ellipsoid({vec(b)}, {vec(cavity_r)}); }}\n'
cavity_scad += '}\ncavity();\n'
(ROOT/'electronics_cavity_v2.scad').write_text(cavity_scad)

keep_scad = scad_header + 'module ellipsoid(c, r) { translate(c) scale(r) sphere(1); }\nmodule keepout(){\n'
for p in cavity_pts:
    keep_scad += f'  ellipsoid({vec(p)}, {vec(keepout_r)});\n'
for a,b in zip(cavity_pts[:-1],cavity_pts[1:]):
    keep_scad += f'  hull() {{ ellipsoid({vec(a)}, {vec(keepout_r)}); ellipsoid({vec(b)}, {vec(keepout_r)}); }}\n'
keep_scad += '}\nkeepout();\n'
(ROOT/'electronics_keepout_v2.scad').write_text(keep_scad)

# Cutters in YZ: polygon is [Y,Z]. Rotate 2D extrusion so extrusion is along X.
# Deep/shallow pockets are tapered toward the grip center, avoiding cookie-cutter prisms.
cutters_scad = scad_header + scad_cells + r'''
module yz_prism(poly, x0, depth, scale2=1.0) {
    // local extrusion Z -> global X; local X->Y, local Y->Z
    translate([x0,0,0]) rotate([0,90,0])
        linear_extrude(height=depth, center=false, convexity=10, scale=scale2)
            polygon(points=poly);
}
module through_cut(poly) {
    translate([-30,0,0]) rotate([0,90,0])
        linear_extrude(height=60, convexity=10)
            polygon(points=poly);
}
module pocket_plus(poly, depth) {
    // starts beyond +X outer face and tapers inward
    yz_prism(poly, 27.0, -depth, 0.72);
}
module pocket_minus(poly, depth) {
    // mirrored construction from -X side
    mirror([1,0,0]) yz_prism(poly, 27.0, -depth, 0.72);
}
'''
# OpenSCAD doesn't like negative extrusion heights, fix modules by direct transform with positive height toward center.
cutters_scad = cutters_scad.replace('yz_prism(poly, 27.0, -depth, 0.72);','translate([27.0,0,0]) rotate([0,-90,0]) linear_extrude(height=depth, convexity=10, scale=0.72) polygon(points=poly);')
cutters_scad = cutters_scad.replace('mirror([1,0,0]) yz_prism(poly, 27.0, -depth, 0.72);','translate([-27.0,0,0]) rotate([0,90,0]) linear_extrude(height=depth, convexity=10, scale=0.72) polygon(points=poly);')
cutters_scad += '\nmodule raw_cutters(){ union(){\n'
for name,kind,side,depth,sid in cell_calls:
    if kind=='through': cutters_scad += f'  through_cut({name});\n'
    elif side>0: cutters_scad += f'  pocket_plus({name}, {depth});\n'
    else: cutters_scad += f'  pocket_minus({name}, {depth});\n'
cutters_scad += '} }\n\n// Remove the protected electronics keepout from every cutter.\nmodule keepout(){\n'
for p in cavity_pts:
    cutters_scad += f'  ellipsoid({vec(p)}, {vec(keepout_r)});\n'
for a,b in zip(cavity_pts[:-1],cavity_pts[1:]):
    cutters_scad += f'  hull() {{ ellipsoid({vec(a)}, {vec(keepout_r)}); ellipsoid({vec(b)}, {vec(keepout_r)}); }}\n'
cutters_scad += '}\nmodule ellipsoid(c,r){translate(c) scale(r) sphere(1);}\ndifference(){ raw_cutters(); keepout(); }\n'
(ROOT/'voronoi_cutters_v2.scad').write_text(cutters_scad)

# Final construction.
final_scad = scad_header + '''\nmodule cavity(){ import("Electronics_Cavity_V2.stl", convexity=10); }\nmodule cutters(){ import("Voronoi_Cutters_V2.stl", convexity=10); }\ndifference(){ import(MASTER, convexity=10); cavity(); cutters(); }\n'''
(ROOT/'grip_voronoi_v2.scad').write_text(final_scad)

hollow_scad = scad_header + '''\ndifference(){ import(MASTER, convexity=10); import("Electronics_Cavity_V2.stl", convexity=10); }\n'''
(ROOT/'grip_hollow_v2.scad').write_text(hollow_scad)

# Build with OpenSCAD.
def run_scad(src:Path, out:Path):
    cmd=['openscad','-o',str(out),str(src)]
    p=subprocess.run(cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=240)
    (ROOT/(src.stem+'.log')).write_text(p.stdout)
    if p.returncode!=0 or not out.exists():
        raise RuntimeError(f'OpenSCAD failed for {src.name}:\n{p.stdout[-4000:]}')

run_scad(ROOT/'electronics_cavity_v2.scad', ROOT/'Electronics_Cavity_V2.stl')
run_scad(ROOT/'electronics_keepout_v2.scad', ROOT/'Electronics_Keepout_V2.stl')
run_scad(ROOT/'voronoi_cutters_v2.scad', ROOT/'Voronoi_Cutters_V2.stl')
run_scad(ROOT/'grip_hollow_v2.scad', ROOT/'Camera_Right_Grip_HOLLOW_V2_98mm.stl')
run_scad(ROOT/'grip_voronoi_v2.scad', ROOT/'Camera_Right_Grip_VORONOI_V2_98mm.stl')

# Validate meshes.
validation={}
for f in ['Camera_Right_Grip_MASTER_98mm.stl','Electronics_Cavity_V2.stl','Electronics_Keepout_V2.stl','Voronoi_Cutters_V2.stl','Camera_Right_Grip_HOLLOW_V2_98mm.stl','Camera_Right_Grip_VORONOI_V2_98mm.stl']:
    mm=trimesh.load(ROOT/f,force='mesh')
    validation[f]={
        'faces':int(len(mm.faces)),
        'vertices':int(len(mm.vertices)),
        'watertight':bool(mm.is_watertight),
        'body_count':int(len(mm.split(only_watertight=False))),
        'volume_mm3':round(float(mm.volume),3),
        'extents_mm':[round(float(x),4) for x in mm.extents],
        'bounds_mm':[[round(float(x),4) for x in row] for row in mm.bounds]
    }

params={
    'version':'V2',
    'master':'Camera_Right_Grip_MASTER_98mm.stl',
    'physical_units':'mm',
    'master_extents_mm':[float(x) for x in mesh.extents],
    'voronoi_seed_count':int(len(seeds)),
    'voronoi_seeds_yz_mm':seeds.tolist(),
    'generated_cut_regions':len(cells),
    'nominal_rib_width_mm':rib,
    'cut_strategy':'sparse smoothed YZ Voronoi with tapered one-sided pockets plus selected through-openings',
    'through_seed_ids':sorted(through_ids),
    'shallow_seed_ids':sorted(shallow_ids),
    'deep_pocket_depth_mm':17.0,
    'shallow_pocket_depth_mm':8.5,
    'pocket_inner_scale':0.72,
    'upper_keepout':'organic/curved 2D union around thumb shelf instead of flat Z cutoff',
    'bottom_keepout':'organic heel + cap zone',
    'electronics_cavity_radii_mm':cavity_r,
    'electronics_keepout_radii_mm':keepout_r,
    'electronics_centerline_xyz_mm':cavity_pts,
    'cells':meta_cells,
}
(ROOT/'process_parameters_v2.json').write_text(json.dumps(params,indent=2))
(ROOT/'validation_summary_v2.json').write_text(json.dumps(validation,indent=2))

readme=f'''# Camera Right Grip — Voronoi V2\n\nV2 is derived from the immutable normalized 98 mm master. It addresses the visible V1 problems: flat cookie-cutter extrusions, hard horizontal top protection, too many cells, sharp fins, and an overly planar appearance.\n\n## What changed from V1\n\n- Reduced to {len(seeds)} intentionally placed Voronoi seeds.\n- Nominal rib spacing increased to ~{rib:.1f} mm.\n- Upper protected region is an organic/curved mask following the thumb/control area rather than a flat Z cutoff.\n- Bottom/heel service region remains structurally protected.\n- Four selected cells are true through-openings.\n- Other cells are tapered one-sided pockets, alternating sides, so the exterior gets depth without turning every cell into a full hole.\n- Two cells are deliberately shallow relief pockets.\n- Voronoi cutters are clipped away from the electronics keepout.\n- Cell polygons are inset and rounded before 3D construction to reduce acute slivers.\n\n## Files\n\n- `Camera_Right_Grip_MASTER_98mm.stl` — immutable canonical master.\n- `Camera_Right_Grip_VORONOI_V2_98mm.stl` — V2 prototype.\n- `Camera_Right_Grip_HOLLOW_V2_98mm.stl` — cavity-only derivative.\n- `Voronoi_Cutters_V2.stl` — the actual V2 cutter set.\n- `Electronics_Cavity_V2.stl` / `Electronics_Keepout_V2.stl` — protected internal volumes.\n- `*_v2.scad` — reproducible OpenSCAD Boolean sources.\n- `process_parameters_v2.json` — deterministic construction parameters.\n- `validation_summary_v2.json` — mesh QA.\n\n## Important design status\n\nThis is a V2 topology/form prototype, not yet print-final. The internal tunnel is still the placeholder envelope from V1 because actual STEP/STL models for the Lolin S2 Mini, joystick, buttons, battery, and connector stack have not yet been fitted. Those components should drive V3 internal geometry.\n\n## Recommended inspection\n\nImport the master, V2 grip, and cutters into the same Onshape/FreeCAD document. Toggle the cutters independently and inspect:\n\n1. top thumb shelf continuity,\n2. minimum rib necks,\n3. heel/cap material,\n4. pocket depth from both sides,\n5. any remaining knife-edge surface intersections.\n'''
(ROOT/'README.md').write_text(readme)

# Zip package.
zip_path=Path('/mnt/data/camera-grip-voronoi-v2.zip')
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(ROOT.iterdir()):
        if p.is_file(): z.write(p, arcname=f'camera-grip-voronoi-v2/{p.name}')

print('Built', zip_path)
print(json.dumps(validation,indent=2))
