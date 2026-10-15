# clip1_clear: synthetic fixture

ILLUSTRATIVE: this is a supplied synthetic render, not real-room capture. Its dimensions come from scene_truth.json and are not tape measurements. It does not complete T2. The ground-truth summary is ../ground_truth.synthetic.json; all three synthetic clip folders have been provided.

## Video (kept outside git)

- Filename: clip1_clear.mp4
- Duration: 21 seconds; 630 frames; 30 fps; 1280 x 720 (read with ffprobe).
- Size: 16,220,314 bytes.
- SHA-256: 363c8716fd52f5d1b4ea79d6fa23a95665fab68ec6eb9066410b5d214ce21443
- Shared-storage link: pending. Source supplied as a local download; teammate access has not been checked.

## Metadata checks

- capture.json passes schema/validate.py capture.
- geometry_truth.json passes schema/validate.py geometry.
- Geometry's referenced points_truth.json is present, with 1,349 finite 3D points.
- Both geometry frame_index and camera_poses have 126 entries. Their times fall within the video duration. These are sampled geometry frames, not all 630 video frames.
- Door endpoints in geometry give 0.86 m horizontal clear width, matching scene_truth.json.
- Scene truth states 2.2 m exit clearance and expected exit verdict pass. The clearance was not independently recomputed and D8's real thresholds are not confirmed.
- check.json's marker-detection and error statistics are supplied results, not independently reproduced here. They are not a checker_report.json.
- The marker dictionary is labelled UNVERIFIED in scene_truth.json; synthetic IDs and dimensions do not constitute Kaushal's real D7/D11 confirmation.

Original JSON files are preserved without alterations. No video is committed, and no a real ground-truth file with invented real measurements is created.
