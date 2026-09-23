FROM python:3.10-slim

# Metadata
LABEL maintainer="pulsepoint-ai"
LABEL version="2.0.0"
LABEL description="PulsePoint AI Platform - Hardened Streamlit Container"
LABEL security.hardened="true"

WORKDIR /app

# Install minimal OS dependencies required for audio processing (ffmpeg, libsndfile1)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create unprivileged system user for runtime security
RUN useradd -m -u 1000 appuser

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code with non-root ownership
COPY --chown=appuser:appuser . .

# Switch to unprivileged user
USER appuser

EXPOSE 8501

# Hardened healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl --fail http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.enableCORS=false", "--server.enableXsrfProtection=true"]