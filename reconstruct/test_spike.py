"""Checks the scale maths of reconstruct/spike.py with a fake model (no GPU, no clip).

A 0.15 m marker is drawn on a wall. The fake model puts the wall at 2.0 model units and calls
the marker edge about 0.075 units wide, so the recovered scale must be about 2.0 m per unit and
the other markers must come out near 0.15 m. Skips itself if numpy or opencv are missing (CI is
standard library only).
"""
import os
import sys

try:
    import cv2
    import numpy as np
except ImportError:
    print("skipped: numpy/opencv-python not installed")
    sys.exit(0)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spike  # noqa: E402

W, H, F = 640, 480, 500.0
K = np.array([[F, 0, W / 2], [0, F, H / 2], [0, 0, 1.0]])
PLANE_Z, EDGE_UNITS = 2.0, 0.30  # model units; the marker is 0.30 units wide, so 0.15 m => 0.5 m per unit
PX = int(round(EDGE_UNITS * F / PLANE_Z))  # marker side in pixels, 75


def marker_img(mid):
    return cv2.aruco.generateImageMarker(cv2.aruco.getPredefinedDictionary(spike.ARUCO_DICT), mid, PX)


def frame():
    img = np.full((H, W), 255, np.uint8)
    for mid, (x, y) in {0: (120, 200), 1: (300, 200), 2: (480, 200)}.items():
        img[y:y + PX, x:x + PX] = marker_img(mid)
    return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)


out = spike.fake_model([frame()] * 3, K, plane_z=PLANE_Z)
res = spike.measure(out, {"marker_id": 0, "marker_size_m": 0.15})
assert res["markers_seen"] == {"0": 3, "1": 3, "2": 3}, res
want = 0.15 / EDGE_UNITS
assert abs(res["scale_factor_m_per_unit"] - want) / want < 0.05, res
for k, v in res["implied_marker_size_m"].items():
    assert abs(v - 0.15) < 0.01, res
print("ok: scale", round(res["scale_factor_m_per_unit"], 4), "implied sizes", res["implied_marker_size_m"])
