$ErrorActionPreference = "Stop"

uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src/patent_rag
uv run pytest --cov=patent_rag --cov-report=term-missing
docker compose config --quiet

Write-Host "All local quality gates passed." -ForegroundColor Green
