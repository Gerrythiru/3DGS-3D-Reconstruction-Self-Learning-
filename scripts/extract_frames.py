"""Prepare COLMAP input images from video_capture/ and image_capture/.

- Samples evenly spaced frames from a video in video_capture/ into
  reconstruction/from_video/images/.
- Copies photos from image_capture/ as-is into
  reconstruction/from_images/images/.
"""

import argparse
import shutil
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parent.parent
VIDEO_DIR = ROOT / "video_capture"
IMAGE_DIR = ROOT / "image_capture"
VIDEO_OUT = ROOT / "reconstruction" / "from_video" / "images"
IMAGE_OUT = ROOT / "reconstruction" / "from_images" / "images"

VIDEO_EXTS = {".mov", ".mp4", ".m4v"}
IMAGE_EXTS = {".jpg", ".jpeg", ".heic", ".png"}


def find_video(video_dir: Path) -> Path:
    videos = [p for p in video_dir.iterdir() if p.suffix.lower() in VIDEO_EXTS]
    if not videos:
        raise FileNotFoundError(f"No video file found in {video_dir}")
    if len(videos) > 1:
        raise ValueError(f"Expected exactly one video in {video_dir}, found {len(videos)}")
    return videos[0]


def extract_frames(video_path: Path, out_dir: Path, target_frames: int) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(video_path))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total <= 0:
        raise RuntimeError(f"Could not read frame count from {video_path}")

    step = max(1, total // target_frames)
    written = 0
    frame_idx = 0
    while True:
        ok = cap.grab()
        if not ok:
            break
        if frame_idx % step == 0:
            ok, frame = cap.retrieve()
            if ok:
                cv2.imwrite(str(out_dir / f"frame_{written:05d}.jpg"), frame)
                written += 1
                if written >= target_frames:
                    break
        frame_idx += 1
    cap.release()
    return written


def copy_images(image_dir: Path, out_dir: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    images = [p for p in image_dir.iterdir() if p.suffix.lower() in IMAGE_EXTS]
    if not images:
        raise FileNotFoundError(f"No images found in {image_dir}")
    for p in images:
        shutil.copy2(p, out_dir / p.name)
    return len(images)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target-frames", type=int, default=200,
        help="Number of frames to sample from the video (default: 200)",
    )
    args = parser.parse_args()

    video_path = find_video(VIDEO_DIR)
    n_video = extract_frames(video_path, VIDEO_OUT, args.target_frames)
    print(f"Wrote {n_video} frames from {video_path.name} -> {VIDEO_OUT}")

    n_images = copy_images(IMAGE_DIR, IMAGE_OUT)
    print(f"Copied {n_images} images from {IMAGE_DIR} -> {IMAGE_OUT}")


if __name__ == "__main__":
    main()
