from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Route:
    repositories: tuple[str, ...]
    capabilities: tuple[str, ...]


def _terms(text: str) -> set[str]:
    return {
        token.strip(".,!?;:()[]{}").casefold()
        for token in text.split()
        if token.strip()
    }


def resolve(request: str) -> Route:
    """
    Lightweight Cosmos control-plane routing.

    Sophyane remains the semantic planner.
    Cosmos only selects obvious capability gateways before
    delegating deeper planning to Sophyane.
    """

    terms = _terms(request)

    repos: list[str] = ["sophyane"]
    caps: list[str] = ["plan"]

    def add(repo: str, capability: str) -> None:
        if repo not in repos:
            repos.append(repo)

        if capability not in caps:
            caps.append(capability)

    if terms & {
        "remember",
        "memory",
        "recall",
        "history",
        "persist",
        "store",
    }:
        add("xerus", "memory")

    if terms & {
        "compile",
        "compiler",
        "language",
        "tokenize",
        "semantic",
        "ir",
    }:
        add("HuobzLang", "language")

    if terms & {
        "neuron",
        "neural",
        "intelligence",
        "spike",
        "synapse",
    }:
        add("neuron", "neural_intelligence")

    if terms & {
        "website",
        "web",
        "serve",
        "http",
        "https",
        "tls",
        "network",
    }:
        add("vps", "transport")

    if terms & {
        "screenshot",
        "visual",
        "browser",
        "render",
        "responsive",
        "verify",
    }:
        add("nifdu", "visual_verify")

    if terms & {
        "cloud",
        "artifact",
        "manifest",
        "account",
    }:
        add("shmry", "artifact")

    # State persistence is useful for any multi-component request.
    if len(repos) > 1:
        add("xerus", "state")

    return Route(
        repositories=tuple(repos),
        capabilities=tuple(caps),
    )
