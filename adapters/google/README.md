# Google adapter (T16)

A thin service that answers questions from a stored `evidence.json`. The verdict, value and requested view
are copied from the file. Gemini may only reword the answer; `explain.guard()` discards any rewrite that
changes a verdict, adds or drops a number, or loses the requested view.

Run locally (no packages needed for the core):

    python3 adapters/google/test_answer.py

Run the API:

    pip install -r adapters/google/requirements.txt
    cd adapters/google && EVIDENCE_PATH=../../samples/handmade/good/evidence.json uvicorn app:app --port 8080
    curl -s localhost:8080/ask -H 'content-type: application/json' -d '{"question":"Is exit_2 clear?"}'

Several clips from one service: set `EVIDENCE_DIR` to a folder with one subfolder per clip (`viewer/demo` has the three synthetic clips) and send `{"question": "...", "clip": "clip2_blocked"}`; without `clip` the file in `EVIDENCE_PATH` answers. The service allows cross-origin calls, so the static viewer (`viewer/`, `?api=<service url>`) can be hosted elsewhere. A question is capped at 300 characters to protect the free Gemini quota. Test (needs fastapi and httpx): `python3 adapters/google/test_app.py`.

Gemini (optional): set `GEMINI_API_KEY` (Google AI Studio) and `GEMINI_MODEL` in the environment. Without
both, answers use the template text. Never commit the key. The model id is deliberately not defaulted
(UNVERIFIED which ids the free tier allows).

Cloud Run (needs your Google Cloud project, free tier only; billing terms UNVERIFIED):

    docker build -f adapters/google/Dockerfile -t hallucinati-google .
    gcloud run deploy hallucinati-google --source . --region <region> --allow-unauthenticated \
      --set-env-vars GEMINI_MODEL=<model> --set-secrets GEMINI_API_KEY=<secret>:latest

The image ships the hand-made sample evidence and the three synthetic clips' evidence (built from scene truth, not by the rules), not measurements, until T11 writes real evidence.
