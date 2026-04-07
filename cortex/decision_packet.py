"""Paquete de decision evidence-first para Cortex VNext."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class EvidenceItem:
    source: str
    kind: str
    value: Any
    weight: float = 1.0
    freshness: float = 1.0
    note: str = ""


@dataclass
class EvidenceBundle:
    items: list[EvidenceItem] = field(default_factory=list)
    coverage: float = 0.0
    conflict_score: float = 0.0
    novelty_score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "coverage": self.coverage,
            "conflict_score": self.conflict_score,
            "novelty_score": self.novelty_score,
            "items": [item.__dict__ for item in self.items],
        }


@dataclass
class DecisionPacket:
    session_id: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    best_hypothesis: str = ""
    trade_action: str = ""
    novelty_score: float = 0.0
    conflict_score: float = 0.0
    evidence_coverage: float = 0.0
    critic_result: str = ""
    verification_result: str = ""
    final_action: str = "HOLD"
    abstain_reason: str = ""
    llm_used: bool = False
    token_usage: int = 0
    shadow_agreement: bool = False
    shadow_regret: float = 0.0
    evidence: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "best_hypothesis": self.best_hypothesis,
            "trade_action": self.trade_action,
            "novelty_score": self.novelty_score,
            "conflict_score": self.conflict_score,
            "evidence_coverage": self.evidence_coverage,
            "critic_result": self.critic_result,
            "verification_result": self.verification_result,
            "final_action": self.final_action,
            "abstain_reason": self.abstain_reason,
            "llm_used": self.llm_used,
            "token_usage": self.token_usage,
            "shadow_agreement": self.shadow_agreement,
            "shadow_regret": self.shadow_regret,
            "evidence": self.evidence,
            "metadata": self.metadata,
        }
