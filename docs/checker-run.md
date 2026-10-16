# Checker run (T34)

Run on 5 Oct 2026 by Shriyashish Mishra, against Nadeem's hand-made pairs (T4, PR #9) and the PLACEHOLDER parameters in `samples/handmade/placeholders.json`. Every number is made up to exercise the spec; none is a measurement. `TOLERANCE` is 0.01 m in `checker/config.py`, a placeholder until D8.

Command: `python3 checker/check.py samples/handmade/<pair>/geometry.json samples/handmade/<pair>/evidence.json --params samples/handmade/placeholders.json`

## good pair: PASS (exit code 0)

```
  exit_1_clear: PASS
  door_1_width: PASS
  exit_2_clear: PASS
PASS
```

## tampered pair: FAIL (exit code 1)

```
  exit_1_clear: PASS
  door_1_width: FAIL (value 1.8 differs from recomputed 0.9000 by more than 0.01)
  exit_2_clear: PASS
FAIL
```

This matches the expected table in `samples/handmade/README.md`. Both `--out` reports validate with `schema/validate.py checker_report` from the T1 draft (PR #5).

## Extra cases tried on the good pair (not saved as files)

Each edit to the good evidence gives FAIL: `not_proven` with a value, `requested_view` removed, `exit_1_clear` reported as pass, a claim removed, and a frame id that is not in `frame_index`.

## Re-run on 12 Oct 2026 (main at 55e5174)

Same command, same placeholder parameters, both pairs: good pair prints `PASS` and exits 0; tampered pair prints `FAIL` with `door_1_width: FAIL (value 1.8 differs from recomputed 0.9000 by more than 0.01)` and exits 1. `python3 schema/validate.py --all` prints ok for all six files. Nothing in `checker/` changed since the 5 Oct run.

T34's done-when (PASS on the good pair, FAIL on the tampered pair, output saved here) is met. Still open and not part of that test: Nadeem's review of `checker/` after merge (D15), and a run on reconstruction output, which does not exist yet.

## What this does not show

- UNVERIFIED: the checker has only seen these two hand-made pairs, so it is not tested against real reconstruction output.
- UNVERIFIED: `TOLERANCE` and every rule parameter wait for D8.
- The spec says the point file format and the z-up floor frame need Kaushal's yes. The checker assumes both as written.
- Independence (D10): written from `docs/rules-spec.md` only; there is no `rules/` yet and nothing is imported from it.

## v0.2 update (14 Oct, T34)

`checker/check.py` now follows spec v0.2 (docs/rules-spec.md section 4): the exit plane margin removes the door plane, a corridor seen fraction replaces the bare floor-point count, and a seen obstacle is tested first. Blank new parameters give exactly the v0.1 behaviour, so every earlier run is unchanged. Written from the spec text only; it imports nothing from `rules/` (D10).

| Run | Result |
| --- | --- |
| `python3 tests/test_checker_v02.py` (door plane, obstacles first, seen fraction, blank parameters) | VERIFIED: ok |
| `python3 tests/synthetic_checker.py` (correct evidence PASS, wrong evidence FAIL, v0.1 parameters) | VERIFIED: ALL AS EXPECTED |
| Rules v0.2 output on the three synthetic clips, `--params samples/handmade/placeholders_v02.json` | VERIFIED: PASS on all three |
| Hand-made good and tampered pair, v0.1 parameters | VERIFIED: good PASS, tampered FAIL |

UNVERIFIED: the checker on the reconstructed geometry of 14 Oct. Those files are on Kaushal's machine, not in git (docs/rules-run.md), so the "checker says FAIL there" note in that file has not been re-run with v0.2. The placeholder parameters (margin 0.15 m, seen fraction 0.3, cell 0.1 m) are still placeholders for D8; the spec v0.2 itself is PROPOSED and not yet accepted by its owner, Nadeem.

## v0.3 update (15 Oct, T34)

`checker/check.py` now follows spec v0.3 (docs/rules-spec.md section 4, step 2): obstacle points are grouped into slices of `OBSTACLE_SLICE_M` along the exit direction and every point whose slice holds fewer than `MIN_OBSTACLE_SLICE_POINTS` points is dropped as reconstruction noise. Blank slice parameters give exactly the v0.2 behaviour, and blank v0.2 parameters give v0.1, so earlier runs are unchanged. Written from the spec text only; it imports nothing from `rules/` (D10).

| Run | Result |
| --- | --- |
| `python3 tests/test_checker_v02.py` (now also: five stray points are not an obstacle, a dense 20-point face at 0.65 m is, blank slice size skips the step) | VERIFIED: ok |
| `python3 tests/synthetic_checker.py` | VERIFIED: ALL AS EXPECTED |
| `python3 tests/e2e.py` (rules to checker on the three truth geometries, `placeholders_v02.json` which already holds the v0.3 slice values) | VERIFIED: ALL AS EXPECTED |

UNVERIFIED: the checker on the seven reconstructions listed in docs/rules-run.md. Those geometry files are on Kaushal's machine and not in git. To close T8 he can run, for each one: `python3 checker/check.py GEOMETRY EVIDENCE --params samples/handmade/placeholders_v02.json` where EVIDENCE is the file `python3 rules/run.py GEOMETRY OUT_DIR` wrote; the rules and the checker now follow the same spec, so PASS is expected on all seven, but I have not seen it. The slice size 0.05 m and count 12 are placeholders fitted to those same clips (docs/rules-run.md), and spec v0.3 is PROPOSED, not accepted by its owner, Nadeem.
