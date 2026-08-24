# Local runbook

## One-time setup

```powershell
uv sync --dev
Copy-Item .env.example .env
docker compose up -d ollama
docker compose --profile setup run --rm model-init
docker compose --profile setup run --rm embedding-init
```

The dedicated host endpoint is `http://127.0.0.1:11435`. Inside Compose, the API uses
`http://ollama:11434`.

## Build the corpus and indexes

```powershell
uv run patent-rag prepare
uv run patent-rag report
uv run patent-rag build-index
uv run patent-rag evaluate
```

## Run the app

Native API process with Docker Ollama:

```powershell
uv run uvicorn patent_rag.api.app:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`.
Open `http://127.0.0.1:8000/audit` to inspect the local event chain.

Full Compose after the index exists:

```powershell
docker compose --profile app up -d --build
```

## Health checks

```powershell
Invoke-RestMethod http://127.0.0.1:11435/api/version
Invoke-RestMethod http://127.0.0.1:8000/api/health
docker exec jp-patent-ollama ollama list
docker logs --tail 100 jp-patent-ollama
Invoke-RestMethod http://127.0.0.1:8000/api/audit/verify
Invoke-RestMethod 'http://127.0.0.1:8000/api/audit/events?limit=5'
uv run patent-rag verify-audit
```

The prompt/answer/review database is `artifacts/audit/audit.sqlite3`. It is intentionally not
committed. Back it up as a SQLite database together with its `-wal` file only while the app is
stopped, or use SQLite's online backup mechanism in a production extension.

## Stop and restart

```powershell
docker compose stop
docker compose start ollama
```

The named `ollama-data` volume preserves the model. `docker compose down` removes containers
and the network but preserves named volumes unless `--volumes` is explicitly supplied.

## GPU note for this workstation

The RTX 3060 is supported, but Ollama's current container reports that driver 546.30 is below
its required 550 minimum, so inference falls back to CPU. Updating the NVIDIA driver is an
optional host-administration step; the application and data pipeline do not require it.
