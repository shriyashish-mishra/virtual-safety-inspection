#!/usr/bin/env python3
"""T14 end-to-end test: geometry to rules to evidence to checker, on the three synthetic clips, compared with ground truth.

    python3 tests/e2e.py [--save docs/e2e-run.md]

For each clip in samples/t2/synthetic/ground_truth.synthetic.json it runs rules/run.py on the clip's truth geometry,
validates evidence.json against the schema, runs checker/check.py (spec v0.2 placeholder parameters) and compares the
verdicts and values with the ground truth. Exit 0 only if every row is as expected. ILLUSTRATIVE: the geometry is the
synthetic scene's own truth, not a reconstruction from video, and the rules parameters are placeholders (D8).
Standard library only; it calls the rules and the checker as programs, so it adds no coupling between them (D10).
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GT = ROOT / "samples/t2/synthetic/ground_truth.synthetic.json"
PARAMS = ROOT / "samples/handmade/placeholders_v02.json"
DOOR_TOL = 0.01  # PLACEHOLDER, same as checker/config.py until D8


def run(*args):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, cwd=ROOT)


def main():
    gt = json.loads(GT.read_text())
    min_clear = json.loads(PARAMS.read_text())["MIN_EXIT_CLEARANCE_M"]
    rows, ok = [], True
    for c in gt["clips"]:
        name = c["clip"].removesuffix(".mp4")
        geom = ROOT / "samples/t2/synthetic" / name / "geometry_truth.json"
        with tempfile.TemporaryDirectory() as tmp:
            r = run("rules/run.py", geom, tmp, "--params", PARAMS)
            ev_path = Path(tmp) / "evidence.json"
            problems = []
            if r.returncode != 0 or not ev_path.exists():
                problems.append(f"rules failed: {r.stderr.strip()[-120:]}")
                rows.append((name, "-", "-", "-", "-", "; ".join(problems))); ok = False
                continue
            v = run("schema/validate.py", "evidence", ev_path)
            if v.returncode != 0:
                problems.append("evidence fails schema")
            rep = Path(tmp) / "report.json"
            k = run("checker/check.py", geom, ev_path, "--params", PARAMS, "--out", rep)
            checker = "PASS" if k.returncode == 0 else "FAIL"
            ev = json.loads(ev_path.read_text())
            claims = {x["id"]: x for x in ev["claims"]}
            ex, dr = claims["exit_1_clear"], claims["door_1_width"]
            if ex["verdict"] != c["expected_verdict"]:
                problems.append(f"exit verdict {ex['verdict']}, wanted {c['expected_verdict']}")
            if c["expected_verdict"] == "fail" and abs(ex["value"] - c["exit_clearance_m"]) > DOOR_TOL:
                problems.append(f"exit value {ex['value']} vs truth {c['exit_clearance_m']}")
            if c["expected_verdict"] == "pass" and not (min_clear <= ex["value"] <= c["exit_clearance_m"]):
                problems.append(f"exit value {ex['value']} outside [{min_clear}, {c['exit_clearance_m']}]")
            if c["expected_verdict"] == "not_proven" and (ex["value"] is not None or not ev.get("requested_view")):
                problems.append("not_proven needs a null value and a requested view")
            if dr["verdict"] != "pass" or abs(dr["value"] - c["door_clear_width_m"]) > DOOR_TOL:
                problems.append(f"door {dr['verdict']} {dr['value']} vs truth {c['door_clear_width_m']}")
            if checker != "PASS":
                problems.append("checker FAIL")
            evv = f"{ex['verdict']}" + ("" if ex["value"] is None else f" {ex['value']:.2f} m")
            rows.append((name, c["expected_verdict"], evv, f"{dr['value']:.2f} m (truth {c['door_clear_width_m']})", checker,
                         "ok" if not problems else "; ".join(problems)))
            ok = ok and not problems
    lines = ["| clip | wanted exit verdict | rules exit claim | rules door width | checker | result |", "| --- | --- | --- | --- | --- | --- |"]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    table = "\n".join(lines)
    print(table)
    print("\nALL AS EXPECTED" if ok else "\nMISMATCH")
    if "--save" in sys.argv:
        out = ROOT / sys.argv[sys.argv.index("--save") + 1]
        out.write_text("# End-to-end run (T14)\n\nILLUSTRATIVE. `python3 tests/e2e.py`: rules/run.py on each clip's truth geometry, schema validation, "
                       "the independent checker (spec v0.2 placeholder parameters, D8 open), compared with samples/t2/synthetic/ground_truth.synthetic.json. "
                       "The geometry is the synthetic scene's truth, not a reconstruction from video; no real clip is involved (T2 pending).\n\n"
                       + table + "\n\n" + ("ALL AS EXPECTED\n" if ok else "MISMATCH\n"))
    return 0 if ok else 1


sys.exit(main())
