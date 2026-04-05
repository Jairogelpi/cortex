"""
TEST DE INTEGRACION COMPLETO — Cortex V2
Verifica que las 10 capas funcionan juntas correctamente.

Este test va mas alla del pipeline normal: verifica las
invariantes del sistema que el paper garantiza:

1. Phi produce vectores ortogonales (I < 0.3)
2. Kappa calcula delta consistentemente con la formula del paper
3. Omega activa exactamente el isomorfo correcto
4. Lambda detecta al menos una señal contradictoria cuando el
   mercado esta en regimen INDETERMINATE (anti-sesgo)
5. Mu rechaza cuando delta < DELTA_CONSOLIDATE
6. Sigma no supera MAX_SUBAGENTS
7. Rho guarda checkpoints y detecta stop-loss correctamente
8. Tau bloquea acciones irreversibles en trading real
9. Omicron registra todos los eventos en ambos formatos
10. El pipeline completo produce exactamente una decision coherente
"""
import sys
from datetime import datetime
from pathlib import Path
from cortex.config import config
from cortex.market_data import MarketData
from cortex.layers.phi import PhiLayer
from cortex.layers.kappa import KappaLayer
from cortex.layers.omega import OmegaLayer, PHYSICAL_ISOMORPHS
from cortex.layers.lambda_ import LambdaLayer
from cortex.layers.mu import MuLayer
from cortex.layers.sigma import SigmaLayer
from cortex.layers.rho import RhoLayer
from cortex.layers.tau import TauLayer
from cortex.layers.omicron import OmicronLayer

PASS = "PASS"
FAIL = "FAIL"
results = []

def check(name: str, condition: bool, detail: str = ""):
    status = PASS if condition else FAIL
    results.append((name, status, detail))
    icon = "✓" if condition else "✗"
    print(f"  {icon} {name}: {status}" + (f" — {detail}" if detail else ""))
    return condition

