# Rules v0 on the synthetic clips (T8 to T11)

ILLUSTRATIVE. Run 14 Oct 2026 by Kaushal with `python3 rules/test_rules.py` (exit 0). Rules written from docs/rules-spec.md only (D10), parameters are the PLACEHOLDERS in samples/handmade/placeholders.json until D8, and the clips are renders (samples/t2/synthetic/), not real captures.

Command: `python3 rules/run.py GEOMETRY.json OUT_DIR [--params FILE]`, then `python3 schema/validate.py evidence OUT_DIR/evidence.json` and `python3 checker/check.py GEOMETRY OUT_DIR/evidence.json --params samples/handmade/placeholders.json`.

## On the scene-truth geometry (what the test checks)
| clip | exit claim | value | door width | confidence (exit) | schema | checker |
| --- | --- | --- | --- | --- | --- | --- |
| clip1_clear | pass | 1.0 m (clear for at least the required distance) | 0.86 m | 1.0 (v0.1 params; 0.70 with the seen fraction) | ok | PASS |
| clip2_blocked | fail | 0.70 m (matches the scene truth) | 0.86 m | 1.0 (v0.1 params) | ok | PASS |
| clip3_unseen | not_proven | null, requested view names exit_1 | 0.86 m | 0 | ok | PASS |

