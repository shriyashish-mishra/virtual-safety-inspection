# How it works

A person films a room with a phone, with a printed ArUco marker of known size in view. The system rebuilds the room in 3D, checks safety rules on the geometry (blocked exit, door clear width) and writes an evidence file. A separate checker recomputes every claim from the stored geometry and prints PASS or FAIL. If a view is missing, the system says `not_proven` and asks for that exact view instead of guessing.

1. **Capture:** clip plus `capture.json` (marker id, measured marker size, room id). Guide: `docs/capture-guide.md`.
2. **Reconstruct:** VGGT (or Depth Anything 3) turns frames into camera poses and points; the marker gives metric scale; `reconstruct/run.py` writes `geometry.json` and a coarse point file in metres (+z up, floor z = 0). Needs a GPU; run on a free notebook GPU. Notes: `docs/install-notes.md`.
3. **Judge:** `rules/` applies `docs/rules-spec.md` and writes `evidence.json`: one claim per opening with verdict, value, confidence, frame links, and a requested view for every `not_proven`.
4. **Check:** `checker/check.py` reads only `geometry.json`, its point file and `evidence.json`, recomputes each claim and prints PASS or FAIL. It never imports `rules/`.
5. **Explain:** Gemini may reword a verdict in plain language; `adapters/google/explain.py` and `viewer/vs-guard.js` discard any rewording that changes a verdict or number.
6. **Show:** `viewer/` is a static page (no build step) that shows the plan, the frames, the checker result and the question box; `scripts/build_hosting.py` and `firebase.json` publish it to Firebase Hosting.

Verdicts are only `pass`, `fail` and `not_proven`. The contract between the stages is `docs/interfaces.md` and the schemas in `schema/`.
