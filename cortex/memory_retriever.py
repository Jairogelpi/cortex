"""Recuperacion de memoria historica ligera para Cortex."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class MemoryHit:
    session_id: str
    score: float
    delta: float
    last_delta: float
    total_consolidated: int
    total_rejected: int
    path: str

    def to_dict(self) -> dict:
        return self.__dict__.copy()


class MemoryRetriever:
    """Lee `data/memory/*.json` y devuelve casos parecidos a un estado actual."""

    def __init__(self, memory_dir: str | Path = "data/memory"):
        self.memory_dir = Path(memory_dir)

    def retrieve(self, query: dict, top_k: int = 3) -> list[MemoryHit]:
        if not self.memory_dir.exists():
            return []

        hits: list[MemoryHit] = []
        for path in sorted(self.memory_dir.glob("*.json")):
            record = self._load_json(path)
            if not record:
                continue
            score = self._score_record(record, query)
            hits.append(MemoryHit(
                session_id=str(record.get("session_id", path.stem)),
                score=score,
                delta=float(record.get("last_delta", 0.0) or 0.0),
                last_delta=float(record.get("last_delta", 0.0) or 0.0),
                total_consolidated=int(record.get("total_consolidated", 0) or 0),
                total_rejected=int(record.get("total_rejected", 0) or 0),
                path=str(path),
            ))

        hits.sort(key=lambda item: item.score, reverse=True)
        return hits[:top_k]

    def _load_json(self, path: Path) -> dict:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _score_record(self, record: dict, query: dict) -> float:
        query_delta = float(query.get("delta", 0.0) or 0.0)
        record_delta = float(record.get("last_delta", 0.0) or 0.0)
        delta_gap = abs(query_delta - record_delta)

        rejected = float(record.get("total_rejected", 0.0) or 0.0)
        consolidated = float(record.get("total_consolidated", 0.0) or 0.0)
        quality = 1.0 - min(1.0, rejected / max(1.0, rejected + consolidated + 1.0))

        score = max(0.0, 1.0 - delta_gap) * 0.7 + quality * 0.3
        return round(min(1.0, score), 4)
