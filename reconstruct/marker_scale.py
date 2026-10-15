"""T6 marker scale: metres per model unit from the printed scale marker, plus door width from the door-edge markers.

    import marker_scale
    res = marker_scale.measure(out, capture, door_edge_offset_m=...)   # out: images (BGR), depth, extr (w2c), intr
    marker_scale.write_scale_source("geometry.json", res)

`out` is what a reconstruction model gives per frame (the same dict reconstruct/spike.py builds for VGGT and
Depth Anything 3). One global scale factor = printed marker size / mean marker edge length in model units (D7:
DICT_4X4_50, scale marker id from capture.json). Door-edge markers are ids 2 and 3 (D11). This module only
measures: it chooses no tolerance (D8) and does not move the model frame to +z up / floor z = 0 (T7 does that).
Needs numpy and opencv-python.
"""
import json

import cv2
import numpy as np

ARUCO_DICT = cv2.aruco.DICT_4X4_50  # D7
DOOR_EDGE_IDS = (2, 3)  # D11, PROPOSED until Nadeem confirms
# PLACEHOLDER, not a decision: distance from a door-edge marker's centre to the clear-opening edge. 0.177 m is the
# value in the synthetic room (tools/synthetic_room). A real room needs a placement rule agreed with Nadeem (T2).
DOOR_EDGE_OFFSET_M = 0.177


def corner_depth(depth, uv):
    u, v = int(round(uv[0])), int(round(uv[1]))
    h, w = depth.shape
    win = depth[max(v - 2, 0):min(v + 3, h), max(u - 2, 0):min(u + 3, w)]
    return float(np.median(win)) if win.size else float("nan")


def detect(out):
    """Every detected marker: id -> list (one per frame it was seen in) of its 4 corners in model world units."""
    det = cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(ARUCO_DICT), cv2.aruco.DetectorParameters())
    found = {}
    for i, img in enumerate(out["images"]):
        corners, ids, _ = det.detectMarkers(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
        if ids is None:
            continue
        R, t = out["extr"][i][:, :3], out["extr"][i][:, 3]  # w2c: Xc = R Xw + t
        K = out["intr"][i]
        for c, mid in zip(corners, ids.ravel()):
            pts = []
            for u, v in c.reshape(4, 2):
                xc = corner_depth(out["depth"][i], (u, v)) * np.linalg.solve(K, np.array([u, v, 1.0]))
                pts.append(R.T @ (xc - t))
            found.setdefault(int(mid), []).append(np.array(pts))
    return found


def edge_len(c):
    return float(np.mean([np.linalg.norm(c[k] - c[(k + 1) % 4]) for k in range(4)]))


def door_width(centres_m, offset_m=DOOR_EDGE_OFFSET_M):
    """Clear width = distance between the two door-edge marker centres minus the offset on each side."""
    a, b = DOOR_EDGE_IDS
    if a not in centres_m or b not in centres_m:
        return None
    return float(np.linalg.norm(centres_m[a] - centres_m[b]) - 2 * offset_m)


def measure(out, capture, door_edge_offset_m=DOOR_EDGE_OFFSET_M, true_door_width_m=None):
    """Scale and door width for one clip. Positions are in metres in the model's own frame."""
    found = detect(out)
    res = {"markers_seen": {str(k): len(v) for k, v in sorted(found.items())},
           "scale_source": {"method": "none", "marker_id": None, "marker_size_m": None}}
    sid, size = capture["marker_id"], capture["marker_size_m"]
    if sid not in found:
        res["error"] = f"scale marker {sid} not detected in any frame"
        return res
    edges = {k: float(np.nanmedian([edge_len(c) for c in v])) for k, v in found.items()}
    s = size / edges[sid]
    centres = {k: np.nanmedian([c.mean(0) for c in v], axis=0) * s for k, v in found.items()}
    res.update(scale_source={"method": "aruco_marker", "marker_id": sid, "marker_size_m": size},
               scale_factor_m_per_unit=s,
               implied_marker_size_m={str(k): round(e * s, 4) for k, e in sorted(edges.items())},
               marker_centres_m={str(k): [round(float(x), 4) for x in c] for k, c in sorted(centres.items())})
    w = door_width(centres, door_edge_offset_m)
    if w is None:
        res["door_width"] = {"error": f"door-edge markers {DOOR_EDGE_IDS} not both detected"}
    else:
        res["door_width"] = {"estimated_m": round(w, 4), "edge_offset_m_PLACEHOLDER": door_edge_offset_m}
        if true_door_width_m is not None:
            res["door_width"].update(true_m=true_door_width_m, error_m=round(w - true_door_width_m, 4),
                                     error_pct=round(100 * (w - true_door_width_m) / true_door_width_m, 2))
    return res


def write_scale_source(geometry_path, res):
    """Set geometry['scale_source'] (schema/geometry.schema.json) from a measure() result."""
    with open(geometry_path) as f:
        g = json.load(f)
    g["scale_source"] = res["scale_source"]
    with open(geometry_path, "w") as f:
        json.dump(g, f, indent=2)
        f.write("\n")
