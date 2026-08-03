"""Run OpenMVS dense reconstruction + meshing from a COLMAP undistorted model.

The local COLMAP build is CPU-only and can't run patch_match_stereo/
stereo_fusion (dense stereo requires CUDA). This picks up where
`colmap image_undistorter` leaves off -- reconstruction/<run>/dense/images/
and reconstruction/<run>/dense/sparse/ -- and does dense reconstruction with
OpenMVS instead, which runs on CPU (much slower than GPU, but works):

    InterfaceCOLMAP   (COLMAP undistorted model -> OpenMVS .mvs scene)
    DensifyPointCloud (dense point cloud -- the slow step on CPU)
    ReconstructMesh   (mesh from the dense point cloud)

This is expected to take a long time on CPU (from ~20 minutes to well over an
hour for 100-300 images, most of it in DensifyPointCloud). Run this directly
in your own terminal rather than through anything with a execution time
limit, and let it run to completion.
"""

import argparse
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Where scripts/../docs/SETUP.md has you extract the OpenMVS release zip.
# Override with the OPENMVS_BIN environment variable if yours differs.
DEFAULT_OPENMVS_BIN = r"C:\tools\OpenMVS\vc17\x64\Release"


def run(cmd: list[str]):
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", choices=["from_video", "from_images"], required=True)
    parser.add_argument(
        "--resolution-level", type=int, default=1,
        help="DensifyPointCloud downscale factor, higher = faster & coarser (default: 1)",
    )
    args = parser.parse_args()

    bin_dir = Path(os.environ.get("OPENMVS_BIN", DEFAULT_OPENMVS_BIN))
    dense = ROOT / "reconstruction" / args.run / "dense"
    images = dense / "images"
    sparse = dense / "sparse"

    if not sparse.exists() or not any(sparse.iterdir()):
        raise FileNotFoundError(
            f"No undistorted model in {sparse}. Run `colmap image_undistorter` "
            f"first (see docs/SETUP.md)."
        )

    scene_mvs = dense / "scene.mvs"
    scene_dense_mvs = dense / "scene_dense.mvs"
    mesh_ply = dense / "scene_dense_mesh.ply"

    # Note: no -w/--working-folder here -- it's applied as a prefix to -i/-o,
    # and since those are already absolute paths that doubles them up
    # (e.g. dense/dense/sparse/...) and the tool fails to find its input.
    run([str(bin_dir / "InterfaceCOLMAP.exe"),
         "-i", str(dense),
         "-o", str(scene_mvs)])

    run([str(bin_dir / "DensifyPointCloud.exe"),
         "-i", str(scene_mvs),
         "-o", str(scene_dense_mvs),
         "--resolution-level", str(args.resolution_level)])

    run([str(bin_dir / "ReconstructMesh.exe"),
         "-i", str(scene_dense_mvs),
         "-o", str(mesh_ply)])

    print(f"\nDone. Dense point cloud: {dense / 'scene_dense.ply'}")
    print(f"Mesh: {mesh_ply}")


if __name__ == "__main__":
    main()
