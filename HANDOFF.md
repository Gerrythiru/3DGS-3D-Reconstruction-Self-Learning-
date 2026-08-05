# HANDOFF

## Objective

Learning project to understand R2S2R (Real → Sim → Real): capture a real
scene, reconstruct it in 3D, bring it into MuJoCo, and eventually train a
robot policy in the reconstructed simulation before deploying back to
reality. Full seven-phase vision (capture → reconstruct → clean → import to
MuJoCo → spawn a robot arm → train RL → add perception) is documented in
`PLAN.md`.

This repo currently scopes only **Phase 1-3**: capture → COLMAP/OpenMVS
reconstruction → Blender cleanup, turning real footage into a clean
`scene.obj`. MuJoCo import, robot spawning, and RL training haven't been
started.

The original test scene (kitchen table with a mug, screwdriver, water
bottle) turned out, once captured, to actually be a full kitchen (island,
cabinets, fridge, stove, backsplash) — see "Learnings" below for why that
mattered.

## What's been built

Scripts (`scripts/`):
- `extract_frames.py` — samples ~200 frames from a video in `video_capture/`
  into `reconstruction/from_video/images/`; copies photos from
  `image_capture/` into `reconstruction/from_images/images/`.
- `run_colmap.py` — drives COLMAP CLI through sparse reconstruction and
  undistortion (`feature_extractor` → `exhaustive_matcher` → `mapper` →
  `model_converter` → `image_undistorter`). Stops there — see CUDA note
  below.
- `run_openmvs.py` — picks up from the undistorted COLMAP model and runs
  OpenMVS (`InterfaceCOLMAP` → `DensifyPointCloud` → `ReconstructMesh`) to
  produce a dense point cloud + mesh on CPU.
- `compare_reconstructions.py` — quantitative comparison (registered image
  count, sparse point count, mean reprojection error, dense point count) plus
  a side-by-side visual render, across the `from_video` vs `from_images`
  datasets.

Blender (`blender/`):
- `cleanup_scene.py` — imports a dense `.ply`, decimates if very dense,
  exports `scene.obj`. Manual cleanup (removing floating geometry/stray
  walls) is inherently a by-hand step in the Blender GUI, documented inline.

Docs:
- `docs/SETUP.md` — install steps for COLMAP (CPU/no-CUDA Windows build),
  OpenMVS (CPU Windows build), Blender, and Python deps, plus the
  machine-specific gotchas discovered along the way (below).

Both datasets exist under `reconstruction/<run>/` (git-ignored, local only):
`from_video` (from one iPhone walk-around video) and `from_images` (from 93
iPhone photos).

## Current state

- **`from_video`**: fully run end-to-end through OpenMVS. 200/200 images
  registered, 65,365 sparse points, 0.79px mean reprojection error,
  1,212,647 dense points, mesh reconstructed (`scene_dense_mesh.ply`,
  626,585 vertices / 1,252,944 faces). Visual inspection (see Learnings)
  shows recognizable major shapes but poor accuracy and holes, because the
  captured scene is a full kitchen, not the small tabletop object cluster
  the plan assumed.
- **`from_images`**: only step 1 done (93 photos copied into
  `reconstruction/from_images/images/`). Steps 2 (COLMAP sparse +
  undistort) and 3 (OpenMVS dense) have not been run yet.
- **Blender cleanup**: not yet done on either run.
- **Next planned capture**: a much simpler scene — a water bottle on a
  stool — using lessons learned below (see "Learnings" and the
  video-vs-photos discussion). Not yet shot.
- Repo pushed to GitHub: https://github.com/Gerrythiru/3DGS-3D-Reconstruction-Self-Learning-
  (public). Only code/docs are tracked — raw captures and reconstruction
  outputs are git-ignored (see "Repo scope" below).

## Issues hit and what we learned

