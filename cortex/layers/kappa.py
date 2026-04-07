"""
CAPA KAPPA - Critic externo (delta score)
Cortex V2, Fase 2

Fundamentado en Zhou et al. (Nature Neuroscience 2025).
Formula: delta = 0.4*RetornoNorm + 0.4*(1-DrawdownNorm) + 0.2*RegimenConsistencia
Umbrales OSF: DELTA_BACKTRACK=0.65 | DELTA_CONSOLIDATE=0.70

Nota: BACKTRACK solo aplica con posiciones abiertas.
Con portfolio en cash no hay estado al que volver.
"""
import json
from dataclasses import dataclass
from datetime import datetime
from openai import OpenAI
from loguru import logger

from cortex.config import config
from cortex.layers.phi import PhiState
from cortex.token_tracker import token_tracker  # H1: medicion real de tokens


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
        lines = [
            f"Kappa Evaluation | delta={self.delta:.4f} | Decision: {self.decision}",
            f"  Retorno norm:         {self.retorno_norm:.4f}",
            f"  Drawdown norm:        {self.drawdown_norm:.4f}",
            f"  Regimen consistencia: {self.regimen_consistencia:.4f}",
            f"  Delta:  0.4*{self.retorno_norm:.4f} + 0.4*{1-self.drawdown_norm:.4f} + 0.2*{self.regimen_consistencia:.4f} = {self.delta:.4f}",
            f"  Posiciones: {self.has_open_positions} | Backtrack: {self.backtrack_required} | Consolidar: {self.consolidate_memory}",
            f"  Reasoning: {self.reasoning}",
        ]
        return "\n".join(lines)


class KappaLayer:
    DELTA_BACKTRACK   = config.DELTA_BACKTRACK
    DELTA_CONSOLIDATE = config.DELTA_CONSOLIDATE

    def __init__(self):
        self.client = OpenAI(
            api_key=config.OPENROUTER_API_KEY,
            base_url=config.OPENROUTER_BASE_URL,
            timeout=config.OPENROUTER_TIMEOUT_SECONDS,
            max_retries=config.OPENROUTER_MAX_RETRIES,
        )
        self.model = config.MODEL_KAPPA
        logger.info(
            f"Capa Kappa inicializada: {self.model} "
            f"(timeout={config.OPENROUTER_TIMEOUT_SECONDS}s)"
        )

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
        reasoning = self._get_reasoning(delta, decision, phi_state,
            retorno_norm, drawdown_norm, reg_consist,
            portfolio_value, initial_value, has_open)

        evaluation = KappaEvaluation(
            delta=delta, retorno_norm=round(retorno_norm,4),
            drawdown_norm=round(drawdown_norm,4), regimen_consistencia=round(reg_consist,4),
            decision=decision, backtrack_required=backtrack,
            consolidate_memory=consolidate, has_open_positions=has_open,
            reasoning=reasoning, timestamp=datetime.now().isoformat(),
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

    def _get_reasoning(self, delta, decision, phi_state,
                       retorno_norm, drawdown_norm, reg_consist,
                       portfolio_value, initial_value, has_open):
        retorno_pct = (portfolio_value - initial_value) / initial_value * 100
        prompt = f"""Eres Kappa, el critic externo de Cortex V2.
PORTFOLIO: ${portfolio_value:,.0f} ({retorno_pct:+.2f}%) | {'posiciones' if has_open else '100% cash'}
MERCADO: {phi_state.regime} | VIX={phi_state.raw_indicators.get('vix')} | Mom={phi_state.raw_indicators.get('momentum_21d_pct')}%
DELTA={delta:.4f} | DECISION={decision}
Explica en UNA frase tecnica por que. Sin markdown."""
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=120, temperature=0.1
            )
            # H1: registrar tokens reales de Kappa
            token_tracker.add("kappa", resp.usage.prompt_tokens, resp.usage.completion_tokens)
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"Kappa reasoning fallback: {e}")
            return f"Delta={delta:.4f}. Decision: {decision}."


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
