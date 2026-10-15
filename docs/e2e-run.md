# End-to-end run (T14)

ILLUSTRATIVE. `python3 tests/e2e.py`: rules/run.py on each clip's truth geometry, schema validation, the independent checker (spec v0.2 placeholder parameters, D8 open), compared with samples/t2/synthetic/ground_truth.synthetic.json. The geometry is the synthetic scene's truth, not a reconstruction from video; no real clip is involved (T2 pending).

| clip | wanted exit verdict | rules exit claim | rules door width | checker | result |
| --- | --- | --- | --- | --- | --- |
| clip1_clear | pass | pass 1.00 m | 0.86 m (truth 0.86) | PASS | ok |
| clip2_blocked | fail | fail 0.70 m | 0.86 m (truth 0.86) | PASS | ok |
| clip3_unseen | not_proven | not_proven | 0.86 m (truth 0.86) | PASS | ok |

ALL AS EXPECTED
