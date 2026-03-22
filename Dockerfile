FROM python:3.12-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE /app/
COPY src /app/src

RUN pip install --no-cache-dir -U pip && pip install --no-cache-dir .

ENV VOICERAG_DATA_DIR=/app/data
EXPOSE 8000

CMD ["uvicorn", "voice_rag.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
