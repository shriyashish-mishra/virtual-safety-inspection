#!/usr/bin/env python3
"""T5 spike script: run VGGT or Depth Anything 3 on one clip and measure scale from the printed marker.

    python3 reconstruct/spike.py vggt CLIP_DIR [--frames 24]
    python3 reconstruct/spike.py da3  CLIP_DIR [--frames 24]
    python3 reconstruct/spike.py fake CLIP_DIR            # no model: checks the maths only

CLIP_DIR holds <name>.mp4 and capture.json (marker_id, marker_size_m); geometry_truth.json is
optional (synthetic clips). One global scale factor = printed marker size / marker edge length in
model units. A throwaway spike number, not the T6 module. It reports measured error only and picks
no tolerance (D8). Needs numpy and opencv-python; torch and the model package only for vggt/da3.
Model calls follow each project's README (read 12 Oct 2026); output key names are UNVERIFIED
until the first GPU run and the script stops with a clear error if they differ.
"""
import argparse
import glob
import json
import os
import sys
import tempfile
import time

import cv2
import numpy as np

ARUCO_DICT = cv2.aruco.DICT_4X4_50  # D7, Kaushal 11 Oct


def sample_frames(video, n, out_dir):
    cap = cv2.VideoCapture(video)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    paths = []
    for i, idx in enumerate(np.linspace(0, total - 1, n).astype(int)):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
        ok, img = cap.read()
        if ok:
            p = os.path.join(out_dir, f"f{i:03d}.png")
            cv2.imwrite(p, img)
            paths.append(p)
    return paths


def run_vggt(paths):
    import torch
    from vggt.models.vggt import VGGT
    from vggt.utils.load_fn import load_and_preprocess_images
    from vggt.utils.pose_enc import pose_encoding_to_extri_intri
    dev = "cuda"
    dtype = torch.bfloat16 if torch.cuda.get_device_capability()[0] >= 8 else torch.float16
    model = VGGT.from_pretrained("facebook/VGGT-1B").to(dev)
    images = load_and_preprocess_images(paths).to(dev)
    torch.cuda.reset_peak_memory_stats()
    t0 = time.time()
    with torch.no_grad(), torch.cuda.amp.autocast(dtype=dtype):
        pred = model(images)
    torch.cuda.synchronize()
    secs = time.time() - t0
    for key in ("pose_enc", "depth"):  # UNVERIFIED key names
        if key not in pred:
            sys.exit(f"VGGT output has no '{key}'; keys are {list(pred)}. Fix run_vggt.")
    extr, intr = pose_encoding_to_extri_intri(pred["pose_enc"], images.shape[-2:])
    imgs = (images.permute(0, 2, 3, 1).clamp(0, 1).cpu().numpy() * 255).astype(np.uint8)
    out = dict(images=imgs[..., ::-1].copy(),  # RGB -> BGR for OpenCV
               depth=pred["depth"][0].float().cpu().numpy().reshape(len(paths), *imgs.shape[1:3]),
               extr=extr[0].float().cpu().numpy(), intr=intr[0].float().cpu().numpy())
    return out, secs, torch.cuda.max_memory_allocated() / 2**30


def run_da3(paths):
    import torch
    from depth_anything_3.api import DepthAnything3
    model = DepthAnything3.from_pretrained("depth-anything/DA3NESTED-GIANT-LARGE").to(device=torch.device("cuda"))
    torch.cuda.reset_peak_memory_stats()
    t0 = time.time()
    p = model.inference(paths)
    torch.cuda.synchronize()
    secs = time.time() - t0
    out = dict(images=p.processed_images[..., ::-1].copy(), depth=p.depth, extr=p.extrinsics, intr=p.intrinsics)
    return out, secs, torch.cuda.max_memory_allocated() / 2**30


def corner_depth(depth, uv):
    u, v = int(round(uv[0])), int(round(uv[1]))
    h, w = depth.shape
    win = depth[max(v - 2, 0):min(v + 3, h), max(u - 2, 0):min(u + 3, w)]
    return float(np.median(win)) if win.size else float("nan")


