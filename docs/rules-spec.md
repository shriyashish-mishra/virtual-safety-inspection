# Rules spec v0.1 (DRAFT, T4)

**Status 15 Oct:** spec v0.2 and v0.3 (sections 2 and 4) are ACCEPTED by Shriyashish Mishra as Nadeem's backup owner, (docs/decisions.md). Nadeem, as owner, may change them; the rules and the checker then follow in one pull request. The words PROPOSED below are kept for history. Parameter values are still placeholders (D8).

Written by Nadeem (T4). The rules (rules/, Nadeem: T8, T9, T10) and the checker (checker/, Shriyashish Mishra: T34) are both written from this text and from nothing else (D10). If the two disagree, this spec is wrong and is fixed first. It describes formulas in words; it depends on no code in rules/.

Field names come from the draft schema v0.1 on branch `shriya/T1-evidence-schema` (not yet approved). If T1 changes a field, this spec follows it.

## 1. Inputs
- `geometry.json` (schema v0.1) and the point file named by its `points_ref.path`, resolved relative to the folder holding `geometry.json`. The point file is part of the geometry: without it no obstacle can be found. "The checker reads only geometry.json and evidence.json" (docs/interfaces.md) is read here as "geometry.json, its point file, and evidence.json".
- `evidence.json` (schema v0.1), checked by the checker only.
- The parameters in section 2.

### Point file (PROPOSED; the T1 draft names the file but not its format)
For `points_ref.kind = point_cloud`: a JSON object `{"schema_version": "0.1", "units": "m", "points": [[x, y, z], ...]}` in the same world frame as `geometry.json`. Kaushal and Shriyashish Mishra must agree this or replace it (for example with PLY) before T7. `occupancy_grid` is not specified in v0.1.

