# Demo script, 60-second Google cut (T19, DRAFT)

Written 14 Oct by Shriyashish Mishra for the recording due Thu 15 Oct. The recording uses the three SYNTHETIC clips (rendered by tools/synthetic_room, not a real room), and the on-screen banner says so. Thresholds are placeholders until D8. Nothing here has been rehearsed yet (UNVERIFIED).

## Setup (before recording, works with no network)
1. From the repo root: `python3 -m http.server 8000`
2. Open http://localhost:8000/viewer/?clip=clip1_clear in a browser, window about 1280 x 800.
3. Screen-record with the OS recorder. Record the Q&A chips (stored answers), not the live box, so no network is needed.

## Script (about 60 seconds)
| Time | On screen | Say |
| --- | --- | --- |
| 0:00-0:08 | Title tab, then clip1 | "Hallucinati. A phone clip of a room becomes a safety verdict that a second program re-checks. This demo uses a synthetic room." |
| 0:08-0:20 | clip1_clear: plan, green exit card, 1.0 m, door 0.86 m, checker PASS | "Clip one. The exit has 1.0 metre clear and the door is 0.86 metres wide. The independent checker recomputed both from the stored geometry and says PASS." |
| 0:20-0:32 | clip2_blocked tab: red card, 0.70 m, frame thumbnail | "Clip two. A box sits 0.70 metres from the exit. The verdict is fail, with the frames that show it." |
| 0:32-0:46 | clip3_unseen tab: yellow card, requested-view box | "Clip three. The floor in front of the exit was never filmed. The system does not guess. It says not proven and asks for the exact view it needs." |
| 0:46-0:56 | Click a Q&A chip, e.g. "Is the exit blocked?" | "The language model only words the answer. The verdict is copied from the evidence file and cannot be changed by the model." |
| 0:56-1:00 | Checker badge | "PASS means the claims were re-verified, not that the room is safe." |

## Rules for the recording
- Say "synthetic" at least once; do not call the numbers measured in a real room.
- Do not say "safe" or "compliant"; the guard in adapters/google/explain.py rejects those words and so should the voice-over.
- The Google hosting route is open (D16). Do not show a deployed URL until one exists.

## Still needed for T19 (not done here)
Full 90-second script, a live re-run, and rehearsal by two people (done-when). Real-room footage replaces the synthetic clips once T2 lands.
