# syntax=docker/dockerfile:1

# 1. Base image: a slim Python 3.11 on Debian. "slim" = smaller than the full
#    image (no build tools/docs we don't need), bigger than "alpine" but far
#    fewer compatibility headaches with numpy/torch wheels.
FROM python:3.11-slim

# 2. Environment tuning for Python inside containers:
#    - PYTHONDONTWRITEBYTECODE: don't litter .pyc files
#    - PYTHONUNBUFFERED: print logs immediately (so `docker logs` is live)
#    - PIP_NO_CACHE_DIR: don't keep pip's download cache in the image
#    - HF_HOME: where sentence-transformers/HuggingFace cache the model, so we
#      can mount it as a volume and avoid re-downloading on every run.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/.cache/huggingface

# 3. All following commands run from /app inside the image.
WORKDIR /app

# 4. Install dependencies FIRST, copying only requirements.txt.
#    This layer is cached and only rebuilds when requirements.txt changes —
#    so editing source code later won't reinstall torch (the slow part).
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# 5. Now copy the application source. (Everything in .dockerignore is skipped.)
COPY . .

# 6. Run as a non-root user for safety, and give it ownership of the writable
#    dirs (SQLite DB + model cache).
RUN useradd --create-home appuser \
    && mkdir -p /app/.data /app/.cache/huggingface \
    && chown -R appuser:appuser /app
USER appuser

# 7. Document the port the server listens on (informational; publishing happens
#    at `docker run -p` / compose).
EXPOSE 8766

# 8. Container-level health check: Docker periodically asks the app "are you
#    alive?" by hitting /health. We use Python (no curl in the slim image).
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0) if urllib.request.urlopen('http://127.0.0.1:8766/health', timeout=3).status==200 else sys.exit(1)"

# 9. The default command. Note --host 0.0.0.0: inside a container the app MUST
#    bind to all interfaces, not 127.0.0.1, or the host can't reach it.
CMD ["python", "-m", "backend.api.server", "--host", "0.0.0.0", "--port", "8766"]
