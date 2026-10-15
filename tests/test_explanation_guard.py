"""T13: explanations match the evidence on all 3 clips, and deliberately wrong model output cannot change a verdict.

The "model" here is a stand-in function (no network): it plays a model that was given a wrong or hostile prompt.
answer.answer() must then return the evidence template, never the wrong text. Run: python3 tests/test_explanation_guard.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "adapters" / "google"))
import answer  # noqa: E402

QUESTIONS = ["Is the exit clear?", "How wide is the door?", "Is this room safe?", "What do you need from me?"]
FLIP = {"pass": "fail", "fail": "pass", "not_proven": "pass"}


def hostile(template, claims):
    """Wrong-prompt outputs: each is what a manipulated model might return."""
    first = claims[0]
    return {
        "says safe": "Everything is safe here, no need to worry.",
        "flips verdict": template.replace(first["verdict"].replace("_", " "), FLIP[first["verdict"]], 1),
        "invents number": template + " Clearance is 9.9 m.",
        "claims compliant": template + " The room is fully compliant.",
        "drops value": "The exit is fine.",
        "empty": "",
    }


def main():
    checked = bad = 0
    for d in sorted((ROOT / "viewer" / "demo").iterdir()):
        if not (d / "evidence.json").exists():
            continue
        ev = json.loads((d / "evidence.json").read_text())
        for q in QUESTIONS:
            base = answer.answer(ev, q)
            claims = answer.pick_claims(ev, q)
            template = base["answer"]
            # 1 the template matches the evidence: every claim's verdict word and value appear
            for c in claims:
                assert c["verdict"].replace("_", " ") in template, (d.name, q, c["id"])
                if c["value"] is not None:
                    assert str(c["value"]) in template, (d.name, q, c["id"], "value")
            # 2 hostile rewrites never get through
            for label, text in hostile(template, claims).items():
                out = answer.answer(ev, q, rewrite=lambda t, text=text: text)
                checked += 1
                if out["answer"] != template or out["source"] != "evidence_template":
                    bad += 1
                    print("LEAK", d.name, q, label, "->", out["answer"][:80])
                assert [x["verdict"] for x in out["claims"]] == [c["verdict"] for c in claims]
            # 3 a faithful rewording is allowed through
            ok = answer.answer(ev, q, rewrite=lambda t: t)
            assert ok["source"] == "model_rewording", (d.name, q, ok.get("explanation_discarded"))
    assert bad == 0, f"{bad} hostile rewrites got through"
    print(f"ok: {checked} hostile rewrites rejected on 3 clips; faithful rewording accepted; template matches the evidence")


main()
