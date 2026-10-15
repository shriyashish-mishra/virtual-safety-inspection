#!/usr/bin/env python3
"""Check the synthetic clips: can the markers be found, and does their size give the right scale?

Reads each clip, runs the OpenCV ArUco detector, solves each marker's pose with the true
intrinsics and compares: (a) the marker-to-camera distance with the true camera path,
(b) the distance between the two door-edge markers with the true layout.  Writes
check.json next to each clip.  Needs numpy and opencv-python.

    python tools/synthetic_room/verify.py --out ~/virtual-safety-synth
"""
import argparse
import json
import os

import cv2
import numpy as np

ARUCO_DICT = cv2.aruco.DICT_4X4_50
CLIPS = ["clip1_clear", "clip2_blocked", "clip3_unseen"]


def quat_to_mat(q):
    w, x, y, z = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def pose_at_frame(poses, t):
    ts = np.array([p["t"] for p in poses])
    k = int(np.argmin(np.abs(ts - t)))
    return poses[k], abs(ts[k] - t)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.expanduser("~/virtual-safety-synth"))
    ap.add_argument("--step", type=int, default=5)
    a = ap.parse_args()
    det = cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(ARUCO_DICT), cv2.aruco.DetectorParameters())
    for name in CLIPS:
        d = os.path.join(a.out, name)
        meta = json.load(open(os.path.join(d, "scene_truth.json")))
        geo = json.load(open(os.path.join(d, "geometry_truth.json")))
        K = np.array(meta["camera"]["K"])
        dist = np.array(meta["camera"]["distortion_k1_k2_p1_p2_k3"])
        size = geo["scale_source"]["marker_size_m"]
        fps = meta["fps"]
        poses = [{"t": fi["t_seconds"], "C": np.array(cp["pose"]["position"]),
                  "R": quat_to_mat(cp["pose"]["rotation_wxyz"])}
                 for fi, cp in zip(geo["frame_index"], geo["camera_poses"])]
        marks = {int(k): (np.array(v["position"]), quat_to_mat(v["rotation_wxyz"])) for k, v in geo["marker_poses"].items()}
        obj = np.array([[-size / 2, size / 2, 0], [size / 2, size / 2, 0], [size / 2, -size / 2, 0],
                        [-size / 2, -size / 2, 0]], np.float64)
        cap = cv2.VideoCapture(os.path.join(d, f"{name}.mp4"))
        n, seen, tries = 0, {i: 0 for i in marks}, 0
        dist_err, width_err, frames_with_pair = [], [], 0
        while True:
            ok, img = cap.read()
            if not ok:
                break
            if n % a.step == 0:
                tries += 1
                corners, ids, _ = det.detectMarkers(img)
                found = {}
                if ids is not None:
                    for c, i in zip(corners, ids.flatten()):
                        i = int(i)
                        if i not in marks:
                            continue
                        seen[i] += 1
                        okp, rv, tv = cv2.solvePnP(obj, c.reshape(4, 2).astype(np.float64), K, dist,
                                                   flags=cv2.SOLVEPNP_IPPE_SQUARE)
                        if okp:
                            found[i] = tv.reshape(3)
                t = n / fps
                p, gap = pose_at_frame(poses, t)
                if gap < 0.1:                       # compare against the true camera pose of the nearest sampled frame
                    for i, tv in found.items():
                        true_d = np.linalg.norm(marks[i][0] - p["C"])
                        dist_err.append(abs(np.linalg.norm(tv) - true_d) / true_d)
                if 2 in found and 3 in found:
                    frames_with_pair += 1
                    true_cc = np.linalg.norm(marks[2][0] - marks[3][0])
                    width_err.append(abs(np.linalg.norm(found[2] - found[3]) - true_cc))
            n += 1
        res = {
            "frames_read": n, "frames_tested": tries,
            "detection_rate_by_marker": {str(i): round(seen[i] / max(tries, 1), 3) for i in seen},
            "marker_distance_relative_error": {"median": round(float(np.median(dist_err)), 4) if dist_err else None,
                                               "p95": round(float(np.percentile(dist_err, 95)), 4) if dist_err else None,
                                               "samples": len(dist_err)},
            "door_marker_pair": {"frames_with_both": frames_with_pair,
                                 "true_centre_distance_m": round(float(np.linalg.norm(marks[2][0] - marks[3][0])), 4),
                                 "abs_error_m_median": round(float(np.median(width_err)), 4) if width_err else None,
                                 "abs_error_m_p95": round(float(np.percentile(width_err, 95)), 4) if width_err else None},
        }
        json.dump(res, open(os.path.join(d, "check.json"), "w"), indent=1)
        print(name, json.dumps(res))


if __name__ == "__main__":
    main()
