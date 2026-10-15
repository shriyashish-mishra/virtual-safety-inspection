#!/usr/bin/env python3
"""T7 run script: one command from a clip to geometry.json (+ points.json) and a run log.

    python3 reconstruct/run.py CLIP_DIR OUT_DIR [--model vggt|da3] [--frames 32]

CLIP_DIR holds capture.json and the clip it names (as in samples/t2/synthetic). The model needs a GPU, so on this
project that means a Kaggle notebook (docs/install-notes.md). Steps: sample frames, run the model, scale from the marker
(marker_scale.py), turn the model frame into the project frame (+z up, floor z = 0), write cameras, markers,
openings (D11: exit id 1, door edges 2 and 3) and a coarse point cloud, validate against schema/geometry.schema.json,
and log time per step and GPU cost. Prototype quality: gravity comes from the cameras (phone held upright, not
rolled), the floor height from a low percentile of the points; neither is shown to work on real footage (UNVERIFIED).
Needs numpy and opencv-python; torch and the model package only for vggt/da3.
"""
import argparse
import json
import os
import sys
import tempfile
import time

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "schema"))
import marker_scale  # noqa: E402

EXIT_ID, DOOR_IDS = 1, marker_scale.DOOR_EDGE_IDS  # D11
FLOOR_ID = 4  # PROPOSED (docs/decisions.md, floor marker proposal): a marker lying flat on the floor sets z = 0
PIXEL_STRIDE, VOXEL_M, MAX_POINTS, FLOOR_PERCENTILE = 8, 0.05, 20000, 2  # coarse point cloud settings


def sample(video, n, out_dir):
    """Write n evenly spaced frames; return paths and (frame index, seconds) for each one that was read."""
    cap = cv2.VideoCapture(video)
    total, fps = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)), cap.get(cv2.CAP_PROP_FPS) or 30.0
    paths, times = [], []
    for idx in np.linspace(0, total - 1, n).astype(int):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
        ok, img = cap.read()
        if ok:
            p = os.path.join(out_dir, f"f{len(paths):03d}.png")
            cv2.imwrite(p, img)
            paths.append(p)
            times.append(round(float(idx) / fps, 4))
    return paths, times


def up_vector(extr):
    """World-frame 'up' from the cameras: OpenCV camera y points down, so up is minus its mean direction."""
    down = np.mean([e[:, :3][1, :] for e in extr], axis=0)  # row 1 of R_w2c = camera y axis in world
    return -down / np.linalg.norm(down)


def marker_normal(corners):
    """Unit normal of a marker (corner order TL, TR, BR, BL) in the model frame, out of the printed face."""
    c = np.nanmedian(np.stack(corners), axis=0)
    n = np.cross(c[1] - c[0], c[0] - c[3])
    return n / np.linalg.norm(n)


def alignment(up):
    """Rotation taking model-frame vectors to a frame where `up` is +z (right-handed)."""
    ref = np.array([1.0, 0, 0]) if abs(up[0]) < 0.9 else np.array([0, 1.0, 0])
    x = ref - ref.dot(up) * up
    x /= np.linalg.norm(x)
    return np.stack([x, np.cross(up, x), up])


def quat_wxyz(R):
    w = np.sqrt(max(1 + R[0, 0] + R[1, 1] + R[2, 2], 0)) / 2
    if w > 1e-6:
        q = [w, (R[2, 1] - R[1, 2]) / (4 * w), (R[0, 2] - R[2, 0]) / (4 * w), (R[1, 0] - R[0, 1]) / (4 * w)]
    else:  # 180 degree rotation
        i = int(np.argmax(np.diag(R)))
        j, k = (i + 1) % 3, (i + 2) % 3
        s = np.sqrt(max(1 + R[i, i] - R[j, j] - R[k, k], 0)) / 2
        v = [0.0] * 3
        v[i] = s
        v[j] = (R[j, i] + R[i, j]) / (4 * s)
        v[k] = (R[k, i] + R[i, k]) / (4 * s)
        q = [(R[k, j] - R[j, k]) / (4 * s)] + v
    q = np.array(q) / np.linalg.norm(q)
    return [round(float(x), 6) for x in q]


