"""
CAPA KAPPA - Critic externo (delta score)
Cortex V2, Fase 2

Fundamentado en Zhou et al. (Nature Neuroscience 2025):
el cortex orbitofrontal (OFC) actua como evaluador independiente
que calibra representaciones hipocampales sin el sesgo del agente
que tomo la decision.

Kappa opera SOLO con el objetivo original y el estado actual.
No tiene acceso al razonamiento de las otras capas.
Su unica funcion: calcular delta y decidir si hacer backtrack.

Formula del paper (Seccion 2.1):
    delta = 0.4 * RetornoNorm + 0.4 * (1 - DrawdownNorm) + 0.2 * RegimenConsistencia

Umbrales (Seccion 2.1, ajustado pre-OSF):
    Si delta < 0.65  -> backtrack al ultimo estado con delta >= 0.70
    Solo consolida memoria si delta >= 0.70
    (DELTA_CONSOLIDATE ajustado de 0.75 a 0.70 — ver CHANGELOG_UMBRALES.md)

Nota de implementacion:
    BACKTRACK solo aplica cuando hay posiciones abiertas.
    Con portfolio en cash, el sistema evalua pero no hace backtrack
    porque no hay estado anterior de posiciones al que volver.

Hipotesis H3 del paper:
    TPR_abstension >= 0.85 cuando todos los Sim < 0.65
    False abstention <= 0.20
"""
import json
from dataclasses import dataclass
from datetime import datetime
from openai import OpenAI
from loguru import logger

from cortex.config import config
from cortex.layers.phi import PhiState


@dataclass
class KappaEvaluation:
    """Resultado de la evaluacion del critic externo."""
    delta: float
    retorno_norm: float
    drawdown_norm: float
    regimen_consistencia: float
    decision: str                # CONTINUE | BACKTRACK | DEFENSIVE | HOLD_CASH
    backtrack_required: bool
    consolidate_memory: bool
    has_open_positions: bool
    reasoning: str
    timestamp: str
    phi_confidence: float

    def summary(self) -> str:
        lines = [
            f"Kappa Evaluation | delta={self.delta:.4f} | Decision: {self.decision}",
            f"  Retorno norm:         {self.retorno_norm:.4f}  (peso 0.4)",
            f"  Drawdown norm:        {self.drawdown_norm:.4f}  (peso 0.4, entra como 1-x={1-self.drawdown_norm:.4f})",
            f"  Regimen consistencia: {self.regimen_consistencia:.4f}  (peso 0.2)",
            f"  Delta formula:        0.4*{self.retorno_norm:.4f} + 0.4*{1-self.drawdown_norm:.4f} + 0.2*{self.regimen_consistencia:.4f} = {self.delta:.4f}",
            f"  Posiciones abiertas:  {self.has_open_positions}",
            f"  Backtrack requerido:  {self.backtrack_required}",
            f"  Consolidar memoria:   {self.consolidate_memory}",
            f"  Confianza Phi:        {self.phi_confidence:.2f}",
            f"  Reasoning: {self.reasoning}",
        ]
        return "\n".join(lines)


