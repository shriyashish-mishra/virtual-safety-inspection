# Decisions that shape the code

Short record of the choices the code depends on. Placeholder values are labelled; nothing here was measured on a real room.

| Decision | What | Status |
| --- | --- | --- |
| Marker (D7) | ArUco `DICT_4X4_50`; scale marker id 0, printed side 0.15 m (measure the printed side with a tape and record it in `capture.json`) | decided; detection range on real footage untested |
| Openings (D11) | Exit marker id 1 (on the door); door-edge markers ids 2 and 3; read by the rules from `marker_poses` | decided; placement beside a real door edge untested |
| Floor marker | A marker, id 4, lying flat on the floor sets floor z = 0 and "up"; without it the run reports the floor as unreliable | accepted; untested on a real floor |
| Geometry frame | Metres, +z up, floor at z = 0 | decided |
| Independence (D10) | The checker never imports from `rules/` and shares no helper code with it; they are written from `docs/rules-spec.md` by different people | in force |
| Verdicts | Only `pass`, `fail`, `not_proven`. The rules decide; the language model only words them and a guard discards any rewording that changes a verdict or number | in force |
| Tolerance (D8) | Door-width reconstruction tolerance 0.10 m, for the prototype only, from three synthetic clips (errors 0.049 to 0.060 m). All rule parameters in `samples/handmade/placeholders*.json` are PLACEHOLDERS | accepted for the prototype |
| Scope | The three synthetic rooms (`tools/synthetic_room`) stand in for real clips; every number shown is from a render. A real room is future work | decided |
| Scale gate | Keep phone video and the marker; no photo-measurement fallback; ask again on a real clip | accepted for the prototype |
| Hosting (D16) | Firebase Hosting on the free plan; the page calls Gemini through Firebase AI Logic; no backend. App Check is not enforced (needs billing); Google requires it from 2 Nov 2026, after which the reword is off and the page shows the evidence answer | live |
| Licence (D9) | MIT | decided |
