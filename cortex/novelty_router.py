"""Router de novedad y conflicto para Cortex evidence-first."""
from dataclasses import dataclass


@dataclass
class NoveltyResult:
    novelty_score: float
    conflict_score: float
    evidence_gap: float
    route: str


class NoveltyRouter:
    """Calcula si la ruta debe ser determinista, LLM minima o abstencion."""

    def route(self, *, best_sim: float, gap: float, evidence_coverage: float, conflict_score: float) -> NoveltyResult:
        novelty_score = round(max(0.0, min(1.0, 1.0 - best_sim + gap * 0.5)), 4)
        evidence_gap = round(max(0.0, 1.0 - evidence_coverage), 4)

        if evidence_coverage < 0.60:
            route = "ABSTAIN"
        elif conflict_score >= 0.70 or novelty_score >= 0.50:
            route = "LLM_REVIEW"
        else:
            route = "DETERMINISTIC"

        return NoveltyResult(
            novelty_score=novelty_score,
            conflict_score=round(conflict_score, 4),
            evidence_gap=evidence_gap,
            route=route,
        )
