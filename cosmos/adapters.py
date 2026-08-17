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

    provider = None

    for candidate in (
        "vercel",
        "cloudflare",
        "godaddy",
        "porkbun",
    ):
        if candidate in request_text:
            provider = candidate
            break

    # No provider guessing beyond explicit user intent.
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
