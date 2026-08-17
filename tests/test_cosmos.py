from pathlib import Path
import tempfile

from cosmos.engine import CosmosEngine
from cosmos.router import resolve


def test_default_route_has_sophyane():
    route = resolve(
        "calculate something"
    )

    assert route.repositories[0] == "sophyane"


def test_visual_request_routes_correctly():
    route = resolve(
        "build website and visually verify screenshot"
    )

    assert "vps" in route.repositories
    assert "nifdu" in route.repositories
    assert "xerus" in route.repositories

    # Explicit deterministic capabilities should route
    # directly to their canonical owners. Sophyane is
    # reserved for semantic/ontology fallback.
    assert "sophyane" not in route.repositories


def test_memory_request_routes_xerus():
    route = resolve(
        "remember this result"
    )

    assert "xerus" in route.repositories


def test_language_request_routes_huobzlang():
    route = resolve(
        "compile this language program"
    )

    assert "HuobzLang" in route.repositories


def test_router_is_deterministic():
    request = (
        "build website and visually verify screenshot"
    )

    assert resolve(request) == resolve(request)


def test_engine_creates_task_directory():
    with tempfile.TemporaryDirectory() as tmp:
        engine = CosmosEngine(
            Path(tmp)
        )

        assert engine.tasks.exists()


def test_publish_routes_to_portis():
    from cosmos.router import resolve

    route = resolve(
        "publish this website to production"
    )

    assert "Portis" in route.repositories
    assert "deployment" in route.capabilities
    assert "sophyane" not in route.repositories


def test_vercel_routes_to_portis():
    from cosmos.router import resolve

    route = resolve(
        "deploy this website through vercel"
    )

    assert "Portis" in route.repositories
    assert "deployment" in route.capabilities


def test_dns_provider_routes_to_portis():
    from cosmos.router import resolve

    for request in (
        "configure my domain through godaddy",
        "set dns through porkbun",
        "host this through cloudflare",
    ):
        route = resolve(request)

        assert "Portis" in route.repositories
        assert "deployment" in route.capabilities


def test_semantic_unknown_falls_back_to_sophyane():
    from cosmos.router import resolve

    route = resolve(
        "make this smarter in the best possible way"
    )

    assert route.repositories == ("sophyane",)
    assert route.capabilities == ("plan",)


def _write_fake_portis_cli(root: Path) -> None:
    cli = root / "portis_provider_cli.py"

    cli.write_text(
        """\
import json
import sys

payload = json.load(sys.stdin)

provider = payload.get("provider_id")
action = payload.get("action")

if action != "validate":
    print(json.dumps({
        "status": "error",
        "error": "unsupported action",
    }))
    raise SystemExit(1)

if provider == "vercel":
    print(json.dumps({
        "status": "needs_input",
        "provider_id": "vercel",
        "missing_fields": [
            "credential_refs",
            "credential:token",
        ],
    }))
else:
    print(json.dumps({
        "status": "needs_input",
        "provider_id": provider,
        "missing_fields": ["provider_id"],
    }))
""",
        encoding="utf-8",
    )


def test_portis_explicit_provider_resolution():
    import os

    from cosmos.adapters import invoke_portis

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_fake_portis_cli(root)

        old = os.environ.get("COSMOS_PORTIS_ROOT")
        os.environ["COSMOS_PORTIS_ROOT"] = str(root)

        try:
            result = invoke_portis({
                "request":
                    "deploy this website through vercel",
                "context": {
                    "product": "/tmp/site",
                },
            })
        finally:
            if old is None:
                os.environ.pop(
                    "COSMOS_PORTIS_ROOT",
                    None,
                )
            else:
                os.environ[
                    "COSMOS_PORTIS_ROOT"
                ] = old

    assert result["repo"] == "Portis"
    assert result["provider_id"] == "vercel"

    response = result["response"]

    assert response["status"] == "needs_input"
    assert "credential_refs" in response["missing_fields"]
    assert "credential:token" in response["missing_fields"]


