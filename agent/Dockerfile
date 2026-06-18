# Worker do Medusa Cut (roda na VPS). Processa a fila de jobs do Supabase.
FROM python:3.12-slim

# ffmpeg (transcode/render) + libs do OpenCV + fonte bold pra legenda (Linux nao tem
# Impact/Arial Black; usa DejaVu Bold via CAPTION_FONT).
RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg libgl1 libglib2.0-0 fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

ENV CAPTION_FONT=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf \
    HF_HOME=/cache/huggingface \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .

# o cache do modelo do whisper vive em volume (ver docker-compose) pra nao baixar
# de novo a cada restart.
CMD ["medusacut-worker"]
