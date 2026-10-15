#!/usr/bin/env python3
"""Synthetic staged-room clips with known ground truth.  ILLUSTRATIVE, not real footage.

A small numpy ray caster renders a furnished room seen by a hand-held phone camera
(lens distortion, motion blur, auto exposure, glare, sensor noise, video compression).
Because the scene is built here, the true door width, exit clearance, marker poses and
camera path are known exactly and are written next to each clip.

Needs numpy and opencv-python (a venv outside the repo is fine).  Nothing here is
a measurement of a real room; do not use it as T2 ground truth.

    python tools/synthetic_room/render.py --out ~/virtual-safety-synth --clip all
"""
import argparse
import json
import math
import os
import time
from multiprocessing import Pool

import cv2
import numpy as np

# ---------------------------------------------------------------- scene constants
W_ROOM, D_ROOM, H_ROOM = 4.6, 3.6, 2.6          # x, y, z extent in metres; floor is z = 0
DOOR_CX, DOOR_CLEAR, DOOR_H = 3.70, 0.86, 2.05   # exit door in the y = 0 wall
ARCH_W, ARCH_D = 0.07, 0.025
JAMB_L, JAMB_R = DOOR_CX - DOOR_CLEAR / 2, DOOR_CX + DOOR_CLEAR / 2
MARKER_M = 0.15                                  # printed black square side
PAPER_M = MARKER_M * 280 / 240                   # white paper margin of half a cell
ARUCO_DICT = cv2.aruco.DICT_4X4_50               # UNVERIFIED: Kaushal confirms dictionary (D7)
MARKERS = {                                      # id: (centre x, centre z, in-plane tilt deg)
    0: (JAMB_L - ARCH_W - 0.02 - PAPER_M / 2, 1.35, 0.7),   # scale marker
    1: (DOOR_CX, 1.30, 0.0),                                  # exit marker on the door leaf
    2: (JAMB_L - ARCH_W - 0.02 - PAPER_M / 2, 1.00, 0.0),   # left door edge
    3: (JAMB_R + ARCH_W + 0.02 + PAPER_M / 2, 1.00, 0.0),   # right door edge
}
FLOOR_MARKER = (4, 2.90, 0.50)                   # id, centre x, centre y: lies flat on the floor, printed face up
UNSEEN = dict(x0=DOOR_CX - 0.6, x1=DOOR_CX + 0.6, y0=0.0, y1=1.5)  # corridor, placeholder size
BLOCK_BOX = (3.40, 0.70, 0.0, 4.00, 1.15, 0.75)  # clip2 obstacle: x0, y0, z0, x1, y1, z1
SIDE_TABLE = (3.45, 2.20, 0.0, 3.95, 2.70, 0.55)  # in line with the exit, 2.2 m away
LAMP = np.array([2.3, 1.8, 2.45], np.float32)

CLIPS = {
    "clip1_clear": dict(box=False, path="A", expect="pass"),
    "clip2_blocked": dict(box=True, path="A", expect="fail"),
    "clip3_unseen": dict(box=False, path="B", expect="not_proven"),
}
# not in CLIPS, so `--clip all` and ground_truth.json stay as they were; render it with --clip clip1_floormarker
EXTRA_CLIPS = {
    "clip1_floormarker": dict(box=False, path="F", expect="pass", floor_marker=FLOOR_MARKER),
    "clip2_floormarker": dict(box=True, path="F", expect="fail", floor_marker=FLOOR_MARKER),
    # clip3's room and rules: the corridor in front of the exit is never filmed. The marker sits at the back of the room
    # (x 3.0, y 3.0) and the phone tilts down to it from near the north wall, so no floor of the corridor (y 0 to 1.5) is seen.
    "clip3_floormarker": dict(box=False, path="G", expect="not_proven", floor_marker=(4, 3.00, 3.00)),
}


# ---------------------------------------------------------------- texture helpers
def lin(a):
    return np.power(np.clip(a, 0, 1), 2.2).astype(np.float32)


def fbm(h, w, rng, scales, amps):
    out = np.zeros((h, w), np.float32)
    for s, a in zip(scales, amps):
        gh, gw = max(2, int(math.ceil(h / s)) + 1), max(2, int(math.ceil(w / s)) + 1)
        g = rng.standard_normal((gh, gw)).astype(np.float32)
        out += a * cv2.resize(g, (w, h), interpolation=cv2.INTER_CUBIC)
    return out


def plain(rng, w_m, h_m, color, ppm=200, var=0.02):
    w, h = max(8, int(w_m * ppm)), max(8, int(h_m * ppm))
    n = fbm(h, w, rng, [80, 12, 2], [var, var * 0.6, var * 0.5])
    img = np.empty((h, w, 3), np.float32)
    for c in range(3):
        img[..., c] = color[c] + n
    return np.clip(img, 0, 1)


def tex_wall(rng, w_m, h_m, base, ppm=250):
    w, h = int(w_m * ppm), int(h_m * ppm)
    n = fbm(h, w, rng, [240, 60, 12, 3], [0.016, 0.010, 0.007, 0.009])
    img = np.empty((h, w, 3), np.float32)
    for c in range(3):
        img[..., c] = base[c] + n
    bh = int(0.09 * ppm)
    y0 = h - bh
    img[y0:] = np.array([0.93, 0.93, 0.91], np.float32) + n[y0:, :, None] * 0.3
    img[y0 - 2:y0] *= 0.72
    img[y0:y0 + 2] *= 0.86
    img[h - 3:] *= 0.65
    cr = int(0.04 * ppm)                                  # ceiling cove shadow
    img[:cr] *= np.linspace(0.8, 1.0, cr)[:, None, None]
    return np.clip(img, 0, 1)


