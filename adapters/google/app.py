"""Thin Cloud Run service for the Google entry (T16): answers from stored evidence.

    EVIDENCE_PATH=samples/handmade/good/evidence.json uvicorn app:app --port 8080
    EVIDENCE_DIR=viewer/demo uvicorn app:app --port 8080     # one folder per clip: <clip>/evidence.json

POST /ask {"question": "...", "clip": "clip2_blocked"}. "clip" is optional and only used with EVIDENCE_DIR.
"""
import os
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import answer as core
import explain

EVIDENCE_PATH = os.environ.get("EVIDENCE_PATH", "evidence.json")
EVIDENCE_DIR = os.environ.get("EVIDENCE_DIR")
app = FastAPI(title="Hallucinati: Virtual Safety Inspection")
# The viewer is a static page on another origin (for example Firebase Hosting); the service serves only stored answers.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"], allow_headers=["content-type"])


class Question(BaseModel):
    question: str = Field(min_length=1, max_length=300)  # a short cap keeps the free Gemini quota from being burnt
    clip: str | None = None


def evidence_path(clip):
    if clip and EVIDENCE_DIR:
        if not re.fullmatch(r"[a-z0-9_-]{1,40}", clip):
            raise HTTPException(400, "bad clip name")
        path = Path(EVIDENCE_DIR) / clip / "evidence.json"
        if not path.is_file():
            raise HTTPException(404, f"no evidence for clip {clip}")
        return str(path)
    return EVIDENCE_PATH


@app.get("/health")
def health():
    return {"ok": True, "evidence": EVIDENCE_PATH, "clips": sorted(p.name for p in Path(EVIDENCE_DIR).iterdir() if p.is_dir()) if EVIDENCE_DIR and Path(EVIDENCE_DIR).is_dir() else []}


@app.post("/ask")
def ask(q: Question):
    rewrite = explain.gemini_rewrite if explain.configured() else None
    return core.answer(core.load(evidence_path(q.clip)), q.question, rewrite)
