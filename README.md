# Voice RAG

B2B-oriented **voice + text** knowledge pipeline with RAG: ingest calls and documents into a shared vector index, query via LiteLLM, cite sources. See **[SPEC.md](SPEC.md)** for the full product and engineering specification (v0.6).

**Status:** Specification and planning; implementation follows [docs/IMPLEMENTATION_PLAN.zh.md](docs/IMPLEMENTATION_PLAN.zh.md).

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
