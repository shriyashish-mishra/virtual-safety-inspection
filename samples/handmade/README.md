# Hand-made test pairs (T4)

Two geometry and evidence pairs, made by hand from docs/rules-spec.md, so the checker (T34) has input before real data exists. **Every number here is made up to exercise the spec; none is a measurement.** Rule parameters come from `placeholders.json`, which holds PLACEHOLDER values for these files only; D8 sets the real ones.

| Folder | What it is | Expected checker overall |
| --- | --- | --- |
| `good/` | geometry.json, its point file points.json, and an evidence.json that follows the spec | PASS |
| `tampered/` | Same geometry and points; evidence identical except `door_1_width` value doubled, 0.9 to 1.8 | FAIL |

## The room
- `exit_1`: centre (0, 0), marker 1 faces +y into the room. Four floor points in its corridor (seen). A box at y = 0.6 to 0.65 sits in the corridor; a point at x = 0.9 is outside the corridor and a lamp at z = 2.3 is above `OBSTACLE_MAX_Z_M`, so both are ignored.
- `door_1`: edges (3.0, 1.6) and (3.0, 2.5), markers 2 and 3.
- `exit_2`: centre (-2, 3), marker 4 faces +x. No floor points in its corridor (unseen).
- Marker 0 is the scale marker (D7). Marker ids 1 to 4 for openings are PLACEHOLDERS until D11 is tested.

## Expected per-claim results (hand-computed, cross-checked by a throwaway script not in the repo)

| Claim | Recomputed verdict | Recomputed value | good/ result | tampered/ result |
| --- | --- | --- | --- | --- |
| exit_1_clear | fail | 0.6 m (nearest box point) | PASS | PASS |
| door_1_width | pass | 0.9 m | PASS | FAIL (reported 1.8) |
| exit_2_clear | not_proven | null | PASS | PASS |

The door width computes to 0.8999999999999999 in floating point, so the checker's `TOLERANCE` placeholder must be above zero. Doubling a value breaks any tolerance below 0.9 m.

Validated against the draft schema on `shriya/T1-evidence-schema`: `python3 schema/validate.py geometry|evidence <file>` gives `ok` for all four files.
