#!/usr/bin/env python3
"""T28-evidence: write fixed evidence for the day-3 integration pipeline.

    python3 rules/stub_evidence.py geometry.json out_dir

Only room_id is read from geometry. Claims, frame links and coverage are made-up
T4 fixture values, not measurements or computed rules. Use stub geometry only.
Standard library only; the independent checker does not import this module.
"""
import argparse
import json
from pathlib import Path

FIXTURE = Path(__file__).resolve().parents[1] / "samples/handmade/good/evidence.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("geometry", type=Path, help="stub geometry.json (only room_id is read)")
    parser.add_argument("out_dir", type=Path)
    args = parser.parse_args()
    try:
        geometry = json.loads(args.geometry.read_text())
        evidence = json.loads(FIXTURE.read_text())
        evidence["room_id"] = geometry["room_id"]
        args.out_dir.mkdir(parents=True, exist_ok=True)
        output = args.out_dir / "evidence.json"
        output.write_text(json.dumps(evidence, indent=2) + "\n")
    except (OSError, ValueError, KeyError) as error:
        parser.exit(2, f"stub input/output error: {error}\n")
    print(f"wrote {output} (STUB: fixed claims; no real measurements)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