def unproject(out, stride=PIXEL_STRIDE):
    """Points from every depth map, in model world units."""
    pts = []
    for i in range(len(out["depth"])):
        d = out["depth"][i]
        h, w = d.shape
        v, u = np.mgrid[0:h:stride, 0:w:stride]
        z = d[v, u]
        ok = np.isfinite(z) & (z > 0)
        pix = np.stack([u[ok], v[ok], np.ones(ok.sum())])
        xc = (np.linalg.inv(out["intr"][i]) @ pix) * z[ok]
        R, t = out["extr"][i][:, :3], out["extr"][i][:, 3]
        pts.append((R.T @ (xc - t[:, None])).T)
    return np.concatenate(pts)


def voxelise(p, size=VOXEL_M, cap=MAX_POINTS):
    v = np.unique(np.round(p / size).astype(np.int64), axis=0) * size
    if len(v) > cap:
        v = v[np.random.default_rng(0).choice(len(v), cap, replace=False)]
    return v


def height_histogram(h, step=0.1):
    """{bin start (m): point count} for the lowest 1.5 m above the chosen floor, plus everything below it."""
    edges = np.arange(0, 1.5 + step, step)
    counts = np.histogram(h, bins=edges)[0]
    out = {"below_0": int((h < 0).sum())}
    out.update({f"{e:.1f}": int(c) for e, c in zip(edges[:-1], counts)})
    return out


def marker_pose(corners, A, s, shift):
    """Pose of a marker in the project frame. Corner order TL, TR, BR, BL; +z points out of the printed face."""
    c = np.nanmedian(np.stack(corners), axis=0) * s
    c = c @ A.T
    x, y = c[1] - c[0], c[0] - c[3]
    x /= np.linalg.norm(x)
    y -= y.dot(x) * x
    y /= np.linalg.norm(y)
    R = np.stack([x, y, np.cross(x, y)], axis=1)
    return {"position": [round(float(a), 4) for a in c.mean(0) - shift], "rotation_wxyz": quat_wxyz(R)}


