"""
PIPELINE CONDICION B — LLM Base sin Cortex
Experimento E2, Ablacion B | OSF: https://osf.io/wdkcx

Paper seccion 3.1:
  "LLM base sin Cortex con misma estrategia: controla la capacidad del modelo"

Que hace:
  - Mismos datos de mercado que Condicion A
  - UNA sola llamada a Claude Sonnet con contexto bruto (sin factorizacion)
  - Sin vector Z, sin isomorfos, sin delta score, sin Lambda, sin Mu
  - El modelo decide directamente: LONG / HOLD / DEFENSIVE / CASH

Por que existe:
  Controla si los resultados de E2 se deben a la arquitectura
  o simplemente a que Claude Sonnet es capaz por si solo.
  Si B aprox A en H4 y H7, las 10 capas no anaden valor causal demostrable.
"""
import json
import time
from datetime import datetime
from openai import OpenAI
from loguru import logger

from cortex.config import config
from cortex.market_data import MarketData
from cortex.layers.rho import RhoLayer


def _call_llm_baseline(indicators: dict, portfolio_value: float,
                       initial_value: float) -> dict:
    """Una sola llamada a Claude Sonnet con contexto bruto."""
    client = OpenAI(
        api_key=config.OPENROUTER_API_KEY,
        base_url=config.OPENROUTER_BASE_URL,
        timeout=config.OPENROUTER_TIMEOUT_SECONDS,
        max_retries=config.OPENROUTER_MAX_RETRIES,
    )
    drawdown_pct = (portfolio_value - initial_value) / initial_value * 100

    prompt = f"""You are a trading agent managing a $100,000 paper trading portfolio.

Current market conditions:
  VIX: {indicators['vix']} (fear index; <20=calm, 20-28=moderate, >28=stressed)
  SPY price: ${indicators['spy_price']}
  Momentum (21d): {indicators['momentum_21d_pct']:+.2f}%
  Realized volatility (21d): {indicators['vol_realized_pct']:.2f}%
  Drawdown from 90d high: {indicators['drawdown_90d_pct']:.2f}%
  Market regime: {indicators['regime']}
  Portfolio value: ${portfolio_value:,.2f}
  Portfolio drawdown from start: {drawdown_pct:+.2f}%

Decide the best trading action for today.

Respond ONLY with valid JSON:
{{
  "decision": "HOLD" or "LONG" or "DEFENSIVE" or "CASH",
  "confidence": <float 0.0-1.0>,
  "instruments": ["SPY"] or ["IEF"] or [],
  "allocation_pct": <float 0.0-1.0>,
  "reasoning": "<under 80 words>"
}}"""

    t0 = time.time()
    response = client.chat.completions.create(
        model=config.MODEL_PHI,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
        temperature=0.1
    )
    latency_ms = round((time.time() - t0) * 1000)

    raw = response.choices[0].message.content.strip()
    tokens_in  = response.usage.prompt_tokens
    tokens_out = response.usage.completion_tokens

    try:
        clean = raw.replace("```json", "").replace("```", "").strip()
        s = clean.find("{"); e = clean.rfind("}")
        data = json.loads(clean[s:e+1]) if s != -1 else {}
    except Exception as ex:
        logger.warning(f"Condicion B fallback parse: {ex}")
        data = {}

    return {
        "decision":       data.get("decision", "HOLD"),
        "confidence":     float(data.get("confidence", 0.5)),
        "instruments":    data.get("instruments", []),
        "allocation_pct": float(data.get("allocation_pct", 0.0)),
        "reasoning":      data.get("reasoning", "parse error"),
        "tokens_in":      tokens_in,
        "tokens_out":     tokens_out,
        "tokens_total":   tokens_in + tokens_out,
        "latency_ms":     latency_ms,
    }


def run_pipeline_b(session_id: str = None, initial_value: float = 100_000.0) -> dict:
    if session_id is None:
        session_id = datetime.now().strftime("b_%Y%m%d_%H%M%S")

    print(f"\n[CONDICION B] LLM base sin Cortex | {session_id}")

    md              = MarketData()
    indicators      = md.get_regime_indicators()
    account         = md.get_account()
    portfolio_value = account["portfolio_value"]

    print(f"  Mercado: VIX={indicators['vix']} | "
          f"Mom={indicators['momentum_21d_pct']:+.2f}% | "
          f"Regimen={indicators['regime']}")

    result     = _call_llm_baseline(indicators, portfolio_value, initial_value)
    decision   = result["decision"]
    confidence = result["confidence"]

    print(f"  Decision={decision} | confidence={confidence:.4f} | "
          f"tokens={result['tokens_total']} | {result['latency_ms']}ms")
    print(f"  Reasoning: {result['reasoning'][:80]}")

    rho = RhoLayer()
    stop_loss = rho.check_stop_loss(portfolio_value)
    if stop_loss:
        decision   = "HOLD"
        confidence = 0.0
        print("  Rho STOP-LOSS activado")

    print(f"[CONDICION B] Final: {decision}\n")

    return {
        "condition":      "B",
        "session_id":     session_id,
        "date":           datetime.now().strftime("%Y-%m-%d"),
        "regime":         indicators["regime"],
        "vix":            indicators["vix"],
        "momentum_21d":   indicators["momentum_21d_pct"],
        "decision":       decision,
        "confidence":     confidence,
        "stop_loss":      stop_loss,
        "portfolio_value":portfolio_value,
        "tokens_total":   result["tokens_total"],
        "latency_ms":     result["latency_ms"],
        "reasoning":      result["reasoning"],
    }


if __name__ == "__main__":
    run_pipeline_b()
