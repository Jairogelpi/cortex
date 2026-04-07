"""Verificador determinista para Cortex evidence-first."""
from dataclasses import dataclass


@dataclass
class VerificationResult:
    status: str
    reason: str


class Verifier:
    def verify(self, *, evidence_coverage: float, conflict_score: float, llm_used: bool) -> VerificationResult:
        if evidence_coverage < 0.60:
            return VerificationResult("failed", "insufficient_coverage")
        if conflict_score >= 0.80:
            return VerificationResult("failed", "conflict_too_high")
        if llm_used:
            return VerificationResult("verified_with_warnings", "llm_reviewed")
        return VerificationResult("verified", "deterministic_path")
