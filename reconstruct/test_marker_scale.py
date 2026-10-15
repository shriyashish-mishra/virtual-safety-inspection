"""Checks reconstruct/marker_scale.py with a fake model (no GPU, no clip).

A 0.15 m marker is drawn on a wall 2.0 model units away, 0.30 units wide, so the scale must come out as 0.5 m
per unit. Markers 2 and 3 are 180 px apart on that wall = 0.72 units = 0.36 m between centres, so the door width
is 0.36 m with no offset and 0.26 m with a 0.05 m offset. Skips itself if numpy or opencv are missing (CI is
standard library only).
"""
import json
import os
import sys
import tempfile

try:
    import cv2
    import numpy as np
except ImportError:
    print("skipped: numpy/opencv-python not installed")
    sys.exit(0)

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import marker_scale  # noqa: E402
import spike  # noqa: E402  (only for its fake_model)

W, H, F = 640, 480, 500.0
K = np.array([[F, 0, W / 2], [0, F, H / 2], [0, 0, 1.0]])
PLANE_Z, EDGE_UNITS = 2.0, 0.30
PX = int(round(EDGE_UNITS * F / PLANE_Z))


def frame(ids=(0, 2, 3)):
    img = np.full((H, W), 255, np.uint8)
    spots = {0: (60, 100), 2: (200, 250), 3: (380, 250)}  # 2 and 3 are 180 px apart
    d = cv2.aruco.getPredefinedDictionary(marker_scale.ARUCO_DICT)
    for mid in ids:
        x, y = spots[mid]
        img[y:y + PX, x:x + PX] = cv2.aruco.generateImageMarker(d, mid, PX)
    return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)


cap = {"marker_id": 0, "marker_size_m": 0.15}
out = spike.fake_model([frame()] * 3, K, plane_z=PLANE_Z)
res = marker_scale.measure(out, cap, door_edge_offset_m=0.0, true_door_width_m=0.36)
assert abs(res["scale_factor_m_per_unit"] - 0.5) < 0.02, res
assert res["scale_source"] == {"method": "aruco_marker", "marker_id": 0, "marker_size_m": 0.15}, res
assert abs(res["door_width"]["estimated_m"] - 0.36) < 0.01 and abs(res["door_width"]["error_m"]) < 0.01, res
res = marker_scale.measure(out, cap, door_edge_offset_m=0.05)
assert abs(res["door_width"]["estimated_m"] - 0.26) < 0.01, res

# scale marker missing: scale_source says none, no number is invented
res = marker_scale.measure(spike.fake_model([frame((2, 3))] * 3, K, plane_z=PLANE_Z), cap)
assert res["scale_source"]["method"] == "none" and "error" in res and "door_width" not in res, res
# door marker missing: scale still reported, door width says why not
res = marker_scale.measure(spike.fake_model([frame((0, 2))] * 3, K, plane_z=PLANE_Z), cap)
assert "error" in res["door_width"] and "scale_factor_m_per_unit" in res, res

# write_scale_source changes only scale_source
good = os.path.join(HERE, "..", "schema", "examples", "geometry.json")
g = json.load(open(good))
g["scale_source"] = {"method": "none", "marker_id": None, "marker_size_m": None}
with tempfile.TemporaryDirectory() as tmp:
    p = os.path.join(tmp, "geometry.json")
    json.dump(g, open(p, "w"))
    marker_scale.write_scale_source(p, marker_scale.measure(out, cap))
    new = json.load(open(p))
    assert new["scale_source"]["method"] == "aruco_marker" and {**new, "scale_source": 0} == {**g, "scale_source": 0}
    sys.path.insert(0, os.path.join(HERE, "..", "schema"))
    import validate  # noqa: E402
    schema = json.load(open(os.path.join(HERE, "..", "schema", "geometry.schema.json")))
    errors = []
    validate.check(new, schema, schema, "geometry", errors)
    assert not errors, errors
print("ok: scale", round(marker_scale.measure(out, cap)["scale_factor_m_per_unit"], 4), "door width", marker_scale.measure(out, cap, 0.0)["door_width"]["estimated_m"])
