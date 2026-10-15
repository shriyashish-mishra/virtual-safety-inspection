"""Checks the viewer's demo data (viewer/demo, built by tools/synthetic_room/make_demo_data.py).  Standard library only.

    python3 tests/test_demo_data.py

For every demo clip: files validate against the schemas, the independent checker agrees with the evidence, the
verdicts match the scene truth in index.json, every frame the evidence cites exists as a JPEG, and every precomputed
answer still passes the guard that keeps verdicts, numbers and the requested view intact. ILLUSTRATIVE data.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "viewer/demo"
sys.path.insert(0, str(ROOT / "adapters/google"))
import answer  # noqa: E402
import explain  # noqa: E402


def run(*args):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, cwd=ROOT)


if not (DEMO / "index.json").exists():
    print("skipped: viewer/demo not built")
    sys.exit(0)

index = json.loads((DEMO / "index.json").read_text())
assert "ILLUSTRATIVE" in index["provenance"], "demo data must say it is synthetic"
checked = 0
for clip in index["clips"]:
    d = DEMO / clip["id"]
    for kind, name in (("evidence", "evidence.json"), ("geometry", "geometry.json"), ("checker_report", "checker_report.json")):
        r = run("schema/validate.py", kind, d / name)
        assert r.returncode == 0, f"{clip['id']} {name}: {r.stdout}{r.stderr}"
    r = run("checker/check.py", d / "geometry.json", d / "evidence.json", "--params", "samples/handmade/placeholders.json")
    assert r.returncode == 0, f"{clip['id']}: checker did not PASS\n{r.stdout}"
    ev = json.loads((d / "evidence.json").read_text())
    exit_claim = next(c for c in ev["claims"] if c["type"] == "blocked_exit")
    assert exit_claim["verdict"] == clip["expected_verdict"], (clip["id"], exit_claim["verdict"], clip["expected_verdict"])
    assert (ev["requested_view"] is not None) == (clip["expected_verdict"] == "not_proven"), clip["id"]
    for c in ev["claims"]:
        for fid in c["frame_ids"]:
            assert (d / "frames" / f"f{fid}.jpg").stat().st_size > 1000, f"{clip['id']}: frame {fid} missing"
    if (d / "answers.json").exists():
        for a in json.loads((d / "answers.json").read_text()):
            claims = [c for c in ev["claims"] if c["id"] in a["claims"]]
            template = " ".join(answer.describe(c, ev) for c in claims)
            if a["source"] == "model_rewording":
                assert explain.guard(a["answer"], template, claims) is None, f"{clip['id']}: reworded answer fails the guard: {a['answer']}"
            else:
                assert a["answer"] == template, f"{clip['id']}: template answer differs from the evidence: {a['answer']}"
    checked += 1
print(f"ok: {checked} demo clips")
