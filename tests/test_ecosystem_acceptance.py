from cosmos.ecosystem_acceptance import (
    CANONICAL_OWNERS,
    CORE_GRAPH,
    PRIVATE_REPOSITORIES,
    PUBLIC_REPOSITORIES,
    validate_ecosystem,
)


def test_canonical_contract_passes():
    result = validate_ecosystem()
    assert result.passed
    assert result.public_count == 32
    assert result.private_count == 1


def test_public_inventory_drift_fails():
    result = validate_ecosystem(PUBLIC_REPOSITORIES[:-1], PRIVATE_REPOSITORIES)
    assert not result.passed
    assert not result.exact_public_set


def test_private_bunker_drift_fails():
    result = validate_ecosystem(PUBLIC_REPOSITORIES, ())
    assert not result.passed
    assert not result.exact_private_set


def test_inventory_order_does_not_change_digest():
    a = validate_ecosystem(PUBLIC_REPOSITORIES, PRIVATE_REPOSITORIES)
    b = validate_ecosystem(reversed(PUBLIC_REPOSITORIES), reversed(PRIVATE_REPOSITORIES))
    assert a.digest == b.digest


def test_canonical_owners_are_unique():
    owners = tuple(CANONICAL_OWNERS.values())
    assert len(owners) == len(set(owners))


def test_core_graph_covers_all_canonical_owners():
    nodes = set(CANONICAL_OWNERS.values())
    graph_nodes = set(CORE_GRAPH)
    graph_targets = {target for targets in CORE_GRAPH.values() for target in targets}
    assert nodes <= graph_nodes | graph_targets
    assert validate_ecosystem().core_graph_connected


def test_acceptance_contract_does_not_claim_runtime_evidence():
    result = validate_ecosystem()
    assert not hasattr(result, "native_execution")
    assert not hasattr(result, "browser_render")
    assert not hasattr(result, "tls_handshake")