def build(out, capture, times, edge_offset_m=marker_scale.DOOR_EDGE_OFFSET_M):
    """geometry dict and point array from one model output. Raises if the scale marker is not seen."""
    res = marker_scale.measure(out, capture, edge_offset_m)
    if res["scale_source"]["method"] == "none":
        raise SystemExit(f"no scale: {res.get('error')}")
    s = res["scale_factor_m_per_unit"]
    found = marker_scale.detect(out)
    up = up_vector(out["extr"])  # from the cameras: assumes an upright, unrolled phone
    up_source, up_shift_deg = "camera_axes", 0.0
    if FLOOR_ID in found:  # the floor marker's normal is up; it measures what the camera axes only assume
        n = marker_normal(found[FLOOR_ID])
        n = n if n.dot(up) > 0 else -n  # the side the cameras are on
        up_shift_deg = float(np.degrees(np.arccos(np.clip(n.dot(up), -1, 1))))
        up, up_source = n, f"marker_{FLOOR_ID}_normal"
    A = alignment(up)
    pts = unproject(out) * s @ A.T
    if FLOOR_ID in found:  # centre of the floor marker, in the same frame as pts
        floor = float((np.nanmedian(np.stack(found[FLOOR_ID]), axis=0) * s @ A.T).mean(0)[2])
        floor_source = f"marker_{FLOOR_ID}"
    else:  # known to be wrong on clips 2 and 3 of the synthetic set; kept until the proposal is decided
        floor = float(np.percentile(pts[:, 2], FLOOR_PERCENTILE))
        floor_source = f"percentile_{FLOOR_PERCENTILE}_FALLBACK_UNRELIABLE"
    shift = np.array([0, 0, floor])
    heights = pts[:, 2] - floor  # kept for the run log: shows why a floor estimate is off
    pts = voxelise(pts - shift)

    cams = []
    for i, e in enumerate(out["extr"]):
        R, t = e[:, :3], e[:, 3]
        c2w_R, pos = R.T, -R.T @ t * s
        cams.append({"frame_id": i, "pose": {"position": [round(float(a), 4) for a in A @ pos - shift],
                                             "rotation_wxyz": quat_wxyz(A @ c2w_R)}})
    markers = {str(k): marker_pose(v, A, s, shift) for k, v in sorted(found.items())}

    def centre(k):
        return np.array(markers[str(k)]["position"])

    def on_floor(p):
        return [round(float(p[0]), 4), round(float(p[1]), 4), 0.0]

    openings = []
    if str(EXIT_ID) in markers:
        openings.append({"id": "exit_1", "kind": "exit", "marker_ids": [EXIT_ID], "points": [on_floor(centre(EXIT_ID))]})
    if all(str(k) in markers for k in DOOR_IDS):
        a, b = centre(DOOR_IDS[0]), centre(DOOR_IDS[1])
        u = (b - a) / np.linalg.norm(b - a)
        openings.append({"id": "door_1", "kind": "door", "marker_ids": list(DOOR_IDS),
                         "points": [on_floor(a + u * edge_offset_m), on_floor(b - u * edge_offset_m)]})
    geometry = {"schema_version": "0.1", "room_id": capture["room_id"], "units": "m", "scale_source": res["scale_source"],
                "frame_index": [{"frame_id": i, "t_seconds": t} for i, t in enumerate(times)],
                "camera_poses": cams, "marker_poses": markers,
                "points_ref": {"kind": "point_cloud", "path": "points.json"}, "openings": openings}
    return geometry, pts, {"scale_factor_m_per_unit": s, "floor_height_model_m": round(floor, 4), "floor_source": floor_source, "up_source": up_source,
                           "up_change_from_camera_axes_deg": round(up_shift_deg, 2),
                           "point_height_percentiles_m": {str(q): round(float(np.percentile(heights, q)), 3)
                                                          for q in (0, 0.5, 1, 2, 5, 10, 25, 50, 75, 95, 100)},
                           "height_histogram_0.1m": height_histogram(heights),
                           "camera_height_m": [round(float(c["pose"]["position"][2]), 3) for c in cams[:: max(1, len(cams) // 8)]],
                           "door_width_m_PLACEHOLDER_OFFSET": res["door_width"].get("estimated_m")}


def validate(geometry):
    import validate as v
    schema = json.load(open(os.path.join(HERE, "..", "schema", "geometry.schema.json")))
    errors = []
    v.check(geometry, schema, schema, "geometry", errors)
    return errors


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("clip_dir")
    ap.add_argument("out_dir")
    ap.add_argument("--model", choices=["vggt", "da3"], default="vggt")
    ap.add_argument("--frames", type=int, default=32)
    a = ap.parse_args(argv)
    log, t0 = {"model": a.model, "frames_requested": a.frames}, time.time()
    capture = json.load(open(os.path.join(a.clip_dir, "capture.json")))
    import spike  # model wrappers; imports torch only when run
    with tempfile.TemporaryDirectory() as tmp:
        paths, times = sample(os.path.join(a.clip_dir, capture["clip"]), a.frames, tmp)
        log["seconds_sampling"] = round(time.time() - t0, 2)
        out, secs, gb = (spike.run_vggt if a.model == "vggt" else spike.run_da3)(paths)
    log.update(frames_used=len(paths), seconds_model=round(secs, 2), peak_gpu_memory_gb=round(gb, 2))
    t1 = time.time()
    geometry, pts, info = build(out, capture, times)
    errors = validate(geometry)
    if errors:
        raise SystemExit("geometry.json does not match the schema: " + "; ".join(errors[:5]))
    os.makedirs(a.out_dir, exist_ok=True)
    with open(os.path.join(a.out_dir, "geometry.json"), "w") as f:
        json.dump(geometry, f, indent=2)
    with open(os.path.join(a.out_dir, "points.json"), "w") as f:
        json.dump({"schema_version": "0.1", "units": "m", "points": np.round(pts, 3).tolist()}, f)
    log.update(info, points_written=len(pts), openings=[o["id"] for o in geometry["openings"]],
               seconds_build=round(time.time() - t1, 2), seconds_total=round(time.time() - t0, 2),
               cost="no money: free notebook GPU quota; GPU seconds used = seconds_total (upper bound)")
    with open(os.path.join(a.out_dir, "run_log.json"), "w") as f:
        json.dump(log, f, indent=2)
    print(json.dumps(log, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
