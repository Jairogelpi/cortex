"""
CAPA KAPPA - Critic externo (delta score) — VERSION OPTIMIZADA H1
Cortex V2, Fase 2

OPTIMIZACION H1: Kappa NO usa LLM.
El delta es 100% deterministico (formula matematica).
El "reasoning" se genera con codigo — no con tokens.
Ahorro: 172 tokens eliminados completamente.

Justificacion: el reasoning de Kappa nunca influye en la decision.
La decision depende exclusivamente de delta vs umbrales pre-registrados.
Un LLM que "explica" una formula matematica no añade valor cientifico.
"""
from dataclasses import dataclass
from datetime import datetime
from loguru import logger

from cortex.config import config
from cortex.layers.phi import PhiState


@dataclass
class KappaEvaluation:
    delta: float
    retorno_norm: float
    drawdown_norm: float
    regimen_consistencia: float
    decision: str
    backtrack_required: bool
    consolidate_memory: bool
    has_open_positions: bool
    reasoning: str
    timestamp: str
    phi_confidence: float

    def summary(self) -> str:
        return (
            f"Kappa | delta={self.delta:.4f} | {self.decision} | "
            f"ret={self.retorno_norm:.3f} dd={self.drawdown_norm:.3f} "
            f"reg={self.regimen_consistencia:.3f} | {self.reasoning}"
        )


class KappaLayer:
    DELTA_BACKTRACK   = config.DELTA_BACKTRACK
    DELTA_CONSOLIDATE = config.DELTA_CONSOLIDATE

    def __init__(self):
        logger.info("Capa Kappa inicializada: deterministico (0 tokens LLM)")

    def evaluate(self, phi_state, portfolio_value, initial_value=100_000.0,
                 spy_benchmark_return=0.0, open_positions=None):
        if open_positions is None:
            open_positions = []
        has_open = len(open_positions) > 0

        retorno_norm  = self._calc_retorno_norm(portfolio_value, initial_value, spy_benchmark_return)
        drawdown_norm = self._calc_drawdown_norm(phi_state)
        reg_consist   = self._calc_regimen_consistencia(phi_state)

        delta = round(max(0.0, min(1.0,
            0.4*retorno_norm + 0.4*(1.0-drawdown_norm) + 0.2*reg_consist
        )), 4)

        decision, backtrack, consolidate = self._decide(delta, phi_state, has_open)

        # Reasoning generado por codigo — 0 tokens LLM
        reasoning = (
            f"0.4×{retorno_norm:.3f}+0.4×{1-drawdown_norm:.3f}+0.2×{reg_consist:.3f}"
            f"={delta:.4f} → {decision}"
        )

        evaluation = KappaEvaluation(
            delta=delta,
            retorno_norm=round(retorno_norm, 4),
            drawdown_norm=round(drawdown_norm, 4),
            regimen_consistencia=round(reg_consist, 4),
            decision=decision,
            backtrack_required=backtrack,
            consolidate_memory=consolidate,
            has_open_positions=has_open,
            reasoning=reasoning,
            timestamp=datetime.now().isoformat(),
            phi_confidence=phi_state.confidence
        )
        logger.info(f"Kappa: delta={delta:.4f} decision={decision} positions={has_open} backtrack={backtrack}")
        return evaluation

    def _calc_retorno_norm(self, portfolio_value, initial_value, spy_return):
        ret_rel = (portfolio_value - initial_value) / initial_value * 100 - spy_return
        return max(0.0, min(1.0, (ret_rel + 10.0) / 20.0))

    def _calc_drawdown_norm(self, phi_state):
        dd = phi_state.raw_indicators.get("drawdown_90d_pct", 0.0)
        return max(0.0, min(1.0, abs(dd) / 30.0))

    def _calc_regimen_consistencia(self, phi_state):
        base = phi_state.confidence
        cp   = ((phi_state.Z8_complejidad + 1.0) / 2.0) * 0.15
        ca   = -0.10 if phi_state.Z4_causalidad < -0.6 else (0.10 if phi_state.Z4_causalidad > 0.5 else 0.0)
        return max(0.05, min(1.0, base - cp + ca))

    def _decide(self, delta, phi_state, has_open):
        regime = phi_state.regime
        if not has_open:
            if delta < 0.55 or regime == "INDETERMINATE":
                return "HOLD_CASH", False, False
            return "CONTINUE", False, delta >= self.DELTA_CONSOLIDATE
        if regime == "INDETERMINATE" and delta < 0.55:
            return "DEFENSIVE", False, False
        if delta < self.DELTA_BACKTRACK:
            return "BACKTRACK", True, False
        return "CONTINUE", False, delta >= self.DELTA_CONSOLIDATE


def test_kappa():
    from cortex.market_data import MarketData
    from cortex.layers.phi import PhiLayer
    md    = MarketData()
    phi   = PhiLayer()
    state = phi.factorize(md.get_regime_indicators())
    kappa = KappaLayer()
    ev    = kappa.evaluate(state, md.get_account()["portfolio_value"])
    print(ev.summary())
    return ev

if __name__ == "__main__":
    test_kappa()
