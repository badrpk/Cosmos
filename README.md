# Cosmos

Cosmos is the control plane, dashboard, and input gateway for the
Shmry Software Inc ecosystem.

Cosmos accepts a requested output, determines which capabilities are
needed, selects peer repositories, executes through bounded adapters,
collects results, stores task state, and exposes output through an API
and dashboard.

## Ecosystem role

Cosmos coordinates 32 peer repositories.

Canonical capabilities remain owned by their respective projects:

- Sophyane: semantic planning, orchestration and validation
- Xerus: durable memory and retrieval
- HuobzLang: language/compiler capability
- Neuron: neural/intelligence capability
- VPS: transport
- Nifdu: rendered visual verification
- Shmry: artifact/cloud/storage capability

Cosmos does not duplicate those implementations.

## API

- POST /api/request
- GET /api/task/<id>
- GET /api/repos
- GET /api/repos/<name>/health
- GET /

## Run

    PYTHONPATH=. COSMOS_PORT=8787 python3 -m cosmos.server

## Test

    PYTHONPATH=. python3 -m pytest -q tests
