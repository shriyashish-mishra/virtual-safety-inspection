#!/usr/bin/env python3
"""T14 fixture test: the independent checker on the synthetic clips' true geometry.  ILLUSTRATIVE.

    python3 tests/synthetic_checker.py

For each synthetic clip (samples/t2/synthetic/) this builds the evidence a correct rules
implementation should write, from the scene truth and docs/rules-spec.md, then runs
checker/check.py on geometry_truth.json. Expected: the checker agrees (PASS) with the
correct evidence and disagrees (FAIL) with evidence that has been made wrong in the way
that matters: a pass on the unseen corridor, a pass on the blocked exit, a fail on the clear one.

Nothing here imports rules/ or reconstruct/ (D10); the evidence is built from the truth file,
not from any rules code. Parameters are the PLACEHOLDERS in samples/handmade/placeholders.json.
Standard library only.
"""
import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYN = ROOT / "samples/t2/synthetic"
PARAMS = ROOT / "samples/handmade/placeholders.json"
CHECKER = ROOT / "checker/check.py"


def expected_evidence(clip_dir, truth, params):
    geom = json.loads((clip_dir / "geometry_truth.json").read_text())
    min_clear = params["MIN_EXIT_CLEARANCE_M"]
    frame = geom["frame_index"][0]["frame_id"]
    claims = []
    if truth["expected_verdict"] == "not_proven":
        claims.append({"id": "exit_1_clear", "type": "blocked_exit", "verdict": "not_proven",
                       "value": None, "unit": None, "confidence": 0.0, "frame_ids": []})
    else:
        value = min(truth["exit_clearance_m"], min_clear)
        verdict = "fail" if truth["exit_clearance_m"] < min_clear else "pass"
        claims.append({"id": "exit_1_clear", "type": "blocked_exit", "verdict": verdict, "value": value,
                       "unit": "m", "confidence": 0.9, "frame_ids": [frame]})
    width = truth["door_clear_width_m"]
    claims.append({"id": "door_1_width", "type": "door_clear_width",
                   "verdict": "pass" if width >= params["MIN_DOOR_CLEAR_WIDTH_M"] else "fail",
                   "value": width, "unit": "m", "confidence": 0.85, "frame_ids": [frame]})
    unproven = [c["id"] for c in claims if c["verdict"] == "not_proven"]
    return {"schema_version": "0.1", "room_id": geom["room_id"], "claims": claims,
            "coverage": {"seen_fraction": 0.0, "unseen_regions": []},
            "requested_view": ({"claim_ids": unproven, "description": "Film the floor in front of the exit from about 2 m away, with the exit marker in frame"} if unproven else None)}


def run_checker(clip_dir, evidence, tmp):
    path = Path(tmp) / "evidence.json"
    path.write_text(json.dumps(evidence))
    r = subprocess.run([sys.executable, str(CHECKER), str(clip_dir / "geometry_truth.json"), str(path),
                        "--params", str(PARAMS)], capture_output=True, text=True)
    return ("PASS" if r.returncode == 0 else "FAIL" if r.returncode == 1 else f"ERROR({r.returncode})"), r.stdout.strip()


def tampered(evidence, how):
    ev = copy.deepcopy(evidence)
    c = ev["claims"][0]
    if how == "pass_on_unseen_or_blocked":
        c.update(verdict="pass", value=1.0, unit="m", confidence=0.9, frame_ids=[0])
        ev["requested_view"] = None
    elif how == "fail_on_clear":
        c.update(verdict="fail", value=0.5, unit="m", confidence=0.9, frame_ids=[0])
    return ev


def main():
    params = json.loads(PARAMS.read_text())
    truth = json.loads((SYN / "ground_truth.synthetic.json").read_text())
    rows, ok = [], True
    for t in truth["clips"]:
        name = t["clip"].replace(".mp4", "")
        d = SYN / name
        good = expected_evidence(d, t, params)
        with tempfile.TemporaryDirectory() as tmp:
            got, _ = run_checker(d, good, tmp)
            rows.append((name, t["expected_verdict"], "correct evidence", got, "PASS"))
            how = "fail_on_clear" if t["expected_verdict"] == "pass" else "pass_on_unseen_or_blocked"
            label = {"fail_on_clear": "says fail on a clear exit",
                     "pass_on_unseen_or_blocked": "says pass on a " + ("blocked exit" if t["expected_verdict"] == "fail" else "never-filmed corridor")}[how]
            got2, _ = run_checker(d, tampered(good, how), tmp)
            rows.append((name, t["expected_verdict"], label, got2, "FAIL"))
    print("| clip | scene truth | evidence given to the checker | checker | wanted |")
    print("| --- | --- | --- | --- | --- |")
    for r in rows:
        print("| " + " | ".join(r) + " |")
        ok &= r[3] == r[4]
    print("\nALL AS EXPECTED" if ok else "\nMISMATCH")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
