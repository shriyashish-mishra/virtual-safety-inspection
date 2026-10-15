#!/usr/bin/env python3
"""Build the static folder that Firebase Hosting serves (T16, D16 route B+). Standard library only.

    python3 scripts/build_hosting.py            # writes hosting-dist/ (git-ignored)

hosting-dist/ holds the viewer, its demo data and the hand-made samples, plus a root page that opens the first clip.
No clips and no keys in git: if an untracked firebase-config.json (Firebase web config) sits in the repo root it is copied in,
and the page then offers a live question box (viewer/live.js). firebase.json points at hosting-dist/.
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "hosting-dist"
SKIP = shutil.ignore_patterns("README.md", ".DS_Store", "__pycache__")

INDEX = """<!doctype html>
<meta charset="utf-8">
<title>Virtual Safety Inspection</title>
<noscript><meta http-equiv="refresh" content="0; url=viewer/?clip=clip1_clear"></noscript>
<script>location.replace("viewer/" + (location.search || "?clip=clip1_clear"));</script>
<p><a href="viewer/?clip=clip1_clear">Open the viewer</a></p>
"""


def main():
    if not (ROOT / "viewer" / "index.html").exists() or not (ROOT / "viewer" / "demo" / "index.json").exists():
        sys.exit("viewer/index.html or viewer/demo is missing; run from a full checkout")
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(ROOT / "viewer", OUT / "viewer", ignore=SKIP)
    shutil.copytree(ROOT / "samples", OUT / "samples", ignore=shutil.ignore_patterns("t2", ".DS_Store"))
    shutil.copytree(ROOT / "adapters" / "google" / "web", OUT / "web", ignore=shutil.ignore_patterns("README.md", "test_*", ".DS_Store"))
    config = ROOT / "firebase-config.json"  # untracked: the Firebase web config, plus an optional appCheckSiteKey
    if config.exists():
        shutil.copy(config, OUT / "firebase-config.json")
    (OUT / "index.html").write_text(INDEX)
    files = [p for p in OUT.rglob("*") if p.is_file()]
    kb = sum(p.stat().st_size for p in files) // 1024
    print(f"wrote {OUT.relative_to(ROOT)}/: {len(files)} files, {kb} KB")


main()
