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



# COSMOS_SHMRY_CLOUD_ROUTING_V1
def _is_shmry_deployment_intent(request: str) -> bool:
    text = request.strip().lower()

    if "shmry" not in text:
        return False

    return any(
        term in text
        for term in (
            "host",
            "hosting",
            "deploy",
            "deployment",
            "publish",
            "release",
            "put this on",
            "put it on",
        )
    )


def resolve(request: str) -> Route:
    """
    Lightweight Cosmos control-plane routing.

    Sophyane remains the semantic planner.
    Cosmos only selects obvious capability gateways before
    delegating deeper planning to Sophyane.
    """

    terms = _terms(request)

    repos: list[str] = []
    caps: list[str] = []

    def add(repo: str, capability: str) -> None:
        if repo not in repos:
            repos.append(repo)

        if capability not in caps:
            caps.append(capability)

    deployment_terms = {
        "deploy",
        "deployment",
        "publish",
        "published",
        "host",
        "hosting",
        "vercel",
        "netlify",
        "cloudflare",
        "godaddy",
        "porkbun",
        "domain",
        "dns",
        "production",
        "live",
        "provider",
        "cdn",
        "delivery",
    }

    if _is_shmry_deployment_intent(request):
        add("shmry", "deployment")
        add("shmry", "shmry_cloud")
    elif terms & deployment_terms:
        add("Portis", "deployment")

    # Deployment/session history belongs to Xerus.
    # These deterministic phrases are stronger than generic
    # semantic fallback because they explicitly refer to
    # previously-used state.
    memory_context_terms = {
        "remember",
        "memory",
        "recall",
        "history",
        "persist",
        "store",
        "usual",
        "previous",
        "previously",
    }

    same_context = (
        "same" in terms
        and bool(
            terms
            & {
                "account",
                "host",
                "hosting",
                "provider",
                "domain",
            }
        )
    )

    last_context = (
        "last" in terms
        and "time" in terms
    )

    existing_context = (
        bool(
            terms
            & {
                "already",
                "existing",
                "current",
            }
        )
        and bool(
            terms
            & {
                "account",
                "host",
                "hosting",
                "provider",
                "domain",
                "dns",
                "managed",
                "configured",
            }
        )
    )

    if (
        terms & memory_context_terms
        or same_context
        or last_context
        or existing_context
    ):
        add("xerus", "memory")

    # Provider ranking is an algorithm-selection problem.
    # Algora owns deterministic comparison/selection rather
    # than Sophyane or Cosmos inventing a provider choice.
    provider_selection = (
        bool(
            terms
            & {
                "cheapest",
                "lowest",
                "cost",
                "affordable",
                "best",
                "value",
                "cdn",
                "global",
                "edge",
            }
        )
        and bool(
            terms
            & (
                deployment_terms
                | {
                    "provider",
                    "delivery",
                }
            )
        )
    )

    if provider_selection:
        add("Algora", "provider_selection")

    # Requests explicitly asking to minimize production/config
    # change are safe-change planning work owned by Codane.
    safe_change = (
        bool(
            terms
            & {
                "avoid",
                "minimal",
                "minimum",
                "safest",
                "safe",
                "necessary",
            }
        )
        and bool(
            terms
            & {
                "change",
                "changing",
                "config",
                "configuration",
                "production",
                "deploy",
                "deployment",
            }
        )
    )

    if safe_change:
        add("Codane", "safe_change_planning")

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

    # Sophyane is the semantic/ontology fallback.
    # Explicit deterministic requests should first go directly
    # to the canonical capability owner.
    if not repos:
        add("sophyane", "plan")

    # State persistence is useful for any multi-component request.
    if len(repos) > 1:
        add("xerus", "state")

    return Route(
        repositories=tuple(repos),
        capabilities=tuple(caps),
    )
