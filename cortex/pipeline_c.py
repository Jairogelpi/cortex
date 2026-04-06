"""
PIPELINE CONDICION C — Solo Phi + Omega + Kappa (sin infraestructura)
Experimento E2, Ablacion C | OSF: https://osf.io/wdkcx

Paper seccion 3.1:
  "Phi+Omega+Kappa sin Lambda+Mu+Sigma+Rho+Tau+Omicron:
   aisla la contribucion de las capas de abstraccion"

Lambda DESACTIVADA: sin validacion anti-sesgo de confirmacion.
Mu DESACTIVADA: sin memoria entre sesiones.
Sigma DESACTIVADA: sin orquestacion de subagentes.
Rho y Tau activos: seguridad siempre.
"""
import time
from datetime import datetime
from loguru import logger

from cortex.config import config
from cortex.market_data import MarketData
from cortex.layers.phi import PhiLayer
from cortex.layers.kappa import KappaLayer
from cortex.layers.omega import OmegaLayer
from cortex.layers.rho import RhoLayer
from cortex.layers.tau import TauLayer


def run_pipeline_c(session_id: str = None, initial_value: float = 100_000.0) -> dict:
    if session_id is None:
        session_id = datetime.now().strftime("c_%Y%m%d_%H%M%S")

    print(f"\n[CONDICION C] Phi+Omega+Kappa sin infraestructura | {session_id}")

    t0              = time.time()
    md              = MarketData()
    indicators      = md.get_regime_indicators()
    account         = md.get_account()
    portfolio_value = account["portfolio_value"]

    print(f"  Mercado: VIX={indicators['vix']} | "
          f"Mom={indicators['momentum_21d_pct']:+.2f}% | "
          f"Regimen={indicators['regime']}")

    phi_state  = PhiLayer().factorize(indicators)
    kappa_eval = KappaLayer().evaluate(
        phi_state, portfolio_value,
        initial_value=initial_value,
        spy_benchmark_return=indicators.get("momentum_21d_pct", 0) / 3.0,
        open_positions=[]
    )
    omega_hyp = OmegaLayer().generate_hypothesis(phi_state)

    decision   = kappa_eval.decision
    signal     = omega_hyp.trading_signal
    confidence = kappa_eval.delta

    print(f"  Phi: regime={phi_state.regime} | delta={kappa_eval.delta:.4f}")
    print(f"  Omega: {omega_hyp.best_isomorph} (sim={omega_hyp.similarity:.4f}) -> {signal}")
    print(f"  Lambda: DESACTIVADA | Mu: DESACTIVADA | Sigma: DESACTIVADA")

    rho = RhoLayer()
    stop_loss = rho.check_stop_loss(portfolio_value)
    if stop_loss:
        decision   = "HOLD"
        confidence = 0.0
        signal     = "CASH"
        print("  Rho STOP-LOSS activado")

    tau_dec = TauLayer().evaluate(
        sigma_decision=decision,
        trading_signal=signal,
        portfolio_value=portfolio_value,
        proposed_allocation_pct=omega_hyp.allocation_pct,
        is_paper_trading=True
    )

    latency_ms   = round((time.time() - t0) * 1000)
    tokens_total = 800 + 200 + 1200  # estimacion: phi + kappa + omega

    print(f"  Tau: {tau_dec.action} | {latency_ms}ms")
    print(f"[CONDICION C] Final: {decision}\n")

    return {
        "condition":       "C",
        "session_id":      session_id,
        "date":            datetime.now().strftime("%Y-%m-%d"),
        "regime":          phi_state.regime,
        "vix":             indicators["vix"],
        "momentum_21d":    indicators["momentum_21d_pct"],
        "decision":        decision,
        "confidence":      confidence,
        "delta":           kappa_eval.delta,
        "isomorph":        omega_hyp.best_isomorph,
        "isomorph_sim":    omega_hyp.similarity,
        "signal":          signal,
        "stop_loss":       stop_loss,
        "tau_action":      tau_dec.action,
        "portfolio_value": portfolio_value,
        "tokens_total":    tokens_total,
        "latency_ms":      latency_ms,
        "lambda_verdict":  "DISABLED",
        "lambda_sim":      None,
        "mu_consolidated": False,
        "sigma_subagents": [],
    }


if __name__ == "__main__":
    run_pipeline_c()
