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

        for repo in route.repositories:
            try:
                result["results"][repo] = invoke(
                    repo,
                    {
                        "task_id": task_id,
                        "request": request,
                        "route":
                            list(route.repositories),
                        "context":
                            context or {},
                    },
                    task_dir,
                )
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
