# Capture guide (DRAFT for T2)

Written 6 Oct by Shriyashish Mishra (owner of the capture.json format, T1) for Nadeem's T2 filming and Kaushal's T5 spike. Anything marked UNVERIFIED or INFERENCE is a proposal to confirm, not a measured fact.

## What to produce (VERIFIED)

Three clips of the staged room, named exactly:

| Clip | What it shows |
| --- | --- |
| clip1_clear | Exit clear |
| clip2_blocked | Exit blocked |
| clip3_unseen | One area of the room that is never filmed, so the system must answer not_proven |

Per room, tape-measure the door clear width and the exit clearance (metres) and write a ground-truth file (samples/t2/ground_truth.template.json is the layout) (per clip: door clear width, exit clearance, expected verdict). Nadeem owns that file.

## Marker

- One printed ArUco marker gives scale (D7 default: one marker of one fixed size, chosen in the spike; UNVERIFIED until Kaushal confirms).
- D11 (PROPOSED, INFERENCE: not tested): reserved marker ids mark the exit (one id) and the two door edges (two ids); the scale marker keeps its own id. Kaushal confirms the actual ids before anything is printed.
- Measure the printed marker's side with a tape after printing and record it in metres in capture.json. Do not use the nominal size.
- Keep the marker flat, unfolded and fully in view for part of every clip.

## Filming (INFERENCE: sensible defaults, not tested; Kaushal may change them after T5)

- Phone video, landscape, one continuous take per clip, steady walk, no digital zoom.
- Start with the door and its marker in frame, then sweep the room, and end back on the exit.
- clip3_unseen: leave one area out on purpose and name which area in the ground-truth file (capture.json has no field for it).
- Avoid motion blur (slow turns) and strong backlight from the door.

## capture.json (one per clip, format from T1, VERIFIED on PR #5)

See schema/examples/capture.json:

    {
      "schema_version": "0.1",
      "room_id": "sample_room",
      "clip": "clip1_clear.mp4",
      "marker_id": 0,
      "marker_size_m": 0.15,
      "recorded_on": "2026-10-07"
    }

The values above are the sample's, not real ones. marker_size_m must be the measured size.

## Where files go

Clips are large: not in git. Share by link and note the link in docs/install-notes.md. Put only small samples in git.

## Open before filming

1. Marker size and ids (Kaushal, D7 and D11).
2. Whether clip3_unseen's unseen area is a wall, a corner or the floor behind an object (Nadeem, ties to T10's coverage check).
