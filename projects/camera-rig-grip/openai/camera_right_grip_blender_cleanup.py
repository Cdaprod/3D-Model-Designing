import bpy
import bmesh
import os
from mathutils import Vector

# ============================================================
# Camera Right Grip - Blender cleanup / sculpt-prep
#
# IMPORTANT:
# This intentionally DOES NOT voxel-fill the scan.
# The previous failure came from forcing a very open scan into
# a volume. This pass preserves the scanned outer surface.
#
# Workflow:
#   1. Import original GLTF
#   2. Keep the dominant mesh object
#   3. Remove tiny disconnected mesh islands
#   4. Merge near-duplicate vertices
#   5. Recalculate normals
#   6. Surface-remesh with QuadriFlow (no volume filling)
#   7. Apply conservative volume-preserving smoothing
#   8. Save .blend + export GLB/STL
#
# Open the resulting .blend and inspect/sculpt BEFORE making it
# watertight or cutting button-board pockets.
# ============================================================

# ---------- PATHS ----------
SOURCE = os.path.expanduser(
    "~/Downloads/Camera Right Grip parts.gltf"
)

OUTPUT_DIR = os.path.expanduser(
    "~/Desktop/camera-grip-cleanup"
)

BLEND_OUT = os.path.join(
    OUTPUT_DIR,
    "Camera_Right_Grip_SCULPT_READY.blend"
)

GLB_OUT = os.path.join(
    OUTPUT_DIR,
    "Camera_Right_Grip_SCULPT_READY.glb"
)

STL_OUT = os.path.join(
    OUTPUT_DIR,
    "Camera_Right_Grip_SCULPT_READY.stl"
)

# ---------- TUNING ----------
# Tiny disconnected components below this face count are removed.
MIN_ISLAND_FACES = 40

# Merge vertices closer than this fraction of the largest object dimension.
MERGE_DISTANCE_FRACTION = 0.00010

# QuadriFlow target. Raise for more detail, lower for lighter sculpting.
TARGET_FACES = 45000

# Conservative smoothing.
SMOOTH_ITERATIONS = 3
SMOOTH_FACTOR = 0.12


def ensure_object_mode():
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')


def delete_everything():
    ensure_object_mode()
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)


def import_gltf(path):
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"\nSource file not found:\n{path}\n\n"
            "Edit SOURCE at the top of the script to match your file location."
        )
    bpy.ops.import_scene.gltf(filepath=path)


def mesh_face_count(obj):
    return len(obj.data.polygons) if obj.type == 'MESH' else 0


def keep_largest_mesh_object():
    mesh_objects = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    if not mesh_objects:
        raise RuntimeError("No mesh objects were imported.")

    main = max(mesh_objects, key=mesh_face_count)

    for obj in list(mesh_objects):
        if obj != main:
            bpy.data.objects.remove(obj, do_unlink=True)

    main.name = "Grip_SCAN_WORKING"
    bpy.context.view_layer.objects.active = main
    main.select_set(True)

    return main


def remove_small_connected_islands(obj, min_faces=40):
    """
    Remove disconnected face islands that are smaller than min_faces.
    This does NOT close holes or invent volume.
    """
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.faces.ensure_lookup_table()

    unvisited = set(bm.faces)
    components = []

    while unvisited:
        seed = unvisited.pop()
        stack = [seed]
        component = {seed}

        while stack:
            face = stack.pop()
            for edge in face.edges:
                for linked_face in edge.link_faces:
                    if linked_face in unvisited:
                        unvisited.remove(linked_face)
                        component.add(linked_face)
                        stack.append(linked_face)

        components.append(component)

    if not components:
        bm.free()
        return

    largest = max(components, key=len)

    # Preserve dominant component and any reasonably substantial islands.
    to_delete = []
    for component in components:
        if component is largest:
            continue
        if len(component) < min_faces:
            to_delete.extend(component)

    if to_delete:
        bmesh.ops.delete(
            bm,
            geom=to_delete,
            context='FACES'
        )

    # Remove vertices/edges left with no faces.
    loose_verts = [v for v in bm.verts if not v.link_faces]
    if loose_verts:
        bmesh.ops.delete(
            bm,
            geom=loose_verts,
            context='VERTS'
        )

    bm.to_mesh(mesh)
    bm.free()
    mesh.update()


