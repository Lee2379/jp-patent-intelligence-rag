# Cost, privacy, and licensing

## Required cash cost: $0

| Component | Required implementation | Metered charge |
|---|---|---:|
| Patent corpus | NII LLM-jp Corpus v4 mirror, local files | $0 |
| Japanese tokenizer | SudachiPy + core dictionary | $0 |
| Embeddings | multilingual E5-small through FastEmbed/ONNX | $0 |
| Sparse and vector index | SciPy + NumPy files on local disk | $0 |
| Answer model | Qwen3 1.7B in Ollama Docker | $0 |
| API and UI | FastAPI + static HTML/CSS/JavaScript | $0 |
| Audit and review | Local SQLite + SHA-256 hash chain | $0 |
| Containers | Docker Desktop local runtime | $0 |
| CI | GitHub Actions within the repository's free allowance | $0 required locally |

No AWS, OpenAI, Anthropic, Pinecone, hosted database, telemetry service, or paid API is used.
The project has no field for an API key.

Electricity and the user's existing computer/network connection are ordinary local operating
costs and are not software-service charges.

## Privacy

- Queries and patent passages remain on the laptop.
- Ollama is reached through a loopback port or the private Compose network.
- The application sends no analytics, traces, or prompts to a third party.
- Prompts, retrieved passages, outputs, and review decisions are retained in the local audit
  database; it is excluded from Git and has no export or delete endpoint in the app.
- Model downloads require the internet once; inference does not.

## Licenses

- Corpus: CC BY 4.0. See the dataset card for attribution.
- Application code: Apache-2.0.
- Qwen3 model: Apache-2.0 according to its model distribution metadata.
- `intfloat/multilingual-e5-small`: MIT model card.

Model and corpus licenses remain independent from the application license.
