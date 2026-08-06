FROM python:3.11-slim

# Install system dependencies (FFmpeg & FFprobe required for 4K video merging & 320kbps audio extraction)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    ca-certificates \
    nodejs \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Deno (JS runtime required by yt-dlp for YouTube cipher decryption)
RUN curl -fsSL https://deno.land/install.sh | sh \
    && cp /root/.deno/bin/deno /usr/local/bin/deno \
    && chmod 755 /usr/local/bin/deno \
    && deno --version

WORKDIR /app

# Copy requirements and install
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir -U yt-dlp

# Copy backend source code
COPY backend /app/backend

# Expose port
EXPOSE 8000

# Set Python path to include /app so modules inside backend import cleanly
ENV PYTHONPATH=/app

# Command to run FastAPI server with Uvicorn
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
