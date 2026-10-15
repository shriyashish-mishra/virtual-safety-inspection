#!/usr/bin/env python3
"""Rules v0: geometry.json to evidence.json.

    python3 rules/run.py GEOMETRY.json OUT_DIR [--params PARAMS.json]

Reads the geometry and its point file, applies docs/rules-spec.md, writes OUT_DIR/evidence.json.
Without --params it uses the PLACEHOLDER values in samples/handmade/placeholders_v02.json (D8 is not decided).
Standard library only; never imports from checker/ (D10).
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import evidence_writer  # noqa: E402


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("geometry")
    ap.add_argument("out_dir")
    ap.add_argument("--params", help="rule parameters JSON (default: the PLACEHOLDER file)")
    a = ap.parse_args(argv)
    params = common.load_params(a.params)
    if not a.params:
        print("NOTE: using PLACEHOLDER parameters (samples/handmade/placeholders_v02.json); D8 is not decided", file=sys.stderr)
    geometry, points = common.load_geometry(a.geometry)
    evidence = evidence_writer.build(geometry, points, params)
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
    for c in evidence["claims"]:
        print(f"{c['id']}: {c['verdict']} value={c['value']} confidence={c['confidence']} frames={len(c['frame_ids'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