def test_portis_does_not_guess_provider():
    import os

    from cosmos.adapters import invoke_portis

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_fake_portis_cli(root)

        old = os.environ.get("COSMOS_PORTIS_ROOT")
        os.environ["COSMOS_PORTIS_ROOT"] = str(root)

        try:
            result = invoke_portis({
                "request":
                    "publish this website",
                "context": {
                    "product": "/tmp/site",
                },
            })
        finally:
            if old is None:
                os.environ.pop(
                    "COSMOS_PORTIS_ROOT",
                    None,
                )
            else:
                os.environ[
                    "COSMOS_PORTIS_ROOT"
                ] = old

    assert result["status"] == "needs_input"
    assert result["missing_fields"] == [
        "provider_id",
    ]


def test_algora_real_provider_selection(
    monkeypatch,
):
    from cosmos.adapters import invoke_algora

    monkeypatch.setenv(
        "COSMOS_ALGORA_ROOT",
        str(
            Path.home()
            / "cosmos-specialist-contract-discovery"
            / "repos"
            / "Algora"
        ),
    )

    result = invoke_algora({
        "selection_mode": "cheapest",
        "required_tags": [
            "deployment",
        ],
        "candidates": [
            {
                "name": "vercel",
                "latency_ms": 40,
                "memory_mb": 128,
                "accuracy": 0.95,
                "cost": 20,
                "tags": [
                    "deployment",
                    "cdn",
                ],
            },
            {
                "name": "cloudflare",
                "latency_ms": 25,
                "memory_mb": 128,
                "accuracy": 0.95,
                "cost": 10,
                "tags": [
                    "deployment",
                    "cdn",
                ],
            },
        ],
    })

    assert result["status"] == "ok"
    assert result["selected"] == "cloudflare"


def test_xerus_real_previous_provider_recall(
    monkeypatch,
    tmp_path,
):
    import sys

    from cosmos.adapters import invoke_xerus

    root = (
        Path.home()
        / "cosmos-specialist-contract-discovery"
        / "repos"
        / "xerus"
    )

    monkeypatch.setenv(
        "COSMOS_XERUS_ROOT",
        str(root),
    )

    monkeypatch.setenv(
        "XERUS_HOME",
        str(tmp_path / "xerus-state"),
    )

    sys.path.insert(
        0,
        str(root / "src"),
    )

    try:
        from xerus.memory import remember

        remember(
            (
                "usual deployment provider "
                "cloudflare account production"
            ),
            namespace="deployment",
            memory_key="deployment-provider",
            metadata={
                "provider_id": "cloudflare",
            },
        )
    finally:
        sys.path.pop(0)

    result = invoke_xerus({
        "query": (
            "usual deployment provider"
        ),
        "namespace": "deployment",
    })

    assert result["status"] == "ok"
    assert result["hits"]
    assert (
        result["hits"][0]["metadata"][
            "provider_id"
        ]
        == "cloudflare"
    )


def test_codane_real_safe_change_validation(
    monkeypatch,
):
    import hashlib

    from cosmos.adapters import invoke_codane

    monkeypatch.setenv(
        "COSMOS_CODANE_ROOT",
        str(
            Path.home()
            / "cosmos-specialist-contract-discovery"
            / "repos"
            / "Codane"
        ),
    )

    source = "provider = 'cloudflare'\n"
    test_source = "def test_provider(): pass\n"

    result = invoke_codane({
        "goal": (
            "Make minimum safe provider change"
        ),
        "changes": [
            {
                "path": "src/provider.py",
                "action": "update",
                "rationale": (
                    "Change provider only"
                ),
                "content_sha256":
                    hashlib.sha256(
                        source.encode()
                    ).hexdigest(),
            },
            {
                "path": "tests/test_provider.py",
                "action": "update",
                "rationale": (
                    "Validate provider change"
                ),
                "content_sha256":
                    hashlib.sha256(
                        test_source.encode()
                    ).hexdigest(),
            },
        ],
        "gates": [
            {
                "name": "tests",
                "command":
                    "python3 -m pytest -q",
                "required": True,
            },
        ],
    })

    assert result["status"] == "ok"
    assert result["errors"] == []
    assert result["evidence_hash"]
