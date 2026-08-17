from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


class PeerUnavailable(RuntimeError):
    pass


class AdapterError(RuntimeError):
    pass


def repo_root(name: str) -> Path:
    base = Path(
        os.environ.get(
            "SHMRY_REPOS",
            str(
                Path.home()
                / ".local/share/shmry-global-census/repos"
            ),
        )
    )

    return base / name


def health(name: str) -> dict[str, Any]:
    root = repo_root(name)

    if not (root / ".git").is_dir():
        return {
            "repo": name,
            "available": False,
        }

    head = subprocess.check_output(
        [
            "git",
            "-C",
            str(root),
            "rev-parse",
            "HEAD",
        ],
        text=True,
        timeout=5,
    ).strip()

    return {
        "repo": name,
        "available": True,
        "head": head,
    }


def invoke_xerus(payload: dict[str, Any]) -> dict[str, Any]:
    root = repo_root("xerus")

    if not root.exists():
        raise PeerUnavailable("xerus")

    env = dict(os.environ)

    env["PYTHONPATH"] = str(root / "src")

    state_root = Path(
        env["COSMOS_STATE"]
    )

    env["XERUS_HOME"] = str(
        state_root / "xerus"
    )

    code = r'''
import json
import sys

from xerus.memory import remember, recall

payload = json.loads(sys.stdin.read())

saved = remember(
    json.dumps(payload, sort_keys=True),
    namespace="cosmos.tasks",
)

found = recall(
    payload.get("request", ""),
    namespace="cosmos.tasks",
)

print(json.dumps({
    "saved": saved,
    "recall_count": len(found),
}))
'''

    result = subprocess.run(
        [sys.executable, "-c", code],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env,
        timeout=15,
    )

    if result.returncode != 0:
        raise AdapterError(
            result.stderr.strip()
            or "Xerus invocation failed"
        )

    return json.loads(result.stdout)


def invoke_huobzlang(
    source: str,
    output_dir: Path,
) -> dict[str, Any]:

    root = repo_root("huobz")
    lang = root / "packages/lang"

    compiler = (
        lang
        / "core_features/compiler.py"
    )

    if not compiler.exists():
        raise PeerUnavailable(
            "HuobzLang delegated compiler"
        )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    source_path = output_dir / "request.hl"
    output_path = output_dir / "request.mc"

    source_path.write_text(
        source,
        encoding="utf-8",
    )

    env = dict(os.environ)
    env["PYTHONPATH"] = str(lang)

    result = subprocess.run(
        [
            sys.executable,
            str(compiler),
            str(source_path),
            str(output_path),
        ],
        cwd=str(lang),
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )

    if result.returncode != 0:
        raise AdapterError(
            result.stderr
            or result.stdout
            or "HuobzLang compiler failed"
        )

    return {
        "source": str(source_path),
        "output": str(output_path),
        "machine_code":
            output_path.read_text(
                encoding="utf-8"
            ),
    }



