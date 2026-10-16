# Spike report (T5)

**Status (14 Oct): T5 is done for the prototype only.** By the 14 Oct scope decision in docs/decisions.md, Shriyashish Mishra's synthetic clips stand in for the real ones until the prototype works; the real-clip rerun (T2) comes after. Every number below is from a synthetic render, measured against `scene_truth.json`, not a tape. No tolerance is chosen (D8).

**Recommendation (one line, INFERENCE from one synthetic clip): use VGGT for the prototype.** It took 32 frames in 12.2 s with 8.77 GB where Depth Anything 3 only fit 8 frames (13.55 GB), and the door-marker error was about the same (+3.92% against +4.21%). Repeat the comparison on the real clip before relying on it.

## Dry run on the synthetic clip (13 Oct 2026)

Clip `clip1_clear.mp4` from Shriyashish Mishra's synthetic set, scale marker id 0 at 0.15 m (D7). Run on a free Kaggle notebook, 2x Tesla T4 (14.5 GiB each), by `reconstruct/spike.py` (SHA-256 `ef30f4ce...c959a`). Ground truth is the synthetic `geometry_truth.json`, not a tape.

| | VGGT (`facebook/VGGT-1B`) | Depth Anything 3 (`DA3NESTED-GIANT-LARGE`) |
| --- | --- | --- |
| Frames used | 32 | 8 (32 and 12 ran out of memory) |
| Inference time | 12.2 s | 12.06 s |
| Peak GPU memory | 8.77 GB | 13.55 GB |
| Door-marker distance error (markers 2 and 3, true 1.215 m) | +3.92% | +4.21% (1.2661 m) |
| Other markers' implied size (true 0.15 m) | not recorded | id 1 0.1475, id 2 0.1483, id 3 0.1465 m |

VERIFIED: both models ran end to end on a T4 and the scale method produced a number for each. The DA3 values are read from the saved run log; the VGGT values are from the earlier run (log not kept in git).

## What this does not show
- The frame counts differ (32 vs 8), so the two columns are not a fair comparison. DA3 at 8 frames saw each door marker in only 2 to 3 frames.
- One synthetic clip, one run each. The 3.92% and 4.21% errors are measurements, not tolerances, and say nothing about a real phone clip.
- Run time excludes model download and load.
- INFERENCE: on this clip VGGT copes with more frames in less memory. Not enough to pick a model; the real clip decides (T21 scale gate).

## T6 dry run: marker scale on all three synthetic clips (14 Oct 2026)

**Still not T6 evidence.** The card needs the three real clips and the D8 tolerance; neither exists. This shows that `reconstruct/marker_scale.py` runs on real model output for all three clips.

VGGT, 32 frames per clip, Kaggle T4, `reconstruct/marker_scale.py` from `main` (2481e01). Scale marker id 0 at 0.15 m (D7). Door width = distance between door-edge marker centres (ids 2 and 3) minus 2 x 0.177 m. **The 0.177 m is the synthetic room's value, a placeholder** until Nadeem sets the marker placement rule for the real room. True width 0.86 m from `scene_truth.json`, not a tape measurement.

| Clip | Scale (m per model unit) | Implied size of markers 1, 2, 3 (true 0.15 m) | Door width estimated | Error |
| --- | --- | --- | --- | --- |
| clip1_clear | 2.524 | 0.1499, 0.1498, 0.1472 | 0.9086 m | +0.049 m (+5.65%) |
| clip2_blocked | 2.438 | 0.1500, 0.1504, 0.1474 | 0.9107 m | +0.051 m (+5.89%) |
| clip3_unseen | 2.731 | 0.1477, 0.1494, 0.1455 | 0.9200 m | +0.060 m (+6.98%) |

Per clip: 11 to 13 s inference, 8.8 GB peak GPU memory. Each marker was seen in 8 to 14 of the 32 frames.

What this shows and does not show:
- VERIFIED: the module ran end to end on all three clips and produced a scale and a door width each time.
- All three door widths come out too wide by 5 to 7 cm. The sign never changes, which looks like a bias, not noise. INFERENCE: not investigated; the cause could be the depth at the marker corners, the single global scale factor, or the placeholder offset.
- The error in metres is almost the same as the centre-to-centre error (clip1: 0.0476 m against 1.215 m true), so a different offset would shift every number by the same amount.
- The three clips are one room with the same marker layout, so this is closer to one test than three. They are synthetic renders, and a model that works here may still fail on real footage.
- No tolerance is chosen here (D8). Whether 5 to 7 cm is acceptable for a 0.86 m door is the team's call after the real clips.
- The model frame is not yet aligned to +z up, floor at z = 0 (T7).

## T7 run script on the three synthetic clips (14 Oct 2026)

`python3 reconstruct/run.py CLIP_DIR OUT_DIR` (VGGT, 32 frames) ran on all three clips on a Kaggle T4: exit 0 each time, `geometry.json` valid against the schema, `points.json` of about 20,000 points, `run_log.json` written. Model time 11 to 12 s, 8.77 GB peak GPU memory, 33 to 74 s per clip in total (the first includes the model download). Cost: no money, free notebook quota. Compared with `geometry_truth.json`, which is a synthetic render and not a tape:

