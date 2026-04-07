"""
CAPA OMICRON - Observabilidad completa
Cortex V2, Fase 9 (ultima capa)

Del paper (Seccion 2.2):
    Metacognicion: el sistema monitoriza su propio funcionamiento.
    Telemetria: delta, regimen, tokens, backtrack events.
    GitHub Actions monitoriza 24/7. Alerta automatica.

Condicion de confianza (Seccion 5):
    Sistema observable en tiempo real.
    Senal de alarma: sistema ciego a sus propios fallos.

Hipotesis H7 relacionada:
    GitHub Actions monitoriza continuamente Rho y Tau.

Del paper: "δ score, régimen detectado, tokens por módulo,
backtrack events publicados en GitHub cada día."
"""
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
from loguru import logger

from cortex.layers.phi import PhiState
from cortex.layers.kappa import KappaEvaluation
from cortex.layers.omega import OmegaHypothesis
from cortex.layers.lambda_ import LambdaValidation
from cortex.layers.sigma import SigmaOrchestration
from cortex.layers.tau import TauDecision
from cortex.layers.rho import RhoStatus
from cortex.decision_packet import DecisionPacket


LOG_DIR = Path("logs")


@dataclass
class OmicronEvent:
    """Un evento de telemetria registrado por Omicron."""
    event_type: str       # HEARTBEAT | BACKTRACK | LAMBDA_CONTRADICTION | STOP_LOSS | etc.
    timestamp: str
    session_id: str
    delta: float
    regime: str
    signal: str
    lambda_verdict: str
    lambda_sim: float
    sigma_decision: str
    tau_approved: bool
    rho_healthy: bool
    portfolio_value: float
    notes: str = ""
    evidence_coverage: float = 0.0
    novelty_score: float = 0.0
    conflict_score: float = 0.0
    critic_result: str = ""
    verification_result: str = ""
    final_action: str = ""
    trade_action: str = ""
    abstain_reason: str = ""
    llm_used: bool = False
    token_usage: int = 0
    shadow_agreement: bool = False
    shadow_regret: float = 0.0

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "session_id": self.session_id,
            "delta": self.delta,
            "regime": self.regime,
            "signal": self.signal,
            "lambda_verdict": self.lambda_verdict,
            "lambda_sim": self.lambda_sim,
            "sigma_decision": self.sigma_decision,
            "tau_approved": self.tau_approved,
            "rho_healthy": self.rho_healthy,
            "portfolio_value": self.portfolio_value,
            "notes": self.notes,
            "evidence_coverage": self.evidence_coverage,
            "novelty_score": self.novelty_score,
            "conflict_score": self.conflict_score,
            "critic_result": self.critic_result,
            "verification_result": self.verification_result,
            "final_action": self.final_action,
            "trade_action": self.trade_action,
            "abstain_reason": self.abstain_reason,
            "llm_used": self.llm_used,
            "token_usage": self.token_usage,
            "shadow_agreement": self.shadow_agreement,
            "shadow_regret": self.shadow_regret,
        }

    def to_markdown_line(self) -> str:
        """Formato para el diario de GitHub (Seccion 5 del paper)."""
        ts = self.timestamp[:19]
        return (
            f"| {ts} | {self.event_type} | {self.regime} | "
            f"δ={self.delta:.4f} | {self.signal} | "
            f"Λ={self.lambda_verdict}({self.lambda_sim:.3f}) | "
            f"Σ={self.sigma_decision} | A={self.final_action or '-'} | T={self.trade_action or '-'} | "
            f"Cov={self.evidence_coverage:.2f} | Nov={self.novelty_score:.2f} | Conf={self.conflict_score:.2f} | "
            f"LLM={'Y' if self.llm_used else 'N'} | SR={self.shadow_regret:.2f} | "
            f"{'✓' if self.tau_approved else '✗'} | "
            f"{'✓' if self.rho_healthy else '⚠'} | "
            f"${int(self.portfolio_value)} |"
        )


