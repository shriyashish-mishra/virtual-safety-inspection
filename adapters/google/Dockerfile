# Build from the repo root:  docker build -f adapters/google/Dockerfile -t hallucinati-google .
FROM python:3.12-slim
WORKDIR /app
COPY adapters/google/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY adapters/google/app.py adapters/google/answer.py adapters/google/explain.py ./
# SAMPLE evidence only: the hand-made file, and the three synthetic clips' evidence (built from scene truth, not by the rules) until T11 writes real evidence
COPY samples/handmade/good/evidence.json ./evidence.json
COPY viewer/demo ./demo
ENV EVIDENCE_PATH=/app/evidence.json EVIDENCE_DIR=/app/demo
# Cloud Run sets PORT; GEMINI_API_KEY and GEMINI_MODEL come from Cloud Run settings, never from the image
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080}"]
