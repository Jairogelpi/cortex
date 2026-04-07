"""Politica de abstencion para Cortex evidence-first."""
from dataclasses import dataclass


@dataclass
class AbstentionDecision:
    action: str
    reason: str


class AbstentionPolicy:
    def decide(self, *, evidence_coverage: float, conflict_score: float, critic_result: str, verification_result: str) -> AbstentionDecision:
        if evidence_coverage < 0.60:
            return AbstentionDecision("ABSTAIN", "evidence_coverage_below_threshold")
        if conflict_score >= 0.70 and critic_result != "resolved":
            return AbstentionDecision("ABSTAIN", "unresolved_conflict")
        if verification_result not in ("verified", "verified_with_warnings"):
            return AbstentionDecision("ABSTAIN", "verification_failed")
        return AbstentionDecision("EXECUTE", "evidence_sufficient")
