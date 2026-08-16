"""Deterministic GitHub-visible acceptance contract for the public ecosystem.

This module validates repository inventory and architectural ownership only.
Runtime evidence (browser rendering, TLS handshakes, native execution, persistence,
etc.) remains represented separately by :mod:`cosmos.evidence` and must not be
inferred from this contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Iterable, Mapping


PUBLIC_REPOSITORIES = (
    "Aivra", "Algora", "Avyra", "cast", "Chrona", "Codane", "Cosmos", "Droidra",
    "Edryx", "huobz", "Lexane", "Lumera", "Lyvera", "Medora", "Mivra", "neuron",
    "nifdu", "Nimora", "Pactra", "Portis", "rangoons", "Rangora", "Rivora", "Rydea",
    "Sakina", "Savora", "shmry", "sophyane", "Veyron", "Voltara", "Voxara", "xerus",
)

PRIVATE_REPOSITORIES = ("SHMRY_BUNKER",)

CANONICAL_OWNERS = {
    "semantic_planning": "sophyane",
    "memory": "xerus",
    "visual_evidence": "nifdu",
    "http_tls": "Veyron",
    "language_compiler": "Lexane",
    "neural_compute": "neuron",
    "cloud_artifacts": "shmry",
    "coordination": "Cosmos",
}

CORE_GRAPH = {
    "sophyane": ("Lexane", "neuron", "xerus", "nifdu", "Veyron", "Cosmos"),
    "Cosmos": ("sophyane", "xerus", "Lexane", "neuron", "nifdu", "Veyron", "shmry"),
    "shmry": ("Cosmos",),
    "Lexane": ("sophyane",),
    "neuron": ("sophyane",),
    "xerus": ("sophyane",),
    "nifdu": ("sophyane",),
    "Veyron": ("sophyane",),
}


@dataclass(frozen=True)
class AcceptanceResult:
    public_count: int
    private_count: int
    exact_public_set: bool
    exact_private_set: bool
    unique_owners: bool
    core_graph_connected: bool
    digest: str

    @property
    def passed(self) -> bool:
        return all((
            self.public_count == 32,
            self.private_count == 1,
            self.exact_public_set,
            self.exact_private_set,
            self.unique_owners,
            self.core_graph_connected,
        ))


def _normalised(values: Iterable[str]) -> tuple[str, ...]:
    cleaned = [value.strip() for value in values if value and value.strip()]
    return tuple(sorted(cleaned, key=str.lower))


def _graph_connected(graph: Mapping[str, Iterable[str]], nodes: Iterable[str]) -> bool:
    wanted = set(nodes)
    if not wanted:
        return True
    adjacency: dict[str, set[str]] = {node: set() for node in wanted}
    for source, targets in graph.items():
        if source not in wanted:
            continue
        for target in targets:
            if target in wanted:
                adjacency[source].add(target)
                adjacency[target].add(source)
    start = next(iter(wanted))
    seen = {start}
    stack = [start]
    while stack:
        current = stack.pop()
        for neighbour in adjacency[current] - seen:
            seen.add(neighbour)
            stack.append(neighbour)
    return seen == wanted


def validate_ecosystem(
    public_repositories: Iterable[str] = PUBLIC_REPOSITORIES,
    private_repositories: Iterable[str] = PRIVATE_REPOSITORIES,
) -> AcceptanceResult:
    public = _normalised(public_repositories)
    private = _normalised(private_repositories)
    expected_public = _normalised(PUBLIC_REPOSITORIES)
    expected_private = _normalised(PRIVATE_REPOSITORIES)

    owner_values = tuple(CANONICAL_OWNERS.values())
    unique_owners = len(owner_values) == len(set(owner_values))
    owner_nodes = set(owner_values)
    connected = _graph_connected(CORE_GRAPH, owner_nodes)

    payload = {
        "public": public,
        "private": private,
        "owners": sorted(CANONICAL_OWNERS.items()),
        "graph": {key: sorted(value) for key, value in sorted(CORE_GRAPH.items())},
    }
    digest = sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    return AcceptanceResult(
        public_count=len(public),
        private_count=len(private),
        exact_public_set=public == expected_public,
        exact_private_set=private == expected_private,
        unique_owners=unique_owners,
        core_graph_connected=connected,
        digest=digest,
    )


__all__ = [
    "AcceptanceResult",
    "CANONICAL_OWNERS",
    "CORE_GRAPH",
    "PRIVATE_REPOSITORIES",
    "PUBLIC_REPOSITORIES",
    "validate_ecosystem",
]