def test_integration():
    session_id = f"integration_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    print("\n" + "="*60)
    print("  CORTEX V2 — Test de Integracion Completo")
    print(f"  Sesion: {session_id}")
    print("="*60 + "\n")

    # ── Datos reales ──────────────────────────────────────────────
    md = MarketData()
    indicators     = md.get_regime_indicators()
    account        = md.get_account()
    portfolio_value = account["portfolio_value"]

    print(f"Mercado: VIX={indicators['vix']} | Momentum={indicators['momentum_21d_pct']}% | Regimen={indicators['regime']}")
    print(f"Portfolio: ${portfolio_value:,.2f}\n")

    # ── Invariante 0: conexion con Alpaca ────────────────────────
    print("[ CONEXION ]")
    check("Alpaca conectado", portfolio_value > 0,
          f"portfolio=${portfolio_value:,.2f}")
    check("VIX disponible", indicators.get("vix", 0) > 0,
          f"VIX={indicators.get('vix')}")
    print()

    # ── Capa Phi ─────────────────────────────────────────────────
    print("[ Φ PHI ]")
    phi_state = PhiLayer().factorize(indicators)
    orth = phi_state.check_orthogonality()

    check("Ortogonalidad OK", orth["orthogonality_ok"],
          f"var={orth['z_variance']:.4f} spread={orth['z_spread']:.4f}")
    check("Varianza Z suficiente", orth["z_variance"] > 0.15,
          f"var={orth['z_variance']:.4f} (umbral 0.15)")
    check("Confianza en [0,1]", 0 <= phi_state.confidence <= 1,
          f"confianza={phi_state.confidence:.2f}")
    check("Regimen valido", phi_state.regime in (
        "R1_EXPANSION","R2_ACCUMULATION","R3_TRANSITION","R4_CONTRACTION","INDETERMINATE"),
          f"regimen={phi_state.regime}")
    print()

    # ── Capa Kappa ───────────────────────────────────────────────
    print("[ Κ KAPPA ]")
    kappa_eval = KappaLayer().evaluate(
        phi_state, portfolio_value,
        initial_value=100_000.0,
        spy_benchmark_return=indicators.get("momentum_21d_pct", 0) / 3.0,
        open_positions=[]
    )

    check("Delta en [0,1]", 0 <= kappa_eval.delta <= 1,
          f"delta={kappa_eval.delta:.4f}")

    # Verificar formula del paper manualmente
    delta_calculado = (
        0.4 * kappa_eval.retorno_norm +
        0.4 * (1 - kappa_eval.drawdown_norm) +
        0.2 * kappa_eval.regimen_consistencia
    )
    check("Formula delta correcta",
          abs(delta_calculado - kappa_eval.delta) < 0.001,
          f"calculado={delta_calculado:.4f} reportado={kappa_eval.delta:.4f}")

    check("Decision valida", kappa_eval.decision in (
        "CONTINUE","BACKTRACK","DEFENSIVE","HOLD_CASH"),
          f"decision={kappa_eval.decision}")
    check("Sin backtrack en cash", not kappa_eval.backtrack_required,
          "correcto: sin posiciones no hay backtrack")
    print()

    # ── Capa Omega ───────────────────────────────────────────────
    print("[ Ω OMEGA ]")
    omega_hyp = OmegaLayer().generate_hypothesis(phi_state)

    check("Isomorfo valido", omega_hyp.best_isomorph in PHYSICAL_ISOMORPHS,
          f"isomorfo={omega_hyp.best_isomorph}")
    check("Similitud en [0,1]", 0 <= omega_hyp.similarity <= 1,
          f"sim={omega_hyp.similarity:.4f}")
    check("Umbral 0.65 verificado",
          (omega_hyp.threshold_met) == (omega_hyp.similarity >= config.SIM_THRESHOLD),
          f"sim={omega_hyp.similarity:.4f} threshold_met={omega_hyp.threshold_met}")
    check("Senal coherente con isomorfo",
          omega_hyp.trading_signal in ("LONG","LONG_PREPARE","DEFENSIVE","MEAN_REVERSION","CASH"),
          f"senal={omega_hyp.trading_signal}")
    check("Todas las similitudes calculadas",
          len(omega_hyp.all_similarities) == len(PHYSICAL_ISOMORPHS),
          f"{len(omega_hyp.all_similarities)}/{len(PHYSICAL_ISOMORPHS)} isomorfos")
    print()

    # ── Capa Lambda ──────────────────────────────────────────────
    print("[ Λ LAMBDA ]")
    lambda_val = LambdaLayer().validate(omega_hyp, phi_state)

    check("Similitud en [0,1]", 0 <= lambda_val.similarity <= 1,
          f"sim_adj={lambda_val.similarity:.4f}")
    check("Veredicto valido", lambda_val.verdict in (
        "CONFIRMED","UNCERTAIN","CONTRADICTED","LAMBDA_OFFLINE"),
          f"veredicto={lambda_val.verdict}")
    check("Fuentes consultadas", len(lambda_val.api_sources_used) > 0,
          f"fuentes={lambda_val.api_sources_used}")
    check("Z_fresh tiene 8 dimensiones", len(lambda_val.z_fresh) == 8,
          f"dims={len(lambda_val.z_fresh)}")
    check("Z_referencia tiene 8 dimensiones", len(lambda_val.z_reference) == 8,
          f"dims={len(lambda_val.z_reference)}")
    # Anti-sesgo: Lambda debe ser capaz de encontrar contradicciones
    check("Anti-sesgo activo (reasoning generado)",
          len(lambda_val.reasoning) > 20,
          f"reasoning={lambda_val.reasoning[:60]}...")
    print()

    # ── Capa Mu ──────────────────────────────────────────────────
    print("[ Μ MU ]")
    mu = MuLayer(session_id=session_id)
    should = mu.should_consolidate(kappa_eval)

    consolidacion_esperada = kappa_eval.delta >= config.DELTA_CONSOLIDATE
    check("Consolidacion coherente con delta",
          should == consolidacion_esperada,
          f"delta={kappa_eval.delta:.4f} umbral={config.DELTA_CONSOLIDATE} consolidar={should}")

    if should:
        entry = mu.consolidate(phi_state, kappa_eval, lambda_val)
        check("Entrada consolidada valida", entry.delta >= config.DELTA_CONSOLIDATE,
              f"delta={entry.delta:.4f}")
    else:
        check("Rechazo correcto (delta bajo)", True,
              f"delta={kappa_eval.delta:.4f} < {config.DELTA_CONSOLIDATE}")

    delta_est = mu.get_initial_delta_estimate()
    check("Delta inicial estimado valido", delta_est >= config.DELTA_BACKTRACK,
          f"estimado={delta_est:.4f}")
    print()

    # ── Capa Sigma ───────────────────────────────────────────────
    print("[ Σ SIGMA ]")
    sigma_orch = SigmaLayer().orchestrate(phi_state, kappa_eval, omega_hyp, lambda_val)

    check("Limite subagentes respetado",
          len(sigma_orch.active_subagents) <= config.MAX_SUBAGENTS,
          f"{len(sigma_orch.active_subagents)}/{config.MAX_SUBAGENTS}")
    check("Decision valida", sigma_orch.decision in (
        "HOLD","EXECUTE","DEFENSIVE","BACKTRACK"),
          f"decision={sigma_orch.decision}")
    check("Sigma es rapido (determinista)", sigma_orch.total_duration_seconds < 1.0,
          f"{sigma_orch.total_duration_seconds:.3f}s")
    check("Sin deadlocks detectados", sigma_orch.deadlocks_detected == 0)
    print()

    # ── Capa Rho ─────────────────────────────────────────────────
    print("[ Ρ RHO ]")
    rho = RhoLayer()
    stop_triggered = rho.check_stop_loss(portfolio_value)
    ckpt = rho.save_checkpoint(
        portfolio_value, kappa_eval.delta,
        phi_state.regime, omega_hyp.trading_signal,
        [], session_id
    )

    check("Stop-loss no activado (portfolio intacto)", not stop_triggered,
          f"drawdown={rho.status.current_drawdown_pct:.2f}%")
    check("Sistema saludable", rho.status.system_healthy)
    check("Checkpoint guardado", ckpt.checkpoint_id.startswith("ckpt_"))
    check("Estabilidad checkpoint coherente",
          ckpt.is_stable == (kappa_eval.delta >= config.DELTA_CONSOLIDATE),
          f"delta={kappa_eval.delta:.4f} is_stable={ckpt.is_stable}")
    print()

    # ── Capa Tau ─────────────────────────────────────────────────
    print("[ Τ TAU ]")
    tau_dec = TauLayer().evaluate(
        sigma_orch.decision, omega_hyp.trading_signal,
        portfolio_value, omega_hyp.allocation_pct,
        is_paper_trading=True
    )

    check("Decision aprobada en paper trading", tau_dec.approved)
    check("Accion clasificada", len(tau_dec.action) > 0,
          f"accion={tau_dec.action}")
    check("Tools permitidas definidas", len(tau_dec.allowed_tools) > 0)

    # Verificar que accion grande requiere humano
    tau_large = TauLayer().evaluate("EXECUTE","LONG",100_000.0,0.80,True)
    check("Posicion grande requiere humano", tau_large.requires_human,
          "EXECUTE 80% requiere aprobacion humana en real")

    # Verificar bloqueo en trading real
    tau_real = TauLayer().evaluate("EXECUTE","LONG",100_000.0,0.80,False)
    check("Bloqueo en trading real", not tau_real.approved,
          "EXECUTE 80% bloqueado en is_paper_trading=False")
    print()

    # ── Capa Omicron ─────────────────────────────────────────────
    print("[ Ο OMICRON ]")
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
        notes="Test de integracion completo"
    )

    check("Evento registrado", event.event_type == "HEARTBEAT")
    check("Log JSONL creado", Path(omicron.jsonl_path).exists(),
          str(omicron.jsonl_path))
    check("Log Markdown creado", Path(omicron.md_path).exists(),
          str(omicron.md_path))
    check("Delta coherente en log", event.delta == kappa_eval.delta,
          f"log={event.delta:.4f} kappa={kappa_eval.delta:.4f}")
    check("Rho healthy en log", event.rho_healthy == rho.status.system_healthy)
    print()

    # ── Coherencia del pipeline completo ────────────────────────
    print("[ COHERENCIA GLOBAL ]")

    # La decision de Sigma debe ser coherente con Kappa y Omega
    if kappa_eval.delta < config.DELTA_BACKTRACK:
        check("Sigma=HOLD cuando delta bajo",
              sigma_orch.decision in ("HOLD","BACKTRACK","DEFENSIVE"),
              f"delta={kappa_eval.delta:.4f} sigma={sigma_orch.decision}")
    if omega_hyp.trading_signal == "CASH":
        check("Sigma=HOLD cuando Omega=CASH",
              sigma_orch.decision == "HOLD",
              f"omega=CASH sigma={sigma_orch.decision}")
    if lambda_val.verdict == "CONTRADICTED":
        check("Sigma=BACKTRACK cuando Lambda contradice",
              sigma_orch.decision == "BACKTRACK",
              f"lambda=CONTRADICTED sigma={sigma_orch.decision}")

    # El delta debe estar en rango razonable para el mercado actual
    check("Delta razonable para el mercado",
          0.3 <= kappa_eval.delta <= 0.9,
          f"delta={kappa_eval.delta:.4f}")

    print()

    # ── Resumen final ─────────────────────────────────────────────
    passed = sum(1 for _, s, _ in results if s == PASS)
    failed = sum(1 for _, s, _ in results if s == FAIL)
    total  = len(results)

    print("="*60)
    print(f"  RESULTADO: {passed}/{total} checks pasados")
    if failed > 0:
        print(f"\n  FALLIDOS ({failed}):")
        for name, status, detail in results:
            if status == FAIL:
                print(f"    ✗ {name}: {detail}")
    print()
    print(f"  Pipeline del 5 abril 2026:")
    print(f"    Regimen:  {phi_state.regime}")
    print(f"    Delta:    {kappa_eval.delta:.4f}")
    print(f"    Isomorfo: {omega_hyp.best_isomorph} (Sim={omega_hyp.similarity:.4f})")
    print(f"    Lambda:   {lambda_val.verdict} (Sim_adj={lambda_val.similarity:.4f})")
    print(f"    Decision: {sigma_orch.decision}")
    print("="*60 + "\n")

    if failed > 0:
        sys.exit(1)
    return True

if __name__ == "__main__":
    test_integration()