**1. No local GPU — COLMAP's dense stereo doesn't run at all on CPU.**
This machine has only an Intel Iris Plus (integrated) GPU, confirmed by
checking `Win32_VideoController` — no NVIDIA adapter, no `nvcuda.dll`, no
CUDA install folder anywhere. COLMAP's no-CUDA Windows build errors
outright on `patch_match_stereo` (`Dense stereo reconstruction requires
CUDA`) — it's not just slower on CPU, it flatly refuses to run. Installing
the CUDA toolkit wouldn't help either: CUDA requires actual NVIDIA silicon,
which this machine doesn't have. **Learning**: check GPU vendor before
assuming "install CUDA" is ever an option; it's a hardware constraint, not a
software gap.

**2. Colab GPU route was explored, then abandoned.** Wrote a notebook
(`colab/colmap_dense_gpu.ipynb`, since deleted) to finish COLMAP's dense
stereo on a free Colab T4 GPU. Never verified end-to-end (no execution
channel into Colab from this environment), and the user ultimately decided
against depending on it. **Learning**: don't hand off unverified automation
for a critical path step if there's a way to test it locally instead.

**3. OpenMVS chosen as the CPU-capable alternative — but with a real
quality cost, not just a speed cost.** OpenMVS's `DensifyPointCloud` +
`ReconstructMesh` do run on CPU (verified locally), but:
   - It's genuinely slow: ~1 hour for 200 images at 1920x1080 on this
     4-core/8-thread i7-1065G7. Background tool sessions used during
     development repeatedly got killed before a run could finish
     (confirmed via `.dmap` count and log timestamps that this was a
     wall-clock/session limit, not a hang or bad data) — full runs need to
     be started directly in the user's own terminal, not through a
     sandboxed/backgrounded call with a duration cap.
   - `InterfaceCOLMAP` requires COLMAP's **undistorted** (PINHOLE) model,
     not the raw sparse output — i.e. `colmap image_undistorter` must run
     first. This step doesn't need CUDA, so it slots in naturally where
     COLMAP's own CPU-only capability stops.

