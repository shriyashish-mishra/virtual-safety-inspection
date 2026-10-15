#!/usr/bin/env python3
"""Checks the rules (T8 to T11) on the three synthetic clips and the hand-made pair.  ILLUSTRATIVE.

    python3 rules/test_rules.py

Expected results come from the scene truth (samples/t2/synthetic/ground_truth.synthetic.json) and from the
hand-computed table in samples/handmade/README.md, not from the rules code. Parameters are the PLACEHOLDERS in
samples/handmade/placeholders.json. The schema validator and the independent checker are run as programs;
nothing is imported from checker/ (D10). Standard library only.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import common  # noqa: E402
import evidence_writer  # noqa: E402

PARAMS = ROOT / "samples/handmade/placeholders.json"
SYN = ROOT / "samples/t2/synthetic"
truth = json.loads((SYN / "ground_truth.synthetic.json").read_text())["clips"]
params = common.load_params(PARAMS)


def run_program(*args):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True)


def check_file(geometry_path, evidence):
    with tempfile.TemporaryDirectory() as tmp:
        ev = Path(tmp) / "evidence.json"
        ev.write_text(json.dumps(evidence))
        v = run_program(ROOT / "schema/validate.py", "evidence", ev)
        assert v.returncode == 0, v.stdout + v.stderr
        c = run_program(ROOT / "checker/check.py", geometry_path, ev, "--params", PARAMS)
        assert c.returncode == 0 and c.stdout.strip().endswith("PASS"), c.stdout + c.stderr


def claim(evidence, cid):
    return next(c for c in evidence["claims"] if c["id"] == cid)


for t in truth:
    name = t["clip"].replace(".mp4", "")
    gpath = SYN / name / "geometry_truth.json"
    geometry, points = common.load_geometry(gpath)
    ev = evidence_writer.build(geometry, points, params)
    check_file(gpath, ev)
    ids = {f["frame_id"] for f in geometry["frame_index"]}
    exit_c, door_c = claim(ev, "exit_1_clear"), claim(ev, "door_1_width")
    assert exit_c["verdict"] == t["expected_verdict"], (name, exit_c)
    if t["expected_verdict"] == "fail":  # value is the nearest obstacle, 0.70 m in the scene truth
        assert abs(exit_c["value"] - t["exit_clearance_m"]) < 0.06, exit_c
    if t["expected_verdict"] == "pass":  # "clear for at least the required distance"
        assert exit_c["value"] == params["MIN_EXIT_CLEARANCE_M"], exit_c
    assert door_c["verdict"] == "pass" and abs(door_c["value"] - t["door_clear_width_m"]) < 1e-6, door_c
    for c in ev["claims"]:
        assert set(c["frame_ids"]) <= ids, c
        if c["verdict"] == "not_proven":
            assert c["value"] is None and c["unit"] is None and c["confidence"] == 0 and c["frame_ids"] == [], c
        else:
            assert c["frame_ids"], c  # a pass or fail always has a frame link
    if t["expected_verdict"] == "not_proven":
        rv = ev["requested_view"]
        assert rv and rv["claim_ids"] == ["exit_1_clear"] and "exit_1" in rv["description"], rv
        assert [u["id"] for u in ev["coverage"]["unseen_regions"]] == ["exit_1_clear"], ev["coverage"]
    else:
        assert ev["requested_view"] is None and ev["coverage"]["unseen_regions"] == [], ev
    print(f"ok {name}: {exit_c['verdict']} {exit_c['value']}, door {door_c['value']:.3f}, checker PASS")

# adding the missing view turns not_proven into a verdict: clip3's geometry plus the floor points clip1 saw
g3, p3 = common.load_geometry(SYN / "clip3_unseen/geometry_truth.json")
_, p1 = common.load_geometry(SYN / "clip1_clear/geometry_truth.json")
assert claim(evidence_writer.build(g3, p3, params), "exit_1_clear")["verdict"] == "not_proven"
more = claim(evidence_writer.build(g3, p3 + p1, params), "exit_1_clear")
assert more["verdict"] == "pass" and more["frame_ids"], more
print("ok clip3 + the extra view: not_proven becomes", more["verdict"])

# hand-made pair: exit_1 fail at 0.6 (box), door 0.9, exit_2 not_proven (hand-computed in samples/handmade/README.md)
hg, hp = common.load_geometry(ROOT / "samples/handmade/good/geometry.json")
hev = evidence_writer.build(hg, hp, params)
check_file(ROOT / "samples/handmade/good/geometry.json", hev)
assert (claim(hev, "exit_1_clear")["verdict"], round(claim(hev, "exit_1_clear")["value"], 3)) == ("fail", 0.6)
assert (claim(hev, "door_1_width")["verdict"], round(claim(hev, "door_1_width")["value"], 3)) == ("pass", 0.9)
assert claim(hev, "exit_2_clear")["verdict"] == "not_proven" and hev["requested_view"]["claim_ids"] == ["exit_2_clear"]
print("ok handmade/good: exit_1 fail 0.6, door 0.9, exit_2 not_proven")

# a door with a missing marker is not proven; a blank parameter stops the run instead of guessing
broken = json.loads(json.dumps(hg))
del broken["marker_poses"]["2"]
assert claim(evidence_writer.build(broken, hp, params), "door_1_width")["verdict"] == "not_proven"
blank = dict(json.loads(PARAMS.read_text()), CORRIDOR_HALF_WIDTH_M=None)
with tempfile.TemporaryDirectory() as tmp:
    pj = Path(tmp) / "p.json"
    pj.write_text(json.dumps(blank))
    try:
        common.load_params(pj)
        raise AssertionError("expected a stop on a blank parameter")
    except SystemExit as e:
        assert "CORRIDOR_HALF_WIDTH_M" in str(e)
print("ok: missing marker -> not_proven; blank parameter -> stops")

# spec v0.2 (PROPOSED): the door plane, the seen fraction and obstacle-first, on a small hand-built corridor.
# exit_1 of samples/handmade/good is at (0, 0) and faces +y; the placeholder corridor is 1.0 m long and 1.0 m wide.
v02 = common.load_params()  # default file = placeholders_v02.json
v01 = dict(v02)
for k in common.OPTIONAL_PARAMS:
    v01.pop(k)
floor_all = [[x / 20, y / 20, 0.0] for x in range(-10, 11) for y in range(0, 21)]   # every corridor square has a floor point
floor_thin = [[0.0, 0.1, 0.0], [0.1, 0.1, 0.0], [-0.1, 0.1, 0.0], [0.0, 0.2, 0.0]]  # 4 points, 3 or more so the old count passes
wall = [[x / 10, 0.01, 1.0 + z / 10] for x in range(-5, 6) for z in range(5)]         # door leaf: s = 0.01, in the height band
box = [[x / 20, 0.6, 0.3 + z / 20] for x in range(-4, 5) for z in range(3)]               # a box face at s = 0.6, 27 points
noise = [[0.0, 0.3, 0.5], [0.1, 0.32, 0.6], [-0.1, 0.35, 0.4], [0.05, 0.31, 0.7], [0.0, 0.33, 0.3]]  # 5 stray points past the margin


def exit_claim(points, p):
    return claim(evidence_writer.build(hg, points, p), "exit_1_clear")


assert exit_claim(floor_all + wall, v01)["verdict"] == "fail" and exit_claim(floor_all + wall, v01)["value"] < 0.02   # the v0.1 problem
c = exit_claim(floor_all + wall, v02)
assert c["verdict"] == "pass" and c["value"] == v02["MIN_EXIT_CLEARANCE_M"] and c["confidence"] == 1.0, c
c = exit_claim(floor_thin + wall, v02)
assert c["verdict"] == "not_proven" and c["frame_ids"] == [], c
assert exit_claim(floor_thin + wall, v01)["verdict"] == "fail"  # v0.1 cannot tell, it sees the wall
c = exit_claim(floor_thin + wall + box, v02)  # a seen obstacle is proof even with thin floor cover
assert c["verdict"] == "fail" and abs(c["value"] - 0.6) < 1e-9, c
c = exit_claim(floor_all + wall + box, v02)
assert c["verdict"] == "fail" and abs(c["value"] - 0.6) < 1e-9, c
print("ok spec v0.2: door plane ignored, thin floor cover -> not_proven, seen obstacle -> fail 0.6")
c = exit_claim(floor_thin + wall + noise, v02)  # spec v0.3: thin scatter is noise, so with thin floor the exit is not proven, not failed
assert c["verdict"] == "not_proven", c
v02_no_slice = {k: v for k, v in v02.items() if k not in ("OBSTACLE_SLICE_M", "MIN_OBSTACLE_SLICE_POINTS")}
assert exit_claim(floor_thin + wall + noise, v02_no_slice)["verdict"] == "fail"  # v0.2 turns the same scatter into a false fail
c = exit_claim(floor_all + wall + noise + box, v02)  # the dense box face still counts, and the nearest distance ignores the noise in front of it
assert c["verdict"] == "fail" and abs(c["value"] - 0.6) < 1e-9, c
print("ok spec v0.3: scatter ignored (not_proven), dense box face still fails at 0.6")
