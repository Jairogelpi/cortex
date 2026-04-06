"""
PIPELINE CONDICION D — Solo Kappa + Rho (sin abstraccion)
Experimento E2, Ablacion D | OSF: https://osf.io/wdkcx

Paper seccion 3.1:
  "Solo Kappa+Rho sin el resto: controla si el backtrack solo
   ya produce el valor"

Sin Phi, sin Omega, sin Lambda, sin Mu, sin Sigma.
Kappa usa indicadores crudos (sin vector Z de Phi).
0 llamadas LLM — completamente deterministico.
"""
import time
from datetime import datetime
from loguru import logger

from cortex.config import config
from cortex.market_data import MarketData
from cortex.layers.rho import RhoLayer
from cortex.layers.tau import TauLayer


def _kappa_raw(indicators: dict, portfolio_value: float,
               initial_value: float) -> dict:
    """
    Kappa deterministico con indicadores crudos (sin vector Z de Phi).
    Formula identica al paper pero sin factorizacion previa.
    """
    retorno      = (portfolio_value - initial_value) / initial_value
    retorno_norm = max(0.0, min(1.0, (retorno + 0.20) / 0.40))

    drawdown      = abs(indicators.get("drawdown_90d_pct", 0.0)) / 100.0
    drawdown_norm = max(0.0, min(1.0, drawdown / 0.30))

    vix    = indicators.get("vix", 20.0)
    mom    = indicators.get("momentum_21d_pct", 0.0)
    regime = indicators.get("regime", "INDETERMINATE")

    regime_map = {
        "R1_EXPANSION":    0.85,
        "R2_ACCUMULATION": 0.75,
        "R3_TRANSITION":   0.70,
        "R4_CONTRACTION":  0.75,
        "INDETERMINATE":   0.45,
    }
    base_consist  = regime_map.get(regime, 0.45)
    vix_penalty   = max(0.0, (vix - 20.0) / 60.0) * 0.20
    mom_boost     = max(0.0, mom / 10.0) * 0.10 if mom > 0 else 0.0
    regimen_consist = max(0.05, min(1.0, base_consist - vix_penalty + mom_boost))

    delta = round(
        0.4 * retorno_norm +
        0.4 * (1.0 - drawdown_norm) +
        0.2 * regimen_consist, 4
    )

    if delta < config.DELTA_BACKTRACK:
        decision = "BACKTRACK"
    elif delta < 0.68:
        decision = "HOLD_CASH"
    elif regime in ("R3_TRANSITION", "R4_CONTRACTION"):
        decision = "DEFENSIVE"
    else:
        decision = "CONTINUE"

    return {"delta": delta, "decision": decision,
            "retorno_norm": round(retorno_norm, 4),
            "drawdown_norm": round(drawdown_norm, 4),
            "regimen_consist": round(regimen_consist, 4)}


def run_pipeline_d(session_id: str = None, initial_value: float = 100_000.0) -> dict:
    if session_id is None:
        session_id = datetime.now().strftime("d_%Y%m%d_%H%M%S")

    print(f"\n[CONDICION D] Kappa+Rho sin abstraccion | {session_id}")

    t0              = time.time()
    md              = MarketData()
    indicators      = md.get_regime_indicators()
    account         = md.get_account()
    portfolio_value = account["portfolio_value"]

    print(f"  Mercado: VIX={indicators['vix']} | "
          f"Mom={indicators['momentum_21d_pct']:+.2f}% | "
          f"Regimen={indicators['regime']}")
    print("  Phi: DESACTIVADA | Omega: DESACTIVADA | Lambda: DESACTIVADA")
    print("  Mu: DESACTIVADA | Sigma: DESACTIVADA")

    kappa_result = _kappa_raw(indicators, portfolio_value, initial_value)
    delta        = kappa_result["delta"]
    decision_k   = kappa_result["decision"]

    signal_map = {
        "BACKTRACK": "CASH", "HOLD_CASH": "CASH",
        "DEFENSIVE": "CASH",
        "CONTINUE":  "LONG" if indicators.get("momentum_21d_pct", 0) > 0 else "CASH",
    }
    signal = signal_map.get(decision_k, "CASH")

    print(f"  Kappa (raw): delta={delta:.4f} | decision={decision_k}")

    rho = RhoLayer()
    stop_loss = rho.check_stop_loss(portfolio_value)
    rho.save_checkpoint(portfolio_value, delta,
                        indicators["regime"], signal,
                        open_positions=[], session_id=session_id)
    if stop_loss:
        decision_k = "HOLD"
        signal     = "CASH"
        delta      = 0.0
        print("  Rho STOP-LOSS activado")

    tau_dec = TauLayer().evaluate(
        sigma_decision="HOLD" if decision_k in ("BACKTRACK","HOLD_CASH") else decision_k,
        trading_signal=signal,
        portfolio_value=portfolio_value,
        proposed_allocation_pct=0.80 if signal == "LONG" else 0.0,
        is_paper_trading=True
    )

    latency_ms = round((time.time() - t0) * 1000)

    print(f"  Tau: {tau_dec.action} | tokens=0 (deterministico) | {latency_ms}ms")
    print(f"[CONDICION D] Final: {decision_k}\n")

    return {
        "condition":       "D",
        "session_id":      session_id,
        "date":            datetime.now().strftime("%Y-%m-%d"),
        "regime":          indicators["regime"],
        "vix":             indicators["vix"],
        "momentum_21d":    indicators["momentum_21d_pct"],
        "decision":        decision_k,
        "confidence":      delta,
        "delta":           delta,
        "signal":          signal,
        "stop_loss":       stop_loss,
        "tau_action":      tau_dec.action,
        "portfolio_value": portfolio_value,
        "tokens_total":    0,
        "latency_ms":      latency_ms,
        "phi_regime":      None,
        "isomorph":        None,
        "lambda_verdict":  "DISABLED",
        "mu_consolidated": False,
    }


if __name__ == "__main__":
    run_pipeline_d()
