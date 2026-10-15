"""Independent checker v0 (T34).

Written from docs/rules-spec.md only (v0.2: exit plane margin, corridor seen fraction, obstacles tested first). Reads geometry.json (plus its point file) and evidence.json.
Imports nothing from rules/ and shares no helper code with it.

    python3 checker/check.py GEOMETRY EVIDENCE --params PARAMS [--out REPORT]

Prints PASS or FAIL for the whole file and one line per claim. Exit code 0 for PASS, 1 for FAIL, 2 for bad input.
"""
import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402


def load(path):
    with open(path) as f:
        return json.load(f)


def floor_dir(q):
    """Marker +z axis projected on the floor, length 1. q is (w, x, y, z)."""
    w, x, y, z = q
    ax = 2 * (x * z + w * y)
    ay = 2 * (y * z - w * x)
    n = math.hypot(ax, ay)
    if n == 0:
        return None
    return ax / n, ay / n


def recompute_exit(op, geom, pts, P):
    """Spec section 4 (v0.3). Blank new parameters give the v0.2, and then the v0.1, behaviour exactly."""
    c = op["points"][0]
    cx, cy = c[0], c[1]
    d = None
    for mid in op.get("marker_ids", []):
        m = geom["marker_poses"].get(str(mid))
        if m is not None:
            d = floor_dir(m["rotation_wxyz"])
        break  # spec: the first marker in marker_ids
    if d is None:
        return "not_proven", None, None
    nx, ny = -d[1], d[0]
    clearance, half = P["MIN_EXIT_CLEARANCE_M"], P["CORRIDOR_HALF_WIDTH_M"]
    margin = P.get("EXIT_PLANE_MARGIN_M") or 0  # blank = 0
    cell, frac = P.get("CORRIDOR_CELL_M"), P.get("MIN_CORRIDOR_SEEN_FRACTION")
    use_fraction = bool(cell) and frac is not None
    if use_fraction:
        n_along, n_across = math.ceil(clearance / cell), math.ceil(2 * half / cell)
        seen_cells = set()
    floor_n, obstacle_s = 0, []
    for x, y, z in pts:
        s = (x - cx) * d[0] + (y - cy) * d[1]
        t = (x - cx) * nx + (y - cy) * ny
        if not (0 <= s <= clearance and abs(t) <= half):
            continue
        if z < P["FLOOR_BAND_M"]:
            floor_n += 1
            if use_fraction:
                seen_cells.add((min(int(s / cell), n_along - 1), min(int((t + half) / cell), n_across - 1)))
        elif z <= P["OBSTACLE_MAX_Z_M"] and s >= margin:
            obstacle_s.append(s)
    slice_m, slice_min = P.get("OBSTACLE_SLICE_M"), P.get("MIN_OBSTACLE_SLICE_POINTS")
    if slice_m and slice_min is not None:  # step 2, v0.3: thin scatter is noise, not an obstacle
        counts = {}
        for v in obstacle_s:
            k = math.floor(v / slice_m)
            counts[k] = counts.get(k, 0) + 1
        obstacle_s = [v for v in obstacle_s if counts[math.floor(v / slice_m)] >= slice_min]
    if obstacle_s and min(obstacle_s) < clearance:  # step 3: a seen obstacle is proof
        return "fail", min(obstacle_s), "m"
    if floor_n < P["MIN_FLOOR_POINTS"]:  # step 4
        return "not_proven", None, None
    if use_fraction and min(1.0, len(seen_cells) / (n_along * n_across)) < frac:  # step 5
        return "not_proven", None, None
    return "pass", (min(obstacle_s) if obstacle_s else clearance), "m"  # step 6


def recompute_door(op, geom, P):
    pts = op.get("points", [])
    if len(pts) != 2 or any(str(m) not in geom["marker_poses"] for m in op.get("marker_ids", [])):
        return "not_proven", None, None
    a, b = pts
    value = math.hypot(a[0] - b[0], a[1] - b[1])
    return ("pass" if value >= P["MIN_DOOR_CLEAR_WIDTH_M"] else "fail"), value, "m"


def suffix_id(op):
    return op["id"] + ("_clear" if op["kind"] == "exit" else "_width")


