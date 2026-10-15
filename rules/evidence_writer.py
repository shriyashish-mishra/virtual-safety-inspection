"""T11: turn rule results into evidence.json (schema v0.1) with frame links. Standard library only."""
import blocked_exit
import coverage
import door_width


def build(geometry, points, params):
    results = []
    for op in geometry["openings"]:
        if op["kind"] == "exit":
            results.append(blocked_exit.evaluate(op, geometry, points, params))
        elif op["kind"] == "door":
            results.append(door_width.evaluate(op, geometry, points, params))
    claims, unseen = [], []
    for r in results:
        op = next(o for o in geometry["openings"] if o["id"] == r["opening_id"])
        proven = r["verdict"] != "not_proven"
        if r["type"] == "blocked_exit":
            confidence = (r["floor_cell_fraction"] if r["floor_cell_fraction"] is not None else 1.0) if proven else 0.0
        else:  # both edge markers located; not a calibrated probability
            confidence = 1.0 if proven else 0.0
        if r["verdict"] == "not_proven":
            unseen.append({"id": r["id"], "description": r.get("reason", "")})
        claims.append({"id": r["id"], "type": r["type"], "verdict": r["verdict"], "value": r["value"],
                       "unit": r["unit"], "confidence": round(confidence, 3),
                       "frame_ids": coverage.frames_showing(op.get("marker_ids", []), geometry) if proven else []})
    return {"schema_version": "0.1", "room_id": geometry["room_id"], "claims": claims,
            "coverage": {"seen_fraction": round(coverage.floor_seen_fraction(points, params), 3), "unseen_regions": unseen},
            "requested_view": coverage.requested_view(results, params)}
