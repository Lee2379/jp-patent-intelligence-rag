# Security policy

## Scope

This is a local portfolio application. It is not exposed to the public internet and is not a
legal production service.

## Controls

- API inputs are length- and type-validated with Pydantic.
- Browser output is HTML-escaped before rendering.
- The Ollama model receives bounded patent evidence and has no tools or filesystem access.
- Citation IDs are validated against the evidence allow-list.
- Docker services bind to loopback interfaces.
- Source data and indexes are excluded from Git.
- Prompt, answer, evidence, and review events are kept in an ignored local SQLite database.
- Audit rows reject ordinary update/delete statements and are linked by a verified SHA-256 chain.
- Local operator labels are explicitly not treated as authenticated identities.
- No secrets or third-party API keys are required.

## Reporting

Open a private GitHub security advisory for a discovered vulnerability. Do not include private
data or machine-specific paths in a public issue.