class KappaLayer:
    """
    Capa Kappa: critic externo independiente.

    Lee los umbrales directamente de config para garantizar
    que cualquier ajuste pre-OSF se propague automaticamente.
    DELTA_BACKTRACK = 0.65  (sin cambio)
    DELTA_CONSOLIDATE = 0.70 (ajustado 0.75->0.70 pre-OSF)
    """

    DELTA_BACKTRACK   = config.DELTA_BACKTRACK    # 0.65 — sin cambio
    DELTA_CONSOLIDATE = config.DELTA_CONSOLIDATE  # 0.70 — ajustado pre-OSF

    def __init__(self):
        self.client = OpenAI(
            api_key=config.OPENROUTER_API_KEY,
            base_url=config.OPENROUTER_BASE_URL
        )
        self.model = config.MODEL_KAPPA
        logger.info(f"Capa Kappa inicializada: {self.model}")

    def evaluate(
        self,
        phi_state: PhiState,
        portfolio_value: float,
        initial_value: float = 100_000.0,
        spy_benchmark_return: float = 0.0,
        open_positions: list = None,
    ) -> KappaEvaluation:
        if open_positions is None:
            open_positions = []
        has_open_positions = len(open_positions) > 0

        retorno_norm         = self._calc_retorno_norm(portfolio_value, initial_value, spy_benchmark_return)
        drawdown_norm        = self._calc_drawdown_norm(phi_state)
        regimen_consistencia = self._calc_regimen_consistencia(phi_state)

        delta = round(max(0.0, min(1.0,
            0.4 * retorno_norm +
            0.4 * (1.0 - drawdown_norm) +
            0.2 * regimen_consistencia
        )), 4)

        decision, backtrack, consolidate = self._decide(delta, phi_state, has_open_positions)

        reasoning = self._get_reasoning(
            delta, decision, phi_state,
            retorno_norm, drawdown_norm, regimen_consistencia,
            portfolio_value, initial_value, has_open_positions
        )

        evaluation = KappaEvaluation(
            delta=delta,
            retorno_norm=round(retorno_norm, 4),
            drawdown_norm=round(drawdown_norm, 4),
            regimen_consistencia=round(regimen_consistencia, 4),
            decision=decision,
            backtrack_required=backtrack,
            consolidate_memory=consolidate,
            has_open_positions=has_open_positions,
            reasoning=reasoning,
            timestamp=datetime.now().isoformat(),
            phi_confidence=phi_state.confidence
        )

        logger.info(
            f"Kappa: delta={delta:.4f} decision={decision} "
            f"positions={has_open_positions} backtrack={backtrack}"
        )
        return evaluation

    def _calc_retorno_norm(self, portfolio_value, initial_value, spy_return) -> float:
        retorno_portfolio = (portfolio_value - initial_value) / initial_value * 100
        retorno_relativo  = retorno_portfolio - spy_return
        return max(0.0, min(1.0, (retorno_relativo + 10.0) / 20.0))

    def _calc_drawdown_norm(self, phi_state: PhiState) -> float:
        drawdown_pct = phi_state.raw_indicators.get("drawdown_90d_pct", 0.0)
        return max(0.0, min(1.0, abs(drawdown_pct) / 30.0))

    def _calc_regimen_consistencia(self, phi_state: PhiState) -> float:
        confidence = phi_state.confidence
        z4 = phi_state.Z4_causalidad
        z8 = phi_state.Z8_complejidad

        base              = confidence
        complexity_penalty = ((z8 + 1.0) / 2.0) * 0.15
        coherence_adj     = -0.10 if z4 < -0.6 else (+0.10 if z4 > 0.5 else 0.0)

        return max(0.05, min(1.0, base - complexity_penalty + coherence_adj))

    def _decide(self, delta, phi_state, has_open_positions) -> tuple:
        regime = phi_state.regime

        if not has_open_positions:
            if delta < 0.55 or regime == "INDETERMINATE":
                return "HOLD_CASH", False, False
            elif delta >= self.DELTA_CONSOLIDATE:
                return "CONTINUE", False, True
            else:
                return "CONTINUE", False, False

        if regime == "INDETERMINATE" and delta < 0.55:
            return "DEFENSIVE", False, False
        if delta < self.DELTA_BACKTRACK:
            return "BACKTRACK", True, False
        if delta >= self.DELTA_CONSOLIDATE:
            return "CONTINUE", False, True
        return "CONTINUE", False, False

    def _get_reasoning(
        self, delta, decision, phi_state,
        retorno_norm, drawdown_norm, regimen_consistencia,
        portfolio_value, initial_value, has_open_positions
    ) -> str:
        retorno_pct     = (portfolio_value - initial_value) / initial_value * 100
        estado_portfolio = "con posiciones abiertas" if has_open_positions else "100% cash"

        prompt = f"""Eres Kappa, el critic externo de Cortex V2. Evalua este estado de forma objetiva.

PORTFOLIO: ${portfolio_value:,.0f} ({retorno_pct:+.2f}%) | {estado_portfolio}
MERCADO: Regimen={phi_state.regime} | VIX={phi_state.raw_indicators.get('vix')} | Momentum={phi_state.raw_indicators.get('momentum_21d_pct')}%
PHI: Z4(causalidad)={phi_state.Z4_causalidad:+.3f} | Z7(valencia)={phi_state.Z7_valencia:+.3f} | Z8(complejidad)={phi_state.Z8_complejidad:+.3f}

DELTA: 0.4*{retorno_norm:.4f} + 0.4*{1-drawdown_norm:.4f} + 0.2*{regimen_consistencia:.4f} = {delta:.4f}
DECISION: {decision}
UMBRAL_CONSOLIDATE: {self.DELTA_CONSOLIDATE} | UMBRAL_BACKTRACK: {self.DELTA_BACKTRACK}

Explica en UNA frase tecnica y directa por que el delta es {delta:.4f} y la decision es {decision}.
Sin markdown, sin saltos de linea."""

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=120,
                temperature=0.1
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"Kappa reasoning fallback: {e}")
            return (
                f"Delta={delta:.4f} = 0.4*{retorno_norm:.3f} + "
                f"0.4*{1-drawdown_norm:.3f} + 0.2*{regimen_consistencia:.3f}. "
                f"Decision: {decision}."
            )


def test_kappa():
    from cortex.market_data import MarketData
    from cortex.layers.phi import PhiLayer

    print("\n" + "="*50)
    print("  CORTEX V2 - Test Capa Kappa (critic externo)")
    print("="*50 + "\n")

    md         = MarketData()
    account    = md.get_account()
    indicators = md.get_regime_indicators()

    print(f"Portfolio: ${account['portfolio_value']:,.2f} | Regimen: {indicators.get('regime')}\n")

    phi       = PhiLayer()
    phi_state = phi.factorize(indicators)
    print(phi_state.summary())

    print("\nEjecutando Kappa...\n")
    kappa      = KappaLayer()
    evaluation = kappa.evaluate(
        phi_state=phi_state,
        portfolio_value=account["portfolio_value"],
        initial_value=100_000.0,
        spy_benchmark_return=indicators.get("momentum_21d_pct", 0.0) / 3.0,
        open_positions=[]
    )

    print(evaluation.summary())

    print("\n--- Decision del sistema ---")
    if evaluation.decision == "HOLD_CASH":
        print(f"  → HOLD CASH (delta={evaluation.delta:.4f} < 0.55 o INDETERMINATE)")
    elif evaluation.decision == "BACKTRACK":
        print(f"  ⚠ BACKTRACK (delta={evaluation.delta:.4f} < {config.DELTA_BACKTRACK})")
        print(f"    Revertir a ultimo estado con delta >= {config.DELTA_CONSOLIDATE}")
    elif evaluation.decision == "DEFENSIVE":
        print(f"  ⚠ DEFENSIVO: 100% cash")
    elif evaluation.consolidate_memory:
        print(f"  ✓ CONTINUAR + consolidar memoria (delta={evaluation.delta:.4f} >= {config.DELTA_CONSOLIDATE})")
    else:
        print(f"  → CONTINUAR sin consolidar (delta={evaluation.delta:.4f}, zona 0.65-0.70)")

    print("\n" + "="*50)
    print("  Kappa OK")
    print("="*50 + "\n")
    return evaluation


if __name__ == "__main__":
    test_kappa()
