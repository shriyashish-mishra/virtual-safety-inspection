#!/usr/bin/env python3
"""Day-3 stub (T28-geometry): write a fixed, schema-valid geometry.json and its point file for any clip.

    python3 reconstruct/stub_geometry.py path/to/clip.mp4 out_dir

Nothing is reconstructed. The clip is never opened. Every number below is made up to exercise
the format (it mirrors samples/handmade/good); none is a measurement. Standard library only.
Frame: +z up, floor at z = 0 (docs/rules-spec.md, PROPOSED). Marker ids 1 to 4 are D11 placeholders.
"""
import json
import sys
from pathlib import Path

GEOMETRY = {'schema_version': '0.1',
 'room_id': 'handmade',
 'units': 'm',
 'scale_source': {'method': 'aruco_marker', 'marker_id': 0, 'marker_size_m': 0.15},
 'frame_index': [{'frame_id': 0, 't_seconds': 0.0},
                 {'frame_id': 1, 't_seconds': 0.5},
                 {'frame_id': 2, 't_seconds': 1.0},
                 {'frame_id': 3, 't_seconds': 1.5},
                 {'frame_id': 4, 't_seconds': 2.0},
                 {'frame_id': 5, 't_seconds': 2.5}],
 'camera_poses': [{'frame_id': 0,
                   'pose': {'position': [0.0, 2.5, 1.5], 'rotation_wxyz': [1.0, 0.0, 0.0, 0.0]}},
                  {'frame_id': 1,
                   'pose': {'position': [0.0, 2.2, 1.5], 'rotation_wxyz': [1.0, 0.0, 0.0, 0.0]}},
                  {'frame_id': 2,
                   'pose': {'position': [0.3, 2.0, 1.5], 'rotation_wxyz': [1.0, 0.0, 0.0, 0.0]}},
                  {'frame_id': 3,
                   'pose': {'position': [1.5, 2.0, 1.5], 'rotation_wxyz': [1.0, 0.0, 0.0, 0.0]}},
                  {'frame_id': 4,
                   'pose': {'position': [1.8, 2.0, 1.5], 'rotation_wxyz': [1.0, 0.0, 0.0, 0.0]}},
                  {'frame_id': 5,
                   'pose': {'position': [1.0, 3.0, 1.5], 'rotation_wxyz': [1.0, 0.0, 0.0, 0.0]}}],
 'marker_poses': {'0': {'position': [1.0, 0.0, 1.0],
                        'rotation_wxyz': [0.7071067811865476, -0.7071067811865476, 0.0, 0.0]},
                  '1': {'position': [0.6, 0.0, 1.2],
                        'rotation_wxyz': [0.7071067811865476, -0.7071067811865476, 0.0, 0.0]},
                  '2': {'position': [3.0, 1.6, 1.0],
                        'rotation_wxyz': [0.7071067811865476, 0.0, -0.7071067811865476, 0.0]},
                  '3': {'position': [3.0, 2.5, 1.0],
                        'rotation_wxyz': [0.7071067811865476, 0.0, -0.7071067811865476, 0.0]},
                  '4': {'position': [-2.0, 3.6, 1.2],
                        'rotation_wxyz': [0.7071067811865476, 0.0, 0.7071067811865476, 0.0]}},
 'points_ref': {'kind': 'point_cloud', 'path': 'points.json'},
 'openings': [{'id': 'exit_1', 'kind': 'exit', 'marker_ids': [1], 'points': [[0.0, 0.0, 1.0]]},
              {'id': 'door_1',
               'kind': 'door',
               'marker_ids': [2, 3],
               'points': [[3.0, 1.6, 1.0], [3.0, 2.5, 1.0]]},
              {'id': 'exit_2', 'kind': 'exit', 'marker_ids': [4], 'points': [[-2.0, 3.0, 1.0]]}]}

POINTS = {'schema_version': '0.1',
 'units': 'm',
 'points': [[-0.3, 0.2, 0.0],
            [0.3, 0.4, 0.0],
            [0.0, 0.8, 0.0],
            [-0.2, 0.5, 0.01],
            [-0.1, 0.6, 0.4],
            [0.1, 0.62, 0.5],
            [0.0, 0.65, 0.3],
            [0.9, 0.3, 0.5],
            [0.0, 0.3, 2.3],
            [2.0, 2.0, 0.0],
            [1.5, 1.0, 0.0]]}


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    clip, out = Path(argv[0]), Path(argv[1])
    geometry = dict(GEOMETRY)
    capture = clip.parent / "capture.json"
    if capture.exists():
        geometry["room_id"] = json.loads(capture.read_text())["room_id"]
    out.mkdir(parents=True, exist_ok=True)
    (out / "geometry.json").write_text(json.dumps(geometry, indent=2) + "\n")
    (out / GEOMETRY["points_ref"]["path"]).write_text(json.dumps(POINTS, indent=2) + "\n")
    print(f"wrote {out / 'geometry.json'} (STUB: fixed output, room_id {geometry['room_id']})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
