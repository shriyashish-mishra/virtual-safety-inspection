# clip2_blocked: synthetic fixture

ILLUSTRATIVE: supplied synthetic render, not real-room capture or tape measurements. This fixture does not complete T2. See ../ground_truth.synthetic.json for supplied scene dimensions; all three synthetic clip folders have been provided.

## Video (kept outside git)

- Filename: clip2_blocked.mp4
- Duration: 21 seconds; 630 frames; 30 fps; 1280 x 720 (read with ffprobe).
- Size: 16,318,568 bytes.
- SHA-256: d238ea7b8821c50e0fef354228c3c5b794b9814b20cd55050bd737ed3935c6dd
- Shared-storage link: pending. Source supplied as a local download; teammate access has not been checked.

## Metadata checks

- capture.json and geometry_truth.json pass the respective repo schemas.
- Capture filename, room ID, scale-marker ID and side length agree with scene/geometry metadata.
- Geometry references the present points_truth.json, containing 1,881 finite 3D points.
- Geometry has 126 frame entries and 126 camera poses with matching IDs; timestamps lie within the 21-second video.
- Geometry door endpoints give 0.86 m horizontal width, agreeing with supplied scene truth.
- Supplied scene truth states 0.7 m exit clearance and expected exit verdict fail. Clearance and verdict were not independently recomputed; D8's real thresholds are not confirmed.
- check.json contains supplied marker-detection/error statistics, not independently reproduced here; it is not a checker_report.json.
- The dictionary is labelled UNVERIFIED in scene_truth.json. Synthetic marker values do not confirm D7/D11 for real capture.

Original JSON files are preserved without alterations. The full video is outside git, and these synthetic values are not placed in a real ground-truth file.
