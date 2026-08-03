"""Import a fused COLMAP point cloud into Blender and export a cleaned .obj.

Run inside Blender:

    blender --background --python blender/cleanup_scene.py -- <input.ply> <output.obj>

This script only handles the mechanical steps (import, optional decimate,
export). Removing floating geometry, stray walls, and other artifacts is
inherently a manual/visual judgment call — do that by hand in the Blender
GUI before running the export step, or open this same file interactively
(`blender --python blender/cleanup_scene.py`, no `--background`) to inspect
before exporting.

Manual cleanup checklist (do in the Blender GUI, in Edit Mode):
  1. Select stray floating points/geometry disconnected from the table -> Delete.
  2. Select any reconstructed walls/floor you don't want -> Delete.
  3. Crop to the table + mug + screwdriver + water bottle region.
Then re-run this script pointing --output at the cleaned file, or just
manually export via File > Export > Wavefront (.obj).
"""

import sys

import bpy

DECIMATE_RATIO = 0.5
FACE_COUNT_THRESHOLD = 500_000  # only decimate meshes denser than this


def parse_args():
    argv = sys.argv
    if "--" not in argv:
        raise SystemExit(__doc__)
    args = argv[argv.index("--") + 1:]
    if len(args) != 2:
        raise SystemExit(__doc__)
    return args[0], args[1]


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def import_ply(path: str):
    if hasattr(bpy.ops.wm, "ply_import"):
        bpy.ops.wm.ply_import(filepath=path)
    else:
        bpy.ops.import_mesh.ply(filepath=path)
    return bpy.context.selected_objects[0]


def decimate_if_dense(obj):
    mesh = obj.data
    if not hasattr(mesh, "polygons") or len(mesh.polygons) == 0:
        print(f"'{obj.name}' has no faces (raw point cloud) — skipping decimate.")
        return
    if len(mesh.polygons) < FACE_COUNT_THRESHOLD:
        return
    mod = obj.modifiers.new(name="Decimate", type="DECIMATE")
    mod.ratio = DECIMATE_RATIO
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)
    print(f"Decimated '{obj.name}' to ratio {DECIMATE_RATIO}.")


def export_obj(path: str):
    if hasattr(bpy.ops.wm, "obj_export"):
        bpy.ops.wm.obj_export(filepath=path)
    else:
        bpy.ops.export_scene.obj(filepath=path)


def main():
    input_path, output_path = parse_args()
    clear_scene()
    obj = import_ply(input_path)
    decimate_if_dense(obj)
    export_obj(output_path)
    print(f"Exported {output_path}")
    print("Remember: run the manual cleanup checklist in this file's docstring")
    print("before treating this .obj as final.")


if __name__ == "__main__":
    main()
