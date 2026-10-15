"""T9: claim door_clear_width, from docs/rules-spec.md section 5. Standard library only."""
import math


def evaluate(opening, geometry, points, params):
    out = {"id": f"{opening['id']}_width", "type": "door_clear_width", "opening_id": opening["id"],
           "verdict": "not_proven", "value": None, "unit": None}
    pts = opening.get("points", [])
    if len(pts) != 2:
        out["reason"] = "a door needs exactly two edge points"
        return out
    absent = [m for m in opening.get("marker_ids", []) if str(m) not in geometry["marker_poses"]]
    if absent:
        out["reason"] = f"marker(s) {absent} missing from marker_poses"
        return out
    a, b = pts
    value = math.hypot(a[0] - b[0], a[1] - b[1])
    out.update(value=value, unit="m", verdict="pass" if value >= params["MIN_DOOR_CLEAR_WIDTH_M"] else "fail")
    return out