## 2. World frame and parameters
- Lengths are metres. One right-handed world frame.
- **Up is +z and the floor is the plane z = 0** (PROPOSED: reconstruction must deliver gravity-aligned geometry with the floor at z = 0; needs Kaushal's yes). "On the floor" and "horizontal distance" below mean: ignore z, use x and y only.
- Rotations are unit quaternions `rotation_wxyz`. A marker's own +z axis points out of the printed face (the OpenCV ArUco convention), so a marker on a wall or door points into the room.

Every number the rules use is a named parameter. **All values are blank on purpose until D8.** Test files may use clearly labelled placeholder values (see samples/handmade/placeholders.json); those are not proposals.

| Parameter | Meaning | Value |
| --- | --- | --- |
| `MIN_EXIT_CLEARANCE_M` | Minimum clear distance in front of an exit for it to count as not blocked. Proposed to D8 by T4 | blank (D8) |
| `CORRIDOR_HALF_WIDTH_M` | Half the width of the strip in front of an exit that must be clear | blank (D8) |
| `FLOOR_BAND_M` | Points with z below this are floor; at or above it they can be obstacles | blank (D8) |
| `OBSTACLE_MAX_Z_M` | Points above this height (lamps, ceiling) are not obstacles | blank (D8) |
| `MIN_FLOOR_POINTS` | Floor points needed inside a region before it counts as seen | blank (D8) |
| `MIN_DOOR_CLEAR_WIDTH_M` | Door width at or above which the door claim passes. Not named in D8 today; D8 should add it | blank (D8) |
| `EXIT_PLANE_MARGIN_M` | Obstacle points closer than this to the exit plane are the door or wall, not obstacles (v0.2, PROPOSED) | blank (D8); blank = 0 |
| `MIN_CORRIDOR_SEEN_FRACTION` | Fraction of the corridor squares that must hold a floor point for the corridor to count as seen (v0.2, PROPOSED) | blank (D8); blank = step skipped |
| `CORRIDOR_CELL_M` | Side of the corridor squares used by the seen fraction (v0.2, PROPOSED) | blank (D8); blank = step skipped |
| `OBSTACLE_SLICE_M` | Side of the corridor slices used to tell an obstacle from noise (v0.3, PROPOSED) | blank (D8); blank = step skipped |
| `MIN_OBSTACLE_SLICE_POINTS` | Points a slice needs to count as an obstacle (v0.3, PROPOSED) | blank (D8); blank = step skipped |
| `TOLERANCE` | Largest difference between reported and recomputed value the checker accepts. Lives in checker/config.py (T34) | blank (D8) |

## 3. Openings
Doors and exits are read from `openings` in geometry.json, never found by the rules themselves (D11 is how reconstruction fills them; its marker ids are PROPOSED).
- A **door** opening has exactly two `points`: its two clear-opening edges (jamb to jamb, after any stop or leaf). Turning marker centres into edge points is reconstruction's job, not the rules'.
- An **exit** opening has one `point`: the centre of the exit at the threshold. Its **into-room direction** `d` is the +z axis of the first marker in its `marker_ids`, taken from `marker_poses`, projected onto the floor and scaled to length 1.

One claim per opening, in the order of `openings`. Claim ids are the opening id plus a suffix: `<exit id>_clear` for an exit, `<door id>_width` for a door.

## 4. Claim: blocked_exit
For an exit with centre `c` and into-room direction `d` (both on the floor):
1. **Corridor.** A floor point `p` is in the corridor when its distance along `d`, `s = (p - c) · d`, satisfies `0 <= s <= MIN_EXIT_CLEARANCE_M`, and its sideways distance, `|(p - c) · n|` with `n` the floor direction at right angles to `d`, is at most `CORRIDOR_HALF_WIDTH_M`. Ends are included.
2. **Obstacles.** Obstacle points are those with `FLOOR_BAND_M <= z <= OBSTACLE_MAX_Z_M` whose floor position is in the corridor and whose `s >= EXIT_PLANE_MARGIN_M` (0 when that parameter is blank). Points closer than the margin are the door or wall the exit is cut into, not obstacles. *(v0.2, PROPOSED: the margin and the order of steps 2 to 5 are new; see the note below.)*
   *(v0.3, PROPOSED)* If `OBSTACLE_SLICE_M` and `MIN_OBSTACLE_SLICE_POINTS` are not blank: group the obstacle points into slices of side `OBSTACLE_SLICE_M` along `d` (slice number `floor(s / OBSTACLE_SLICE_M)`) and drop every point whose slice holds fewer than `MIN_OBSTACLE_SLICE_POINTS` points. Thin scatter of reconstruction noise is not an obstacle.
3. **Fail.** If there are obstacle points: value = the smallest `s` among them, unit `m`. If value < `MIN_EXIT_CLEARANCE_M`: verdict `fail`. Stop. An obstacle that was seen is proof, however much of the floor was seen.
4. **Seen?** Count the points with `z < FLOOR_BAND_M` whose floor position is in the corridor. If fewer than `MIN_FLOOR_POINTS`: verdict `not_proven`, value null, unit null. Stop.
5. **Seen enough?** If `MIN_CORRIDOR_SEEN_FRACTION` and `CORRIDOR_CELL_M` are not blank: cut the corridor into squares of side `CORRIDOR_CELL_M` (`ceil(MIN_EXIT_CLEARANCE_M / CORRIDOR_CELL_M)` along `d` times `ceil(2 * CORRIDOR_HALF_WIDTH_M / CORRIDOR_CELL_M)` across, counted from the exit centre and from the left edge). The seen fraction is the number of squares holding at least one point with `z < FLOOR_BAND_M`, divided by the number of squares (capped at 1). If it is below `MIN_CORRIDOR_SEEN_FRACTION`: verdict `not_proven`, value null, unit null. Stop.
6. **Pass.** value = the smallest `s` among obstacle points if there are any (it is then at least `MIN_EXIT_CLEARANCE_M`), otherwise `MIN_EXIT_CLEARANCE_M` (meaning "clear for at least the required distance"; the rule does not look further). Unit `m`. Verdict `pass`.

**Why v0.2 (14 Oct, Kaushal; PROPOSED, Nadeem owns this spec and Shriyashish Mishra's checker must follow it).** On the reconstructed geometry of the three synthetic clips the v0.1 rule said `fail` at about 0.004 m on all three: 424, 735 and 474 points of the door leaf and wall sit at `s` of about 0 inside the height band, and clip 3 (corridor never filmed) still had 52 floor points. Changes: (a) the margin removes the door plane; (b) a seen fraction replaces a bare point count as the "was the floor filmed" test; (c) obstacles are tested first so that a visible obstacle is not hidden by thin floor coverage (the floor behind a box is hidden by the box). Blank new parameters give exactly the v0.1 behaviour, except that (c) changes the result when an obstacle is seen and the floor is not (v0.1: `not_proven`, v0.2: `fail`).

**Why v0.3 (15 Oct, Kaushal; PROPOSED).** On the floor-marker reconstructions v0.2 gave a false `fail` on the clip whose corridor was never filmed (5 stray points past the margin, at s 0.19 to 0.35 m) and a clearance of 0.156 m on the clip with the box at 0.70 m (stray points at 0.16 m; the box face itself starts at about 0.65 m). The box face shows up as slices of 17 or more points per 0.05 m, the noise as slices of 9 or fewer. Blank new parameters give the v0.2 behaviour.

The seen test (steps 4 and 5) is a stand-in for real coverage (T10 replaces it, and must not return pass or fail for an unseen corridor).

## 5. Claim: door_clear_width
For a door with edge points `a` and `b`:
1. If the opening does not have exactly two points, or any of its `marker_ids` is missing from `marker_poses`: verdict `not_proven`, value null, unit null.
2. **Value.** The horizontal distance between `a` and `b`: `sqrt((ax - bx)^2 + (ay - by)^2)`. Unit `m`.
3. **Verdict.** `pass` if value >= `MIN_DOOR_CLEAR_WIDTH_M`, otherwise `fail`.

## 6. Fields the rules fill but the checker does not recompute in v0.1
- `confidence`: method set in T8; not checked in v0.1. A `not_proven` claim has confidence 0.
- `frame_ids`: the rules list frames that show the opening (method set in T8/T10). The checker checks only that every id exists in `frame_index`, and that a pass or fail claim has at least one frame id.
- `coverage`: written by T10; not recomputed in v0.1.
- `requested_view`: null when no claim is `not_proven`; otherwise it lists every `not_proven` claim id and names the view, for example "film the floor in front of exit_2 from about 2 m away".

## 7. What the checker does
For each claim in evidence.json, recompute verdict and value from the geometry with sections 3 to 5, then:
- **result PASS** when all of these hold: the claim's opening exists in geometry; the recomputed verdict equals the reported verdict; for pass and fail, `|recomputed value - reported value| <= TOLERANCE`; for not_proven, both values are null; the frame id test in section 6 holds.
- **result FAIL** otherwise, with a short `reason`.
- An opening in geometry with no claim in evidence, or a claim whose opening is missing, is a FAIL.
- `overall` is PASS only when every claim's result is PASS. A confirmed `fail` verdict is still result PASS: the checker reports agreement, not safety.

## 8. Not in v0.1
`distance_to_exit` (T23, stretch); real visibility-based coverage (T10); occupancy grids; confidence method (T8).
