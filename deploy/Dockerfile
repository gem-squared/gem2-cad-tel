# CAD Trust Engine Lite — production container
# Base: python:3.12-slim (Debian Trixie). Apt for poppler (pdf2image runtime),
# then pip for opencv-headless + paddleocr stack. Models download lazily on
# first OCR call (~500MB; one-time per container).

FROM python:3.12-slim

LABEL org.opencontainers.image.title="CAD Trust Engine Lite"
LABEL org.opencontainers.image.description="Per-field EEF-tagged JSON + Refusal Over Bluff for CAD/floor plan recognition"
LABEL org.opencontainers.image.source="https://github.com/gem-squared/gem2-cad-tel"
LABEL org.opencontainers.image.licenses="MIT-equivalent (proprietary source, public-licensed corpus)"

# System deps — only poppler-utils is strictly required at runtime
# (pdf2image shells out to pdftoppm); curl is for HEALTHCHECK.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        poppler-utils \
        curl \
        ca-certificates \
        tini \
    && rm -rf /var/lib/apt/lists/*

# Set up app user (avoid running as root inside container)
RUN useradd --create-home --uid 1000 cadtrust

WORKDIR /app

# Copy requirements first for Docker layer cache friendliness — pip install
# only re-runs when requirements.txt actually changes
COPY requirements.txt /app/requirements.txt

# Pin pip; install in --no-cache-dir to keep image lean
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/requirements.txt

# Copy the rest of the project (respects .dockerignore)
COPY . /app

# Persistent state — audit DB writes here; mounted as a named volume in compose
ENV GEM2_VISION_AUDIT_DB=/data/audit.sqlite
RUN mkdir -p /data && chown -R cadtrust:cadtrust /data /app

USER cadtrust

# Streamlit binds to 0.0.0.0 inside the container; Caddy is the only thing
# exposed to the public internet
EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -fsS http://localhost:8501/_stcore/health || exit 1

# tini reaps zombies + handles SIGTERM cleanly so docker stop terminates fast
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "-m", "streamlit", "run", "ui/app.py", \
     "--server.address=0.0.0.0", \
     "--server.port=8501", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false", \
     "--server.enableCORS=false", \
     "--server.enableXsrfProtection=true"]
