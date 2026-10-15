"""Checker settings (T34).

TOLERANCE is a PLACEHOLDER, not a decision. D8 sets the real value after the T5 spike.
It is in metres. Doubling a door width (the tamper test) must exceed it, so keep it well below 0.9.
"""

TOLERANCE = 0.01  # PLACEHOLDER until D8

# Rule parameters have no default on purpose: docs/rules-spec.md keeps them blank until D8.
# They are passed in with --params (a JSON object with these names).
REQUIRED_PARAMS = (
    "MIN_EXIT_CLEARANCE_M",
    "CORRIDOR_HALF_WIDTH_M",
    "FLOOR_BAND_M",
    "OBSTACLE_MAX_Z_M",
    "MIN_FLOOR_POINTS",
    "MIN_DOOR_CLEAR_WIDTH_M",
)
