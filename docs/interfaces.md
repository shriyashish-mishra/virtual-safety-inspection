# Interfaces between lanes

This is the interim contract: Kaushal and Nadeem start from it on day 1 without waiting for T1, and T1 turns it into the frozen schema. Only field names and meaning are fixed here; formats follow in T1.

| Hand-off | Producer | Consumer | Must contain |
| --- | --- | --- | --- |
| clip.mp4 plus capture.json | Shriyashish Mishra | Kaushal | Video, marker size in metres, room id. Filmed by Nadeem in T2; Shriyashish Mishra owns the capture.json format (T1); stored outside git, by link |
| geometry.json | Kaushal | Nadeem, checker | schema\_version, units (metres), scale\_source, camera\_poses, marker\_poses (marker id to pose), frame\_index, points\_ref (coarse point cloud or occupancy grid in metres), openings (door and exit positions found from marker ids, see D11) |
| evidence.json | Nadeem | Viewer, checker | schema\_version, room\_id, claims (id, type, verdict, value, unit, confidence, frame\_ids), coverage, requested\_view |
| checker\_report.json | Checker | Viewer, tracker | per claim: recomputed value, tolerance, result |

Three rules keep the checker honest and the lanes decoupled:

1. The checker reads only geometry.json and evidence.json. It never imports code from rules/.
2. Rules and checker are written from one written spec, docs/rules-spec.md, by two different people (D10): Nadeem writes the spec and the rules; Shriyashish Mishra writes the checker (T34). If they disagree, the spec is wrong and the team fixes the spec first.
3. The reasoning model may explain a verdict but can never change it; the verdict comes from the rules alone.

Tolerances are decided only after the spike (D8). Until then done-when tests say within tolerance and the number is blank on purpose, so nobody invents one. T4's tamper test uses one named constant in a single config file and a clearly large change (double the value); the constant is replaced after D8.