**4. Command-line gotchas discovered the hard way (now documented in
`docs/SETUP.md` and fixed in the scripts):**
   - COLMAP: running `colmap.exe` directly from `bin\` (added to PATH)
     rather than via the bundled `COLMAP.bat` launcher breaks Qt plugin
     loading (`qt.qpa.plugin: Could not find the Qt platform plugin
     "windows"`). Fix: also set a `QT_PLUGIN_PATH` env var pointing at the
     extracted `plugins\` folder.
   - OpenMVS tools print **nothing** to stdout/stderr — they log to a
     `<Tool>-<timestamp>.log` file in the working directory instead. Exit
     code 1 with zero console output is normal for `--help`, not a crash —
     always check the log file.
   - Passing `-w <folder>` (working-folder) *together with* an absolute
     path for `-i`/`-o` doubles the path (e.g.
     `dense/dense/sparse/cameras.bin`) and the tool fails to find its
     input. Fix: don't pass `-w` when `-i`/`-o` are already absolute.
     Omitting `-w` means OpenMVS defaults the working folder to the
     current directory — which is also *why* running the manual commands
     from the project root scattered ~2GB of `depth*.dmap` cache files and
     log files at the repo root instead of inside `reconstruction/.../dense/`
     (cleaned up; now `.gitignore`'d as a pattern too).

**5. OpenMVS's dense-cloud PLY format broke `trimesh`.** OpenMVS's
`DensifyPointCloud` output has per-vertex list properties (`view_indices`,
`view_weights`) that `trimesh`'s strict PLY parser rejects (`PLY is
unexpected length!`) — this would have silently broken
`compare_reconstructions.py` the first time someone actually ran it against
real OpenMVS output. Fixed by switching that script to `plyfile`, which
handles per-vertex list properties correctly. Verified against the real
`from_video` dense cloud (1,212,647 points) afterward. **Learning**: test
scripts against real pipeline output, not just that they import cleanly —
this bug wouldn't have shown up any other way.

**6. Reconstruction quality was poor — but for a legible, non-mysterious
reason.** Rendered the `from_video` dense point cloud from three angles and
compared against a real photo of the actual space. The scene is a full
kitchen (island, cabinets, stainless fridge/stove, tiled backsplash, guitar
on a far wall) rather than the small tabletop object cluster the original
plan assumed. Visible problems and their causes:
   - **Ghosting/doubled edges** on cabinet fronts and countertop edges —
     camera pose drift accumulating around a large loop.
   - **Holes concentrated on large flat low-texture surfaces** (white
     cabinet doors, ceiling, plain countertop) — COLMAP/OpenMVS need
     distinctive visual features to match between frames; blank painted
     surfaces give them almost nothing.
   - **Reflective/specular surfaces** (stainless steel appliances, tiled
     backsplash) actively break feature matching, since the same point
     looks different from different viewing angles.
   - Notably, the *sparse* stats looked great in isolation (200/200 images
     registered, 0.79px mean reprojection error) — those numbers alone
     didn't predict the poor dense/visual result. **Learning**: sparse
     registration quality and dense reconstruction quality are not the same
     thing; low reprojection error just means the recovered camera poses
     are self-consistent, not that the scene had enough texture for dense
     coverage.

**7. Planning the next (simpler) capture.** Decided to recapture a much
smaller, simpler scene — a water bottle on a stool — to isolate the
pipeline from scene-complexity confounds. Key decisions and reasoning:
   - **Photos over video** was the initial recommendation for a small
     object (higher native resolution, no motion blur, per-shot focus
     control) — but the user opted to stick with **video only**, reasoning
     that `extract_frames.py` already reliably guarantees ~200 well-overlapped
     frames and the tooling is proven. Reasonable tradeoff, with caveats
     given: use the standard (not 0.5x ultra-wide) lens, shoot at the
     highest resolution available, move slowly especially when transitioning
     between height rings (to avoid motion blur), and increase
     `--target-frames` (e.g. to 300) since a multi-ring single take is a
     longer/more complex path than the flat kitchen loop.
   - Multiple height rings (low/eye-level/high), not a single flat loop, to
     get full coverage of a small object.
   - A **textured surface** under the object (patterned cloth, etc.) to
     avoid the same low-texture problem seen in the kitchen capture.
   - Flagged that if the water bottle itself is clear/reflective, that's a
     hard physical limitation for photogrammetry (transparent/reflective
     objects break the multi-view-consistency assumption) — not something
     technique can fully fix.
   - **Not yet shot or captured.**

## Repo scope (what's tracked vs. not)

The GitHub repo is public, so raw personal photos/video and large
intermediate binaries are deliberately excluded via `.gitignore`:
`video_capture/`, `image_capture/`, `raw data/`, and `reconstruction/`
(which holds `database.db`, per-frame `.dmap` files, dense `.ply` clouds,
etc. — several individual files exceed GitHub's 100MB hard limit anyway).
Only `scripts/`, `blender/`, `docs/`, and the root markdown files are
tracked. This means the actual capture data and reconstruction outputs
referenced above exist locally only, not in the pushed repo.

## Immediate next steps

1. Run step 2 (COLMAP sparse + undistort) and step 3 (OpenMVS dense) on
   `from_images`, then run `compare_reconstructions.py` for a real
   video-vs-photos comparison (on the kitchen data, for what it's worth).
2. Do the Blender cleanup pass on `from_video`'s `scene_dense_mesh.ply` (or
   `scene_dense.ply`) to produce a first `scene.obj`.
3. Shoot the water-bottle-on-a-stool capture using the lessons above, then
   run the same pipeline on it as a cleaner, higher-quality test case.
4. Only after a genuinely clean `scene.obj` exists: start Phase 4 (MuJoCo
   import).
