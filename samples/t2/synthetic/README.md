# Synthetic three-clip fixture set

ILLUSTRATIVE: synthetic renders made by Shriya with tools/synthetic_room (PR #24) and preserved here by Nadeem, not real room captures. Scene dimensions are not tape measurements. These fixtures support synthetic testing and do not close T2's current real-capture requirement.

| Clip | Door width (scene m) | Exit clearance (scene m) | Supplied expected exit verdict | Video duration |
| --- | --- | --- | --- | --- |
| clip1_clear | 0.86 | 2.2 | pass | 21 s |
| clip2_blocked | 0.86 | 0.7 | fail | 21 s |
| clip3_unseen | 0.86 | 2.2 | not_proven | 18 s |

All capture and geometry JSON files pass the repo schemas. Original source metadata and small geometry/point files are preserved in each folder; full videos stay outside git. ground_truth.synthetic.json summarizes supplied scene truth with explicit synthetic provenance. complete_clip_set means the synthetic set only; real_capture_complete is false.

For clip3, scene truth names the omitted exit-floor corridor and reports zero visible corridor pixels; its physical clearance must not be treated as an observed evidence value. Supplied detection/error statistics are not independently reproduced and no rule/checker verdict run has been claimed. D8 thresholds remain unset.

Still needed: shared-storage folder link and teammate access confirmation. T2 completion also needs real recordings/measurements and marker confirmation, or an explicitly agreed scope change recorded by the team.
