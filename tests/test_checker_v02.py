"""Checker follows spec v0.2 and v0.3 (T34). Small made-up point sets, one exit at the origin facing +y.
Run: python3 tests/test_checker_v02.py"""
import importlib.util
import pathlib

spec = importlib.util.spec_from_file_location("check", pathlib.Path(__file__).resolve().parent.parent / "checker" / "check.py")
chk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(chk)

GEOM = {"marker_poses": {"1": {"rotation_wxyz": [0.7071067811865476, -0.7071067811865476, 0, 0]}}}  # marker +z points to +y
OP = {"id": "exit_1", "kind": "exit", "points": [[0, 0, 0]], "marker_ids": [1]}
V01 = {"MIN_EXIT_CLEARANCE_M": 1.0, "CORRIDOR_HALF_WIDTH_M": 0.5, "FLOOR_BAND_M": 0.05, "OBSTACLE_MAX_Z_M": 2.0, "MIN_FLOOR_POINTS": 3}
V02 = dict(V01, EXIT_PLANE_MARGIN_M=0.15, MIN_CORRIDOR_SEEN_FRACTION=0.3, CORRIDOR_CELL_M=0.1)
V03 = dict(V02, OBSTACLE_SLICE_M=0.05, MIN_OBSTACLE_SLICE_POINTS=12)


def floor(n_along=10, n_across=10):
    return [(-0.45 + 0.1 * j, 0.05 + 0.1 * i, 0.0) for i in range(n_along) for j in range(n_across)]  # covers the corridor


def run(pts, P):
    return chk.recompute_exit(OP, GEOM, pts, P)[:2]


def main():
    door_leaf = [(0.0, 0.02, 1.0), (0.2, 0.03, 1.2)]  # door plane, s about 0
    box = [(0.0, 0.7, 0.4)]
    assert run(floor() + door_leaf, V01)[0] == "fail", "v0.1: door plane counts as an obstacle"
    assert run(floor() + door_leaf, V02) == ("pass", 1.0), "v0.2: the margin removes the door plane"
    assert run(floor() + box, V02) == ("fail", 0.7)
    assert run(box, V02) == ("fail", 0.7), "a seen obstacle is proof even with no floor seen (obstacles first)"
    assert run([], V02)[0] == "not_proven", "no floor points"
    thin = floor()[:5] * 1 + [(0.4, 0.95, 0.0)] * 3  # enough points for v0.1, few squares
    assert run(thin, V01)[0] == "pass" and run(thin, V02)[0] == "not_proven", "seen fraction"
    assert run(floor(), dict(V02, MIN_CORRIDOR_SEEN_FRACTION=None))[0] == "pass", "blank fraction skips step 5"
    # v0.3: scattered noise is not an obstacle, a dense face is
    noise = [(0.0, 0.19 + 0.02 * i, 0.4) for i in range(5)]               # 5 stray points past the margin
    assert run(floor() + noise, V02)[0] == "fail", "v0.2: stray points count as an obstacle"
    assert run(floor() + noise, V03) == ("pass", 1.0), "v0.3: thin slices are dropped"
    face = [(-0.2 + 0.03 * i, 0.65 + 0.001 * (i % 3), 0.5) for i in range(20)]  # 20 points in one slice
    out = run(floor() + noise + face, V03)
    assert out[0] == "fail" and 0.64 < out[1] < 0.66, out
    assert run(floor() + noise, dict(V03, OBSTACLE_SLICE_M=None))[0] == "fail", "blank slice size skips the step"
    print("ok: checker v0.2 and v0.3 steps behave as the spec says")


main()
