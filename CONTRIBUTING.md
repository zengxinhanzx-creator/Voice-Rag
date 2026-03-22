# Contributing to Voice RAG

Thank you for your interest in this project.

## How to contribute

1. **Issues** — Open an issue to discuss bugs, features, or design questions before large changes.
2. **Pull requests** — Keep changes focused; reference related issues when applicable.
3. **Specification** — Product and API behavior is defined in [`SPEC.md`](SPEC.md). Implementation milestones are tracked in [`docs/IMPLEMENTATION_PLAN.zh.md`](docs/IMPLEMENTATION_PLAN.zh.md).

## Development setup

When the Python package is present (`pyproject.toml` at the repo root):

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest
ruff check .
ruff format .
```

Copy `.env.example` to `.env` and configure keys as described in the spec and README.

## Code style

- Python 3.11+
- Formatter and linter: **Ruff** (see `pyproject.toml` when available)

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (see `LICENSE` when present).
