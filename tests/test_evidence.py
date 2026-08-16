import unittest

from cosmos.evidence import Evidence, EvidenceLedger


class EvidenceTests(unittest.TestCase):
    def test_validation(self):
        with self.assertRaises(ValueError):
            Evidence("", "health", "pass")
        with self.assertRaises(ValueError):
            Evidence("xerus", "magic", "pass")
        with self.assertRaises(ValueError):
            Evidence("xerus", "health", "maybe")
        with self.assertRaises(ValueError):
            Evidence("xerus", "health", "pass", artifact_sha256="bad")

    def test_duplicate_evidence_rejected(self):
        ledger = EvidenceLedger(["xerus"])
        ledger.record(Evidence("xerus", "health", "pass"))
        with self.assertRaises(ValueError):
            ledger.record(Evidence("XERUS", "health", "pass"))

    def test_peer_health_and_degraded(self):
        ledger = EvidenceLedger(["xerus", "nifdu"])
        ledger.record(Evidence("xerus", "health", "pass"))
        ledger.record(Evidence("nifdu", "health", "pass"))
        ledger.record(Evidence("nifdu", "render", "fail", "viewport mismatch"))
        self.assertEqual(ledger.peer_status("xerus"), "healthy")
        self.assertEqual(ledger.peer_status("nifdu"), "degraded")

    def test_expected_peer_without_evidence_is_unknown(self):
        ledger = EvidenceLedger(["xerus"])
        summary = ledger.summary()
        self.assertEqual(summary["peers"]["xerus"], "unknown")
        self.assertEqual(summary["counts"]["unknown"], 1)

    def test_claims_only_include_passing_kinds(self):
        ledger = EvidenceLedger()
        ledger.record(Evidence("Lexane", "contract", "pass"))
        ledger.record(Evidence("Lexane", "native", "skip"))
        ledger.record(Evidence("nifdu", "render", "fail"))
        self.assertEqual(ledger.claims(), {"Lexane": ["contract"]})

    def test_health_does_not_imply_native(self):
        ledger = EvidenceLedger(["xerus"])
        ledger.record(Evidence("xerus", "health", "pass"))
        self.assertEqual(ledger.claims()["xerus"], ["health"])
        self.assertNotIn("native", ledger.claims()["xerus"])

    def test_kind_counts(self):
        ledger = EvidenceLedger()
        ledger.record(Evidence("a", "health", "pass"))
        ledger.record(Evidence("b", "health", "fail"))
        ledger.record(Evidence("c", "native", "skip"))
        summary = ledger.summary()
        self.assertEqual(summary["by_kind"]["health"], {"pass": 1, "fail": 1, "skip": 0})
        self.assertEqual(summary["by_kind"]["native"], {"pass": 0, "fail": 0, "skip": 1})

    def test_manifest_is_deterministic(self):
        def build():
            ledger = EvidenceLedger(["xerus", "Lexane"])
            ledger.record(Evidence("xerus", "persistence", "pass", "roundtrip"))
            ledger.record(Evidence("Lexane", "contract", "pass", "compile adapter"))
            return ledger

        first = build()
        second = build()
        self.assertEqual(first.manifest(), second.manifest())
        self.assertEqual(first.evidence_sha256(), second.evidence_sha256())
        self.assertEqual(len(first.evidence_sha256()), 64)

    def test_digest_normalized(self):
        digest = "A" * 64
        evidence = Evidence("shmry", "security", "pass", artifact_sha256=digest)
        self.assertEqual(evidence.artifact_sha256, "a" * 64)


if __name__ == "__main__":
    unittest.main()
