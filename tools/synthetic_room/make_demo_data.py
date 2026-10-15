#!/usr/bin/env python3
"""Build the viewer's demo data from the synthetic clips.  ILLUSTRATIVE.

    python3 tools/synthetic_room/make_demo_data.py --clips ~/virtual-safety-synth --out viewer/demo

For each clip: copies the true geometry and point file, writes the evidence a correct rules
implementation should produce (built from the scene truth and docs/rules-spec.md, NOT by rules/,
which does not exist yet), runs the independent checker on it, picks the frames that really
show the exit and the door, saves them as small JPEGs, and writes plan.json for the top-down view.

Needs numpy and opencv-python (render.py constants and frame extraction). Placeholder parameters from
samples/handmade/placeholders.json; D8 has not set real ones.
"""
import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

import cv2

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import render  # noqa: E402  (scene constants and footprints only)

PARAMS = ROOT / "samples/handmade/placeholders.json"
CHECKER = ROOT / "checker/check.py"
TITLES = {
    "clip1_clear": "Clear exit",
    "clip2_blocked": "Blocked exit",
    "clip3_unseen": "Exit never filmed",
}


def quat_to_mat(q):
    w, x, y, z = q
    return [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]


def visible(pose, K, w, h, p, near=0.3):
    """Is world point p inside the image for this camera-to-world pose (frustum only, no occlusion)?"""
    C, R = pose["position"], quat_to_mat(pose["rotation_wxyz"])
    d = [p[i] - C[i] for i in range(3)]
    cam = [sum(R[r][c] * d[r] for r in range(3)) for c in range(3)]  # R^T d
    if cam[2] < near:
        return False
    u = K[0][0] * cam[0] / cam[2] + K[0][2]
    v = K[1][1] * cam[1] / cam[2] + K[1][2]
    return 0 <= u < w and 0 <= v < h


