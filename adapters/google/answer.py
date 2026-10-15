"""Answer a question from stored evidence (T16). Standard library only.

The verdict, value and requested view are copied from evidence.json, never recomputed or changed.
A model may only reword the answer (explain.py); this file holds the facts and the fallback text.
"""
import json
import re

VERDICT_WORDS = {"pass": "pass", "fail": "fail", "not_proven": "not proven"}
TYPE_HINTS = {"blocked_exit": ("exit", "blocked", "egress"), "door_clear_width": ("door", "width", "wide")}


def load(path):
    with open(path) as f:
        return json.load(f)


def pick_claims(evidence, question):
    """Claims whose id appears in the question, else whose type hints match, else all claims."""
    q = question.lower().replace("_", " ")
    claims = evidence["claims"]
    # "exit_2" or "exit 2" selects exit_2_clear: match on the first two words of the claim id
    by_id = [c for c in claims if " ".join(c["id"].lower().split("_")[:2]) in q]
    if by_id:
        return by_id
    words = set(re.findall(r"[a-z]+", q))
    by_type = [c for c in claims if words & set(TYPE_HINTS.get(c["type"], ()))]
    return by_type or claims


def describe(claim, evidence):
    word = VERDICT_WORDS[claim["verdict"]]
    if claim["verdict"] == "not_proven":
        view = evidence.get("requested_view") or {}
        ask = view.get("description", "a view that covers it")
        return f"{claim['id']}: not proven. The evidence does not cover it. Missing view: {ask}."
    tail = f"(confidence {claim['confidence']}, frames {claim['frame_ids']})."
    if claim["type"] == "blocked_exit":
        # the value of a pass is the distance checked, not a measurement of free space
        if claim["verdict"] == "pass":
            return f"{claim['id']} ({claim['type']}): {word}. No obstacle found within {claim['value']} {claim['unit']} of the exit {tail}"
        return f"{claim['id']} ({claim['type']}): {word}. The nearest obstacle is {claim['value']} {claim['unit']} from the exit {tail}"
    return f"{claim['id']} ({claim['type']}): {word}, measured {claim['value']} {claim['unit']} {tail}"


def answer(evidence, question, rewrite=None):
    """rewrite: optional function(template_text) -> reworded text, e.g. explain.gemini_rewrite."""
    import explain
    claims = pick_claims(evidence, question)
    template = " ".join(describe(c, evidence) for c in claims)
    out = {"room_id": evidence["room_id"],
           "claims": [{k: c[k] for k in ("id", "type", "verdict", "value", "unit")} for c in claims],
           "answer": template, "source": "evidence_template"}
    if rewrite:
        try:
            text = rewrite(template)
            problem = explain.guard(text, template, claims)
            if problem is None:
                out.update(answer=text, source="model_rewording")
            else:
                out["explanation_discarded"] = problem
        except Exception as e:  # network, quota, bad key, bad response: the template answer stands
            out["explanation_discarded"] = f"model call failed: {type(e).__name__} {getattr(e, 'code', '')}".strip()
    return out
