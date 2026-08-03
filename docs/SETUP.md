# Setup

## Input data

- `video_capture/` — one `.mov`/`.mp4` of the table, walked around the mug,
  screwdriver, and water bottle.
- `image_capture/` — 100-300 `.jpg`/`.heic` photos of the same scene from
  different viewpoints.

Drop your files into these folders before running the scripts in `scripts/`.

## COLMAP (Windows, CPU build)

This machine has no dedicated NVIDIA GPU (Intel Iris Plus only), so use the
CPU-only COLMAP build — the CUDA build will not run.

1. From https://github.com/colmap/colmap/releases, download the **no-CUDA**
   Windows release asset (named e.g. `colmap-x64-windows-nocuda.zip`; exact
   naming varies by release — pick the one without `cuda` in the name).
2. Extract it somewhere stable, e.g. `C:\tools\COLMAP_extract`. The `bin\`
   subfolder contains `colmap.exe`.
3. Add `bin\` to your `PATH` (System Properties → Environment Variables), so
   `colmap.exe` is callable from a terminal.
4. Also set a `QT_PLUGIN_PATH` user environment variable pointing at the
   extracted `plugins\` folder (e.g. `C:\tools\COLMAP_extract\plugins`).
   Without it you'll hit `qt.qpa.plugin: Could not find the Qt platform
   plugin "windows"` — the official `COLMAP.bat` launcher sets this for you,
   but running `colmap.exe` directly from `bin\` on PATH does not.
5. Verify: open a **new** terminal (env var changes need a fresh session)
   and run `colmap -h`. You should see COLMAP's help text with no Qt error.

**Important limitation**: the no-CUDA build cannot run `patch_match_stereo`
(dense stereo) at all — it's not just slower on CPU, it refuses to run
(`Dense stereo reconstruction requires CUDA`). Sparse reconstruction
(`feature_extractor` → `exhaustive_matcher` → `mapper` → `image_undistorter`)
works fine on CPU — `scripts/run_colmap.py` stops right after
`image_undistorter`. For the dense step, use OpenMVS instead (below), which
runs dense reconstruction on CPU.

## OpenMVS (Windows, CPU dense reconstruction)

Since this machine has no CUDA GPU, COLMAP's own dense stereo can't run.
OpenMVS picks up from COLMAP's undistorted sparse model and does its own
dense point cloud + mesh reconstruction, and its CPU build actually works
(just slower than GPU).

1. From https://github.com/cdcseacave/openMVS/releases, download
   `OpenMVS_Windows_x64.zip` (the plain CPU build — not the `_CUDA.7z` one,
   this machine has no NVIDIA GPU).
2. Extract it, e.g. to `C:\tools\OpenMVS`. The executables end up nested at
   `OpenMVS\vc17\x64\Release\` (the `vc17` part may differ by release — check
   where `InterfaceCOLMAP.exe` actually landed).
3. No PATH changes needed — `scripts/run_openmvs.py` calls the binaries by
   full path. If you extracted somewhere other than
   `C:\tools\OpenMVS\vc17\x64\Release`, set an `OPENMVS_BIN` environment
   variable pointing at the folder containing the `.exe` files.
4. Verify: `& "C:\tools\OpenMVS\vc17\x64\Release\InterfaceCOLMAP.exe" -h`.
   OpenMVS tools don't print to the console — they write a log file (e.g.
   `InterfaceCOLMAP-<timestamp>.log`) in the working directory; open that to
   confirm you see the usage text and no errors.

**Expect this to be slow.** `DensifyPointCloud` (the dense stereo step) is
the bottleneck on CPU — for ~200 images at 1920x1080 this can take from
20 minutes to well over an hour, even at reduced `--resolution-level`. Run
`scripts/run_openmvs.py` directly in your own terminal and let it run to
completion rather than through anything with an execution time limit.

## Blender (Windows)

1. Download from https://www.blender.org/download/ (any recent stable
   release works).
2. Run the installer, accept defaults.
3. Add Blender's install directory (contains `blender.exe`) to `PATH` so
   `blender --background --python <script>.py` works from a terminal.
4. Verify: `blender --version`.

## Python dependencies

```
pip install opencv-python plyfile matplotlib
```

(`opencv-python` is already installed; `plyfile` loads OpenMVS's dense
`.ply` point clouds — trimesh's strict PLY parser rejects OpenMVS's
per-vertex `view_indices`/`view_weights` list properties — and `matplotlib`
renders the side-by-side comparison in `compare_reconstructions.py`.)
