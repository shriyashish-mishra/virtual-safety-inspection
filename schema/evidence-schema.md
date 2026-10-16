# Schema v0.1 (DRAFT until all three approve)

The frozen contract between lanes (T1). It turns the table in docs/interfaces.md into typed JSON Schema files. Once approved, no field changes without a version bump that all three approve in writing.

| File | Schema | Written by | Read by |
| --- | --- | --- | --- |
| capture.json | [capture.schema.json](capture.schema.json) | Whoever films (Nadeem, T2); format owned by Shriyashish Mishra | Kaushal |
| geometry.json | [geometry.schema.json](geometry.schema.json) | Kaushal | Nadeem, checker |
| evidence.json | [evidence.schema.json](evidence.schema.json) | Nadeem | Viewer, checker |
| checker_report.json | [checker_report.schema.json](checker_report.schema.json) | Checker (Shriyashish Mishra, T34) | Viewer, tracker |

Check a file: `python3 schema/validate.py evidence path/to/evidence.json` (kinds: capture, geometry, evidence, checker_report). Check every sample and example: `python3 schema/validate.py --all`. Standard library only; any draft 2020-12 validator gives the same answer.

## Rules every file follows
- `schema_version` is the string `"0.1"`. Lengths are metres. Unknown fields are rejected, so a typo fails loudly.
- `room_id` is lower case letters, digits, `_` and `-`.
- A verdict is `pass`, `fail` or `not_proven`, nothing else. A `not_proven` claim has `value: null` and the file's `requested_view` names the claim and the exact view needed.
- `frame_ids` in evidence point to `frame_id` entries in geometry's `frame_index`.
- The checker `result` says whether the checker agrees with the reported claim, not whether the room is safe. A failed exit that the checker confirms is `result: PASS`, and `overall` is PASS only when every claim's result is PASS.
- `tolerance` is `null` until D8 sets tolerances; no number is invented before then.

## Field choices made in this draft (please check)
These go beyond what docs/interfaces.md fixed, so each needs a yes from the lane that uses it.

| Choice | Lane to confirm |
| --- | --- |
| Claim types: `blocked_exit`, `door_clear_width`, `distance_to_exit`; `value` is the clear distance (exit) or clear width (door) in metres | Nadeem |
| `coverage` = `seen_fraction` (0 to 1) plus a list of `unseen_regions` with id and description | Nadeem |
| `requested_view` = null or `{claim_ids, description}` | Nadeem |
| Poses are `position` [x, y, z] plus `rotation_wxyz` quaternion; `frame_index` maps `frame_id` to `t_seconds` in the clip | Kaushal |
| `marker_poses` is keyed by marker id as a string (JSON keys are strings) | Kaushal |
| `points_ref` points to a separate file (`point_cloud` or `occupancy_grid`) instead of holding points inline | Kaushal |
| `openings`: a door has its two edge points, an exit one centre point, each with the marker ids that found it (D11) | Kaushal, Nadeem |
| `scale_source.method` is `aruco_marker`, `photo_measurement` (T22 fallback) or `none` | Kaushal |
| Checker report repeats the reported verdict and value next to the recomputed value, with an optional `reason` | Nadeem (reviews the checker) |

## Samples
`samples/pass.json` and `samples/fail.json` are evidence files; `samples/*.checker_report.json` are the matching checker reports for the viewer. `schema/examples/` holds one capture.json and one geometry.json. **All numbers in them are made up to exercise the format; they are not measurements.** Together they cover all three verdicts: the pass sample has two passes; the fail sample has a failed exit, a `not_proven` door with a requested view, and a checker that agrees with both.

## Written approvals (T1 done-when: all three)
One line each: name, date, what is approved. Version stays 0.1 unless someone changes a field.

- Kaushal, 15 Oct: APPROVED for the geometry.json choices in the table above (poses and `frame_index`, `marker_poses` keyed by marker id as a string, `points_ref`, `openings` with D11 marker ids, `scale_source`). Basis: `reconstruct/run.py` writes geometry that validates against `geometry.schema.json` on seven reconstructed synthetic clips (docs/spike-report.md, docs/rules-run.md), and `python3 schema/validate.py --all` prints ok for all six files. Not reviewed beyond that: the evidence and checker-report choices (Nadeem's and Shriyashish Mishra's); I only know that rules v0 writes evidence that validates on all of those clips. One gap, not a change: geometry carries no camera field of view, so pose-based visibility (T10) is not possible; it can be added later as an optional field. No field changes requested.
- Nadeem: pending
- Shriyashish Mishra: author (draft in PR #5); written approval of the final text pending

