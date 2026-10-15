# clip3_unseen: synthetic fixture

ILLUSTRATIVE: supplied synthetic render, not real-room capture or tape measurements. All three synthetic fixtures are now present; T2's real-capture requirement remains incomplete. See ../ground_truth.synthetic.json.

## Video (kept outside git)

- Filename: clip3_unseen.mp4
- Duration: 18 seconds; 540 frames; 30 fps; 1280 x 720 (read with ffprobe).
- Size: 15,186,747 bytes.
- SHA-256: 8342e4f08ac0f978dc725023776ef869e384ab82d77328707a13f1bb50fd4d47
- Shared-storage link: pending. Source supplied as a local download; teammate access has not been checked.

## Metadata checks

- capture.json and geometry_truth.json pass the respective repo schemas.
- Capture filename, room ID, scale-marker ID and side length agree with scene/geometry metadata.
- Geometry references the present points_truth.json, containing 605 finite 3D points.
- Geometry has 108 frame entries and 108 camera poses with matching IDs; timestamps lie within the 18-second video.
- Geometry door endpoints give 0.86 m horizontal width, agreeing with supplied scene truth.
- Scene truth states 2.2 m physical scene clearance but expected exit verdict not_proven: floor corridor x 3.10..4.30 m, y 0.00..1.50 m is omitted. Supplied visibility statistics report zero corridor floor pixels. Visibility was not independently recomputed from the video here.
- The physical scene clearance is distinct from the evidence value: an unproven claim should have a null value under docs/rules-spec.md.
- check.json contains supplied marker-detection/error statistics, not independently reproduced here; it is not a checker_report.json.
- The dictionary is labelled UNVERIFIED in scene_truth.json. Synthetic marker values do not confirm D7/D11 for real capture.

Original JSON files are preserved without alterations. The video remains outside git and synthetic values are not placed in a real ground-truth file.
