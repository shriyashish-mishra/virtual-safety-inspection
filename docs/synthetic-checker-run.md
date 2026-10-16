# Checker on the synthetic clips (T14 fixture test)

ILLUSTRATIVE. Run on 12 Oct 2026 by Shriyashish Mishra with `python3 tests/synthetic_checker.py` (exit 0). The clips are renders, not real captures (samples/t2/synthetic/), and the rule parameters are the PLACEHOLDERS in samples/handmade/placeholders.json until D8.

The test builds the evidence a correct rules implementation should write from the scene truth and `docs/rules-spec.md`, then runs `checker/check.py` on each clip's `geometry_truth.json` and point file. It imports nothing from `rules/` or `reconstruct/` (D10); the real rules (T8) and real reconstruction do not exist yet, so this is not a test of either.

| clip | scene truth | evidence given to the checker | checker | wanted |
| --- | --- | --- | --- | --- |
| clip1_clear | pass | correct evidence | PASS | PASS |
| clip1_clear | pass | says fail on a clear exit | FAIL | FAIL |
| clip2_blocked | fail | correct evidence | PASS | PASS |
| clip2_blocked | fail | says pass on a blocked exit | FAIL | FAIL |
| clip3_unseen | not_proven | correct evidence | PASS | PASS |
| clip3_unseen | not_proven | says pass on a never-filmed corridor | FAIL | FAIL |

Why the wrong evidence fails, from the checker's own output: clip 1 recomputes pass (1.0000 m, the placeholder minimum); clip 2 recomputes fail at 0.7000 m (the box is 0.70 m from the door); clip 3 recomputes `not_proven` because the corridor has too few floor points. PASS on correct evidence means agreement, not a safe room.

What this does not show:
- UNVERIFIED: any result on reconstructed geometry. These point clouds come from the scene's truth, so they have no reconstruction noise or scale error.
- UNVERIFIED: the real rules. A mismatch between the rules and the checker would show only once T8 exists.
- The clip 3 corridor size and every parameter are placeholders for D8.
