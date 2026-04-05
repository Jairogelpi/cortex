"""
Pipeline completo Cortex V2 - las 10 capas en secuencia.
Phi -> Kappa -> Omega -> Lambda -> Mu -> Sigma -> Rho -> Tau -> Omicron
"""
from datetime import datetime
from cortex.config import config
from cortex.market_data import MarketData
from cortex.layers.phi import PhiLayer
from cortex.layers.kappa import KappaLayer
from cortex.layers.omega import OmegaLayer
from cortex.layers.lambda_ import LambdaLayer
from cortex.layers.mu import MuLayer
from cortex.layers.sigma import SigmaLayer
from cortex.layers.rho import RhoLayer
from cortex.layers.tau import TauLayer
from cortex.layers.omicron import OmicronLayer
from loguru import logger


def run_pipeline(session_id: str = None) -> dict:
    """
    Ejecuta el pipeline completo de Cortex V2.
    Retorna el estado final del sistema.
    """
    if session_id is None:
        session_id = datetime.now().strftime("session_%Y%m%d_%H%M%S")

    print("\n" + "="*60)
    print("  CORTEX V2 — Pipeline completo (10 capas)")
    print(f"  Sesion: {session_id}")
    print("="*60 + "\n")

    # ── Datos reales ──────────────────────────────────────────────
    md = MarketData()
    indicators     = md.get_regime_indicators()
    account        = md.get_account()
    portfolio_value = account["portfolio_value"]

    print(f"Mercado: VIX={indicators['vix']} | Momentum={indicators['momentum_21d_pct']}% | Regimen={indicators['regime']}")
    print(f"Portfolio: ${portfolio_value:,.2f}\n")

    # ── Capa 1: Phi ───────────────────────────────────────────────
    print("[ Φ ] Factorizando estado...")
    phi_state = PhiLayer().factorize(indicators)
    print(f"      Regimen={phi_state.regime} | Confianza={phi_state.confidence:.2f} | Ortogonalidad={'OK' if phi_state.check_orthogonality()['orthogonality_ok'] else 'REVISAR'}")

    # ── Capa 2: Kappa ─────────────────────────────────────────────
    print("[ Κ ] Calculando delta...")
    kappa_eval = KappaLayer().evaluate(
        phi_state, portfolio_value,
        initial_value=100_000.0,
        spy_benchmark_return=indicators.get("momentum_21d_pct", 0) / 3.0,
        open_positions=[]
    )
    print(f"      delta={kappa_eval.delta:.4f} | Decision={kappa_eval.decision}")

    # ── Capa 3: Omega ─────────────────────────────────────────────
    print("[ Ω ] Detectando isomorfo (Opus)...")
    omega_hyp = OmegaLayer().generate_hypothesis(phi_state)
    print(f"      Isomorfo={omega_hyp.best_isomorph} | Sim={omega_hyp.similarity:.4f} | Senal={omega_hyp.trading_signal}")

    # ── Capa 4: Lambda ────────────────────────────────────────────
    print("[ Λ ] Validando contra datos reales (anti-sesgo)...")
    lambda_val = LambdaLayer().validate(omega_hyp, phi_state)
    print(f"      Veredicto={lambda_val.verdict} | Sim_adj={lambda_val.similarity:.4f} | Contradicciones={len(lambda_val.contradictions)}")

    # ── Capa 5: Mu ────────────────────────────────────────────────
    print("[ Μ ] Memoria selectiva (sleep replay)...")
    mu = MuLayer(session_id=session_id)
    should_consolidate = mu.should_consolidate(kappa_eval)
    if should_consolidate:
        mu.consolidate(phi_state, kappa_eval, lambda_val)
        print(f"      CONSOLIDADO: delta={kappa_eval.delta:.4f} >= {config.DELTA_CONSOLIDATE}")
    else:
        print(f"      RECHAZADO: delta={kappa_eval.delta:.4f} < {config.DELTA_CONSOLIDATE} (correcto)")

    # ── Capa 6: Sigma ─────────────────────────────────────────────
    print("[ Σ ] Orquestando subagentes...")
    sigma_orch = SigmaLayer().orchestrate(phi_state, kappa_eval, omega_hyp, lambda_val)
    print(f"      Decision={sigma_orch.decision} | Subagentes={sigma_orch.active_subagents}")

    # ── Capa 7: Rho ───────────────────────────────────────────────
    print("[ Ρ ] Verificando fiabilidad...")
    rho = RhoLayer()
    stop_loss = rho.check_stop_loss(portfolio_value)
    checkpoint = rho.save_checkpoint(
        portfolio_value, kappa_eval.delta,
        phi_state.regime, omega_hyp.trading_signal,
        open_positions=[], session_id=session_id
    )
    print(f"      Stop-loss={'ACTIVADO' if stop_loss else 'OK'} | Checkpoint={checkpoint.checkpoint_id}")

    # ── Capa 8: Tau ───────────────────────────────────────────────
    print("[ Τ ] Governance (aprobacion)...")
    tau_dec = TauLayer().evaluate(
        sigma_decision=sigma_orch.decision,
        trading_signal=omega_hyp.trading_signal,
        portfolio_value=portfolio_value,
        proposed_allocation_pct=omega_hyp.allocation_pct,
        is_paper_trading=True
    )
    print(f"      Aprobada={tau_dec.approved} | Requiere_humano={tau_dec.requires_human} | Accion={tau_dec.action}")

    # ── Capa 9: Omicron ───────────────────────────────────────────
    print("[ Ο ] Registrando telemetria...")
    omicron = OmicronLayer(session_id=session_id)
    event = omicron.record(
        event_type="HEARTBEAT",
        phi_state=phi_state,
        kappa_eval=kappa_eval,
        omega_hyp=omega_hyp,
        lambda_val=lambda_val,
        sigma_orch=sigma_orch,
        tau_dec=tau_dec,
        rho_status=rho.status,
        portfolio_value=portfolio_value,
        notes=f"Pipeline completo. Contradicciones Lambda: {lambda_val.contradictions[:1]}"
    )
    summary = omicron.get_session_summary()
    print(f"      Evento registrado: {event.event_type}")
    print(f"      Log JSONL: {summary['log_jsonl']}")
    print(f"      Log MD:    {summary['log_md']}")

    # ── Resultado final ───────────────────────────────────────────
    print("\n" + "="*60)
    print("  RESULTADO FINAL DEL PIPELINE")
    print("="*60)
    print(f"  Φ  Regimen:      {phi_state.regime}")
    print(f"  Κ  Delta:        {kappa_eval.delta:.4f}  ({kappa_eval.decision})")
    print(f"  Ω  Isomorfo:     {omega_hyp.best_isomorph}  (Sim={omega_hyp.similarity:.4f})")
    print(f"  Λ  Validacion:   {lambda_val.verdict}  (Sim_adj={lambda_val.similarity:.4f})")
    print(f"  Μ  Memoria:      {'consolidado' if should_consolidate else 'rechazado'}")
    print(f"  Σ  Orquestacion: {sigma_orch.decision}")
    print(f"  Ρ  Stop-loss:    {'ACTIVADO' if stop_loss else 'OK'}  (drawdown={rho.status.current_drawdown_pct:.2f}%)")
    print(f"  Τ  Governance:   {'APROBADO' if tau_dec.approved else 'BLOQUEADO'}  ({tau_dec.action})")
    print(f"  Ο  Telemetria:   {event.event_type} registrado")
    print()
    print(f"  ACCION FINAL: {sigma_orch.decision}")
    if sigma_orch.decision == "HOLD":
        print(f"  -> Mantener 100% cash. Regimen incierto (Lorenz/INDETERMINATE).")
        print(f"     No se ejecuta ninguna orden en Alpaca.")
    elif sigma_orch.decision == "EXECUTE":
        print(f"  -> Ejecutar: {omega_hyp.instruments} al {omega_hyp.allocation_pct*100:.0f}%")
        print(f"     Pendiente de aprobacion en Tau (paper trading: auto-aprobado).")
    elif sigma_orch.decision == "DEFENSIVE":
        print(f"  -> Posicion defensiva: {omega_hyp.instruments}")
    elif sigma_orch.decision == "BACKTRACK":
        print(f"  -> Backtrack al ultimo estado estable (gestionado por Rho).")
    print("="*60 + "\n")

    return {
        "session_id": session_id,
        "regime": phi_state.regime,
        "delta": kappa_eval.delta,
        "isomorph": omega_hyp.best_isomorph,
        "lambda_verdict": lambda_val.verdict,
        "sigma_decision": sigma_orch.decision,
        "tau_approved": tau_dec.approved,
        "stop_loss": stop_loss,
        "portfolio_value": portfolio_value,
        "omicron_summary": summary
    }


if __name__ == "__main__":
    run_pipeline()