def spread(ids, k):
    """Up to k ids spread over the list (first, middle, last...)."""
    if len(ids) <= k:
        return list(ids)
    return [ids[round(i * (len(ids) - 1) / (k - 1))] for i in range(k)]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--clips", required=True, help="folder with the rendered clip folders (clip1_clear/...)")
    ap.add_argument("--out", default=str(ROOT / "viewer/demo"))
    a = ap.parse_args()
    params = json.loads(PARAMS.read_text())
    out = Path(a.out)
    index = []
    for name, title in TITLES.items():
        src = Path(a.clips) / name
        scene = json.loads((src / "scene_truth.json").read_text())
        geo = json.loads((src / "geometry_truth.json").read_text())
        pts = json.loads((src / "points_truth.json").read_text())["points"]
        truth = scene["truth"]
        W, H = scene["resolution"]
        K = scene["camera"]["K"]
        poses = {c["frame_id"]: c["pose"] for c in geo["camera_poses"]}
        times = {f["frame_id"]: f["t_seconds"] for f in geo["frame_index"]}
        cor = render.UNSEEN
        corridor_pts = [[cor["x0"] + (cor["x1"] - cor["x0"]) * i / 5, cor["y0"] + (cor["y1"] - cor["y0"]) * j / 5, 0.0]
                        for i in range(6) for j in range(6)]
        door_pts = [geo["marker_poses"]["2"]["position"], geo["marker_poses"]["3"]["position"]]
        # frames that really show the corridor and the door edges
        seen_cor = {fid: sum(visible(p, K, W, H, q) for q in corridor_pts) for fid, p in poses.items()}
        cor_frames = [f for f, n in sorted(seen_cor.items(), key=lambda t: -t[1]) if n >= 10]
        door_frames = [f for f in sorted(poses) if all(visible(poses[f], K, W, H, q) for q in door_pts)]
        frame_exit = sorted(spread(sorted(cor_frames[:12]), 3))
        frame_door = spread(door_frames, 3)

        min_clear = params["MIN_EXIT_CLEARANCE_M"]
        claims = []
        if truth["expected_verdict"] == "not_proven":
            claims.append({"id": "exit_1_clear", "type": "blocked_exit", "verdict": "not_proven", "value": None,
                           "unit": None, "confidence": 0.0, "frame_ids": []})
        else:
            claims.append({"id": "exit_1_clear", "type": "blocked_exit",
                           "verdict": "fail" if truth["exit_clearance_m"] < min_clear else "pass",
                           "value": min(truth["exit_clearance_m"], min_clear), "unit": "m", "confidence": 0.9,
                           "frame_ids": frame_exit})
        width = truth["door_clear_width_m"]
        claims.append({"id": "door_1_width", "type": "door_clear_width",
                       "verdict": "pass" if width >= params["MIN_DOOR_CLEAR_WIDTH_M"] else "fail",
                       "value": width, "unit": "m", "confidence": 0.85, "frame_ids": frame_door})
        floor_cells = {(int(p[0] / 0.1), int(p[1] / 0.1)) for p in pts if p[2] < 0.05}
        total = int(render.W_ROOM / 0.1) * int(render.D_ROOM / 0.1)
        unproven = [c["id"] for c in claims if c["verdict"] == "not_proven"]
        evidence = {
            "schema_version": "0.1", "room_id": geo["room_id"], "claims": claims,
            "coverage": {"seen_fraction": round(min(1.0, len(floor_cells) / total), 2),
                         "unseen_regions": ([{"id": "exit_1_floor", "description": "Floor in front of exit_1 never in view"}] if unproven else [])},
            "requested_view": ({"claim_ids": unproven, "description": "Film the floor in front of exit_1 from about 2 m away, with the exit marker in frame"} if unproven else None),
        }
        dest = out / name
        (dest / "frames").mkdir(parents=True, exist_ok=True)
        (dest / "geometry.json").write_text(json.dumps(geo))
        (dest / "points_truth.json").write_text(json.dumps({"schema_version": "0.1", "units": "m", "points": pts}))
        geo["points_ref"]["path"] = "points_truth.json"
        (dest / "geometry.json").write_text(json.dumps(geo))
        (dest / "evidence.json").write_text(json.dumps(evidence, indent=1) + "\n")
        r = subprocess.run([sys.executable, str(CHECKER), str(dest / "geometry.json"), str(dest / "evidence.json"),
                            "--params", str(PARAMS), "--out", str(dest / "checker_report.json")],
                           capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit(f"{name}: checker did not PASS the expected evidence:\n{r.stdout}{r.stderr}")
        # key frames
        cap = cv2.VideoCapture(str(src / f"{name}.mp4"))
        fps = scene["fps"]
        for fid in sorted({f for c in claims for f in c["frame_ids"]}):
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(round(times[fid] * fps)))
            ok, img = cap.read()
            if ok:
                img = cv2.resize(img, (480, 270), interpolation=cv2.INTER_AREA)
                cv2.imwrite(str(dest / "frames" / f"f{fid}.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 72])
        # top-down plan
        rects, foot, _ = render.build_scene(name == "clip2_blocked")
        obstacles = [{"x0": f[0], "x1": f[1], "y0": f[2], "y1": f[3]} for f in foot]
        special = [render.SIDE_TABLE] + ([render.BLOCK_BOX] if name == "clip2_blocked" else [])
        plan = {
            "room": {"w": render.W_ROOM, "d": render.D_ROOM},
            "corridor": cor, "door": {"x0": render.JAMB_L, "x1": render.JAMB_R},
            "furniture": obstacles,
            "key_obstacles": [{"x0": b[0], "y0": b[1], "x1": b[3], "y1": b[4],
                               "label": "box" if b is render.BLOCK_BOX else "side table"} for b in special],
            "camera_path": [[round(p["position"][0], 3), round(p["position"][1], 3)] for _, p in sorted(poses.items())],
            "markers": {k: [v["position"][0], v["position"][1]] for k, v in geo["marker_poses"].items()},
            "floor_cells_seen": sorted([c[0], c[1]] for c in floor_cells),
            "frame_times": {str(k): round(v, 2) for k, v in times.items()},
        }
        (dest / "plan.json").write_text(json.dumps(plan))
        index.append({"id": name, "title": title, "expected_verdict": truth["expected_verdict"],
                      "door_clear_width_m": width, "exit_clearance_m": truth["exit_clearance_m"],
                      "unseen_area": truth["unseen_area"]})
        print(f"{name}: exit frames {frame_exit}, door frames {frame_door}, checker PASS, seen {evidence['coverage']['seen_fraction']}")
    (out / "index.json").write_text(json.dumps({
        "provenance": "ILLUSTRATIVE synthetic room rendered by tools/synthetic_room; evidence built from the scene truth; rules v0 (rules/run.py) gives the same verdicts and values on this geometry (checkpoint of 14 Oct); parameters are placeholders until D8",
        "clips": index}, indent=1) + "\n")


if __name__ == "__main__":
    main()
