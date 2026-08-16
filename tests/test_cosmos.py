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

    assert "sophyane" in route.repositories
    assert "vps" in route.repositories
    assert "nifdu" in route.repositories
    assert "xerus" in route.repositories


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
