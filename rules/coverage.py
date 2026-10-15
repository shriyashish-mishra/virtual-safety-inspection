"""T10: coverage, frame links and the view request. Standard library only.

Seen or not for a claim is decided by the rule itself (spec section 4, step 2: enough floor points
in the corridor). This module turns that into the evidence file's coverage block and requested_view,
and links each claim to the frames that show its markers. Frame links and the grid size use the
PLACEHOLDERS in common.py; they never change a verdict.
"""
import math

from common import GRID_M, VIEW_HALF_ANGLE_DEG, rotation_matrix


def frames_showing(marker_ids, geometry):
    """Frame ids whose camera axis is within VIEW_HALF_ANGLE_DEG of every marker in marker_ids.
    If none qualifies, the single best frame (smallest worst angle) so a pass or fail always has a link."""
    positions = [geometry["marker_poses"][str(m)]["position"] for m in marker_ids if str(m) in geometry["marker_poses"]]
    if not positions:
        return []
    scored = []
    for cam in geometry["camera_poses"]:
        c = cam["pose"]["position"]
        fwd = tuple(row[2] for row in rotation_matrix(cam["pose"]["rotation_wxyz"]))  # +z of camera-to-world = looks forward
        worst = 0.0
        for p in positions:
            v = (p[0] - c[0], p[1] - c[1], p[2] - c[2])
            n = math.sqrt(sum(a * a for a in v))
            if n < 1e-9:
                worst = 180.0
                continue
            cosang = max(-1.0, min(1.0, sum(a * b for a, b in zip(v, fwd)) / n))
            worst = max(worst, math.degrees(math.acos(cosang)))
        scored.append((worst, cam["frame_id"]))
    inside = sorted(f for ang, f in scored if ang <= VIEW_HALF_ANGLE_DEG)
    return inside or [min(scored)[1]]


def floor_seen_fraction(points, params):
    """Fraction of GRID_M cells, inside the x-y box of all points, that hold at least one floor point."""
    if not points:
        return 0.0
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    x0, y0 = min(xs), min(ys)
    nx, ny = int((max(xs) - x0) / GRID_M) + 1, int((max(ys) - y0) / GRID_M) + 1
    seen = {(int((p[0] - x0) / GRID_M), int((p[1] - y0) / GRID_M)) for p in points if p[2] < params["FLOOR_BAND_M"]}
    return len(seen) / (nx * ny)


def requested_view(claims, params):
    """null when nothing is not_proven; otherwise name the view that would decide each unproven claim."""
    unproven = [c for c in claims if c["verdict"] == "not_proven"]
    if not unproven:
        return None
    parts = []
    for c in unproven:
        if c["type"] == "blocked_exit":
            parts.append(f"film the floor in front of {c['opening_id']}: the strip from the exit out to "
                         f"{params['MIN_EXIT_CLEARANCE_M']} m, {2 * params['CORRIDOR_HALF_WIDTH_M']} m wide, fully in view")
        else:
            parts.append(f"film both edges of {c['opening_id']} with their markers in view")
    return {"claim_ids": [c["id"] for c in unproven], "description": "; ".join(parts)}
