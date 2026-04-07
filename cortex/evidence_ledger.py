"""Registro ligero de evidencia para la ruta evidence-first."""
from dataclasses import dataclass, field

from cortex.decision_packet import EvidenceItem, EvidenceBundle


@dataclass
class EvidenceLedger:
    items: list[EvidenceItem] = field(default_factory=list)

    def add(self, item: EvidenceItem) -> None:
        self.items.append(item)

    def build_bundle(self, coverage: float = 0.0, conflict_score: float = 0.0, novelty_score: float = 0.0) -> EvidenceBundle:
        return EvidenceBundle(
            items=list(self.items),
            coverage=coverage,
            conflict_score=conflict_score,
            novelty_score=novelty_score,
        )
