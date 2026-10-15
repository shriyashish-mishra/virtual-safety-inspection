# Viewer v1 (T12)

One static page, `index.html`: no build step, no server code, nothing leaves the browser except an optional question to the Google service.

For the chosen clip it shows the independent checker result (PASS or FAIL), a top-down plan with the exit corridor coloured by verdict (hatched amber for not proven), each claim with the video frames the evidence cites, the missing-view request, and questions answered from the evidence by the Google adapter.

## Run it

From the repo root: `python3 -m http.server`, then open http://localhost:8000/viewer/

| URL | Shows |
| --- | --- |
| `?clip=clip1_clear`, `?clip=clip2_blocked`, `?clip=clip3_unseen` | the three synthetic demo clips (data in `viewer/demo/`) |
| `?sample=pass`, `?sample=fail` | the older hand-made files in `samples/` (no plan, frames or answers) |
| `?api=http://localhost:8090` | adds a box that asks a live Google adapter (`POST /ask`) instead of using the precomputed answers |

Opened as a plain file, the browser will not read other files; use the two Open buttons to pick an `evidence.json` and `checker_report.json`.

## Where the demo data comes from (ILLUSTRATIVE)

`viewer/demo/` is built from the synthetic clips, not from a real room, and **not by the rules**: the evidence is written from the scene truth and `docs/rules-spec.md`. Rules v0 (`python3 rules/run.py viewer/demo/<clip>/geometry.json OUT`) now exists and gives the same verdicts and values on this geometry (checkpoint of 14 Oct, docs/rules-run.md), but the files here are not its output; it also reads the truth geometry, not a reconstruction. The independent checker recomputes the evidence and prints PASS. Rule parameters are the placeholders in `samples/handmade/placeholders.json` (D8). To use the rules' output instead, replace `evidence.json` per clip; the viewer needs no change.

    python3 tools/synthetic_room/render.py --out ~/virtual-safety-synth          # the clips (needs numpy, opencv-python)
    python3 tools/synthetic_room/make_demo_data.py --clips ~/virtual-safety-synth --out viewer/demo
    python3 tools/synthetic_room/make_demo_answers.py                            # Gemini rewording only if GEMINI_API_KEY and GEMINI_MODEL are set
    python3 tests/test_demo_data.py                                              # schemas, checker, frames and answers

`answers.json` records for each answer whether it was copied from the evidence or reworded by Gemini after `explain.guard()` accepted it, and why a rewording was thrown away.

## Hosting (UNVERIFIED)

`viewer/` is plain files, so any static host works. Firebase Hosting on the free Spark plan needs no payment method (Google's pricing page); whether the Google Cloud AI Builder Cup accepts that as "deployed on Firebase or Cloud Run" is not confirmed. The live Q&A needs `adapters/google` on Cloud Run, which needs a billing account.

## Browser guard (viewer/vs-guard.js, T16)
For the Firebase route (D16, B+) the page calls Gemini itself, so the checks that stop the model changing a verdict must run in the page. `vs-guard.js` is a dependency-free port of `pick_claims`, `describe` and `guard` from `adapters/google`. Use `VSGuard.answer(evidence, question, modelText)`: it returns the evidence-template answer, and the model wording only if the guard accepts it (else `explanation_discarded` says why). `python3 tests/test_guard_parity.py` runs both versions on 105 cases and fails if they differ (needs node). Not yet wired to a model call: that needs the Firebase SDK (a dependency, so Shriya's yes) and Kaushal's project.