class OmicronLayer:
    """
    Capa Omicron: observabilidad completa del sistema.

    Registra todos los eventos del pipeline en:
    1. logs/cortex_YYYYMMDD.jsonl  (telemetria maquina)
    2. logs/cortex_YYYYMMDD.md     (diario legible, para GitHub)

    Del paper: "el sistema es auditable en tiempo real."
    Los logs en Markdown son los que se publican en GitHub cada dia.
    """

    def __init__(self, session_id: str):
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        self.session_id = session_id
        self.events: list = []
        date_str = datetime.now().strftime("%Y%m%d")
        self.jsonl_path = LOG_DIR / f"cortex_{date_str}.jsonl"
        self.md_path    = LOG_DIR / f"cortex_{date_str}.md"
        self._init_md_log()
        logger.info(f"Omicron inicializado: sesion={session_id}")

    def record(
        self,
        event_type: str,
        phi_state: PhiState,
        kappa_eval: KappaEvaluation,
        omega_hyp: OmegaHypothesis,
        lambda_val: LambdaValidation,
        sigma_orch: SigmaOrchestration,
        tau_dec: TauDecision,
        rho_status: RhoStatus,
        portfolio_value: float,
        notes: str = "",
        decision_packet: Optional[DecisionPacket] = None,
    ) -> OmicronEvent:
        """Registra un evento completo del pipeline."""

        event = OmicronEvent(
            event_type=event_type,
            timestamp=datetime.now().isoformat(),
            session_id=self.session_id,
            delta=kappa_eval.delta,
            regime=phi_state.regime,
            signal=omega_hyp.trading_signal,
            lambda_verdict=lambda_val.verdict,
            lambda_sim=lambda_val.similarity,
            sigma_decision=sigma_orch.decision,
            tau_approved=tau_dec.approved,
            rho_healthy=rho_status.system_healthy,
            portfolio_value=portfolio_value,
            notes=notes,
            evidence_coverage=decision_packet.evidence_coverage if decision_packet else 0.0,
            novelty_score=decision_packet.novelty_score if decision_packet else 0.0,
            conflict_score=decision_packet.conflict_score if decision_packet else 0.0,
            critic_result=decision_packet.critic_result if decision_packet else "",
            verification_result=decision_packet.verification_result if decision_packet else "",
            final_action=decision_packet.final_action if decision_packet else "",
            trade_action=decision_packet.trade_action if decision_packet else "",
            abstain_reason=decision_packet.abstain_reason if decision_packet else "",
            llm_used=decision_packet.llm_used if decision_packet else False,
            token_usage=decision_packet.token_usage if decision_packet else 0,
            shadow_agreement=decision_packet.shadow_agreement if decision_packet else False,
            shadow_regret=decision_packet.shadow_regret if decision_packet else 0.0,
        )

        self.events.append(event)
        self._write_jsonl(event)
        self._write_md(event)

        # Alertas automaticas para eventos criticos
        if event_type in ("BACKTRACK", "STOP_LOSS", "LAMBDA_CONTRADICTION"):
            logger.critical(
                f"OMICRON ALERTA: {event_type} | "
                f"delta={kappa_eval.delta:.4f} | "
                f"portfolio=${portfolio_value:,.0f}"
            )

        logger.info(
            f"Omicron: {event_type} registrado | "
            f"delta={kappa_eval.delta:.4f} | "
            f"regimen={phi_state.regime} | "
            f"Sigma={sigma_orch.decision}"
        )
        return event

    def get_session_summary(self) -> dict:
        """Resumen de la sesion actual."""
        if not self.events:
            return {"events": 0, "session_id": self.session_id}

        deltas = [e.delta for e in self.events]
        evidence_coverages = [e.evidence_coverage for e in self.events]
        novelty_scores = [e.novelty_score for e in self.events]
        conflict_scores = [e.conflict_score for e in self.events]
        return {
            "session_id": self.session_id,
            "total_events": len(self.events),
            "delta_mean": round(sum(deltas) / len(deltas), 4),
            "delta_min":  round(min(deltas), 4),
            "delta_max":  round(max(deltas), 4),
            "evidence_coverage_mean": round(sum(evidence_coverages) / len(evidence_coverages), 4),
            "novelty_score_mean": round(sum(novelty_scores) / len(novelty_scores), 4),
            "conflict_score_mean": round(sum(conflict_scores) / len(conflict_scores), 4),
            "backtracks": sum(1 for e in self.events if e.event_type == "BACKTRACK"),
            "regimes_seen": list(set(e.regime for e in self.events)),
            "signals_seen": list(set(e.signal for e in self.events)),
            "lambda_verdicts": list(set(e.lambda_verdict for e in self.events)),
            "log_jsonl": str(self.jsonl_path),
            "log_md":    str(self.md_path),
        }

    def _init_md_log(self):
        """Inicializa el archivo Markdown si no existe."""
        if not self.md_path.exists():
            header = (
                "# Cortex V2 — Diario de Trading\n\n"
                f"Generado automaticamente. Sesion: {self.session_id}\n\n"
                "| Timestamp | Evento | Regimen | Delta | Senal | Lambda | Sigma | Action | Cov | Nov | Conf | LLM | Tau | Rho | Portfolio |\n"
                "|-----------|--------|---------|-------|-------|--------|-------|--------|-----|-----|------|-----|-----|-----|----------|\n"
            )
            self.md_path.write_text(header, encoding="utf-8")

    def _write_jsonl(self, event: OmicronEvent):
        with open(self.jsonl_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")

    def _write_md(self, event: OmicronEvent):
        with open(self.md_path, "a", encoding="utf-8") as f:
            f.write(event.to_markdown_line() + "\n")
