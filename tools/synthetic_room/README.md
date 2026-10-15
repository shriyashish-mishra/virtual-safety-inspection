# Synthetic staged-room clips (ILLUSTRATIVE)

Generates three test clips of a furnished room, filmed by a simulated hand-held phone, with the true answers known exactly. Use them to run the pipeline (marker detection, reconstruction, rules, checker, viewer) before real footage exists. **They are not real footage and not T2 ground truth.** Real clips and tape measurements are still Nadeem's T2.

## Run

    python3 -m venv ~/.venvs/virtual-safety
    ~/.venvs/virtual-safety/bin/pip install -r tools/synthetic_room/requirements.txt
    ~/.venvs/virtual-safety/bin/python tools/synthetic_room/render.py --out ~/virtual-safety-synth
    ~/.venvs/virtual-safety/bin/python tools/synthetic_room/verify.py --out ~/virtual-safety-synth

About 15 to 20 minutes for the three clips (they render in parallel). Output stays outside git: clips are large (keep large files out of git). Share them by link.

## What you get per clip (`clip1_clear`, `clip2_blocked`, `clip3_unseen`)

| File | What it is |
| --- | --- |
| `<clip>.mp4` | 1280x720, 30 fps, 18 to 21 s, lens distortion, hand shake, motion blur, auto exposure, noise, compression |
| `capture.json` | Valid against schema/capture.schema.json (marker id 0, 0.15 m) |
| `geometry_truth.json` | The true geometry in schema v0.1 form: camera poses every 5th frame, marker poses, door and exit openings |
| `points_truth.json` | Floor cells the camera actually saw, plus obstacle surfaces. No walls, so the exit rule has something to read |
| `scene_truth.json` | Camera intrinsics and distortion, true door width, exit clearance, expected verdict, marker layout |
| `check.json` | Written by verify.py: marker detection rate and scale error |

`ground_truth.json` (all three clips, in the layout of samples/t2/ground_truth.template.json) is written next to the clip folders when you render `--clip all`.

## The room (metres, floor is z = 0)

4.6 x 3.6 x 2.6. Exit door in the y = 0 wall, clear width 0.86 between x = 3.27 and 4.13. Markers (OpenCV `DICT_4X4_50`, black square 0.15 m):

| Id | Role | Where |
| --- | --- | --- |
| 0 | scale | wall left of the door, upper |
| 1 | exit | on the door leaf |
| 2 | left door edge | wall beside the architrave |
| 3 | right door edge | wall beside the architrave |
| 4 | floor (only in `clip1_floormarker`) | lying flat at x 2.90, y 0.50, printed face up |

| Clip | Setup | Truth |
| --- | --- | --- |
| clip1_clear | Nothing in front of the exit; a side table 2.2 m away, in line with it | clearance 2.2 m, pass |
| clip2_blocked | Cardboard box 0.70 m from the door | clearance 0.70 m, fail |
| clip3_unseen | Same room as clip 1, but the camera never films the floor corridor in front of the exit | not_proven |

Three extra clips test the floor-marker proposal (docs/decisions.md). They are not part of `--clip all`: render each with `--clip <name>`, and they do not appear in `ground_truth.json`. The first three clips are unchanged.

| Clip | Same room and truth as | Marker 4 (lying flat, printed face up) | In view |
| --- | --- | --- | --- |
| `clip1_floormarker` | clip1_clear (pass) | x 2.90, y 0.50 | 16.5 to 19.5 s, 70 to 80 px wide |
| `clip2_floormarker` | clip2_blocked (fail, box at 0.70 m) | x 2.90, y 0.50 | 16.5 to 19.5 s |
| `clip3_floormarker` | clip3_unseen (not_proven) | x 3.00, y 3.00, at the back of the room | 17.7 to 20.0 s; the phone turns west at level gaze before tilting, so none of the corridor floor is ever filmed (renderer count: 0 corridor pixels) |

The unseen corridor is x 3.10 to 4.30, y 0 to 1.5 (a placeholder, D8 sets the real size). The renderer counts floor pixels inside it: clips 1 and 2 see it, clip 3 sees none.

## Conventions and limits

- Camera pose: camera-to-world, OpenCV axes (x right, y down, z forward). Marker pose: marker-to-world, +z out of the printed face.
- UNVERIFIED: the dictionary and marker ids (D7, D11 are Kaushal's call); where door-edge markers sit (beside the architrave, offset recorded in `scene_truth.json`); whether VGGT or Depth Anything 3 reconstruct these clips as well as real ones.
- A ray-cast render, not a photograph: soft textures, simplified furniture, no reflections. A model that works here may still fail on real footage.
- `points_truth.json` leaves out the extra clutter (desk, shelf, bag, bin), because none of it is in the exit corridor.