def check(geom, pts, ev, P, tol):
    openings = {suffix_id(o): o for o in geom.get("openings", [])}
    frames = {f["frame_id"] for f in geom.get("frame_index", [])}
    claims = ev.get("claims", [])
    rows = []
    seen = set()
    for cl in claims:
        cid = cl["id"]
        seen.add(cid)
        row = {"claim_id": cid, "reported_verdict": cl["verdict"], "reported_value": cl.get("value"),
               "recomputed_value": None, "tolerance": tol, "unit": cl.get("unit")}
        op = openings.get(cid)
        why = []
        if op is None:
            why.append("no opening in geometry for this claim")
        else:
            if op["kind"] == "exit":
                verdict, value, unit = recompute_exit(op, geom, pts, P)
                want_type = "blocked_exit"
            else:
                verdict, value, unit = recompute_door(op, geom, P)
                want_type = "door_clear_width"
            row["recomputed_value"] = value
            if cl["type"] != want_type:
                why.append(f"type {cl['type']} but opening is a {op['kind']}")
            if verdict != cl["verdict"]:
                why.append(f"recomputed verdict {verdict}, reported {cl['verdict']}")
            if cl["verdict"] == "not_proven":
                if cl.get("value") is not None or cl.get("unit") is not None:
                    why.append("not_proven must have null value and unit")
            else:
                if cl.get("unit") != "m":
                    why.append("unit must be m")
                if value is not None and cl.get("value") is not None and abs(value - cl["value"]) > tol:
                    why.append(f"value {cl['value']} differs from recomputed {value:.4f} by more than {tol}")
                if cl.get("value") is None:
                    why.append("pass/fail claim has no value")
                if not cl.get("frame_ids"):
                    why.append("pass/fail claim has no frame ids")
        bad = [f for f in cl.get("frame_ids", []) if f not in frames]
        if bad:
            why.append(f"frame ids not in frame_index: {bad}")
        row["result"] = "FAIL" if why else "PASS"
        if why:
            row["reason"] = "; ".join(why)
        rows.append(row)
    for cid in openings:
        if cid not in seen:
            rows.append({"claim_id": cid, "reported_verdict": "not_proven", "reported_value": None,
                         "recomputed_value": None, "tolerance": tol, "unit": None, "result": "FAIL",
                         "reason": "opening in geometry has no claim in evidence"})
    # requested_view invariant (spec section 6): lists exactly the not_proven claims, null if none
    np_ids = sorted(c["id"] for c in claims if c["verdict"] == "not_proven")
    rv = ev.get("requested_view")
    rv_ids = sorted(rv["claim_ids"]) if rv else []
    if rv_ids != np_ids or (np_ids and not (rv or {}).get("description")):
        rows.append({"claim_id": "requested_view", "reported_verdict": "not_proven", "reported_value": None,
                     "recomputed_value": None, "tolerance": tol, "unit": None, "result": "FAIL",
                     "reason": f"requested_view lists {rv_ids}, not_proven claims are {np_ids}"})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("geometry")
    ap.add_argument("evidence")
    ap.add_argument("--params", required=True, help="JSON file with the rule parameters (blank until D8)")
    ap.add_argument("--out", help="write checker_report.json here")
    a = ap.parse_args()
    try:
        geom, ev, P = load(a.geometry), load(a.evidence), load(a.params)
        missing = [k for k in config.REQUIRED_PARAMS if not isinstance(P.get(k), (int, float))]
        if missing:
            raise ValueError(f"params missing {missing}")
        pts_path = os.path.join(os.path.dirname(os.path.abspath(a.geometry)), geom["points_ref"]["path"])
        pts = load(pts_path)["points"]
    except (OSError, ValueError, KeyError) as e:
        print(f"bad input: {e}", file=sys.stderr)
        return 2
    rows = check(geom, pts, ev, P, config.TOLERANCE)
    overall = "PASS" if all(r["result"] == "PASS" for r in rows) else "FAIL"
    for r in rows:
        print(f"  {r['claim_id']}: {r['result']}" + (f" ({r['reason']})" if "reason" in r else ""))
    print(overall)
    if a.out:
        with open(a.out, "w") as f:
            json.dump({"schema_version": "0.1", "room_id": ev["room_id"], "overall": overall, "claims": rows}, f, indent=2)
            f.write("\n")
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
