"""Compare the from_video and from_images reconstructions.

Quantitative: parses COLMAP's own text output (images.txt, points3D.txt) for
registered image count, sparse point count, and mean reprojection error, plus
the dense point count from OpenMVS's DensifyPointCloud output.

Visual: loads both dense point clouds and saves a side-by-side scatter plot
for eyeballing.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from plyfile import PlyData

ROOT = Path(__file__).resolve().parent.parent
RUNS = ["from_video", "from_images"]


def count_registered_images(images_txt: Path) -> int:
    lines = [l for l in images_txt.read_text().splitlines() if not l.startswith("#") and l.strip()]
    # Each registered image occupies two lines (pose line + POINTS2D line).
    return len(lines) // 2


def parse_points3d(points3d_txt: Path) -> tuple[int, float]:
    errors = []
    for line in points3d_txt.read_text().splitlines():
        if line.startswith("#") or not line.strip():
            continue
        fields = line.split()
        errors.append(float(fields[7]))  # POINT3D_ID X Y Z R G B ERROR ...
    if not errors:
        return 0, float("nan")
    return len(errors), float(np.mean(errors))


def load_dense_ply(path: Path):
    """Read vertex positions + colors from an OpenMVS dense point cloud.

    OpenMVS's DensifyPointCloud output has per-vertex list properties
    (view_indices, view_weights) that trimesh's strict PLY parser rejects
    ("PLY is unexpected length!"), so this uses plyfile instead.
    """
    vertex = PlyData.read(path)["vertex"]
    points = np.stack([vertex["x"], vertex["y"], vertex["z"]], axis=1)
    colors = None
    if "red" in vertex.data.dtype.names:
        colors = np.stack([vertex["red"], vertex["green"], vertex["blue"]], axis=1) / 255.0
    return points, colors


def stats_for_run(run: str) -> dict:
    sparse_model = ROOT / "reconstruction" / run / "sparse" / "0"
    images_txt = sparse_model / "images.txt"
    points3d_txt = sparse_model / "points3D.txt"
    dense_ply = ROOT / "reconstruction" / run / "dense" / "scene_dense.ply"

    n_registered = count_registered_images(images_txt)
    n_sparse_points, mean_error = parse_points3d(points3d_txt)

    n_dense_points = None
    if dense_ply.exists():
        points, _ = load_dense_ply(dense_ply)
        n_dense_points = len(points)

    return {
        "run": run,
        "registered_images": n_registered,
        "sparse_points": n_sparse_points,
        "mean_reprojection_error": mean_error,
        "dense_points": n_dense_points,
        "dense_ply": dense_ply if dense_ply.exists() else None,
    }


def print_table(rows: list[dict]):
    headers = ["run", "registered_images", "sparse_points", "mean_reprojection_error", "dense_points"]
    print("".join(h.ljust(24) for h in headers))
    for r in rows:
        print("".join(str(r[h]).ljust(24) for h in headers))


def save_visual_comparison(rows: list[dict], out_path: Path):
    available = [r for r in rows if r["dense_ply"] is not None]
    if not available:
        print("No dense .ply files found, skipping visual comparison.")
        return

    fig = plt.figure(figsize=(6 * len(available), 6))
    for i, r in enumerate(available):
        points, colors = load_dense_ply(r["dense_ply"])

        ax = fig.add_subplot(1, len(available), i + 1, projection="3d")
        ax.scatter(points[:, 0], points[:, 1], points[:, 2], c=colors, s=0.5)
        ax.set_title(f"{r['run']} ({len(points)} pts)")
        ax.set_box_aspect([1, 1, 1])

    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    print(f"Saved visual comparison to {out_path}")


def main():
    rows = [stats_for_run(run) for run in RUNS]
    print_table(rows)

    out_path = ROOT / "reconstruction" / "comparison.png"
    save_visual_comparison(rows, out_path)


if __name__ == "__main__":
    main()