def tex_floor(rng, w_m, d_m, ppm=250):
    w, h = int(w_m * ppm), int(d_m * ppm)
    pw = int(0.15 * ppm)
    palette = np.array([[0.62, 0.44, 0.27], [0.56, 0.38, 0.22], [0.68, 0.50, 0.32],
                        [0.50, 0.34, 0.20]], np.float32)
    img = np.zeros((h, w, 3), np.float32)
    for j in range(int(math.ceil(h / pw))):
        ya, yb = j * pw, min(h, (j + 1) * pw)
        x = -int(rng.uniform(0, 1.2) * ppm)
        while x < w:
            ln = int(rng.uniform(0.9, 1.8) * ppm)
            xa, xb = max(0, x), min(w, x + ln)
            if xb > xa:
                img[ya:yb, xa:xb] = palette[rng.integers(len(palette))] * rng.uniform(0.92, 1.08)
                img[ya:yb, max(0, xb - 2):xb] *= 0.35
            x += ln
        img[max(0, yb - 2):yb] *= 0.4
    streak = cv2.resize(rng.standard_normal((h, max(2, w // 70))).astype(np.float32), (w, h),
                        interpolation=cv2.INTER_CUBIC)
    fine = cv2.resize(rng.standard_normal((h // 2, w // 10)).astype(np.float32), (w, h),
                      interpolation=cv2.INTER_CUBIC)
    blot = fbm(h, w, rng, [180, 60], [0.04, 0.03])
    img *= (1 + 0.09 * streak + 0.04 * fine + blot)[..., None]
    return np.clip(img, 0, 1)


def tex_ceiling(rng, w_m, d_m):
    return plain(rng, w_m, d_m, (0.93, 0.93, 0.92), ppm=100, var=0.01)


def tex_rug(rng, w_m, d_m, ppm=200):
    w, h = int(w_m * ppm), int(d_m * ppm)
    img = np.zeros((h, w, 3), np.float32)
    img[:] = (0.46, 0.17, 0.15)
    b = int(0.10 * ppm)
    img[b:-b, b:-b] = (0.80, 0.72, 0.58)
    yy, xx = np.mgrid[0:h, 0:w]
    d = (np.abs((xx % 40) - 20) + np.abs((yy % 40) - 20)) < 12
    inner = np.zeros((h, w), bool)
    inner[2 * b:-2 * b, 2 * b:-2 * b] = True
    img[d & inner] = (0.19, 0.28, 0.40)
    img[b - 3:b] = (0.2, 0.2, 0.2)
    fib = cv2.resize(rng.standard_normal((h, w)).astype(np.float32), (w, h))
    img *= (1 + 0.10 * fib)[..., None]
    return np.clip(img, 0, 1)


def tex_door(rng, w_m, h_m, ppm=300):
    img = plain(rng, w_m, h_m, (0.40, 0.44, 0.43), ppm=ppm, var=0.004)
    h, w = img.shape[:2]
    k = int(0.25 * ppm)
    img[h - k:] = img[h - k:] * 0.5 + 0.5 * np.array([0.62, 0.62, 0.60], np.float32)
    img[h - k - 2:h - k] *= 0.5
    for (x0, x1, y0, y1) in [(0.09, 0.77, 0.12, 0.93), (0.09, 0.77, 0.99, 1.88)]:
        a, b = int(x0 * ppm), int(x1 * ppm)
        c, d = int(y0 * ppm), int(y1 * ppm)
        img[c:d, a:b] *= 1.04
        img[c:c + 3, a:b] *= 0.8
        img[c:d, a:a + 3] *= 0.8
        img[d - 3:d, a:b] *= 1.12
        img[c:d, b - 3:b] *= 1.12
    return np.clip(img, 0, 1)


def tex_exit_sign(rng, w_m, h_m, ppm=300):
    w, h = int(w_m * ppm), int(h_m * ppm)
    img = np.zeros((h, w, 3), np.uint8)
    img[:] = (60, 150, 20)
    cv2.rectangle(img, (4, 4), (w - 5, h - 5), (235, 245, 235), 3)
    cv2.putText(img, "EXIT", (int(w * 0.20), int(h * 0.72)), cv2.FONT_HERSHEY_DUPLEX, h / 55.0,
                (255, 255, 255), max(2, h // 22), cv2.LINE_AA)
    return img[..., ::-1].astype(np.float32) / 255


def tex_window(rng, w_m, h_m, ppm=200):
    w, h = int(w_m * ppm), int(h_m * ppm)
    y = np.linspace(0, 1, h)[:, None, None]
    sky = (1 - y) * np.array([0.55, 0.75, 1.0]) + y * np.array([0.90, 0.95, 1.0])
    img = np.broadcast_to(sky, (h, w, 3)).astype(np.float32).copy()
    tree = fbm(h, w, rng, [40, 14], [0.5, 0.35])
    mask = np.clip((tree - 0.2) * 3, 0, 1)[..., None] * np.clip((y - 0.25) * 2.5, 0, 1)
    img = img * (1 - mask) + mask * np.array([0.08, 0.16, 0.06], np.float32)
    img = img * 22.0                                        # HDR sky
    f = int(0.05 * ppm)
    img[:f] = img[-f:] = img[:, :f] = img[:, -f:] = 0.9
    img[h // 2 - 3:h // 2 + 3] = 0.9
    img[:, w // 2 - 3:w // 2 + 3] = 0.9
    return img


def tex_books(rng, w_m, h_m, ppm=300):
    w, h = int(w_m * ppm), int(h_m * ppm)
    img = np.zeros((h, w, 3), np.float32)
    img[:] = (0.34, 0.24, 0.14)
    n_sh = 5
    sh = h // n_sh
    for s in range(n_sh):
        y1 = (s + 1) * sh - 6
        y0 = s * sh + 10
        img[y0:y1, 8:w - 8] = (0.10, 0.08, 0.06)
        x = 12
        while x < w - 20:
            if rng.random() < 0.12:
                x += int(rng.uniform(10, 40))
                continue
            bw = int(rng.uniform(9, 22))
            bhh = int((y1 - y0) * rng.uniform(0.62, 0.95))
            col = np.array(cv2.cvtColor(np.uint8([[[rng.uniform(0, 179), rng.uniform(60, 170),
                                                  rng.uniform(70, 200)]]]), cv2.COLOR_HSV2RGB)[0, 0],
                           np.float32) / 255
            xe = min(w - 12, x + bw)
            img[y1 - bhh:y1, x:xe] = col
            img[y1 - bhh:y1, x:x + 1] *= 0.5
            img[y1 - bhh + 6:y1 - bhh + 9, x:xe] = np.clip(col * 1.4 + 0.15, 0, 1)
            x = xe + 1
        img[y1:y1 + 6] = (0.45, 0.32, 0.18)
    img *= (1 + fbm(h, w, rng, [6, 2], [0.05, 0.04]))[..., None]
    return np.clip(img, 0, 1)


def tex_cardboard(rng, w_m, h_m, ppm=300, text=None, tape=False):
    w, h = int(w_m * ppm), int(h_m * ppm)
    img = plain(rng, w_m, h_m, (0.66, 0.50, 0.32), ppm=ppm, var=0.02)
    x = np.arange(w)[None, :]
    img *= (1 + 0.04 * np.sin(x / 1.8))[..., None]
    if tape:
        c = w // 2
        img[:, c - int(0.025 * ppm):c + int(0.025 * ppm)] = (0.72, 0.58, 0.40)
    if text:
        t = (img * 255).astype(np.uint8)
        cv2.putText(t, text, (int(w * 0.10), int(h * 0.55)), cv2.FONT_HERSHEY_SIMPLEX, w / 520.0,
                    (40, 40, 45), 2, cv2.LINE_AA)
        img = t.astype(np.float32) / 255
    return np.clip(img, 0, 1)


def tex_art(rng, w_m, h_m, ppm=200):
    w, h = int(w_m * ppm), int(h_m * ppm)
    img = plain(rng, w_m, h_m, (0.9, 0.88, 0.82), ppm=ppm, var=0.01)
    cols = [(0.82, 0.33, 0.20), (0.15, 0.35, 0.50), (0.93, 0.76, 0.28), (0.25, 0.45, 0.35)]
    for i in range(7):
        x0, y0 = int(rng.uniform(0.1, 0.6) * w), int(rng.uniform(0.1, 0.6) * h)
        x1, y1 = x0 + int(rng.uniform(0.15, 0.35) * w), y0 + int(rng.uniform(0.15, 0.35) * h)
        img[y0:y1, x0:x1] = cols[i % 4]
    f = int(0.03 * ppm)
    img[:f] = img[-f:] = img[:, :f] = img[:, -f:] = (0.12, 0.10, 0.09)
    return img


def tex_screen(rng, w_m, h_m, ppm=300):
    w, h = int(w_m * ppm), int(h_m * ppm)
    y = np.linspace(0, 1, h)[:, None, None]
    img = np.broadcast_to((1 - y) * np.array([0.10, 0.28, 0.55]) + y * np.array([0.05, 0.10, 0.25]),
                          (h, w, 3)).astype(np.float32).copy()
    for i in range(6):
        r0 = int(h * (0.12 + 0.13 * i))
        img[r0:r0 + 3, int(w * 0.08):int(w * rng.uniform(0.4, 0.9))] = 0.8
    f = int(0.012 * ppm)
    img[:f] = img[-f:] = img[:, :f] = img[:, -f:] = 0.02
    return img


def tex_fabric(rng, w_m, h_m, ppm=200):
    w, h = max(8, int(w_m * ppm)), max(8, int(h_m * ppm))
    x = np.arange(w)[None, :]
    folds = 0.82 + 0.18 * np.sin(x / 5.0 + 1.5 * np.sin(x / 31.0))
    img = np.empty((h, w, 3), np.float32)
    for c, v in enumerate((0.30, 0.45, 0.46)):
        img[..., c] = v * folds
    img *= (1 + fbm(h, w, rng, [30, 3], [0.03, 0.03]))[..., None]
    return np.clip(img, 0, 1)


def tex_paper(rng, w_m, h_m, ppm=300):
    w, h = int(w_m * ppm), int(h_m * ppm)
    img = np.full((h, w, 3), 0.9, np.float32)
    for r in range(int(h / 14)):
        y = 10 + r * 14
        img[y:y + 2, 8:int(w * rng.uniform(0.5, 0.95))] = 0.35
    return img


def tex_calendar(rng, w_m, h_m, ppm=200):
    w, h = int(w_m * ppm), int(h_m * ppm)
    img = np.full((h, w, 3), 0.94, np.float32)
    img[:int(h * 0.38)] = (0.30, 0.45, 0.60)
    for i in range(1, 7):
        img[int(h * 0.38) + int((h * 0.62) * i / 7):][:1] = 0.4
    for j in range(1, 7):
        img[int(h * 0.38):, int(w * j / 7):int(w * j / 7) + 1] = 0.4
    return img


def tex_marker(marker_id, rng):
    m = cv2.aruco.generateImageMarker(cv2.aruco.getPredefinedDictionary(ARUCO_DICT), marker_id, 240)
    pad = np.full((280, 280), 255, np.uint8)
    pad[20:260, 20:260] = m
    a = 0.05 + 0.87 * pad.astype(np.float32) / 255
    a = a[..., None].repeat(3, 2) * np.array([1.0, 0.99, 0.96], np.float32)
    paper = fbm(280, 280, rng, [60, 8], [0.015, 0.012])[..., None]
    return np.clip(a * (1 + paper), 0, 1)


def tex_metal(rng, w_m, h_m, color=(0.7, 0.7, 0.72)):
    return plain(rng, w_m, h_m, color, ppm=200, var=0.03)


# ---------------------------------------------------------------- scene
class Rect:
    def __init__(self, name, O, u, v, tex, kind="wall", ks=0.0, shin=20.0, emis=0.0):
        self.name, self.kind, self.ks, self.shin, self.emis = name, kind, ks, shin, emis
        self.O, self.u, self.v = (np.asarray(a, np.float64) for a in (O, u, v))
        n = np.cross(self.u, self.v)
        self.n = n / np.linalg.norm(n)
        self.uu, self.vv = float(self.u @ self.u), float(self.v @ self.v)
        t = lin(tex)
        self.ppm = t.shape[1] / math.sqrt(self.uu)
        self.mips = [t]
        while min(self.mips[-1].shape[:2]) >= 4 and len(self.mips) < 8:
            self.mips.append(cv2.pyrDown(self.mips[-1]))
        self.corners = np.array([self.O, self.O + self.u, self.O + self.u + self.v, self.O + self.v])


def add_box(rects, name, mn, mx, faces, occ=None, **mat):
    if occ is not None:
        occ.append((np.array(mn, np.float32), np.array(mx, np.float32)))
    x0, y0, z0 = mn
    x1, y1, z1 = mx
    dx, dy, dz = x1 - x0, y1 - y0, z1 - z0
    spec = {
        "front": ((x0, y0, z0), (dx, 0, 0), (0, 0, dz), dx, dz),
        "back": ((x1, y1, z0), (-dx, 0, 0), (0, 0, dz), dx, dz),
        "left": ((x0, y1, z0), (0, -dy, 0), (0, 0, dz), dy, dz),
        "right": ((x1, y0, z0), (0, dy, 0), (0, 0, dz), dy, dz),
        "top": ((x0, y0, z1), (dx, 0, 0), (0, dy, 0), dx, dy),
    }
    for f, (O, u, v, wm, hm) in spec.items():
        src = faces.get(f, faces.get("*"))
        tex = src(wm, hm) if callable(src) else src
        rects.append(Rect(f"{name}.{f}", O, u, v, tex, **mat))


def build_scene(with_box, seed=7, floor_marker=None):
    rng = np.random.default_rng(seed)
    R = []
    OCC = []
    wall = (0.80, 0.76, 0.68)
    R.append(Rect("floor", (0, 0, 0), (W_ROOM, 0, 0), (0, D_ROOM, 0), tex_floor(rng, W_ROOM, D_ROOM),
                  kind="floor", ks=0.10, shin=60))
    R.append(Rect("ceiling", (0, 0, H_ROOM), (0, D_ROOM, 0), (W_ROOM, 0, 0), tex_ceiling(rng, W_ROOM, D_ROOM)))
    R.append(Rect("wall_s", (W_ROOM, 0, 0), (-W_ROOM, 0, 0), (0, 0, H_ROOM), tex_wall(rng, W_ROOM, H_ROOM, wall)))
    R.append(Rect("wall_n", (0, D_ROOM, 0), (W_ROOM, 0, 0), (0, 0, H_ROOM), tex_wall(rng, W_ROOM, H_ROOM, (0.74, 0.77, 0.76))))
    R.append(Rect("wall_w", (0, 0, 0), (0, D_ROOM, 0), (0, 0, H_ROOM), tex_wall(rng, D_ROOM, H_ROOM, wall)))
    R.append(Rect("wall_e", (W_ROOM, D_ROOM, 0), (0, -D_ROOM, 0), (0, 0, H_ROOM), tex_wall(rng, D_ROOM, H_ROOM, wall)))
    R.append(Rect("lamp", (LAMP[0] - 0.25, LAMP[1] - 0.25, H_ROOM - 0.006), (0, 0.5, 0), (0.5, 0, 0),
                  np.full((8, 8, 3), 0.95, np.float32), kind="lamp", emis=6.0))
    R.append(Rect("rug", (1.0, 1.0, 0.008), (1.9, 0, 0), (0, 1.7, 0), tex_rug(rng, 1.9, 1.7), kind="floor", ks=0.0))

    # exit door in the south wall
    white = plain(rng, 0.2, 0.2, (0.90, 0.90, 0.88), ppm=100, var=0.01)
    add_box(R, "arch_l", (JAMB_L - ARCH_W, 0, 0), (JAMB_L, ARCH_D, DOOR_H + ARCH_W), {"*": white}, ks=0.05)
    add_box(R, "arch_r", (JAMB_R, 0, 0), (JAMB_R + ARCH_W, ARCH_D, DOOR_H + ARCH_W), {"*": white}, ks=0.05)
    add_box(R, "arch_t", (JAMB_L, 0, DOOR_H), (JAMB_R, ARCH_D, DOOR_H + ARCH_W), {"*": white}, ks=0.05)
    R.append(Rect("door_leaf", (JAMB_R, 0.012, 0), (-DOOR_CLEAR, 0, 0), (0, 0, DOOR_H),
                  tex_door(rng, DOOR_CLEAR, DOOR_H), kind="door", ks=0.08, shin=30))
    metal = tex_metal(rng, 0.2, 0.2)
    add_box(R, "handle", (JAMB_L + 0.06, 0.012, 0.98), (JAMB_L + 0.20, 0.07, 1.02), {"*": metal}, ks=0.6, shin=80)
    add_box(R, "exit_sign", (DOOR_CX - 0.2, 0, DOOR_H + ARCH_W + 0.06), (DOOR_CX + 0.2, 0.07, DOOR_H + ARCH_W + 0.26),
            {"*": plain(rng, 0.1, 0.1, (0.2, 0.2, 0.2), ppm=100), "back": tex_exit_sign(rng, 0.4, 0.2)}, ks=0.0)
    for r in R[-6:]:
        if r.name == "exit_sign.back":
            r.emis = 1.6
    # markers on the south wall / door leaf (centre x, centre z); image right = -x, up = +z
    for mid, (cx, cz, tilt) in MARKERS.items():
        y = 0.016 if mid == 1 else 0.004
        a = math.radians(tilt)
        # image right is -x and up is +z, rotated in the wall plane by the small tilt
        ur = np.array([-math.cos(a), 0, -math.sin(a)])
        up = np.array([math.sin(a), 0, math.cos(a)])
        c = np.array([cx, y, cz])
        O = c - ur * PAPER_M / 2 - up * PAPER_M / 2
        R.append(Rect(f"marker_{mid}", O, ur * PAPER_M, up * PAPER_M, tex_marker(mid, rng), kind="marker", ks=0.03))
    if floor_marker:
        mid, cx, cy = floor_marker
        ur, up = np.array([1.0, 0, 0]), np.array([0, 1.0, 0])   # seen from above: right = +x, top = +y, normal = +z
        O = np.array([cx, cy, 0.004]) - ur * PAPER_M / 2 - up * PAPER_M / 2
        R.append(Rect(f"marker_{mid}", O, ur * PAPER_M, up * PAPER_M, tex_marker(mid, rng), kind="marker", ks=0.03))
    # extinguisher
    add_box(R, "extinguisher", (2.50, 0.0, 0.80), (2.63, 0.13, 1.28),
            {"*": plain(rng, 0.1, 0.4, (0.72, 0.08, 0.06), ppm=150)}, occ=OCC, ks=0.4, shin=50)
    # window, east wall
    R.append(Rect("window", (W_ROOM - 0.004, 2.5, 0.95), (0, -1.4, 0), (0, 0, 1.2), tex_window(rng, 1.4, 1.2),
                  kind="window", emis=1.0))
    # desk, monitor, chair on the west wall
    wood = lambda w, h: plain(rng, w, h, (0.72, 0.62, 0.48), ppm=200, var=0.03)
    dark = plain(rng, 0.2, 0.2, (0.06, 0.06, 0.07), ppm=100, var=0.01)
    add_box(R, "desk_top", (0.0, 0.9, 0.72), (0.65, 2.3, 0.75), {"*": wood}, occ=OCC, ks=0.12, shin=40)
    for i, (lx, ly) in enumerate([(0.03, 0.93), (0.60, 0.93), (0.03, 2.24), (0.60, 2.24)]):
        add_box(R, f"desk_leg{i}", (lx, ly, 0.0), (lx + 0.04, ly + 0.04, 0.72), {"*": dark}, ks=0.2)
    add_box(R, "monitor", (0.15, 1.35, 0.95), (0.19, 1.85, 1.25),
            {"*": dark, "right": tex_screen(rng, 0.5, 0.3)}, occ=OCC, ks=0.1)
    for r in R[-5:]:
        if r.name == "monitor.right":
            r.emis = 1.3
    add_box(R, "monitor_stand", (0.12, 1.57, 0.75), (0.20, 1.63, 0.95), {"*": dark})
    add_box(R, "keyboard", (0.30, 1.40, 0.75), (0.50, 1.80, 0.765), {"*": dark}, ks=0.15)
    add_box(R, "chair_seat", (0.78, 1.35, 0.44), (1.22, 1.80, 0.48),
            {"*": plain(rng, 0.2, 0.2, (0.18, 0.20, 0.24), ppm=100, var=0.02)}, occ=OCC)
    add_box(R, "chair_back", (1.18, 1.35, 0.48), (1.22, 1.80, 0.95),
            {"*": plain(rng, 0.2, 0.2, (0.18, 0.20, 0.24), ppm=100, var=0.02)}, occ=OCC)
    add_box(R, "chair_post", (0.98, 1.56, 0.10), (1.02, 1.60, 0.44), {"*": dark}, ks=0.3)
    add_box(R, "chair_base_a", (0.80, 1.55, 0.06), (1.20, 1.61, 0.10), {"*": dark})
    add_box(R, "chair_base_b", (0.97, 1.37, 0.06), (1.03, 1.78, 0.10), {"*": dark})
    # bookshelf on the north wall
    add_box(R, "shelf", (0.60, 3.30, 0.0), (1.70, 3.60, 1.90),
            {"*": plain(rng, 0.5, 0.5, (0.34, 0.24, 0.14), ppm=100, var=0.02), "front": tex_books(rng, 1.1, 1.9)},
            occ=OCC, ks=0.05)
    # pictures
    R.append(Rect("picture_n", (2.3, D_ROOM - 0.012, 1.15), (0.9, 0, 0), (0, 0, 0.6), tex_art(rng, 0.9, 0.6)))
    R.append(Rect("picture_w", (0.012, 1.0, 1.50), (0, 0.5, 0), (0, 0, 0.7), tex_art(rng, 0.5, 0.7)))
    # side table in line with the exit
    add_box(R, "side_table", SIDE_TABLE[:3], SIDE_TABLE[3:],
            {"*": plain(rng, 0.5, 0.55, (0.28, 0.18, 0.11), ppm=200, var=0.03)}, occ=OCC, ks=0.12, shin=40)
    foot = [(0.0, 0.65, 0.9, 2.3), (0.78, 1.22, 1.35, 1.80), (0.60, 1.70, 3.30, 3.60),
            (SIDE_TABLE[0], SIDE_TABLE[3], SIDE_TABLE[1], SIDE_TABLE[4]), (2.50, 2.63, 0.0, 0.13)]

    # ---- detail that adds parallax and clutter (kept clear of the exit corridor)
    bb = plain(rng, 0.2, 0.1, (0.93, 0.93, 0.91), ppm=100, var=0.008)
    for nm, a, b in [("bb_s1", (0, 0, 0), (JAMB_L - ARCH_W, 0.012, 0.09)),
                     ("bb_s2", (JAMB_R + ARCH_W, 0, 0), (W_ROOM, 0.012, 0.09)),
                     ("bb_n", (0, D_ROOM - 0.012, 0), (W_ROOM, D_ROOM, 0.09)),
                     ("bb_w", (0, 0, 0), (0.012, D_ROOM, 0.09)),
                     ("bb_e", (W_ROOM - 0.012, 0, 0), (W_ROOM, D_ROOM, 0.09))]:
        add_box(R, nm, a, b, {"*": bb}, ks=0.15, shin=30)
    fabric = lambda w, h: tex_fabric(rng, w, h)
    add_box(R, "curtain_a", (W_ROOM - 0.11, 0.72, 0.15), (W_ROOM - 0.02, 1.10, 2.38), {"*": fabric})
    add_box(R, "curtain_b", (W_ROOM - 0.11, 2.50, 0.15), (W_ROOM - 0.02, 2.88, 2.38), {"*": fabric})
    add_box(R, "curtain_rod", (W_ROOM - 0.12, 0.65, 2.40), (W_ROOM - 0.08, 2.95, 2.44), {"*": metal}, ks=0.5, shin=60)
    add_box(R, "hinge_a", (JAMB_R - 0.012, 0.010, 0.25), (JAMB_R, 0.030, 0.35), {"*": metal}, ks=0.5, shin=60)
    add_box(R, "hinge_b", (JAMB_R - 0.012, 0.010, 1.00), (JAMB_R, 0.030, 1.10), {"*": metal}, ks=0.5, shin=60)
    add_box(R, "hinge_c", (JAMB_R - 0.012, 0.010, 1.75), (JAMB_R, 0.030, 1.85), {"*": metal}, ks=0.5, shin=60)
    add_box(R, "threshold", (JAMB_L, 0, 0), (JAMB_R, 0.06, 0.012), {"*": metal}, ks=0.4, shin=50)
    add_box(R, "laptop", (0.15, 0.97, 0.75), (0.45, 1.26, 0.768), {"*": metal}, occ=OCC, ks=0.35, shin=60)
    add_box(R, "papers", (0.10, 2.02, 0.75), (0.32, 2.22, 0.760),
            {"*": plain(rng, 0.2, 0.2, (0.9, 0.9, 0.88), ppm=100), "top": lambda w, h: tex_paper(rng, w, h)})
    add_box(R, "backpack", (0.10, 0.30, 0.0), (0.42, 0.58, 0.44),
            {"*": plain(rng, 0.3, 0.4, (0.10, 0.14, 0.24), ppm=150, var=0.03)}, occ=OCC)
    add_box(R, "bin", (0.08, 2.45, 0.0), (0.30, 2.68, 0.30),
            {"*": plain(rng, 0.2, 0.3, (0.20, 0.20, 0.21), ppm=100, var=0.02)}, occ=OCC, ks=0.2)
    foot += [(0.10, 0.42, 0.30, 0.58), (0.08, 0.30, 2.45, 2.68)]
    plate = lambda: plain(rng, 0.08, 0.08, (0.93, 0.93, 0.92), ppm=300, var=0.006)
    R.append(Rect("switch", (2.99, 0.004, 1.16), (-0.08, 0, 0), (0, 0, 0.08), plate(), ks=0.3))
    R.append(Rect("socket", (1.34, 0.004, 0.26), (-0.08, 0, 0), (0, 0, 0.08), plate(), ks=0.3))
    R.append(Rect("calendar", (3.55, D_ROOM - 0.010, 1.20), (0.35, 0, 0), (0, 0, 0.50), tex_calendar(rng, 0.35, 0.50)))
    if with_box:
        b = BLOCK_BOX
        add_box(R, "cardboard_box", b[:3], b[3:],
                {"*": lambda w, h: tex_cardboard(rng, w, h),
                 "front": lambda w, h: tex_cardboard(rng, w, h, text="THIS SIDE UP", tape=False),
                 "top": lambda w, h: tex_cardboard(rng, w, h, tape=True)}, occ=OCC, ks=0.02)
        foot.append((b[0], b[3], b[1], b[4]))
    return R, foot, OCC


# ---------------------------------------------------------------- camera
def look_rotation(pos, look):
    f = look - pos
    f = f / np.linalg.norm(f)
    right = np.cross(f, [0, 0, 1.0])
    right /= np.linalg.norm(right)
    down = np.cross(f, right)
    return np.stack([right, down, f], 1)


class Path:
    HZ = 200

    def __init__(self, wps, T, seed):
        rng = np.random.default_rng(seed)
        hz = self.HZ
        self.T = T
        ts = np.arange(0, T + 0.5, 1 / hz)
        wt = [w[0] for w in wps]
        pos = np.stack([np.interp(ts, wt, [w[1][i] for w in wps]) for i in range(3)], 1)
        look = np.stack([np.interp(ts, wt, [w[2][i] for w in wps]) for i in range(3)], 1)

        def smooth(a, sec):
            sg = int(sec * hz)
            k = np.exp(-0.5 * (np.arange(-3 * sg, 3 * sg + 1) / sg) ** 2)
            k /= k.sum()
            pad = np.pad(a, ((3 * sg, 3 * sg), (0, 0)), mode="edge")
            return np.stack([np.convolve(pad[:, i], k, mode="valid") for i in range(a.shape[1])], 1)

        self.pos = smooth(pos, 0.7)
        self.look = smooth(look, 0.55)
        speed = np.linalg.norm(np.gradient(self.pos, 1 / hz, axis=0), axis=1)
        sp = np.clip(speed / 0.25, 0, 1)
        sh = smooth(rng.standard_normal((len(ts), 6)), 0.10)
        sh /= sh.std(0)
        amp = np.array([0.004, 0.004, 0.003, 0.0075, 0.0075, 0.004])
        self.shake = sh * amp
        bob = np.sin(2 * math.pi * 1.7 * ts + 0.6) * sp
        self.pos[:, 2] += 0.010 * bob
        self.shake[:, 3] += 0.0035 * bob
        self.ts = ts

    def at(self, t):
        t = float(np.clip(t, 0, self.T))
        pos = np.array([np.interp(t, self.ts, self.pos[:, i]) for i in range(3)])
        look = np.array([np.interp(t, self.ts, self.look[:, i]) for i in range(3)])
        sh = np.array([np.interp(t, self.ts, self.shake[:, i]) for i in range(6)])
        pos = pos + sh[:3]
        R0 = look_rotation(pos, look)
        Rc = cv2.Rodrigues(np.array([sh[3], sh[4], sh[5]]))[0]
        return pos, R0 @ Rc


PATH_A = [  # clip1 / clip2: start on the door, sweep the room, end on the exit and the floor in front of it
    (0.0, (3.15, 2.25, 1.45), (3.70, 0.0, 1.20)),
    (2.5, (3.00, 2.30, 1.45), (3.70, 0.0, 1.15)),
    (5.0, (2.50, 2.20, 1.45), (0.00, 1.8, 1.30)),
    (8.0, (1.90, 2.80, 1.45), (0.30, 3.6, 1.30)),
    (11.0, (2.20, 2.70, 1.45), (2.80, 3.6, 1.45)),
    (13.0, (2.80, 2.70, 1.45), (4.60, 3.3, 1.35)),
    (15.0, (3.00, 2.95, 1.45), (4.60, 1.8, 1.30)),
    (17.0, (3.00, 2.00, 1.45), (3.70, 0.0, 0.90)),
    (19.0, (3.00, 1.55, 1.45), (3.70, 0.2, 0.30)),
    (20.6, (3.10, 1.70, 1.45), (3.70, 0.0, 1.20)),
    (21.2, (3.10, 1.70, 1.45), (3.70, 0.0, 1.20)),
]
PATH_F = [  # clip1_floormarker: PATH_A, but at 17 to 19 s the phone tilts down to the marker on the floor
    (0.0, (3.15, 2.25, 1.45), (3.70, 0.0, 1.20)),
    (2.5, (3.00, 2.30, 1.45), (3.70, 0.0, 1.15)),
    (5.0, (2.50, 2.20, 1.45), (0.00, 1.8, 1.30)),
    (8.0, (1.90, 2.80, 1.45), (0.30, 3.6, 1.30)),
    (11.0, (2.20, 2.70, 1.45), (2.80, 3.6, 1.45)),
    (13.0, (2.80, 2.70, 1.45), (4.60, 3.3, 1.35)),
    (15.0, (3.00, 2.95, 1.45), (4.60, 1.8, 1.30)),
    (17.0, (3.00, 2.00, 1.45), (FLOOR_MARKER[1], FLOOR_MARKER[2] + 0.6, 0.0)),
    (19.0, (3.00, 1.55, 1.45), (FLOOR_MARKER[1], FLOOR_MARKER[2], 0.0)),
    (20.0, (3.05, 1.65, 1.45), (3.70, 0.0, 0.60)),
    (20.6, (3.10, 1.70, 1.45), (3.70, 0.0, 1.20)),
    (21.2, (3.10, 1.70, 1.45), (3.70, 0.0, 1.20)),
]
PATH_G = [  # clip3_floormarker: PATH_B, then the phone turns west at level gaze (looking past the north wall, never south),
            # tilts down to the floor marker at the back of the room, levels out, and turns back to the door
    (0.0, (3.10, 2.90, 1.45), (3.70, 0.0, 1.45)),
    (2.5, (3.00, 2.95, 1.45), (3.70, 0.0, 1.50)),
    (5.0, (2.60, 2.90, 1.45), (0.00, 1.8, 1.40)),
    (8.0, (1.90, 2.80, 1.45), (0.30, 3.6, 1.40)),
    (10.5, (2.30, 2.75, 1.45), (2.80, 3.6, 1.50)),
    (12.5, (2.90, 2.80, 1.45), (4.60, 3.3, 1.40)),
    (13.8, (3.40, 3.15, 1.45), (3.40, 3.6, 1.45)),
    (15.0, (3.50, 3.20, 1.45), (2.20, 3.20, 1.45)),
    (16.6, (3.70, 3.25, 1.45), (2.20, 3.20, 1.45)),
    (18.0, (4.20, 3.25, 1.45), (3.00, 3.00, 0.0)),
    (19.8, (4.20, 3.25, 1.45), (3.00, 3.00, 0.0)),
    (21.0, (3.70, 3.25, 1.45), (2.20, 3.20, 1.45)),
    (22.6, (2.80, 2.90, 1.45), (3.70, 0.0, 1.55)),
    (24.0, (2.80, 2.90, 1.45), (3.70, 0.0, 1.55)),
]
PATH_B = [  # clip3: stays at the back of the room, level gaze, so the floor in front of the exit is never filmed
    (0.0, (3.10, 2.90, 1.45), (3.70, 0.0, 1.45)),
    (2.5, (3.00, 2.95, 1.45), (3.70, 0.0, 1.50)),
    (5.0, (2.60, 2.90, 1.45), (0.00, 1.8, 1.40)),
    (8.0, (1.90, 2.80, 1.45), (0.30, 3.6, 1.40)),
    (10.5, (2.30, 2.75, 1.45), (2.80, 3.6, 1.50)),
    (12.5, (2.90, 2.80, 1.45), (4.60, 3.3, 1.40)),
    (14.5, (3.00, 3.00, 1.45), (4.60, 1.8, 1.40)),
    (16.5, (2.80, 2.90, 1.45), (3.70, 0.0, 1.55)),
    (18.0, (2.80, 2.90, 1.45), (3.70, 0.0, 1.55)),
]


class Camera:
    def __init__(self, W, H, hfov_deg=66.0, dist=(-0.045, 0.010, 0.0, 0.0, 0.0)):
        self.W, self.H = W, H
        self.f = (W / 2) / math.tan(math.radians(hfov_deg / 2))
        self.K = np.array([[self.f, 0, W / 2], [0, self.f, H / 2], [0, 0, 1]], np.float64)
        self.dist = np.array(dist, np.float64)
        px = np.stack(np.meshgrid(np.arange(W) + 0.5, np.arange(H) + 0.5), -1).reshape(-1, 1, 2).astype(np.float64)
        n = cv2.undistortPoints(px, self.K, self.dist).reshape(H, W, 2).astype(np.float32)
        self.rays = np.dstack([n, np.ones((H, W), np.float32)])
        self.rnorm = np.linalg.norm(self.rays, axis=2)

    def project(self, pts_cam):
        p, _ = cv2.projectPoints(pts_cam.reshape(-1, 1, 3), np.zeros(3), np.zeros(3), self.K, self.dist)
        return p.reshape(-1, 2)


# ---------------------------------------------------------------- rendering
def sample_tex(r, s, v, lod):
    """Bilinear lookup in the mip chain of r at texture coords (s, v), per-pixel level lod."""
    h0, w0 = r.mips[0].shape[:2]
    tx = (s * w0 - 0.5).astype(np.float32)
    ty = ((1 - v) * h0 - 0.5).astype(np.float32)
    lf = np.floor(lod).astype(np.int32)
    fr = (lod - lf).astype(np.float32)[..., None]
    out = np.zeros(s.shape + (3,), np.float32)
    for l in np.unique(lf):
        m = lf == l
        a, b = int(l), min(int(l) + 1, len(r.mips) - 1)
        samples = []
        for lv in (a, b):
            sc = 2.0 ** -lv
            samples.append(cv2.remap(r.mips[lv], (tx + 0.5) * sc - 0.5, (ty + 0.5) * sc - 0.5,
                                     cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE))
        mix = samples[0] * (1 - fr) + samples[1] * fr
        out[m] = mix[m]
    return out


def raycast(cam, rects, C, R):
    H, W = cam.H, cam.W
    D = cam.rays @ R.T.astype(np.float32)           # world directions with unit camera-z
    zb = np.full((H, W), np.inf, np.float32)
    alb = np.zeros((H, W, 3), np.float32)
    pos = np.zeros((H, W, 3), np.float32)
    nrm = np.zeros((H, W, 3), np.float32)
    rid = np.full((H, W), -1, np.int16)
    Cf = C.astype(np.float32)
    for i, r in enumerate(rects):
        if r.n @ (C - r.O) <= 1e-6:
            continue
        pc = (r.corners - C) @ R                     # corners in camera frame
        if np.all(pc[:, 2] <= 0.02):
            continue
        if np.any(pc[:, 2] <= 0.02):
            x0, x1, y0, y1 = 0, W, 0, H
        else:
            px = cam.project(pc)
            x0, x1 = int(max(0, math.floor(px[:, 0].min()) - 3)), int(min(W, math.ceil(px[:, 0].max()) + 4))
            y0, y1 = int(max(0, math.floor(px[:, 1].min()) - 3)), int(min(H, math.ceil(px[:, 1].max()) + 4))
            if x1 <= x0 or y1 <= y0:
                continue
        Dr = D[y0:y1, x0:x1]
        den = Dr @ r.n.astype(np.float32)
        num = float((r.O - C) @ r.n)
        with np.errstate(divide="ignore", invalid="ignore"):
            t = (num / den).astype(np.float32)
        zsub = zb[y0:y1, x0:x1]
        ok = (t > 0.05) & (t < zsub)
        if not ok.any():
            continue
        P = Cf + t[..., None] * Dr
        d = P - r.O.astype(np.float32)
        s = (d @ r.u.astype(np.float32)) / r.uu
        v = (d @ r.v.astype(np.float32)) / r.vv
        ok &= (s >= 0) & (s <= 1) & (v >= 0) & (v <= 1)
        if not ok.any():
            continue
        cosang = np.abs(den) / cam.rnorm[y0:y1, x0:x1]
        foot = t * (r.ppm / cam.f) / np.maximum(cosang, 0.12)
        lod = np.clip(np.log2(np.maximum(foot, 1e-6)), 0, len(r.mips) - 1.001).astype(np.float32)
        col = sample_tex(r, np.clip(s, 0, 1), np.clip(v, 0, 1), lod)
        zsub[ok] = t[ok]
        alb[y0:y1, x0:x1][ok] = col[ok]
        pos[y0:y1, x0:x1][ok] = P[ok]
        nrm[y0:y1, x0:x1][ok] = r.n
        rid[y0:y1, x0:x1][ok] = i
    return zb, alb, pos, nrm, rid


WIN_PTS = np.array([[W_ROOM - 0.2, y, z] for y in (1.4, 2.2) for z in (1.3, 1.9)], np.float32)


def shadow_factor(pos, nrm, light_pts, occ, full_shape):
    """Fraction of the light points visible from each pixel (computed at half resolution)."""
    H, W = full_shape
    p = pos[::2, ::2].reshape(-1, 3)
    o = p + nrm[::2, ::2].reshape(-1, 3) * 0.012
    vis = np.zeros(len(p), np.float32)
    for lp in light_pts:
        d = lp - o
        dist = np.sqrt((d * d).sum(1))
        d /= dist[:, None] + 1e-9
        inv = 1.0 / np.where(np.abs(d) < 1e-6, 1e-6, d)
        blocked = np.zeros(len(p), bool)
        for mn, mx in occ:
            t1, t2 = (mn - o) * inv, (mx - o) * inv
            tmin = np.minimum(t1, t2).max(1)
            tmax = np.maximum(t1, t2).min(1)
            blocked |= (tmax > np.maximum(tmin, 0)) & (tmin < dist)
        vis += ~blocked
    vis = (vis / len(light_pts)).reshape(pos[::2, ::2].shape[:2])
    vis = cv2.resize(vis, (W, H), interpolation=cv2.INTER_LINEAR)
    return cv2.GaussianBlur(vis, (0, 0), 1.5)


def shadow_factor_dir(pos, nrm, ldir, occ, full_shape):
    far = [np.array([W_ROOM, 2.0, 1.5], np.float32) + ldir * 30.0 + j for j in
           (np.array([0, 0.5, 0.5], np.float32), np.array([0, -0.5, -0.5], np.float32))]
    return shadow_factor(pos, nrm, far, occ, full_shape)


SUN_L = np.array([0.55, 0.15, 0.80], np.float32)
SUN_L /= np.linalg.norm(SUN_L)
WIN = dict(y0=1.1, y1=2.5, z0=0.95, z1=2.15)


def sun_patch(pos, nrm):
    """Where sunlight coming through the east window lands (mullions and frame cast their shadow)."""
    t = (W_ROOM - pos[..., 0]) / SUN_L[0]
    qy = pos[..., 1] + SUN_L[1] * t
    qz = pos[..., 2] + SUN_L[2] * t
    m = (qy > WIN["y0"] + 0.05) & (qy < WIN["y1"] - 0.05) & (qz > WIN["z0"] + 0.05) & (qz < WIN["z1"] - 0.05)
    m &= (np.abs(qy - 1.8) > 0.03) & (np.abs(qz - 1.55) > 0.03)
    m &= pos[..., 0] < W_ROOM - 0.05
    return cv2.GaussianBlur(m.astype(np.float32), (0, 0), 3.0) * np.clip((nrm * SUN_L).sum(2), 0, 1)


def shade(rects, foot, occ, C, alb, pos, nrm, rid):
    Cf = C.astype(np.float32)
    H, W = rid.shape
    mats = np.array([[r.ks, r.shin, r.emis] for r in rects] + [[0, 1, 0]], np.float32)
    kinds = np.array([r.kind for r in rects] + ["none"])
    m = mats[rid]                                    # rid -1 maps to the last (dummy) row
    ks, shin, emis = m[..., 0], m[..., 1], m[..., 2]
    V = Cf - pos
    V /= np.maximum(np.linalg.norm(V, axis=2, keepdims=True), 1e-6)
    amb = np.array([0.10, 0.108, 0.12], np.float32) * (0.75 + 0.25 * nrm[..., 2:3])
    E = np.broadcast_to(amb, alb.shape).copy()
    spec = np.zeros(rid.shape, np.float32)
    lights = [(LAMP, np.array([1.0, 0.90, 0.78], np.float32), 14.0)] + \
             [(p, np.array([0.80, 0.90, 1.0], np.float32), 3.2) for p in WIN_PTS]
    lamp_pts = [LAMP + np.array([dx, dy, 0], np.float32) for dx in (-0.2, 0.2) for dy in (-0.2, 0.2)]
    vis_lamp = shadow_factor(pos, nrm, lamp_pts, occ, rid.shape)
    for li, (lp, lc, inten) in enumerate(lights):
        L = lp - pos
        d2 = (L * L).sum(2)
        L /= np.sqrt(d2)[..., None] + 1e-6
        nl = np.clip((nrm * L).sum(2), 0, 1)
        att = inten / (d2 + 0.8)
        if li == 0:
            att = att * vis_lamp
        E += (nl * att)[..., None] * lc
        h = L + V
        h /= np.maximum(np.linalg.norm(h, axis=2, keepdims=True), 1e-6)
        nh = np.clip((nrm * h).sum(2), 0, 1)
        spec += ks * (nh ** shin) * att * nl * 0.5
    sun = sun_patch(pos, nrm)
    if sun.max() > 0.01:
        sv = shadow_factor_dir(pos, nrm, SUN_L, occ, rid.shape)
        E += (sun * sv * 5.0)[..., None] * np.array([1.0, 0.92, 0.78], np.float32)
    # soft occlusion: room corners and contact shadows under furniture
    planes = np.stack([pos[..., 0], W_ROOM - pos[..., 0], pos[..., 1], D_ROOM - pos[..., 1],
                       pos[..., 2], H_ROOM - pos[..., 2]], 0)
    planes = np.where(planes < 0.02, np.inf, planes)
    dmin = planes.min(0)
    ao = 1 - 0.45 * np.exp(-np.minimum(dmin, 5) / 0.30)
    fl = kinds[rid] == "floor"
    if fl.any():
        px, py = pos[..., 0][fl], pos[..., 1][fl]
        occ = np.ones(px.shape, np.float32)
        for (x0, x1, y0, y1) in foot:
            dd = np.hypot(np.maximum(np.maximum(x0 - px, px - x1), 0), np.maximum(np.maximum(y0 - py, py - y1), 0))
            occ *= 1 - 0.55 * np.exp(-dd / 0.15)
        ao[fl] *= occ
    col = alb * E * ao[..., None] + spec[..., None]
    em = emis > 0
    col[em] = alb[em] * emis[em][..., None]
    return col


class Post:
    def __init__(self, seed):
        self.rng = np.random.default_rng(seed)
        self.exp = None

    def run(self, hdr, cam, R_now, R_others, dt_shutter):
        H, W = hdr.shape[:2]
        # exposure: keep mid grey, with lag, and let the bright window push the exposure down
        lum = hdr @ np.array([0.2126, 0.7152, 0.0722], np.float32)
        target = 0.20 / (math.exp(np.log(np.clip(lum, 1e-4, 8)).mean()) + 1e-4)
        self.exp = target if self.exp is None else self.exp + 0.12 * (target - self.exp)
        x = hdr * self.exp
        # bloom
        bright = np.clip(x - 0.9, 0, None)
        bl = cv2.GaussianBlur(bright, (0, 0), 6) * 0.5 + cv2.GaussianBlur(bright, (0, 0), 22) * 0.6
        x = x + bl
        # filmic curve then sRGB
        a, b, c, d, e = 2.51, 0.03, 2.43, 0.59, 0.14
        x = np.clip((x * (a * x + b)) / (x * (c * x + d) + e), 0, 1)
        x = np.power(x, 1 / 2.2)
        x *= np.array([0.99, 1.0, 1.02], np.float32)[None, None]   # slightly warm (BGR order applied later)
        # rotation blur from the hand-held motion during the shutter
        K = cam.K
        acc = np.zeros_like(x)
        for Rt in R_others:
            Hm = K @ (Rt.T @ R_now) @ np.linalg.inv(K)
            acc += cv2.warpPerspective(x, Hm, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        x = acc / len(R_others)
        x = cv2.GaussianBlur(x, (0, 0), 0.55)
        x = np.clip(x + 0.5 * (x - cv2.GaussianBlur(x, (0, 0), 1.2)), 0, 1)          # phone sharpening
        # lateral chromatic aberration: red and blue magnified by a hair
        cx, cy = W / 2, H / 2
        gy, gx = np.mgrid[0:H, 0:W].astype(np.float32)
        for ch, sc in ((0, 1.0007), (2, 0.9993)):
            mx_ = (gx - cx) / sc + cx
            my_ = (gy - cy) / sc + cy
            x[..., ch] = cv2.remap(x[..., ch].copy(), mx_, my_, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        # vignette
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r2 = ((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (W / 2)) ** 2
        x *= (1 - 0.22 * r2)[..., None]
        # sensor noise: shot + read, a little chroma noise
        sig = 0.006 + 0.020 * np.sqrt(np.clip(x, 0, 1)) * (1.0 / (1.0 + 4 * self.exp))
        n = self.rng.standard_normal(x.shape).astype(np.float32)
        ln = self.rng.standard_normal(x.shape[:2]).astype(np.float32)[..., None]
        x = x + sig * (0.7 * n + 0.7 * ln)
        return (np.clip(x, 0, 1)[..., ::-1] * 255 + 0.5).astype(np.uint8)   # RGB -> BGR


# ---------------------------------------------------------------- truth export
def mat_to_quat_wxyz(R):
    t = np.trace(R)
    if t > 0:
        s = math.sqrt(t + 1) * 2
        q = [0.25 * s, (R[2, 1] - R[1, 2]) / s, (R[0, 2] - R[2, 0]) / s, (R[1, 0] - R[0, 1]) / s]
    elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
        s = math.sqrt(1 + R[0, 0] - R[1, 1] - R[2, 2]) * 2
        q = [(R[2, 1] - R[1, 2]) / s, 0.25 * s, (R[0, 1] + R[1, 0]) / s, (R[0, 2] + R[2, 0]) / s]
    elif R[1, 1] > R[2, 2]:
        s = math.sqrt(1 + R[1, 1] - R[0, 0] - R[2, 2]) * 2
        q = [(R[0, 2] - R[2, 0]) / s, (R[0, 1] + R[1, 0]) / s, 0.25 * s, (R[1, 2] + R[2, 1]) / s]
    else:
        s = math.sqrt(1 + R[2, 2] - R[0, 0] - R[1, 1]) * 2
        q = [(R[1, 0] - R[0, 1]) / s, (R[0, 2] + R[2, 0]) / s, (R[1, 2] + R[2, 1]) / s, 0.25 * s]
    q = np.array(q) / np.linalg.norm(q)
    return [round(float(v), 6) for v in q]


def marker_truth(floor_marker=None):
    out = {}
    for mid, (cx, cz, tilt) in MARKERS.items():
        a = math.radians(tilt)
        ur = np.array([-math.cos(a), 0, -math.sin(a)])
        up = np.array([math.sin(a), 0, math.cos(a)])
        n = np.cross(ur, up)
        Rm = np.stack([ur, up, n], 1)
        y = 0.016 if mid == 1 else 0.004
        out[str(mid)] = {"position": [round(cx, 4), y, round(cz, 4)], "rotation_wxyz": mat_to_quat_wxyz(Rm)}
    if floor_marker:
        mid, cx, cy = floor_marker
        Rm = np.stack([[1.0, 0, 0], [0, 1.0, 0], [0, 0, 1.0]], 1)
        out[str(mid)] = {"position": [cx, cy, 0.004], "rotation_wxyz": mat_to_quat_wxyz(Rm)}
    return out


def build_points(rects, seen_cells, with_box, step=0.05):
    pts = []
    cell = 0.1
    for gx in range(seen_cells.shape[0]):
        for gy in range(seen_cells.shape[1]):
            if not seen_cells[gx, gy]:
                continue
            for dx in np.arange(cell / 4, cell, cell / 2):
                for dy in np.arange(cell / 4, cell, cell / 2):
                    x, y = gx * cell + dx, gy * cell + dy
                    if any(f[0] <= x <= f[1] and f[2] <= y <= f[3] for f in
                           [(0.0, 0.65, 0.9, 2.3), (0.78, 1.22, 1.35, 1.8), (0.6, 1.7, 3.3, 3.6),
                            (SIDE_TABLE[0], SIDE_TABLE[3], SIDE_TABLE[1], SIDE_TABLE[4])] + (
                               [(BLOCK_BOX[0], BLOCK_BOX[3], BLOCK_BOX[1], BLOCK_BOX[4])] if with_box else [])):
                        continue
                    pts.append([round(float(x), 3), round(float(y), 3), 0.0])
    boxes = [("side_table", SIDE_TABLE)] + ([("cardboard_box", BLOCK_BOX)] if with_box else [])
    for _, b in boxes:
        x0, y0, z0, x1, y1, z1 = b
        for x in np.arange(x0, x1 + 1e-6, step):
            for z in np.arange(0.02, z1 + 1e-6, step):
                for y in (y0, y1):
                    pts.append([round(float(x), 3), round(float(y), 3), round(float(z), 3)])
        for y in np.arange(y0, y1 + 1e-6, step):
            for z in np.arange(0.02, z1 + 1e-6, step):
                for x in (x0, x1):
                    pts.append([round(float(x), 3), round(float(y), 3), round(float(z), 3)])
        for x in np.arange(x0, x1 + 1e-6, step):
            for y in np.arange(y0, y1 + 1e-6, step):
                pts.append([round(float(x), 3), round(float(y), 3), round(float(z1), 3)])
    return pts


# ---------------------------------------------------------------- main per-clip job
def render_clip(job):
    name, out_root, W, H, fps, limit, stills = job
    cfg = CLIPS.get(name) or EXTRA_CLIPS[name]
    out = os.path.join(out_root, name)
    os.makedirs(out, exist_ok=True)
    rects, foot, occ = build_scene(cfg["box"], floor_marker=cfg.get("floor_marker"))
    cam = Camera(W, H)
    wps = {"A": PATH_A, "B": PATH_B, "F": PATH_F, "G": PATH_G}[cfg["path"]]
    T = wps[-1][0] if cfg["path"] in ("B", "G") else 21.0
    path = Path(wps, T, seed=12 if cfg["path"] in ("B", "G") else 11)
    nfr = int(T * fps)
    if limit:
        nfr = min(nfr, limit)
    post = Post(seed=3)
    vpath = os.path.join(out, f"{name}.mp4")
    vw = None if stills else cv2.VideoWriter(vpath, cv2.VideoWriter_fourcc(*"mp4v"), fps, (W, H))
    cells_seen = np.zeros((int(W_ROOM / 0.1) + 1, int(D_ROOM / 0.1) + 1), bool)
    corridor_px = 0
    poses = []
    t0 = time.time()
    stills_set = set(stills or [])
    frames_to_do = sorted(stills_set) if stills else range(nfr)
    for i in frames_to_do:
        t = i / fps
        C, R = path.at(t)
        zb, alb, pos, nrm, rid = raycast(cam, rects, C, R)
        hdr = shade(rects, foot, occ, C, alb, pos, nrm, rid)
        # floor coverage and corridor visibility from the z-buffer
        kinds = np.array([r.kind for r in rects] + ["none"])[rid]
        fm = (kinds == "floor")[::3, ::3]
        fx, fy = pos[::3, ::3, 0][fm], pos[::3, ::3, 1][fm]
        cells_seen[np.clip((fx / 0.1).astype(int), 0, cells_seen.shape[0] - 1),
                   np.clip((fy / 0.1).astype(int), 0, cells_seen.shape[1] - 1)] = True
        inside = (fx >= UNSEEN["x0"]) & (fx <= UNSEEN["x1"]) & (fy >= UNSEEN["y0"]) & (fy <= UNSEEN["y1"])
        corridor_px += int(inside.sum())
        shutter = 1 / 60
        others = [path.at(t + dt)[1] for dt in np.linspace(-shutter / 2, shutter / 2, 5)]
        img = post.run(hdr, cam, R, others, shutter)
        if stills:
            cv2.imwrite(os.path.join(out, f"still_{i:04d}.png"), img)
        else:
            vw.write(img)
            if i % 5 == 0:
                poses.append((i, t, C.copy(), R.copy()))
        if i % 30 == 0:
            print(f"[{name}] frame {i}/{nfr}  {time.time() - t0:.0f}s", flush=True)
    if stills:
        return name
    vw.release()

    # ---- truth files
    room_id = "synthetic-room"
    gj = {
        "schema_version": "0.1", "room_id": room_id, "units": "m",
        "scale_source": {"method": "aruco_marker", "marker_id": 0, "marker_size_m": MARKER_M},
        "frame_index": [{"frame_id": k, "t_seconds": round(t, 4)} for k, (i, t, _, _) in enumerate(poses)],
        "camera_poses": [{"frame_id": k, "pose": {"position": [round(float(c), 5) for c in C],
                                                  "rotation_wxyz": mat_to_quat_wxyz(R)}}
                         for k, (i, t, C, R) in enumerate(poses)],
        "marker_poses": marker_truth(cfg.get("floor_marker")),
        "points_ref": {"kind": "point_cloud", "path": "points_truth.json"},
        "openings": [
            {"id": "exit_1", "kind": "exit", "marker_ids": [1], "points": [[DOOR_CX, 0.0, 0.0]]},
            {"id": "door_1", "kind": "door", "marker_ids": [2, 3],
             "points": [[JAMB_L, 0.0, 0.0], [JAMB_R, 0.0, 0.0]]},
        ],
    }
    json.dump(gj, open(os.path.join(out, "geometry_truth.json"), "w"), indent=1)
    pts = build_points(rects, cells_seen, cfg["box"])
    json.dump({"schema_version": "0.1", "units": "m", "points": pts}, open(os.path.join(out, "points_truth.json"), "w"))
    json.dump({"schema_version": "0.1", "room_id": room_id, "clip": f"{name}.mp4", "marker_id": 0,
               "marker_size_m": MARKER_M, "recorded_on": "2026-10-11"},
              open(os.path.join(out, "capture.json"), "w"), indent=2)
    clearance = (BLOCK_BOX[1] if cfg["box"] else SIDE_TABLE[1])
    seen_frac = float(cells_seen[int(UNSEEN["x0"] / 0.1):int(UNSEEN["x1"] / 0.1),
                                 int(UNSEEN["y0"] / 0.1):int(UNSEEN["y1"] / 0.1)].mean())
    meta = {
        "ILLUSTRATIVE": "synthetic render, not a real room; do not use as T2 ground truth",
        "clip": f"{name}.mp4", "resolution": [W, H], "fps": fps, "frames": nfr,
        "camera": {"K": cam.K.tolist(), "distortion_k1_k2_p1_p2_k3": cam.dist.tolist(), "hfov_deg": 66.0,
                   "pose_convention": "camera-to-world, OpenCV axes (x right, y down, z forward)"},
        "truth": {"door_clear_width_m": DOOR_CLEAR, "exit_clearance_m": round(clearance, 3),
                  "exit_clearance_note": "distance from the exit threshold (y=0) to the nearest obstacle in line with the exit",
                  "expected_verdict": cfg["expect"],
                  "unseen_area": ("floor corridor in front of the exit: x %.2f..%.2f m, y %.2f..%.2f m"
                                  % (UNSEEN["x0"], UNSEEN["x1"], UNSEEN["y0"], UNSEEN["y1"])) if cfg["expect"] == "not_proven" else None},
        "marker_layout": {"dictionary": "DICT_4X4_50 (UNVERIFIED)", "printed_black_side_m": MARKER_M,
                          "ids": {"0": "scale (left of the door, upper)", "1": "exit, on the door leaf",
                                  "2": "left door edge (beside the architrave)", "3": "right door edge (beside the architrave)",
                                  **({"4": "floor marker, lying flat, printed face up"} if cfg.get("floor_marker") else {})},
                          "door_edge_offset_note": "markers 2 and 3 sit beside the architrave; their centres are %.3f m from the clear-opening edge" % (ARCH_W + 0.02 + PAPER_M / 2)},
        "check": {"corridor_floor_pixels_seen": corridor_px, "corridor_floor_fraction_seen": round(seen_frac, 3)},
        "render_seconds": round(time.time() - t0, 1),
    }
    json.dump(meta, open(os.path.join(out, "scene_truth.json"), "w"), indent=1)
    print(f"[{name}] done in {time.time() - t0:.0f}s, corridor px seen {corridor_px}", flush=True)
    return name


def write_ground_truth(out_root):
    """One ground_truth.json for the three clips, in the layout of samples/t2/ground_truth.template.json."""
    gt = {"schema_version": "0.1", "units": "m", "room_id": "synthetic-room",
          "ILLUSTRATIVE": "synthetic render, not tape-measured; do not use as T2 ground truth", "clips": []}
    for name in CLIPS:
        t = json.load(open(os.path.join(out_root, name, "scene_truth.json")))["truth"]
        gt["clips"].append({"clip": f"{name}.mp4", "door_clear_width_m": t["door_clear_width_m"],
                            "exit_clearance_m": t["exit_clearance_m"], "expected_verdict": t["expected_verdict"],
                            "unseen_area": t["unseen_area"]})
    json.dump(gt, open(os.path.join(out_root, "ground_truth.json"), "w"), indent=2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.expanduser("~/virtual-safety-synth"))
    ap.add_argument("--clip", default="all", choices=["all"] + list(CLIPS) + list(EXTRA_CLIPS))
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--frames", type=int, default=0, help="render only the first N frames (test)")
    ap.add_argument("--stills", default="", help="comma list of frame numbers: write PNGs instead of video")
    a = ap.parse_args()
    names = list(CLIPS) if a.clip == "all" else [a.clip]
    stills = [int(x) for x in a.stills.split(",") if x] or None
    jobs = [(n, a.out, a.width, a.height, a.fps, a.frames, stills) for n in names]
    with Pool(len(jobs)) as p:
        p.map(render_clip, jobs)
    if not stills and a.clip == "all":
        write_ground_truth(a.out)


if __name__ == "__main__":
    main()
