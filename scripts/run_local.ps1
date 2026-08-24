$ErrorActionPreference = "Stop"

docker compose up -d ollama
$modelList = Invoke-RestMethod http://127.0.0.1:11435/api/tags
if (-not ($modelList.models.name -contains "qwen3:1.7b")) {
    docker compose --profile setup run --rm model-init
}

uv run uvicorn patent_rag.api.app:app --host 127.0.0.1 --port 8000
