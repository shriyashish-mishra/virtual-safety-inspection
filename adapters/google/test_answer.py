"""python3 adapters/google/test_answer.py  (run from the repo root; no packages needed)"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import answer  # noqa: E402

GOOD = os.path.join(os.path.dirname(__file__), "..", "..", "samples", "handmade", "good", "evidence.json")
ev = answer.load(GOOD)

r = answer.answer(ev, "Is exit_2 clear?")
assert r["claims"][0]["verdict"] == "not_proven" and "Film the floor" in r["answer"], r
r = answer.answer(ev, "How wide is the door?")
assert [c["id"] for c in r["claims"]] == ["door_1_width"] and r["claims"][0]["value"] == 0.9, r
r = answer.answer(ev, "Give me a summary")
assert len(r["claims"]) == 3, r

# model rewording: accepted only if it keeps every verdict, number and the requested view
r = answer.answer(ev, "Is exit_2 clear?", lambda t: "Exit 2 is not proven; please film the floor in front of exit_2 from about 2 m away with the exit marker in frame.")
assert r["source"] == "model_rewording", r
r = answer.answer(ev, "Is exit_2 clear?", lambda t: "Exit 2 is clear. Pass.")
assert r["source"] == "evidence_template" and "explanation_discarded" in r, r
r = answer.answer(ev, "How wide is the door?", lambda t: "The door is 1.2 m wide, pass.")
assert r["source"] == "evidence_template" and "numbers" in r["explanation_discarded"], r
r = answer.answer(ev, "How wide is the door?", lambda t: "The door is wide enough.")
assert r["source"] == "evidence_template", r
r = answer.answer(ev, "How wide is the door?", lambda t: "The door is 0.9 m wide, a pass, so the room is safe.")
assert r["source"] == "evidence_template" and "beyond the evidence" in r["explanation_discarded"], r
def boom(t): raise OSError("offline")
r = answer.answer(ev, "How wide is the door?", boom)
assert r["source"] == "evidence_template" and "failed" in r["explanation_discarded"], r
print("ok")
