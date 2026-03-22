# Voice RAG

[![CI](https://github.com/zengxinhanzx-creator/Voice-Rag/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/zengxinhanzx-creator/Voice-Rag/actions/workflows/ci.yml)

**GitHub:** [zengxinhanzx-creator/Voice-Rag](https://github.com/zengxinhanzx-creator/Voice-Rag)

B2B-oriented **voice + text** knowledge pipeline with RAG: ingest calls and documents into a shared vector index, query via [LiteLLM](https://github.com/BerriAI/litellm), cite sources. Product and API behavior are defined in **[SPEC.md](SPEC.md)** (v0.6).

**Status:** P0 text RAG (local `.txt` / `.md`, Chroma, citations) is implemented; call ingest, URL ingest, and admin UI are planned per [docs/IMPLEMENTATION_PLAN.zh.md](docs/IMPLEMENTATION_PLAN.zh.md).

## Quickstart

1. `cp .env.example .env` and set at least `OPENAI_API_KEY` (or another provider key supported by LiteLLM) if you use cloud LLM generation.
2. Create a virtualenv and install:

```bash
pip install -e ".[dev]"
```

3. Index documents and ask:

```bash
voice-rag index-docs ./path/to/docs
voice-rag ask "Your question?"
```

4. HTTP API:

```bash
uvicorn voice_rag.api.main:app --host 0.0.0.0 --port 8000
```

- `GET /health` — `{ "status": "ok", "llm_model": "...", "embed_mode": "..." }`
- `POST /api/v1/query` — JSON `{ "text": "...", "tenant_id": null, "top_k": 5 }` → `Answer` shape (see SPEC §6.6)

Embeddings default to **local** `sentence-transformers` (`VOICERAG_EMBED_MODE=local`). Set `VOICERAG_EMBED_MODE=litellm` and `VOICERAG_EMBED_MODEL` for API embeddings.

### Docker

```bash
cp .env.example .env   # optional; compose references .env if present
docker compose up --build
```

Service listens on port **8000**. Vector data persists in the named volume `voice_rag_data` (see `docker-compose.yml`).

### Configuration notes

- **`VOICERAG_CHUNK_SIZE` / `VOICERAG_CHUNK_OVERLAP`:** units are **characters** (see SPEC §8 / §16).
- **CORS:** the demo API enables `Access-Control-Allow-Origin: *` without credentials. For production, put the API behind a reverse proxy and restrict origins (SPEC §12.0).

### Legal / content (NFR-11)

**Web crawling, third-party sites, and copyright:** deployment and compliance are your responsibility. This project provides technical knobs (e.g. URL allowlists, timeouts); it does not bypass paywalls or terms of service on your behalf. See SPEC **NFR-11**.

## Development

```bash
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest && ruff check . && ruff format --check .
```

## License

MIT — see [LICENSE](LICENSE).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Security

See [SECURITY.md](SECURITY.md).
