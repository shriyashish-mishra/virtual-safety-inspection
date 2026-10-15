# Virtual Safety Inspection: submission text

Team Hallucinati (Shriya, Kaushal, Nadeem) for the Google Cloud AI Builder Cup 2026.

## One line
Film a room with a phone; get a verdict on the exit and the door, an independent checker that re-verifies it, and an honest "not proven" with the exact missing view when the clip does not cover a claim.

## The problem
Blocked exits and narrow doors are found on site visits and written up as opinions. A phone clip is cheap, but a model that looks at it can sound sure and be wrong. We want a result that a second program can recompute and that says what it cannot show.

## What we built
- **Pipeline.** A clip with a printed ArUco marker of known size, a 3D reconstruction in metres, rules on the geometry, an evidence file, and a separate checker that reads only the geometry and evidence files and never imports the rules.
- **Verdicts.** Only pass, fail or not_proven. The rules decide them. Gemini explains them in plain words and cannot change them: the answer is copied from the evidence file, and a guard discards any rewording that changes a verdict, adds or drops a number, drops the requested view, or says "safe" or "compliant" (`adapters/google/explain.py`; the same guard runs in the browser in `viewer/vs-guard.js`; `tests/test_guard_parity.py`, 105 cases agree; `tests/test_explanation_guard.py`, 72 hostile rewordings rejected).
- **Independent check.** On the three clips the checker returns PASS for the correct evidence and FAIL for deliberately wrong evidence (`docs/synthetic-checker-run.md`, `tests/e2e.py`).
- **Hosting.** Firebase Hosting on the free plan; the page calls Gemini through Firebase AI Logic. Live: https://virtual-safety-hallucinati.web.app/ (clips `/?clip=clip1_clear`, `/?clip=clip2_blocked`, `/?clip=clip3_unseen`).

## Gemini
Gemini turns a verdict and its numbers into a sentence for a facility manager. It never produces a verdict. The guard is how that limit is enforced and tested.

## Not proven is an answer
When the clip never showed the floor in front of the exit, the system says not proven and names the view to film ("Film the floor in front of exit_1 from about 2 m away, with the exit marker in frame"). It does not guess.

## The viewer
The room from above with the exit path, a green or red claim card with the video frames behind it, the checker's PASS or FAIL, the missing-view request, and a question box. PASS means the claims were re-verified, not that the room is safe.

## What is real and what is not
- The three demo clips are SYNTHETIC: rendered by `tools/synthetic_room` with known geometry. They are not a real room.
- Reconstruction from a real phone clip with measured scale is not yet shown; the reconstruction script ran on the synthetic clips with VGGT on a free GPU (`docs/spike-report.md`).
- Rule thresholds and the checker tolerance are placeholders (`docs/decisions.md`).
- The numbers (1.0 m, 0.70 m, 0.86 m) come from the synthetic scene, not from measuring a real room.