def invoke_portis(
    payload: dict[str, Any],
) -> dict[str, Any]:

    root = Path(
        os.environ.get(
            "COSMOS_PORTIS_ROOT",
            str(repo_root("Portis")),
        )
    )

    cli = root / "portis_provider_cli.py"

    if not cli.exists():
        raise PeerUnavailable(
            f"Portis callable contract unavailable: {cli}"
        )

    context = payload.get("context") or {}

    request_text = str(
        payload.get("request", "")
    ).casefold()

    provider = str(
        payload.get("provider_id")
        or context.get("provider_id")
        or ""
    ).strip() or None

    if provider is None:
        for candidate in (
            "vercel",
            "cloudflare",
            "godaddy",
            "porkbun",
        ):
            if candidate in request_text:
                provider = candidate
                break

    # No provider guessing beyond explicit user intent or a
    # provider deterministically resolved by a specialist.
    if provider is None:
        return {
            "repo": "Portis",
            "mode": "provider-selection-required",
            "status": "needs_input",
            "missing_fields": [
                "provider_id",
            ],
        }

    artifact = (
        context.get("product")
        or context.get("artifact")
        or ""
    )

    domain = context.get("domain")

    credential_refs = dict(
        context.get("credential_refs")
        or {}
    )

    request = {
        "action": "validate",
        "provider_id": provider,
        "artifact": artifact,
        "environment": context.get(
            "environment",
            "production",
        ),
        "credential_refs": credential_refs,
    }

    if domain:
        request["domain"] = domain

    result = subprocess.run(
        [
            sys.executable,
            str(cli),
        ],
        input=json.dumps(request),
        text=True,
        capture_output=True,
        cwd=str(root),
        timeout=15,
    )

    try:
        response = json.loads(
            result.stdout
        )
    except Exception as exc:
        raise AdapterError(
            "Portis returned invalid JSON"
        ) from exc

    if result.returncode != 0:
        raise AdapterError(
            response.get(
                "error",
                {},
            ).get(
                "message",
                "Portis invocation failed",
            )
        )

    return {
        "repo": "Portis",
        "mode": "provider-contract",
        "provider_id": provider,
        "response": response,
    }


def invoke(
    repo: str,
    payload: dict[str, Any],
    task_dir: Path,
) -> dict[str, Any]:

    if repo == "Portis":
        return invoke_portis(payload)

    if repo == "xerus":
        return invoke_xerus(payload)

    if repo == "Algora":
        return invoke_algora(payload)

    if repo == "Codane":
        return invoke_codane(payload)

    if repo == "HuobzLang":
        source = (
            "START:\n"
            "PRINT COSMOS_REQUEST\n"
            "LOAD 32\n"
            "HALT\n"
        )

        return invoke_huobzlang(
            source,
            task_dir / "huobzlang",
        )

    # Safe initial behavior for peers without a frozen callable
    # contract: expose availability and provenance rather than
    # inventing an API.
    return {
        "repo": repo,
        "mode": "health-contract",
        "health": health(repo),
    }


