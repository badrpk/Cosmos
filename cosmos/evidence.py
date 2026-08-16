"""Deterministic integration evidence for the Cosmos control plane.

Cosmos coordinates peers; it must not overstate what a health check proves. This
module records evidence with an explicit check kind (health, contract, native,
render, persistence, security, etc.) and produces reproducible summaries.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
import json
from typing import Iterable


VALID_KINDS = {
    "health",
    "contract",
    "native",
    "render",
    "persistence",
    "security",
    "transport",
    "reproducibility",
}

VALID_STATUSES = {"pass", "fail", "skip"}


@dataclass(frozen=True)
class Evidence:
    peer: str
    kind: str
    status: str
    detail: str = ""
    artifact_sha256: str | None = None

    def __post_init__(self) -> None:
        if not self.peer or not self.peer.strip():
            raise ValueError("peer is required")
        if self.kind not in VALID_KINDS:
            raise ValueError(f"unsupported evidence kind: {self.kind}")
        if self.status not in VALID_STATUSES:
            raise ValueError(f"unsupported evidence status: {self.status}")
        if self.artifact_sha256 is not None:
            digest = self.artifact_sha256.lower()
            if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise ValueError("artifact_sha256 must be a 64-character hex digest")
            object.__setattr__(self, "artifact_sha256", digest)


class EvidenceLedger:
    def __init__(self, expected_peers: Iterable[str] = ()) -> None:
        peers = [p.strip() for p in expected_peers if p and p.strip()]
        if len(set(peers)) != len(peers):
            raise ValueError("expected peers must be unique")
        self.expected_peers = tuple(sorted(peers, key=str.lower))
        self._items: dict[tuple[str, str], Evidence] = {}

    def record(self, evidence: Evidence) -> Evidence:
        key = (evidence.peer.lower(), evidence.kind)
        if key in self._items:
            raise ValueError(f"duplicate evidence for {evidence.peer}/{evidence.kind}")
        self._items[key] = evidence
        return evidence

    def items(self) -> tuple[Evidence, ...]:
        return tuple(
            sorted(self._items.values(), key=lambda e: (e.peer.lower(), e.kind, e.status, e.detail))
        )

    def peer_status(self, peer: str) -> str:
        matches = [e for e in self._items.values() if e.peer.lower() == peer.lower()]
        if not matches:
            return "unknown"
        if any(e.status == "fail" for e in matches):
            return "degraded"
        if any(e.status == "pass" for e in matches):
            return "healthy"
        return "unknown"

    def summary(self) -> dict[str, object]:
        observed = {e.peer for e in self._items.values()}
        peers = sorted(set(self.expected_peers) | observed, key=str.lower)
        statuses = {peer: self.peer_status(peer) for peer in peers}
        counts = {
            "healthy": sum(v == "healthy" for v in statuses.values()),
            "degraded": sum(v == "degraded" for v in statuses.values()),
            "unknown": sum(v == "unknown" for v in statuses.values()),
        }
        by_kind = {
            kind: {
                "pass": sum(e.kind == kind and e.status == "pass" for e in self._items.values()),
                "fail": sum(e.kind == kind and e.status == "fail" for e in self._items.values()),
                "skip": sum(e.kind == kind and e.status == "skip" for e in self._items.values()),
            }
            for kind in sorted(VALID_KINDS)
            if any(e.kind == kind for e in self._items.values())
        }
        return {
            "peer_count": len(peers),
            "evidence_count": len(self._items),
            "counts": counts,
            "peers": statuses,
            "by_kind": by_kind,
        }

    def claims(self) -> dict[str, list[str]]:
        """Return only claims directly supported by passing evidence."""
        claims: dict[str, list[str]] = {}
        for evidence in self.items():
            if evidence.status != "pass":
                continue
            claims.setdefault(evidence.peer, []).append(evidence.kind)
        return {peer: sorted(kinds) for peer, kinds in sorted(claims.items(), key=lambda x: x[0].lower())}

    def manifest(self) -> dict[str, object]:
        return {
            "version": 1,
            "expected_peers": list(self.expected_peers),
            "evidence": [asdict(e) for e in self.items()],
            "summary": self.summary(),
            "claims": self.claims(),
        }

    def evidence_sha256(self) -> str:
        payload = json.dumps(self.manifest(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return sha256(payload.encode("utf-8")).hexdigest()


__all__ = ["Evidence", "EvidenceLedger", "VALID_KINDS", "VALID_STATUSES"]
