#!/usr/bin/env python3
"""Precompute the viewer's demo answers with the Google adapter (adapters/google).  Standard library only.

    python3 tools/synthetic_room/make_demo_answers.py [--demo viewer/demo]

Writes answers.json next to each clip's evidence.json: for a fixed list of questions, the answer, where it
came from (evidence_template, or model_rewording when Gemini reworded it and explain.guard() accepted the
rewrite) and, when a rewrite was thrown away, why. Set GEMINI_API_KEY and GEMINI_MODEL in the environment to
let Gemini reword; without them every answer is the template text. The key is never written to a file.
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "adapters/google"))
import answer  # noqa: E402
import explain  # noqa: E402

QUESTIONS = [
    "Is the exit clear?",
    "How wide is the door?",
    "Is this room safe?",
    "What do you need from me?",
]


def retrying(call, tries=4):
    """Gemini's free tier answers 503 or times out now and then; retry with a growing pause before giving up."""
    def wrapped(text):
        for i in range(tries):
            try:
                return call(text)
            except Exception:
                if i == tries - 1:
                    raise
                time.sleep(5 * (i + 1))
    return wrapped


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--demo", default=str(ROOT / "viewer/demo"))
    a = ap.parse_args()
    use_model = explain.configured()
    print("Gemini rewording:", "on" if use_model else "off (set GEMINI_API_KEY and GEMINI_MODEL)")
    for clip_dir in sorted(Path(a.demo).glob("clip*")):
        evidence = answer.load(str(clip_dir / "evidence.json"))
        rows = []
        for q in QUESTIONS:
            r = answer.answer(evidence, q, retrying(explain.gemini_rewrite) if use_model else None)
            rows.append({"question": q, "answer": r["answer"], "source": r["source"],
                         "claims": [c["id"] for c in r["claims"]],
                         **({"explanation_discarded": r["explanation_discarded"]} if "explanation_discarded" in r else {})})
            if use_model:
                time.sleep(4)  # stay inside the free-tier request rate
        (clip_dir / "answers.json").write_text(json.dumps(rows, indent=1) + "\n")
        print(clip_dir.name, [(x["source"], x.get("explanation_discarded", "")) for x in rows])


if __name__ == "__main__":
    main()
