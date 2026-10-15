#!/usr/bin/env python3
"""Make print-ready ArUco marker pages for the staged room (T2).  Needs numpy and opencv-python.

    python3 tools/make_markers.py out_dir            # ids 0 to 3, 150 mm black square (D7, D11)
    python3 tools/make_markers.py out_dir --ids 0 1 2 3 --size-mm 150

Writes marker_<id>.png, one A4 page each at 300 dpi (the file says so, so "actual size" printing works).
Print at 100 percent, no "fit to page". Then MEASURE the printed black square with a tape and write that
number, in metres, in capture.json as marker_size_m. Do not use the nominal size.
Ids (D7, D11 in docs/decisions.md): 0 scale, 1 exit (on the door), 2 and 3 door edges. Dictionary DICT_4X4_50.
"""
import argparse
import struct
import zlib
from pathlib import Path

import cv2
import numpy as np

DPI = 300
A4 = (2480, 3508)  # width, height in pixels at 300 dpi
ROLE = {0: "scale", 1: "exit (on the door)", 2: "left door edge", 3: "right door edge"}


def with_dpi(png_bytes, dpi):
    """Insert a pHYs chunk so printers and viewers know the pixel size."""
    ppm = int(round(dpi / 0.0254))
    data = struct.pack(">IIB", ppm, ppm, 1)
    chunk = struct.pack(">I", len(data)) + b"pHYs" + data + struct.pack(">I", zlib.crc32(b"pHYs" + data) & 0xFFFFFFFF)
    i = png_bytes.index(b"IDAT") - 4  # chunk length field of the first IDAT
    return png_bytes[:i] + chunk + png_bytes[i:]


def page(marker_id, size_mm):
    side = int(round(size_mm / 25.4 * DPI))
    side -= side % 6  # whole pixels per cell
    marker = cv2.aruco.generateImageMarker(cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50), marker_id, side)
    img = np.full((A4[1], A4[0]), 255, np.uint8)
    x0, y0 = (A4[0] - side) // 2, (A4[1] - side) // 2
    img[y0:y0 + side, x0:x0 + side] = marker
    actual_mm = side / DPI * 25.4
    label = f"ArUco DICT_4X4_50  id {marker_id} ({ROLE.get(marker_id, 'extra')})"
    cv2.putText(img, label, (150, 200), cv2.FONT_HERSHEY_SIMPLEX, 2.0, 0, 4, cv2.LINE_AA)
    cv2.putText(img, f"Black square = {actual_mm:.1f} mm when printed at 100% (actual size). MEASURE it after printing.",
                (150, 320), cv2.FONT_HERSHEY_SIMPLEX, 1.1, 0, 2, cv2.LINE_AA)
    # a 100 mm ruler line to check the print scale
    ruler = int(round(100 / 25.4 * DPI))
    cv2.line(img, (150, A4[1] - 250), (150 + ruler, A4[1] - 250), 0, 6)
    cv2.putText(img, "this line must measure 100 mm", (150, A4[1] - 190), cv2.FONT_HERSHEY_SIMPLEX, 1.1, 0, 2, cv2.LINE_AA)
    ok, buf = cv2.imencode(".png", img)
    return with_dpi(buf.tobytes(), DPI), actual_mm


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out_dir")
    ap.add_argument("--ids", type=int, nargs="+", default=[0, 1, 2, 3])
    ap.add_argument("--size-mm", type=float, default=150.0)
    a = ap.parse_args()
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for mid in a.ids:
        data, actual = page(mid, a.size_mm)
        (out / f"marker_{mid}.png").write_bytes(data)
        print(f"wrote {out / f'marker_{mid}.png'}  (black square {actual:.1f} mm at 100% print)")


if __name__ == "__main__":
    main()