def marker_world_corners(out, det):
    """For every frame, every detected marker: its 4 corners in the model's world frame (model units)."""
    found = {}
    for i, img in enumerate(out["images"]):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = det.detectMarkers(gray)
        if ids is None:
            continue
        R, t = out["extr"][i][:, :3], out["extr"][i][:, 3]  # w2c: Xc = R Xw + t (OpenCV)
        K = out["intr"][i]
        for c, mid in zip(corners, ids.ravel()):
            pts = []
            for u, v in c.reshape(4, 2):
                d = corner_depth(out["depth"][i], (u, v))
                xc = d * np.linalg.solve(K, np.array([u, v, 1.0]))
                pts.append(R.T @ (xc - t))
            found.setdefault(int(mid), []).append(np.array(pts))
    return found


def edge_len(c):
    return float(np.mean([np.linalg.norm(c[k] - c[(k + 1) % 4]) for k in range(4)]))


def measure(out, capture, truth=None):
    det = cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(ARUCO_DICT), cv2.aruco.DetectorParameters())
    found = marker_world_corners(out, det)
    res = {"markers_seen": {str(k): len(v) for k, v in sorted(found.items())}}
    sid, size = capture["marker_id"], capture["marker_size_m"]
    if sid not in found:
        res["error"] = f"scale marker {sid} not detected in any frame"
        return res
    edges = {k: float(np.nanmedian([edge_len(c) for c in v])) for k, v in found.items()}
    s = size / edges[sid]
    res["scale_factor_m_per_unit"] = s
    res["implied_marker_size_m"] = {str(k): round(e * s, 4) for k, e in sorted(edges.items())}
    centres = {k: np.nanmedian([c.mean(0) for c in v], axis=0) for k, v in found.items()}
    if truth and 2 in centres and 3 in centres:
        tp = truth["marker_poses"]
        true_d = float(np.linalg.norm(np.array(tp["2"]["position"]) - np.array(tp["3"]["position"])))
        est_d = float(np.linalg.norm(centres[2] - centres[3]) * s)
        res["door_marker_distance"] = {"true_m": round(true_d, 4), "estimated_m": round(est_d, 4),
                                       "error_m": round(est_d - true_d, 4), "error_pct": round(100 * (est_d - true_d) / true_d, 2)}
    return res


def fake_model(frames, K, scale=0.5, plane_z=2.0):
    """Stands in for a model: identity cameras and a flat wall at plane_z model units (self-test only)."""
    n = len(frames)
    h, w = frames[0].shape[:2]
    return dict(images=np.stack(frames), depth=np.full((n, h, w), plane_z, np.float32),
                extr=np.tile(np.hstack([np.eye(3), np.zeros((3, 1))]), (n, 1, 1)), intr=np.tile(K, (n, 1, 1)))


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("model", choices=["vggt", "da3", "fake"])
    ap.add_argument("clip_dir")
    ap.add_argument("--frames", type=int, default=24)
    a = ap.parse_args(argv)
    d = a.clip_dir
    capture = json.load(open(os.path.join(d, "capture.json")))
    gt = os.path.join(d, "geometry_truth.json")
    truth = json.load(open(gt)) if os.path.exists(gt) else None
    video = os.path.join(d, capture["clip"])
    with tempfile.TemporaryDirectory() as tmp:
        paths = sample_frames(video, a.frames, tmp)
        if a.model == "fake":
            sys.exit("fake is for test_spike.py; run vggt or da3")
        out, secs, gb = (run_vggt if a.model == "vggt" else run_da3)(paths)
    report = {"model": a.model, "clip": capture["clip"], "frames": len(paths),
              "inference_seconds": round(secs, 2), "peak_gpu_memory_gb": round(gb, 2),
              "dry_run_on_synthetic_clip": truth is not None, **measure(out, capture, truth)}
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
