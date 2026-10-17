"""Optional Gemini rewording of an answer (T16). Standard library only.

The model may only reword. guard() rejects any rewrite that changes a verdict, drops or adds a number, or
loses the requested view; the caller then returns the template text. The verdict never comes from here.

    GEMINI_API_KEY   key from Google AI Studio, set in the environment (never in git)
    GEMINI_MODEL     model id to call; no default on purpose, the id is not verified here
"""
import json
import os
import re
import urllib.request

VERDICT_RE = {"pass": r"\bpass(es|ed)?\b", "fail": r"\bfail(s|ed|ure)?\b", "not_proven": r"\bnot[ _]proven\b"}
NUM_RE = re.compile(r"\d+(?:\.\d+)?")
OVERCLAIM_RE = re.compile(r"\b(safe|unsafe|compliant|compliance|certified|hazard[- ]free)\b")  # the evidence never says safe

PROMPT = ("Reword the safety-inspection answer below in one or two plain sentences for a facility manager. "
          "Do not change any verdict, number or unit. Do not add facts, advice or instructions. Name each measurement as the text does (a distance stays a distance). If a view is missing, keep the request.\n\n")


def guard(rewrite, template, claims):
    """Return None if the rewrite is acceptable, else the reason it was discarded."""
    low = rewrite.lower()
    for verdict, pattern in VERDICT_RE.items():
        wanted = any(c["verdict"] == verdict for c in claims)
        found = re.search(pattern, low) is not None
        if wanted and not found:
            return f"missing verdict {verdict}"
        if found and not wanted:
            return f"adds verdict {verdict}"
    if OVERCLAIM_RE.search(low) and not OVERCLAIM_RE.search(template.lower()):
        return "claims beyond the evidence (safe or compliant)"
    allowed = set(NUM_RE.findall(template))
    extra = set(NUM_RE.findall(rewrite)) - allowed
    if extra:
        return f"numbers not in the evidence: {sorted(extra)}"
    for c in claims:
        if c["value"] is not None:
            forms = {str(c["value"])}  # a whole number may be written 1 or 1.0
            if float(c["value"]).is_integer():
                forms.add(str(int(c["value"])))
            if not any(f in rewrite for f in forms):
                return f"missing value {c['value']}"
    if any(c["verdict"] == "not_proven" for c in claims) and "view" not in low and "film" not in low:
        return "requested view dropped"
    return None


def gemini_rewrite(template):
    """Call Gemini and return its text. Raises on any error; the caller falls back to the template."""
    key, model = os.environ["GEMINI_API_KEY"], os.environ["GEMINI_MODEL"]
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps({"contents": [{"parts": [{"text": PROMPT + template}]}]}).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": key})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)["candidates"][0]["content"]["parts"][0]["text"].strip()


def configured():
    return bool(os.environ.get("GEMINI_API_KEY") and os.environ.get("GEMINI_MODEL"))
