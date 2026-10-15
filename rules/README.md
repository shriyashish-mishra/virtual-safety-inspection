# Judging lane

## Day-3 evidence stub (T28-evidence)

From the repo root:

```sh
python3 reconstruct/stub_geometry.py /tmp/no-video/clip.mp4 /tmp/t28-stub
python3 rules/stub_evidence.py /tmp/t28-stub/geometry.json /tmp/t28-stub
python3 schema/validate.py evidence /tmp/t28-stub/evidence.json
python3 checker/check.py /tmp/t28-stub/geometry.json /tmp/t28-stub/evidence.json --params samples/handmade/placeholders.json --out /tmp/t28-stub/checker_report.json
```

The writer emits the existing fixed T4 evidence fixture, changing only room_id to match the geometry hand-off. It computes no rules or coverage and is intended for the fixed geometry stub, not reconstructed or synthetic-scene geometry. Values, confidence, frame links, marker IDs and rule parameters are placeholders. No video is read. Standard library only.

Open viewer/index.html and pick the generated evidence.json and checker_report.json using its two Open controls. Expect exit_1 fail, door_1 pass, exit_2 not_proven, the named missing-view request, and checker PASS. Checker PASS means agreement, not a safe room.

Real rules and evidence writing remain T8–T11.

## Rules v0 (T8 to T11)

Run: `python3 rules/run.py GEOMETRY.json OUT_DIR [--params FILE]`; test: `python3 rules/test_rules.py`. Results and open problems: docs/rules-run.md. Written from docs/rules-spec.md only; the checker is run as a program and never imported (D10). Parameters are PLACEHOLDERS until D8.

- Exit rule: open problem on reconstructed clouds, see docs/rules-run.md.
- Coverage: frame links use a placeholder view angle (VIEW_HALF_ANGLE_DEG).
