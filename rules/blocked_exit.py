"""T8: claim blocked_exit, from docs/rules-spec.md section 4. Standard library only."""
import math

from common import floor_direction


def corridor_frame(opening, geometry):
    """(centre, d, n) of an exit on the floor, or None when the exit direction is unknown."""
    marker = geometry["marker_poses"].get(str(opening["marker_ids"][0])) if opening.get("marker_ids") else None
    if marker is None or len(opening["points"]) != 1:
        return None
    d = floor_direction(marker)
    if d is None:
        return None
    c = opening["points"][0]
    return (c[0], c[1]), d, (-d[1], d[0])


def in_corridor(p, frame, params):
    (cx, cy), d, n = frame
    dx, dy = p[0] - cx, p[1] - cy
    s = dx * d[0] + dy * d[1]
    side = abs(dx * n[0] + dy * n[1])
    return (0 <= s <= params["MIN_EXIT_CLEARANCE_M"] and side <= params["CORRIDOR_HALF_WIDTH_M"]), s


def floor_cell_fraction(floor_points, frame, params):
    """Fraction of the corridor's CORRIDOR_CELL_M cells that hold at least one floor point (spec section 4, step 5)."""
    cell, half, length = params["CORRIDOR_CELL_M"], params["CORRIDOR_HALF_WIDTH_M"], params["MIN_EXIT_CLEARANCE_M"]
    (cx, cy), d, n = frame
    total = math.ceil(length / cell) * math.ceil(2 * half / cell)
    cells = set()
    for p in floor_points:
        dx, dy = p[0] - cx, p[1] - cy
        cells.add((int((dx * d[0] + dy * d[1]) / cell), int((dx * n[0] + dy * n[1] + half) / cell)))
    return min(1.0, len(cells) / total)


def evaluate(opening, geometry, points, params):
    """Return {id, type, verdict, value, unit, floor_points, obstacle_points, floor_cell_fraction, reason}."""
    out = {"id": f"{opening['id']}_clear", "type": "blocked_exit", "opening_id": opening["id"],
           "verdict": "not_proven", "value": None, "unit": None, "floor_points": 0, "obstacle_points": 0,
           "floor_cell_fraction": None}
    frame = corridor_frame(opening, geometry)
    if frame is None:
        out["reason"] = "exit direction unknown: exit marker pose missing or pointing straight up"
        return out
    margin = params.get("EXIT_PLANE_MARGIN_M") or 0.0
    slice_m, slice_min = params.get("OBSTACLE_SLICE_M"), params.get("MIN_OBSTACLE_SLICE_POINTS")
    floor, obstacles = [], []
    for p in points:
        inside, s = in_corridor(p, frame, params)
        if not inside:
            continue
        if p[2] < params["FLOOR_BAND_M"]:
            floor.append(p)
        elif p[2] <= params["OBSTACLE_MAX_Z_M"] and s >= margin:  # closer than the margin is the door or wall itself
            obstacles.append(s)
    if slice_m and slice_min:  # thin scatter is reconstruction noise, not an obstacle: keep only dense slices of the corridor
        counts = {}
        for d in obstacles:
            counts[int(d / slice_m)] = counts.get(int(d / slice_m), 0) + 1
        obstacles = [d for d in obstacles if counts[int(d / slice_m)] >= slice_min]
    out["floor_points"], out["obstacle_points"] = len(floor), len(obstacles)
    cell = params.get("CORRIDOR_CELL_M")
    if cell:
        out["floor_cell_fraction"] = floor_cell_fraction(floor, frame, params)
    if obstacles and min(obstacles) < params["MIN_EXIT_CLEARANCE_M"]:  # an obstacle that was seen is proof, however much floor was seen
        out.update(value=min(obstacles), unit="m", verdict="fail")
        return out
    needed = params.get("MIN_CORRIDOR_SEEN_FRACTION")
    if len(floor) < params["MIN_FLOOR_POINTS"]:
        out["reason"] = f"only {len(floor)} floor points in the corridor, {params['MIN_FLOOR_POINTS']} needed"
        return out
    if needed and cell and out["floor_cell_fraction"] < needed:
        out["reason"] = f"floor seen in {out['floor_cell_fraction']:.2f} of the corridor, {needed} needed"
        return out
    out.update(value=min(obstacles) if obstacles else params["MIN_EXIT_CLEARANCE_M"], unit="m", verdict="pass")
    return out