def _load_module_from_file(
    module_name: str,
    path: Path,
):
    """Load one specialist module without installing it globally."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        module_name,
        path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"cannot load specialist module: {path}"
        )

    module = importlib.util.module_from_spec(spec)

    # Dataclasses and similar decorators resolve the defining
    # module through sys.modules while class bodies execute.
    # Register before exec_module(), just like normal import.
    sys.modules[module_name] = module

    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise

    return module


def invoke_algora(payload: dict) -> dict:
    """
    Ask Algora to rank deployment-provider candidates.

    Cosmos supplies provider evidence; Algora performs the
    deterministic selection. It does not invent provider facts.
    """
    import os

    root = Path(
        os.environ.get(
            "COSMOS_ALGORA_ROOT",
            Path.home() / "Algora",
        )
    )

    module_path = root / "algora.py"

    if not module_path.exists():
        return {
            "repo": "Algora",
            "status": "unavailable",
            "reason": "algora.py not found",
        }

    algora = _load_module_from_file(
        "cosmos_external_algora",
        module_path,
    )

    candidates = list(
        payload.get("candidates") or []
    )

    if not candidates:
        return {
            "repo": "Algora",
            "status": "needs_input",
            "missing_fields": [
                "candidates",
            ],
        }

    selector = algora.Algora()

    for item in candidates:
        name = str(
            item.get("name") or ""
        ).strip()

        if not name:
            continue

        benchmark = algora.Benchmark(
            latency_ms=float(
                item.get("latency_ms", 0)
            ),
            memory_mb=float(
                item.get("memory_mb", 0)
            ),
            accuracy=float(
                item.get("accuracy", 1.0)
            ),
            cost=float(
                item.get("cost", 0)
            ),
        )

        selector.register(
            name,
            lambda n=name: n,
            benchmark,
            tags=item.get("tags") or (),
        )

    mode = str(
        payload.get("selection_mode")
        or "balanced"
    ).casefold()

    if mode == "cheapest":
        weights = algora.Weights(
            latency=0,
            memory=0,
            accuracy=0,
            cost=1,
        )
    elif mode in {"fastest", "latency"}:
        weights = algora.Weights(
            latency=1,
            memory=0,
            accuracy=0,
            cost=0,
        )
    else:
        weights = algora.Weights()

    required_tags = tuple(
        payload.get("required_tags") or ()
    )

    ranked = selector.rank(
        algora.Constraints(),
        weights=weights,
        required_tags=required_tags,
    )

    if not ranked:
        return {
            "repo": "Algora",
            "status": "needs_input",
            "reason": (
                "no candidate satisfies constraints"
            ),
        }

    selected = ranked[0]["name"]

    return {
        "repo": "Algora",
        "status": "ok",
        "selected": selected,
        "ranking": [
            {
                "name": row["name"],
                "score": row["score"],
            }
            for row in ranked
        ],
    }


def invoke_xerus(payload: dict) -> dict:
    """
    Recall deployment state from Xerus persistent memory.
    """
    import os
    import sys

    root = Path(
        os.environ.get(
            "COSMOS_XERUS_ROOT",
            Path.home() / "xerus",
        )
    )

    src = root / "src"

    if not (src / "xerus" / "memory.py").exists():
        return {
            "repo": "xerus",
            "status": "unavailable",
            "reason": "xerus memory runtime not found",
        }

    old_path = list(sys.path)

    try:
        sys.path.insert(
            0,
            str(src),
        )

        from xerus.memory import recall

        query = str(
            payload.get("query")
            or payload.get("request")
            or ""
        ).strip()

        if not query:
            return {
                "repo": "xerus",
                "status": "needs_input",
                "missing_fields": [
                    "query",
                ],
            }

        hits = recall(
            query,
            namespace=payload.get(
                "namespace",
                "deployment",
            ),
            limit=int(
                payload.get("limit", 8)
            ),
        )

        return {
            "repo": "xerus",
            "status": "ok",
            "hits": hits,
        }

    finally:
        sys.path[:] = old_path


def invoke_codane(payload: dict) -> dict:
    """
    Validate a proposed minimal/safe deployment change plan.
    """
    import os

    root = Path(
        os.environ.get(
            "COSMOS_CODANE_ROOT",
            Path.home() / "Codane",
        )
    )

    module_path = root / "codane.py"

    if not module_path.exists():
        return {
            "repo": "Codane",
            "status": "unavailable",
            "reason": "codane.py not found",
        }

    codane = _load_module_from_file(
        "cosmos_external_codane",
        module_path,
    )

    raw_changes = list(
        payload.get("changes") or []
    )

    if not raw_changes:
        return {
            "repo": "Codane",
            "status": "needs_input",
            "missing_fields": [
                "changes",
            ],
        }

    changes = []

    for item in raw_changes:
        changes.append(
            codane.FileChange(
                path=item["path"],
                action=item["action"],
                rationale=item["rationale"],
                content_sha256=item.get(
                    "content_sha256"
                ),
            )
        )

    gates = []

    for item in payload.get("gates") or []:
        gates.append(
            codane.ValidationGate(
                name=item["name"],
                command=item["command"],
                required=bool(
                    item.get(
                        "required",
                        True,
                    )
                ),
            )
        )

    plan = codane.build_plan(
        goal=str(
            payload.get("goal")
            or "Minimize deployment changes"
        ),
        changes=changes,
        gates=gates,
        notes=payload.get("notes") or (),
    )

    errors = codane.validate_plan(plan)

    return {
        "repo": "Codane",
        "status": (
            "ok"
            if not errors
            else "rejected"
        ),
        "errors": errors,
        "plan": plan.canonical(),
        "evidence_hash": (
            plan.evidence_hash()
        ),
    }
