"""Checks reconstruct/run.py with a fake model (no GPU, no clip): scale, up direction, floor, openings, schema.

The fake wall is 2.0 model units from identity cameras, markers 0, 1, 2, 3 are drawn on it (0.30 units wide, so
0.5 m per unit). Image rows run downward, so a marker drawn higher in the picture must come out higher (+z).
Skips itself if numpy or opencv are missing (CI is standard library only).
"""
import os
import sys

try:
    import cv2
    import numpy as np
except ImportError:
    print("skipped: numpy/opencv-python not installed")
    sys.exit(0)

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import marker_scale  # noqa: E402
import run  # noqa: E402
import spike  # noqa: E402  (only for its fake_model)

W, H, F = 640, 480, 500.0
K = np.array([[F, 0, W / 2], [0, F, H / 2], [0, 0, 1.0]])
PLANE_Z, PX = 2.0, 75  # 0.30 units = 75 px at 2.0 units away
SPOTS = {0: (60, 100), 1: (300, 60), 2: (200, 250), 3: (380, 250)}  # top-left pixel of each marker


def frame(spots=SPOTS):
    img = np.full((H, W), 255, np.uint8)
    d = cv2.aruco.getPredefinedDictionary(marker_scale.ARUCO_DICT)
    for mid, (x, y) in spots.items():
        img[y:y + PX, x:x + PX] = cv2.aruco.generateImageMarker(d, mid, PX)
    return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)


# quaternions rebuild the rotation they came from
rng = np.random.default_rng(1)
for _ in range(50):
    Q, _r = np.linalg.qr(rng.normal(size=(3, 3)))
    Q *= np.sign(np.linalg.det(Q))
    w, x, y, z = run.quat_wxyz(Q)
    R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                  [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                  [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    assert np.allclose(R, Q, atol=1e-4), (R, Q)
A = run.alignment(np.array([0.0, -1.0, 0.0]))
assert np.allclose(A @ [0, -1, 0], [0, 0, 1]) and abs(np.linalg.det(A) - 1) < 1e-9

out = spike.fake_model([frame()] * 3, K, plane_z=PLANE_Z)
cap = {"schema_version": "0.1", "room_id": "fake-room", "clip": "x.mp4", "marker_id": 0, "marker_size_m": 0.15}
geo, pts, info = run.build(out, cap, [0.0, 1.0, 2.0], edge_offset_m=0.05)
assert not run.validate(geo), run.validate(geo)
assert abs(info["scale_factor_m_per_unit"] - 0.5) < 0.02, info
m = {k: np.array(v["position"]) for k, v in geo["marker_poses"].items()}
# marker 0 is drawn 150 px above marker 2: 150 * 2.0 / 500 * 0.5 = 0.30 m higher
assert abs((m["0"][2] - m["2"][2]) - 0.30) < 0.02, m
# a marker on the wall faces the camera: its +z axis is horizontal and points back at the camera
q = geo["marker_poses"]["2"]["rotation_wxyz"]
w, x, y, z = q
normal = np.array([2 * (x * z + y * w), 2 * (y * z - x * w), 1 - 2 * (x * x + y * y)])
cam_fwd = A @ [0, 0, 1.0]
assert abs(normal[2]) < 0.05 and normal.dot(cam_fwd) < -0.95, (normal, cam_fwd)
# openings: exit and door on the floor, door width = centre distance (0.36 m) minus 2 x 0.05 m
ops = {o["id"]: o for o in geo["openings"]}
assert ops["exit_1"]["points"][0][2] == 0.0 and all(p[2] == 0.0 for p in ops["door_1"]["points"]), ops
width = np.linalg.norm(np.array(ops["door_1"]["points"][0]) - np.array(ops["door_1"]["points"][1]))
assert abs(width - 0.26) < 0.01, width
# floor is the lowest part of the point cloud
assert abs(np.percentile(pts[:, 2], run.FLOOR_PERCENTILE)) < run.VOXEL_M, pts[:, 2].min()
assert len(geo["camera_poses"]) == 3 and geo["frame_index"][2]["t_seconds"] == 2.0

# marker normal: a square lying in the x-y plane, corners TL, TR, BR, BL seen from +z, faces +z
sq = [np.array([[0, 1, 0], [1, 1, 0], [1, 0, 0], [0, 0, 0]], float)]
assert np.allclose(run.marker_normal(sq), [0, 0, 1]), run.marker_normal(sq)
# without a floor marker the percentile fallback is used and says so
assert info["floor_source"].startswith("percentile") and "UNRELIABLE" in info["floor_source"], info
# with marker 4 in view it sets the floor: z = 0 at its centre; marker 2 is 130 px higher = 130 * 2.0 / 500 * 0.5 = 0.26 m
with_floor = dict(SPOTS)
with_floor[run.FLOOR_ID] = (500, 380)
out4 = spike.fake_model([frame(with_floor)] * 3, K, plane_z=PLANE_Z)
geo4, _pts4, info4 = run.build(out4, cap, [0.0, 1.0, 2.0], edge_offset_m=0.05)
assert info4["floor_source"] == "marker_4", info4
m4 = {k: np.array(v["position"]) for k, v in geo4["marker_poses"].items()}
# here marker 4 is drawn on the same wall as the others, so its normal (toward the camera) becomes "up" and the whole
# wall plane sits at height 0: this checks the plumbing, not a real floor
assert info4["up_source"] == "marker_4_normal" and abs(info4["up_change_from_camera_axes_deg"] - 90) < 2, info4
assert all(abs(v[2]) < 0.02 for v in m4.values()), m4
assert not run.validate(geo4), run.validate(geo4)

# no scale marker: it stops instead of guessing
try:
    run.build(spike.fake_model([np.full((H, W, 3), 255, np.uint8)] * 2, K), cap, [0.0, 1.0])
    raise AssertionError("expected a stop")
except SystemExit as e:
    assert "no scale" in str(e)
print("ok: scale", round(info["scale_factor_m_per_unit"], 3), "door width", round(float(width), 3), "points", len(pts))