| Check | clip1_clear | clip2_blocked | clip3_unseen |
| --- | --- | --- | --- |
| Door width (true 0.86 m) | 0.908 m | 0.910 m | 0.921 m |
| Exit point from the door midpoint (true 0) | 0.03 m | 0.03 m | 0.01 m |
| Exit marker normal against the door line (true 90 deg) | 89.8 | 89.9 | 88.2 |
| Marker heights against truth | within 0.04 m | 0.12 to 0.16 m too low | 0.52 to 0.54 m too low |
| Camera height, mean absolute error | 0.24 m | 0.39 m | 0.51 m |

What this shows and does not show:
- VERIFIED: the one command works end to end on all three clips and its output is schema-valid. The door and exit openings land on the floor plane (z = 0), the exit marker faces into the room at the right angle to the door, and the door width has the same 5 to 7 cm bias as in the T6 section.
- **Not working: the floor height.** On clip1 it is right (markers within 4 cm); on clip2 everything sits 12 to 16 cm too low and on clip3 about 52 cm too low. The shift is the same for every marker in a clip, so it comes from the floor estimate (2nd percentile of the point heights), not from tilt. Cause not found; clip3 is the clip where the corridor floor is never filmed, which fits but is not shown. Rules that use height above the floor (floor band, obstacle height) would misjudge clips 2 and 3 until this is fixed.
- **Floor height, diagnosed (14 Oct, rerun with the height log; VERIFIED on these three synthetic clips, INFERENCE beyond them).** Tilt is not the cause: a plane fitted to the points near the true floor is within 0.8 degrees of level on every clip. The cause is that the point heights have no floor peak, so a low percentile just picks the lowest 2% of points, whatever they are. Points sit well below the true floor (clip2 down to about 0.4 m below it, clip3 about 0.9 m below), and exactly 1540 voxels fall below the chosen floor in all three clips, which is what a percentile cut gives. Tried by eye on the voxel cloud: a lowest-dense-bin rule is off by 0.07, 0.11 and -0.33 m on the three clips, so no percentile or density rule is justified from three clips and none was added. Options for the team: (a) a marker lying on the floor, so floor z is that marker's centre (a placement rule, which is Nadeem's to set with the door-edge rule; not tested because no synthetic clip has one); (b) a plane fit on a floor region marked by hand. Until one is chosen, height above the floor is unreliable and `floor_height_model_m` in run_log.json should not be trusted.
- **Floor marker tried (14 Oct, `clip1_floormarker`, VGGT, 32 frames, one run; VERIFIED for this clip only).** `run.py` took the floor from marker 4 (`floor_source: marker_4`) and the floor marker itself landed at z = 0.0 (true 0.004). The four wall markers then came out 0.12 to 0.15 m too high (0.133, 0.142, 0.122, 0.151 m; true heights 1.35, 1.30, 1.00, 1.00 m), against 0.002 to 0.04 m too high on the original clip1 with the percentile rule. Door width 0.898 m (true 0.86). So on this clip the floor marker does not beat the percentile rule: it pins the floor, but the model's height between the floor marker and the wall markers is off by 12 to 15 cm. Cause not found. INFERENCE, untested: the floor marker is seen at a shallow angle for about 3 s, so its depth, or a small tilt of the up direction over the 2 to 3 m between the markers (3 degrees is about 13 cm), could produce this. The x and y errors in the run are meaningless (the model's frame has an arbitrary origin and heading); only z is compared. No tolerance is picked here (D8).
- **Floor marker normal as up (14 Oct, same clip, rerun; VERIFIED for this clip only).** In the first floor-marker run the marker's normal was 11.2 degrees off vertical and the wall-marker normals had a vertical part of about -0.2, so the camera-axes "up" was off by about 11 degrees. `run.py` now takes up from marker 4's normal when it is seen (`up_source: marker_4_normal`, `up_change_from_camera_axes_deg: 11.21`). Result: wall markers 0.053, 0.042, 0.034 and 0.022 m too high (was 0.12 to 0.15), floor marker at z = 0.0, wall-marker normals vertical part -0.013 to -0.002 (horizontal to within a degree), door width unchanged at 0.898 m. This matched the prediction from recomputing the saved poses. What remains: 2 to 5 cm too high on one clip, with a floor marker seen for about 3 s; no tolerance is picked (D8). Not shown: whether it holds on real footage or on other synthetic rooms; the marker-4 rule is still PROPOSED and unsigned by Nadeem.
- "Clean checkout" was approximated: the five files were uploaded as a Kaggle dataset, not cloned.
- Same caveats as before: synthetic renders, one room, one run each, no tolerance chosen (D8).

## Deferred until the real clip exists (T2)
1. Nadeem's real `clip1_clear.mp4`, `capture.json` and tape-measured door width (T2).
2. Rerun both models on it with the same frame count where memory allows.
3. Compare the error against the tape, then propose D8 from the result.

Install recipe and Kaggle quirks: docs/install-notes.md.
