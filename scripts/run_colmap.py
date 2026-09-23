"""Run the COLMAP sparse pipeline + undistortion on one of the prepared datasets.

Requires `colmap` on PATH (see docs/SETUP.md). Runs the same pipeline for
either dataset so the two runs are directly comparable:

    feature_extractor -> exhaustive_matcher -> mapper (sparse)
    -> model_converter (TXT export, for compare_reconstructions.py)
    -> image_undistorter (PINHOLE model, ready for OpenMVS)

Stops after undistortion: COLMAP's own dense stereo (patch_match_stereo /
stereo_fusion) requires CUDA, which this machine doesn't have. Run
scripts/run_openmvs.py next to finish dense reconstruction on CPU.
"""

import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(cmd: list[str]):
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", choices=["from_video", "from_images"], required=True)
    args = parser.parse_args()

    workspace = ROOT / "reconstruction" / args.run
    images = workspace / "images"
    database = workspace / "database.db"
    sparse = workspace / "sparse"
    sparse_model = sparse / "0"
    dense = workspace / "dense"

    if not images.exists() or not any(images.iterdir()):
        raise FileNotFoundError(
            f"No images in {images}. Run scripts/extract_frames.py first."
        )

    sparse.mkdir(parents=True, exist_ok=True)

    run(["colmap", "feature_extractor",
         "--database_path", str(database),
         "--image_path", str(images)])

    # use_gpu=0 forces CPU-only matching. The OpenGL SiftGPU matcher (used
    # on this machine's Intel iGPU, no CUDA available) has a hardcoded
    # 16384 max-matches limit that isn't exposed through any tunable flag
    # (confirmed: neither --SiftExtraction.max_num_features nor
    # --FeatureMatching.max_num_matches change it) -- it crashed outright
    # (STATUS_ACCESS_VIOLATION) at both 500 and 300 frames, so frame count
    # wasn't the actual driver. CPU matching sidesteps the OpenGL backend
    # entirely; slower, but avoids the crash mechanism rather than
    # gambling on reducing the odds of hitting it.
    run(["colmap", "exhaustive_matcher",
         "--database_path", str(database),
         "--FeatureMatching.use_gpu", "0"])

    run(["colmap", "mapper",
         "--database_path", str(database),
         "--image_path", str(images),
         "--output_path", str(sparse)])

    # Text export for compare_reconstructions.py to parse.
    run(["colmap", "model_converter",
         "--input_path", str(sparse_model),
         "--output_path", str(sparse_model),
         "--output_type", "TXT"])

    run(["colmap", "image_undistorter",
         "--image_path", str(images),
         "--input_path", str(sparse_model),
         "--output_path", str(dense),
         "--output_type", "COLMAP"])

    print(f"\nDone. Undistorted model ready at {dense}.")
    print("Next: python scripts/run_openmvs.py --run " + args.run)


if __name__ == "__main__":
    main()
