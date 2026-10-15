"""python3 adapters/google/test_app.py  (run from the repo root; needs fastapi and httpx, skips itself without them)"""
import os
import sys

try:
    from fastapi.testclient import TestClient
except ImportError:
    print("skipped: fastapi and httpx not installed")
    sys.exit(0)

here = os.path.dirname(os.path.abspath(__file__))
os.environ["EVIDENCE_DIR"] = os.path.join(here, "..", "..", "viewer", "demo")
os.environ["EVIDENCE_PATH"] = os.path.join(here, "..", "..", "samples", "handmade", "good", "evidence.json")
os.environ.pop("GEMINI_API_KEY", None)  # template answers only: no network in this test
sys.path.insert(0, here)
import app  # noqa: E402

c = TestClient(app.app)
if not os.path.isdir(os.environ["EVIDENCE_DIR"]):
    print("skipped: viewer/demo not built")
    sys.exit(0)
assert c.get("/health").json()["clips"], "no clips listed"
r = c.post("/ask", json={"question": "Is the exit clear?", "clip": "clip2_blocked"}).json()
assert r["claims"][0]["verdict"] == "fail" and r["claims"][0]["value"] == 0.7 and r["source"] == "evidence_template", r
r = c.post("/ask", json={"question": "Is the exit clear?", "clip": "clip3_unseen"}).json()
assert r["claims"][0]["verdict"] == "not_proven" and "Film the floor" in r["answer"], r
r = c.post("/ask", json={"question": "Is exit_2 clear?"}).json()   # no clip: the default file
assert r["claims"][0]["id"] == "exit_2_clear", r
assert c.post("/ask", json={"question": "x", "clip": "../../etc"}).status_code == 400
assert c.post("/ask", json={"question": "x", "clip": "nope"}).status_code == 404
assert c.post("/ask", json={"question": "x" * 301}).status_code == 422
assert c.options("/ask", headers={"Origin": "https://example.web.app", "Access-Control-Request-Method": "POST"}).headers.get("access-control-allow-origin") == "*"
print("ok")
