"""
Pipeline Cortex V2 — VERSION UNIFICADA (minimos tokens)
OSF: https://osf.io/wdkcx

ARQUITECTURA REVOLUCIONARIA:
  Antes:  Phi(LLM) + Kappa(LLM) + Omega(LLM) + Lambda(LLM) = 4 llamadas, ~2284 tokens
  Ahora:  UnifiedLayer(1 LLM) + Kappa(0 LLM) = 1 llamada, ~260 tokens

  Reduccion: ~88%
  Ratio A/B esperado: ~260/400 = 0.65x (cerca del objetivo 0.45x)

Las capas Mu, Sigma, Rho, Tau, Omicron no usan LLM — sin cambio.
"""
from datetime import datetime
from cortex.config import config
from cortex.market_data import MarketData
from cortex.layers.kappa import KappaLayer
from cortex.layers.mu import MuLayer
from cortex.layers.sigma import SigmaLayer
from cortex.layers.rho import RhoLayer
from cortex.layers.tau import TauLayer
from cortex.layers.omicron import OmicronLayer
from cortex.unified_layer import UnifiedLayer, _get_market_data_fresh
from cortex.token_tracker import token_tracker
from loguru import logger


def run_pipeline(session_id: str = None) -> dict:
    if session_id is None:
        session_id = datetime.now().strftime("session_%Y%m%d_%H%M%S")

    token_tracker.reset()

    print("\n" + "="*60)
    print("  CORTEX V2 — Pipeline unificado (1 llamada LLM)")
    print(f"  Sesion: {session_id}")
    print("="*60 + "\n")

    md              = MarketData()
    indicators      = md.get_regime_indicators()
    account         = md.get_account()
    portfolio_value = account["portfolio_value"]

    print(f"Mercado: VIX={indicators['vix']} | Mom={indicators['momentum_21d_pct']}% | Reg={indicators['regime']}")
    print(f"Portfolio: ${portfolio_value:,.2f}\n")

    # ── Datos frescos (Yahoo Finance + FRED) para UnifiedLayer ─────
    print("[ DATA ] Obteniendo datos frescos...")
    fresh = _get_market_data_fresh()
    print(f"         VIX_ch5d={fresh.get('vix_change_5d',0):+.1f} Mom5d={fresh.get('spy_momentum_5d_pct',0):+.1f}% sources={fresh.get('sources',[])}")

    # ── UnifiedLayer: Phi + Omega + Lambda en 1 llamada LLM ────────
    print("[ UNIFIED ] Phi+Omega+Lambda (1 llamada LLM)...")
    unified = UnifiedLayer()
    phi_state, omega_hyp, lambda_val = unified.run(indicators, fresh)
    tok_unified = token_tracker.total()
    print(f"            {omega_hyp.best_isomorph} Sim={omega_hyp.similarity:.4f} -> {lambda_val.verdict}")
    print(f"            Tokens reales: {tok_unified} (1 llamada)")

    # ── Kappa: deterministico (0 tokens LLM) ───────────────────────
    print("[ K ] Kappa deterministico (0 tokens)...")
    kappa_eval = KappaLayer().evaluate(
        phi_state, portfolio_value,
        initial_value=100_000.0,
        spy_benchmark_return=indicators.get("momentum_21d_pct", 0) / 3.0,
        open_positions=[]
    )
    print(f"      delta={kappa_eval.delta:.4f} | {kappa_eval.decision}")

    # ── Mu: memoria selectiva ───────────────────────────────────────
    print("[ M ] Mu...")
    mu = MuLayer(session_id=session_id)
    should_consolidate = mu.should_consolidate(kappa_eval)
    if should_consolidate:
        mu.consolidate(phi_state, kappa_eval, lambda_val)
        print(f"      CONSOLIDADO: delta={kappa_eval.delta:.4f} >= {config.DELTA_CONSOLIDATE}")
    else:
        print(f"      RECHAZADO: delta={kappa_eval.delta:.4f} < {config.DELTA_CONSOLIDATE}")

    # ── Sigma ───────────────────────────────────────────────────────
    print("[ S ] Sigma...")
    sigma_orch = SigmaLayer().orchestrate(phi_state, kappa_eval, omega_hyp, lambda_val)
    print(f"      Decision={sigma_orch.decision}")

    # ── Rho ─────────────────────────────────────────────────────────
    print("[ R ] Rho...")
    rho       = RhoLayer()
    stop_loss = rho.check_stop_loss(portfolio_value)
    checkpoint= rho.save_checkpoint(
        portfolio_value, kappa_eval.delta,
        phi_state.regime, omega_hyp.trading_signal,
        open_positions=[], session_id=session_id
    )
    print(f"      Stop-loss={'ACTIVADO' if stop_loss else 'OK'} | {checkpoint.checkpoint_id}")

    # ── Tau ─────────────────────────────────────────────────────────
    print("[ T ] Tau...")
    tau_dec = TauLayer().evaluate(
        sigma_decision=sigma_orch.decision,
        trading_signal=omega_hyp.trading_signal,
        portfolio_value=portfolio_value,
        proposed_allocation_pct=omega_hyp.allocation_pct,
        is_paper_trading=True
    )
    print(f"      {tau_dec.action}")

    # ── H1: tokens reales ───────────────────────────────────────────
    token_summary = token_tracker.summary()
    tokens_real   = token_summary["total"]
    print(f"\n[ H1 ] Tokens reales: {tokens_real} | {token_summary['by_layer']}")

    # ── Omicron ─────────────────────────────────────────────────────
    print("[ O ] Omicron...")
    omicron = OmicronLayer(session_id=session_id)
    event   = omicron.record(
        event_type="HEARTBEAT",
        phi_state=phi_state,
        kappa_eval=kappa_eval,
        omega_hyp=omega_hyp,
        lambda_val=lambda_val,
        sigma_orch=sigma_orch,
        tau_dec=tau_dec,
        rho_status=rho.status,
        portfolio_value=portfolio_value,
        notes=f"Unified pipeline. Tokens={tokens_real}. Contradictions={lambda_val.contradictions[:1]}"
    )
    summary = omicron.get_session_summary()
    print(f"      {event.event_type} | {summary['log_jsonl']}")

    print("\n" + "="*60)
    print("  RESULTADO")
    print("="*60)
    print(f"  Phi  {phi_state.regime}")
    print(f"  K    delta={kappa_eval.delta:.4f}  ({kappa_eval.decision})")
    print(f"  Omega {omega_hyp.best_isomorph}  Sim={omega_hyp.similarity:.4f}")
    print(f"  Lambda {lambda_val.verdict}  Sim_adj={lambda_val.similarity:.4f}  contra={len(lambda_val.contradictions)}")
    print(f"  M    {'CONSOLIDADO' if should_consolidate else 'rechazado'}")
    print(f"  S    {sigma_orch.decision}")
    print(f"  R    {'STOP' if stop_loss else 'OK'}  drawdown={rho.status.current_drawdown_pct:.2f}%")
    print(f"  T    {tau_dec.action}")
    print(f"  H1   {tokens_real} tokens REALES (1 llamada LLM)")
    print()
    print(f"  ACCION: {sigma_orch.decision}")
    print("="*60 + "\n")

    return {
        "session_id":      session_id,
        "regime":          phi_state.regime,
        "delta":           kappa_eval.delta,
        "isomorph":        omega_hyp.best_isomorph,
        "lambda_verdict":  lambda_val.verdict,
        "sigma_decision":  sigma_orch.decision,
        "tau_approved":    tau_dec.approved,
        "stop_loss":       stop_loss,
        "portfolio_value": portfolio_value,
        "tokens_total":    tokens_real,
        "tokens_by_layer": token_summary["by_layer"],
        "omicron_summary": summary,
    }


if __name__ == "__main__":
    run_pipeline()
