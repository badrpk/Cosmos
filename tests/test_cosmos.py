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