Adding the missing view (clip 3's geometry plus the floor points clip 1 saw) turns clip 3's exit claim from not_proven into pass. The hand-made pair gives exit_1 fail 0.6, door 0.9, exit_2 not_proven, as hand-computed in samples/handmade/README.md.

## On the reconstructed geometry (run.py output of 14 Oct, VGGT; local check, the files are not in git)
Spec v0.1 gave `fail` at about 0.004 m on all three clips: 424, 735 and 474 door-leaf and wall points sit at distance s of about 0 inside the height band, and clip 3 (corridor never filmed) still had 52 floor points. Fix: spec v0.2 (docs/rules-spec.md section 4, PROPOSED): a margin around the exit plane, a seen fraction instead of a bare point count, and obstacles tested first. Run with `samples/handmade/placeholders_v02.json`:

| clip | v0.1 exit | v0.2 exit | wanted | v0.2 value vs scene truth | floor seen in corridor | door width |
| --- | --- | --- | --- | --- | --- | --- |
| clip1_clear | fail 0.004 m | pass 1.0 m | pass | n/a (clear) | 0.52 | 0.908 m |
| clip2_blocked | fail 0.0004 m | fail 0.204 m | fail | 0.204 m vs 0.70 m | 0.16 | 0.910 m |
| clip3_unseen | fail 0.005 m | not_proven | not_proven | n/a | 0.09 | 0.921 m |
| clip1_floormarker | not run | pass 1.0 m | pass | n/a (clear) | 1.00 | 0.898 m |

- All four verdicts are now the wanted ones. VERIFIED for these four reconstructions only; the margin (0.15 m) and seen fraction (0.3) are PLACEHOLDERS picked from these same clips, so this is a fit, not a test.
- The clip 2 value is wrong: stray points between 0.2 and 0.6 m (about 15 of them, noise around the box) set the nearest distance at 0.204 m, the box face is at about 0.6 m in the reconstruction (0.70 m true). The verdict does not change, the number the viewer shows does. Not fixed; a robust nearest distance (for example needing several points in a slice) is a spec choice for Nadeem.
- The checker does not implement v0.2, so on these reconstructed files it says FAIL (it recomputes the v0.1 rule). That is the expected disagreement until Shriya updates it from the spec (D10: the rules author does not write the checker). On the truth geometry and the hand-made pair, where both versions agree, it says PASS.
- Clips 2 and 3 were reconstructed with the old percentile floor (0.14 and 0.52 m off). No floor-marker versions of them exist, so the rules were not run with a correct floor on those two.

## With the floor marker, and spec v0.3 (15 Oct; Kaggle run of the three floor-marker clips, VGGT, 32 frames; files local, not in git)
All three runs used marker 4 for the floor and for "up" (`floor_source: marker_4`, up moved by 11.1 to 11.2 degrees). Wall-marker heights against truth: clip1 0.02 to 0.05 m too high, clip2 0.05 to 0.07 m, clip3 0.11 to 0.23 m (the marker was seen for only about 2 s at the back of the room). Door widths 0.898, 0.892, 0.919 m (true 0.86).

Spec v0.2 gave the right verdict on clips 1 and 2 but a false `fail` at 0.19 m on clip 3 (corridor never filmed, 0 floor points) because 5 stray points sat past the 0.15 m margin, and a clearance of 0.156 m on clip 2 (stray points; the box face is at about 0.65 m). Spec v0.3 (PROPOSED, docs/rules-spec.md section 4 step 2) drops points in corridor slices holding fewer than `MIN_OBSTACLE_SLICE_POINTS` (12) points per `OBSTACLE_SLICE_M` (0.05 m): the box face is slices of 17 or more, the noise 9 or fewer.

| reconstruction | v0.3 exit | wanted | value vs scene truth |
| --- | --- | --- | --- |
| clip1_floormarker | pass 1.0 m | pass | n/a |
| clip2_floormarker | fail 0.651 m | fail | 0.651 vs 0.70 m |
| clip3_floormarker | not_proven | not_proven | n/a |
| clip1_clear (percentile floor) | pass 1.0 m | pass | n/a |
| clip2_blocked (percentile floor) | fail 0.608 m | fail | 0.608 vs 0.70 m |
| clip3_unseen (percentile floor) | not_proven | not_proven | n/a |
| the three scene-truth geometries | pass, fail 0.70, not_proven | same | checker PASS on all three |

- VERIFIED for these seven reconstructions of one synthetic room. The slice size (0.05 m) and count (12) are PLACEHOLDERS picked from these same clips: a fit, not a test.
- The checker still follows v0.2, so it says FAIL on the clip 2 and clip 3 floor-marker reconstructions and on the old clip 2 (it recomputes the noise as an obstacle). It says PASS everywhere v0.2 and v0.3 agree. Shriya has to update it from the spec (D10: the rules author does not write the checker).
- Not shown: real footage; other rooms; a floor marker seen for longer or shorter; clips 2 and 3 with the floor off (the percentile-floor versions still pass, but their floors were 0.14 and 0.52 m wrong, so their agreement is partly luck).

## Placeholders added by these rules (none changes a verdict)
- `VIEW_HALF_ANGLE_DEG = 30` in rules/common.py: a frame is linked to a claim when the claim's markers are within this angle of the camera axis. Geometry carries no camera field of view, so a real value needs intrinsics in the schema. If no frame qualifies the single best frame is linked, so a pass or fail always has a link.
- `GRID_M = 0.1`: cell size for `coverage.seen_fraction`.
- Spec v0.2 parameters `EXIT_PLANE_MARGIN_M` 0.15, `MIN_CORRIDOR_SEEN_FRACTION` 0.3, `CORRIDOR_CELL_M` 0.1 in samples/handmade/placeholders_v02.json (the default for rules/run.py); samples/handmade/placeholders.json is unchanged and still drives the checker.
- Confidence: exit pass or fail = fraction of the corridor squares that hold a floor point (1.0 when the spec v0.2 parameters are blank); door = 1.0 when both edge markers are located; not_proven = 0 (spec section 6). A heuristic, not a calibrated probability.

## Not shown
Any result on real footage; whether VIEW_HALF_ANGLE_DEG finds the frames a person would pick; any value for the D8 parameters.

## Task check, 15 Oct: is each rules task done? (Kaushal)
Done-when read from the internal task cards, results from the sections above. Prototype scope applies (synthetic clips stand in for real ones; docs/decisions.md).

### T8 blocked exit: NOT done
Done when: verdict matches the ground truth on all 3 clips and the checker agrees. The verdicts match the scene truth on all six reconstructions and on the three truth geometries. The checker agrees on the truth geometries, and on the reconstructed ones only where spec v0.2 and v0.3 give the same result: it still follows v0.2, so it says FAIL on the clip 2 and clip 3 floor-marker reconstructions and on the old clip 2. Needs Shriya to update the checker to spec v0.3 (D10: I do not write it) and Nadeem to accept or change v0.3. Also Needs T1 (schema approvals pending) and T2 (real clips, replaced by the synthetic ones under the prototype scope).

### T9 door clear width: done for the prototype
Done when: value is within the D8 tolerance of the tape on all 3 clips. The "tape" is the scene truth, 0.86 m. D8 door-width tolerance is 0.10 m, signed by Kaushal only (15 Oct; Nadeem and Shriya pending). Door width in the geometry that `run.py` made, from the rules' value (the rule only measures the distance between the door edge points):

| reconstruction | door width | error vs 0.86 m |
| --- | --- | --- |
| clip1_clear | 0.908 m | +0.048 |
| clip2_blocked | 0.910 m | +0.050 |
| clip3_unseen | 0.921 m | +0.061 |
| clip1_floormarker | 0.898 m | +0.038 |
| clip2_floormarker | 0.892 m | +0.032 |
| clip3_floormarker | 0.919 m | +0.059 |

All six are within 0.10 m (worst +0.061). The scene-truth geometries give 0.86 m exactly. Caveats: the 0.177 m door-edge offset in `run.py` is a placeholder, so the width depends on it (a real room needs a tape-measured offset); the errors are all too wide; D8 is one signature of three; one synthetic room.

### T10 coverage and view request: done-when met, approach is points-based
Done when: the unseen-area clip returns not_proven and a request; adding the clip turns it into a verdict; nothing outside coverage gets pass or fail. Results:
- clip3_unseen and clip3_floormarker: `not_proven`, `value` null, `frame_ids` empty, and a requested view: "film the floor in front of exit_1: the strip from the exit out to 1.0 m, 1.0 m wide, fully in view". `coverage.unseen_regions` names exit_1_clear with the reason, and `seen_fraction` is 0.052 and 0.291.
- Adding the missing view turns it into a verdict: clip 3's geometry plus the floor points clip 1 saw gives `pass` (rules/test_rules.py; valid only on the scene-truth geometries, which share one world frame; reconstructions each have their own arbitrary frame, so their point clouds cannot be merged).
- Nothing outside coverage gets pass or fail: the exit claim needs the corridor floor seen (spec section 4, steps 4 and 5), the door claim needs both edge markers.
Not as the card words it: "from camera poses". The unseen test counts floor points in the corridor; camera poses are used only to link frames to a claim (a placeholder 30 degree view angle). Real visibility from poses and intrinsics is not implemented, and the geometry carries no camera field of view.
