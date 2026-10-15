"""Shared reading helpers for the rules (T8 to T11). Standard library only.

The rules never import from checker/ and share no code with it (D10): they are written from
docs/rules-spec.md alone. Parameters are blank until D8; they are read from a JSON file, and the
default file holds PLACEHOLDERS (samples/handmade/placeholders.json).
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLACEHOLDER_PARAMS = ROOT / "samples/handmade/placeholders_v02.json"
REQUIRED_PARAMS = ("MIN_EXIT_CLEARANCE_M", "CORRIDOR_HALF_WIDTH_M", "FLOOR_BAND_M", "OBSTACLE_MAX_Z_M",
                   "MIN_FLOOR_POINTS", "MIN_DOOR_CLEAR_WIDTH_M")
OPTIONAL_PARAMS = ("EXIT_PLANE_MARGIN_M", "MIN_CORRIDOR_SEEN_FRACTION", "CORRIDOR_CELL_M", "OBSTACLE_SLICE_M", "MIN_OBSTACLE_SLICE_POINTS")  # spec v0.2 (PROPOSED); absent = step skipped
# Not in docs/rules-spec.md and not in D8: used only to link frames to a claim (frame_ids) and to size
# the coverage grid. PLACEHOLDERS until the team decides them; none of them changes a verdict.
VIEW_HALF_ANGLE_DEG = 30.0   # a frame "shows" a marker when the marker is within this angle of the camera axis
GRID_M = 0.1                 # cell size for the coverage and confidence counts


def load_params(path=None):
    p = json.loads(Path(path or PLACEHOLDER_PARAMS).read_text())
    missing = [k for k in REQUIRED_PARAMS if p.get(k) is None]
    if missing:
        raise SystemExit(f"parameters missing or blank (D8 not decided?): {', '.join(missing)}")
    return p


def load_geometry(path):
    path = Path(path)
    geometry = json.loads(path.read_text())
    ref = geometry["points_ref"]
    if ref.get("kind") != "point_cloud":
        raise SystemExit(f"points_ref kind {ref.get('kind')!r} is not supported (point_cloud only)")
    points = json.loads((path.parent / ref["path"]).read_text())["points"]
    return geometry, points


def rotation_z_axis(q):
    """The +z axis of a rotation given as a unit quaternion (w, x, y, z)."""
    w, x, y, z = q
    return (2 * (x * z + y * w), 2 * (y * z - x * w), 1 - 2 * (x * x + y * y))


def rotation_matrix(q):
    w, x, y, z = q
    return ((1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)),
            (2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)),
            (2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)))


def unit(v):
    n = math.sqrt(sum(a * a for a in v))
    return None if n < 1e-9 else tuple(a / n for a in v)


def floor_direction(marker_pose):
    """Unit vector on the floor along the marker's printed-face normal (into the room), or None if it points straight up or down."""
    z = rotation_z_axis(marker_pose["rotation_wxyz"])
    return unit((z[0], z[1]))
