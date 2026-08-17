from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

from .adapters import invoke
from .router import resolve


class CosmosEngine:
    def __init__(self, state_root: Path):
        self.state_root = state_root
        self.tasks = state_root / "tasks"

        self.tasks.mkdir(
            parents=True,
            exist_ok=True,
        )

    def execute(
        self,
        request: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        task_id = uuid.uuid4().hex[:16]

        task_dir = self.tasks / task_id

        task_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        route = resolve(request)

        result: dict[str, Any] = {
            "task_id": task_id,
            "request": request,
            "created_at": time.time(),
            "route": {
                "repositories":
                    list(route.repositories),
                "capabilities":
                    list(route.capabilities),
            },
            "results": {},
            "errors": {},
            "status": "running",
        }

        execution_context = dict(
            context or {}
        )

        provider_id = str(
            execution_context.get(
                "provider_id",
                "",
            )
            or ""
        ).strip() or None

        # Specialists execute before Portis so their output can
        # enrich the deployment context deterministically.
        execution_order = [
            repo
            for repo in route.repositories
            if repo != "Portis"
        ]

        if "Portis" in route.repositories:
            execution_order.append("Portis")

        for repo in execution_order:
            try:
                payload = {
                    "task_id": task_id,
                    "request": request,
                    "route":
                        list(route.repositories),
                    "context":
                        execution_context,
                }

                if repo == "xerus":
                    payload.update({
                        "query": request,
                        "namespace":
                            execution_context.get(
                                "memory_namespace",
                                "deployment",
                            ),
                    })

                elif repo == "Algora":
                    payload.update({
                        "selection_mode":
                            _selection_mode(request),
                        "required_tags":
                            execution_context.get(
                                "required_provider_tags",
                                ["deployment"],
                            ),
                        "candidates":
                            _provider_candidates(
                                execution_context
                            ),
                    })

                elif repo == "Codane":
                    payload.update(
                        _safe_change_payload(
                            request,
                            execution_context,
                        )
                    )

                elif repo == "Portis":
                    if provider_id:
                        execution_context[
                            "provider_id"
                        ] = provider_id

                        payload[
                            "provider_id"
                        ] = provider_id

                peer_result = invoke(
                    repo,
                    payload,
                    task_dir,
                )

                result["results"][repo] = (
                    peer_result
                )

                if repo == "xerus":
                    recalled = (
                        _provider_from_xerus(
                            peer_result
                        )
                    )

                    if recalled:
                        provider_id = recalled
                        execution_context[
                            "provider_id"
                        ] = recalled

                elif repo == "Algora":
                    selected = str(
                        peer_result.get(
                            "selected",
                            "",
                        )
                        or ""
                    ).strip()

                    if selected:
                        provider_id = selected
                        execution_context[
                            "provider_id"
                        ] = selected

                elif repo == "Codane":
                    if (
                        peer_result.get("status")
                        == "rejected"
                    ):
                        result["status"] = (
                            "blocked"
                        )

                        break

            except Exception as exc:
                result["errors"][repo] = {
                    "type":
                        type(exc).__name__,
                    "message":
                        str(exc),
                }

        result["status"] = (
            "completed"
            if not result["errors"]
            else "completed_with_errors"
        )

        path = task_dir / "result.json"

        path.write_text(
            json.dumps(
                result,
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        return result


def _provider_from_xerus(result: dict[str, Any]) -> str | None:
    hits = list(result.get("hits") or [])

    for hit in hits:
        metadata = hit.get("metadata") or {}

        provider = str(
            metadata.get("provider_id") or ""
        ).strip()

        if provider:
            return provider

    return None


def _selection_mode(request: str) -> str:
    text = request.casefold()

    if any(
        term in text
        for term in (
            "cheapest",
            "lowest cost",
            "best value",
            "affordable",
        )
    ):
        return "cheapest"

    if any(
        term in text
        for term in (
            "fastest",
            "lowest latency",
        )
    ):
        return "fastest"

    return "balanced"


def _provider_candidates(
    context: dict[str, Any],
) -> list[dict[str, Any]]:
    return list(
        context.get("provider_candidates")
        or context.get("providers")
        or []
    )


def _safe_change_payload(
    request: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    plan = dict(
        context.get("safe_change_plan")
        or {}
    )

    return {
        "goal": (
            plan.get("goal")
            or request
        ),
        "changes": list(
            plan.get("changes")
            or context.get("changes")
            or []
        ),
        "gates": list(
            plan.get("gates")
            or context.get("gates")
            or []
        ),
        "notes": list(
            plan.get("notes")
            or []
        ),
    }