def clean_mesh(obj):
    # Apply transform so geometry operations behave consistently.
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(
        location=False,
        rotation=False,
        scale=True
    )

    dims = obj.dimensions
    max_dim = max(dims.x, dims.y, dims.z)
    merge_dist = max_dim * MERGE_DISTANCE_FRACTION

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')

    # Merge very-close duplicate vertices.
    try:
        bpy.ops.mesh.remove_doubles(threshold=merge_dist)
    except Exception:
        # Blender versions where the operator was renamed internally.
        bpy.ops.mesh.merge_by_distance(distance=merge_dist)

    # Recalculate outside normals.
    bpy.ops.mesh.normals_make_consistent(inside=False)

    bpy.ops.object.mode_set(mode='OBJECT')


def duplicate_original_reference(obj):
    ref = obj.copy()
    ref.data = obj.data.copy()
    ref.name = "Grip_SCAN_REFERENCE"
    bpy.context.collection.objects.link(ref)

    # Hide untouched reference by default.
    ref.hide_set(True)
    ref.hide_render = True

    return ref


def quadriflow_surface_remesh(obj):
    """
    QuadriFlow remeshes the SURFACE rather than voxel-filling a volume.
    This is why we use it here.
    """
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    before = len(obj.data.polygons)

    try:
        bpy.ops.object.quadriflow_remesh(
            target_faces=TARGET_FACES,
            preserve_sharp=False,
            preserve_boundary=True,
            use_mesh_symmetry=False,
            seed=0
        )
        print(
            f"QuadriFlow complete: {before} -> "
            f"{len(obj.data.polygons)} faces"
        )
    except Exception as exc:
        print("\nWARNING: QuadriFlow did not run.")
        print(exc)
        print(
            "The cleaned scan is still usable. "
            "You can run Object > Remesh > QuadriFlow manually."
        )


def conservative_smooth(obj):
    mod = obj.modifiers.new(
        name="Grip_Surface_Soften",
        type='LAPLACIANSMOOTH'
    )

    mod.iterations = SMOOTH_ITERATIONS
    mod.lambda_factor = SMOOTH_FACTOR
    mod.lambda_border = 0.02
    mod.use_volume_preserve = True
    mod.use_normalized = True

    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)


def shade_smooth(obj):
    for poly in obj.data.polygons:
        poly.use_smooth = True


def center_view_on(obj):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)


def export_outputs(obj):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Save full Blender project first.
    bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT)

    # Export ONLY working sculpt-ready object.
    ensure_object_mode()
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    # GLB
    bpy.ops.export_scene.gltf(
        filepath=GLB_OUT,
        export_format='GLB',
        use_selection=True
    )

    # STL - Blender 4.x operator first, older fallback second.
    try:
        bpy.ops.wm.stl_export(
            filepath=STL_OUT,
            export_selected_objects=True
        )
    except Exception:
        try:
            bpy.ops.export_mesh.stl(
                filepath=STL_OUT,
                use_selection=True
            )
        except Exception as exc:
            print("WARNING: STL export failed:", exc)


def main():
    print("\n=== Camera Right Grip cleanup ===")

    delete_everything()
    import_gltf(SOURCE)

    obj = keep_largest_mesh_object()

    print("Imported dominant mesh:")
    print("  vertices:", len(obj.data.vertices))
    print("  faces:", len(obj.data.polygons))
    print("  dimensions:", tuple(round(v, 6) for v in obj.dimensions))

    remove_small_connected_islands(
        obj,
        min_faces=MIN_ISLAND_FACES
    )

    clean_mesh(obj)

    # Keep hidden pre-remesh reference inside the .blend.
    duplicate_original_reference(obj)

    quadriflow_surface_remesh(obj)
    conservative_smooth(obj)
    shade_smooth(obj)

    obj.name = "Grip_ENVELOPE_SCULPT_READY"

    center_view_on(obj)
    export_outputs(obj)

    print("\n=== DONE ===")
    print("BLEND:", BLEND_OUT)
    print("GLB:  ", GLB_OUT)
    print("STL:  ", STL_OUT)
    print(
        "\nNext: inspect the surface in Sculpt Mode. "
        "Do NOT Boolean hardware into it yet."
    )


main()
