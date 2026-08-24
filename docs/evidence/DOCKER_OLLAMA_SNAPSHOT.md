# Docker Ollama evidence snapshot

Observed on 2026-08-24 after `docker compose up -d ollama` and local model initialization.

```text
Container: jp-patent-ollama
Ollama version: 0.32.15
Host binding: 127.0.0.1:11435 -> container 11434
Production model: qwen3:1.7b
Ollama model ID: 8f68893c685c
Size: ~1.4 GB
Reported parameters: 2.0B
Format: GGUF
Quantization: Q4_K_M
Cloud inference: disabled
```

The Compose image is pinned to digest
`sha256:57d60e686821ea81a7748a3ec8141308c8b8f95b27105713954abf7a6529e700`.

Hardware observation:

```text
GPU: NVIDIA GeForce RTX 3060 Laptop GPU, 6144 MiB
Driver: 546.30
Ollama reported minimum: 550
Active inference backend: CPU fallback
```

This warning does not block local inference. Updating the host NVIDIA driver is optional and is
not performed by the project scripts.

The larger `qwen3:4b` was measured first but exceeded the 180-second CPU timeout with an
eight-passage prompt. The production choice combines four retrieved UI results, a coherent
two-passage generation pack, JSON-schema output, and `qwen3:1.7b`; the final cold-container E2E
completed in 29.93 seconds and the warmed native run in 8.26 seconds.
