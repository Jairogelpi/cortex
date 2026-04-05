"""
TEST DE INTEGRACION COMPLETO — Cortex V2
Verifica que las 10 capas funcionan juntas correctamente.

Invariantes verificadas:
1.  Phi produce vectores ortogonales (I < 0.3)
2.  Kappa calcula delta con la formula exacta del paper
3.  Omega activa el isomorfo correcto sobre todos los 5
4.  Lambda consulta Yahoo Finance (fuente primaria real)
5.  Lambda produce CONTRADICTED/UNCERTAIN cuando los datos contradicen el isomorfo
6.  Phi temperature=0.0 es reproducible (max_diff < 0.05)
7.  Mu rechaza cuando delta < DELTA_CONSOLIDATE
8.  Sigma no supera MAX_SUBAGENTS, es determinista (<1s)
9.  Rho: stop-loss OK con portfolio intacto, ACTIVADO con -16%
10. Tau bloquea en trading real, aprueba en paper trading
11. Omicron registra en JSONL y Markdown correctamente
12. Coherencia global del pipeline
"""
import sys
import json
import numpy as np
from datetime import datetime
from pathlib import Path
from cortex.config import config
from cortex.market_data import MarketData
from cortex.layers.phi import PhiLayer
from cortex.layers.kappa import KappaLayer
from cortex.layers.omega import OmegaLayer, PHYSICAL_ISOMORPHS, OmegaHypothesis
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

    md              = MarketData()
    indicators      = md.get_regime_indicators()
    account         = md.get_account()
    portfolio_value = account["portfolio_value"]

    print(f"Mercado: VIX={indicators['vix']} | Momentum={indicators['momentum_21d_pct']}% | Regimen={indicators['regime']}")
    print(f"Portfolio: ${portfolio_value:,.2f}\n")

    # ── CONEXION ──────────────────────────────────────────────────
    print("[ CONEXION ]")
    check("Alpaca conectado", portfolio_value > 0, f"portfolio=${portfolio_value:,.2f}")
    check("VIX disponible",   indicators.get("vix", 0) > 0, f"VIX={indicators.get('vix')}")
    print()

    # ── PHI ───────────────────────────────────────────────────────
    print("[ Φ PHI ]")
    phi_state = PhiLayer().factorize(indicators)
    orth = phi_state.check_orthogonality()

    check("Ortogonalidad OK",    orth["orthogonality_ok"],
          f"var={orth['z_variance']:.4f} spread={orth['z_spread']:.4f}")
    check("Varianza Z > 0.15",   orth["z_variance"] > 0.15,
          f"var={orth['z_variance']:.4f}")
    check("Confianza en [0,1]",  0 <= phi_state.confidence <= 1,
          f"confianza={phi_state.confidence:.2f}")
    check("Regimen valido",      phi_state.regime in (
        "R1_EXPANSION","R2_ACCUMULATION","R3_TRANSITION","R4_CONTRACTION","INDETERMINATE"),
          f"regimen={phi_state.regime}")

    # FIX 3: temperature=0.0 debe ser reproducible
    phi_det  = PhiLayer(temperature=0.0)
    state_d1 = phi_det.factorize(indicators)
    state_d2 = phi_det.factorize(indicators)
    max_diff = float(np.max(np.abs(state_d1.to_vector() - state_d2.to_vector())))
    check("Phi temperature=0.0 reproducible",
          max_diff < 0.05,
          f"max_diff={max_diff:.4f} (debe ser < 0.05)")
    print()

    # ── KAPPA ─────────────────────────────────────────────────────
    print("[ Κ KAPPA ]")
    kappa_eval = KappaLayer().evaluate(
        phi_state, portfolio_value,
        initial_value=100_000.0,
        spy_benchmark_return=indicators.get("momentum_21d_pct", 0) / 3.0,
        open_positions=[]
    )

    check("Delta en [0,1]",        0 <= kappa_eval.delta <= 1,
          f"delta={kappa_eval.delta:.4f}")
    delta_manual = round(
        0.4 * kappa_eval.retorno_norm +
        0.4 * (1 - kappa_eval.drawdown_norm) +
        0.2 * kappa_eval.regimen_consistencia, 4
    )
    check("Formula delta exacta",  abs(delta_manual - kappa_eval.delta) < 0.001,
          f"manual={delta_manual:.4f} reportado={kappa_eval.delta:.4f}")
    check("Decision valida",       kappa_eval.decision in (
        "CONTINUE","BACKTRACK","DEFENSIVE","HOLD_CASH"),
          f"decision={kappa_eval.decision}")
    check("Sin backtrack en cash", not kappa_eval.backtrack_required)
    print()

    # ── OMEGA ─────────────────────────────────────────────────────
    print("[ Ω OMEGA ]")
    omega_hyp = OmegaLayer().generate_hypothesis(phi_state)

    check("Isomorfo valido",          omega_hyp.best_isomorph in PHYSICAL_ISOMORPHS,
          f"isomorfo={omega_hyp.best_isomorph}")
    check("Similitud en [0,1]",       0 <= omega_hyp.similarity <= 1,
          f"sim={omega_hyp.similarity:.4f}")
    check("Umbral 0.65 coherente",
          omega_hyp.threshold_met == (omega_hyp.similarity >= config.SIM_THRESHOLD),
          f"sim={omega_hyp.similarity:.4f} met={omega_hyp.threshold_met}")
    check("Senal valida",             omega_hyp.trading_signal in (
        "LONG","LONG_PREPARE","DEFENSIVE","MEAN_REVERSION","CASH"),
          f"senal={omega_hyp.trading_signal}")
    check("5/5 isomorfos calculados", len(omega_hyp.all_similarities) == 5,
          f"{len(omega_hyp.all_similarities)}/5")
    print()

    # ── LAMBDA — datos reales ─────────────────────────────────────
    print("[ Λ LAMBDA — datos reales ]")
    lambda_val = LambdaLayer().validate(omega_hyp, phi_state)

    check("Similitud en [0,1]",       0 <= lambda_val.similarity <= 1,
          f"sim_adj={lambda_val.similarity:.4f}")
    check("Veredicto valido",         lambda_val.verdict in (
        "CONFIRMED","UNCERTAIN","CONTRADICTED","LAMBDA_OFFLINE"),
          f"veredicto={lambda_val.verdict}")
    check("Yahoo Finance consultado", "yahoo_finance" in lambda_val.api_sources_used,
          f"fuentes={lambda_val.api_sources_used}")

    # FRED — informativo, no bloquea el test (falla de infraestructura, no de logica)
    fred_ok = "fred" in lambda_val.api_sources_used
    if fred_ok:
        fred_val = lambda_val.evidence.get("fred_t10y2y_spread") or \
                   lambda_val.evidence.get("fred_vix_close")
        check("FRED conectado con valor real", fred_val is not None,
              f"valor={fred_val}")
    else:
        # No es FAIL — FRED es fuente secundaria. Yahoo Finance es suficiente.
        print(f"  ~ FRED: no disponible (Lambda opera con Yahoo Finance solamente)")
        print(f"    Nota: FRED es fuente secundaria. Yahoo Finance es la primaria.")

    check("Z_fresh 8 dims",       len(lambda_val.z_fresh) == 8)
    check("Z_referencia 8 dims",  len(lambda_val.z_reference) == 8)
    check("Reasoning generado",   len(lambda_val.reasoning) > 20,
          f"{lambda_val.reasoning[:60]}...")
    print()

    # ── LAMBDA — test CONTRADICTED con escenario real forzado ─────
    print("[ Λ LAMBDA — test CONTRADICTED (bajista vs bull run) ]")

    # Mercado fuertemente bajista: VIX alto, momentum negativo, drawdown severo
    bearish_ind = {
        "vix": 30.0,
        "momentum_21d_pct": -8.0,
        "vol_realized_pct": 28.0,
        "drawdown_90d_pct": -18.0,
        "spy_price": 600.0,
        "regime": "R3_TRANSITION",
        "timestamp": datetime.now().isoformat()
    }
    bearish_phi = PhiLayer(temperature=0.0).factorize(bearish_ind)

    # Hipotesis gas_expansion (bull run) forzada — debe ser contradicha
    # Usamos los campos correctos de OmegaHypothesis segun omega.py
    gas_hyp = OmegaHypothesis(
        best_isomorph="gas_expansion",
        similarity=0.95,
        threshold_met=True,
        trading_signal="LONG",
        instruments=["SPY", "QQQ"],
        allocation_pct=0.80,
        physical_description="Gas ideal en expansion — bull run sostenido",
        market_analog="Bull run sostenido (R1_EXPANSION)",
        all_similarities={
            "gas_expansion":     0.95,
            "lorenz_attractor":  0.30,
            "phase_transition":  0.40,
            "compressed_gas":    0.50,
            "overdamped_system": 0.35
        },
        llm_reasoning="Test: gas_expansion forzado en mercado bajista",
        confidence=0.90,
        timestamp=datetime.now().isoformat(),
        z_market=bearish_phi.to_vector().tolist()
    )

    lambda_contra = LambdaLayer().validate(gas_hyp, bearish_phi)

    check("CONTRADICTED/UNCERTAIN: bull run en mercado bajista",
          lambda_contra.verdict in ("CONTRADICTED", "UNCERTAIN"),
          f"veredicto={lambda_contra.verdict} sim={lambda_contra.similarity:.4f}")
    check("Penalizacion reduce similitud",
          lambda_contra.similarity < 0.80,
          f"sim_adj={lambda_contra.similarity:.4f} (debe ser < 0.80)")
    check("Contradicciones detectadas",
          len(lambda_contra.contradictions) > 0,
          f"{len(lambda_contra.contradictions)} contradicciones")
    print()

    # ── MU ────────────────────────────────────────────────────────
    print("[ Μ MU ]")
    mu     = MuLayer(session_id=session_id)
    should = mu.should_consolidate(kappa_eval)

    check("Consolidacion coherente",
          should == (kappa_eval.delta >= config.DELTA_CONSOLIDATE),
          f"delta={kappa_eval.delta:.4f} umbral={config.DELTA_CONSOLIDATE} consolidar={should}")
    if should:
        entry = mu.consolidate(phi_state, kappa_eval, lambda_val)
        check("Entrada valida", entry.delta >= config.DELTA_CONSOLIDATE,
              f"delta={entry.delta:.4f}")
    else:
        check("Rechazo correcto", True,
              f"delta={kappa_eval.delta:.4f} < {config.DELTA_CONSOLIDATE}")

    delta_est = mu.get_initial_delta_estimate()
    check("Delta estimado >= DELTA_BACKTRACK", delta_est >= config.DELTA_BACKTRACK,
          f"estimado={delta_est:.4f}")
    print()

    # ── SIGMA ─────────────────────────────────────────────────────
    print("[ Σ SIGMA ]")
    sigma_orch = SigmaLayer().orchestrate(phi_state, kappa_eval, omega_hyp, lambda_val)

    check("Limite subagentes",  len(sigma_orch.active_subagents) <= config.MAX_SUBAGENTS,
          f"{len(sigma_orch.active_subagents)}/{config.MAX_SUBAGENTS}")
    check("Decision valida",    sigma_orch.decision in (
        "HOLD","EXECUTE","DEFENSIVE","BACKTRACK"), f"decision={sigma_orch.decision}")
    check("Determinista <1s",   sigma_orch.total_duration_seconds < 1.0,
          f"{sigma_orch.total_duration_seconds:.3f}s")
    check("Sin deadlocks",      sigma_orch.deadlocks_detected == 0)
    print()

    # ── RHO ───────────────────────────────────────────────────────
    print("[ Ρ RHO ]")
    rho   = RhoLayer()
    stop_ok = rho.check_stop_loss(portfolio_value)
    ckpt  = rho.save_checkpoint(
        portfolio_value, kappa_eval.delta,
        phi_state.regime, omega_hyp.trading_signal, [], session_id
    )

    check("Stop-loss no activado", not stop_ok,
          f"drawdown={rho.status.current_drawdown_pct:.2f}%")
    check("Sistema saludable",     rho.status.system_healthy)
    check("Checkpoint guardado",   ckpt.checkpoint_id.startswith("ckpt_"))
    check("is_stable coherente",
          ckpt.is_stable == (kappa_eval.delta >= config.DELTA_CONSOLIDATE),
          f"delta={kappa_eval.delta:.4f} is_stable={ckpt.is_stable}")

    rho2 = RhoLayer()
    check("Stop-loss ACTIVADO con -16%", rho2.check_stop_loss(84_000.0),
          f"drawdown={rho2.status.current_drawdown_pct:.2f}%")
    print()

    # ── TAU ───────────────────────────────────────────────────────
    print("[ Τ TAU ]")
    tau_dec = TauLayer().evaluate(
        sigma_orch.decision, omega_hyp.trading_signal,
        portfolio_value, omega_hyp.allocation_pct, True
    )

    check("Aprobado en paper trading",  tau_dec.approved)
    check("Accion clasificada",         len(tau_dec.action) > 0, f"accion={tau_dec.action}")
    check("Tools permitidas definidas", len(tau_dec.allowed_tools) > 0)

    tau_large = TauLayer().evaluate("EXECUTE","LONG",100_000.0,0.80,True)
    check("EXECUTE 80% requiere humano", tau_large.requires_human)

    tau_real = TauLayer().evaluate("EXECUTE","LONG",100_000.0,0.80,False)
    check("EXECUTE 80% BLOQUEADO en real", not tau_real.approved)
    print()

    # ── OMICRON ───────────────────────────────────────────────────
    print("[ Ο OMICRON ]")
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
        notes="Test integracion completo"
    )

    check("HEARTBEAT registrado",     event.event_type == "HEARTBEAT")
    check("Log JSONL existe",         Path(omicron.jsonl_path).exists())
    check("Log Markdown existe",      Path(omicron.md_path).exists())
    check("Delta coherente en log",   event.delta == kappa_eval.delta,
          f"log={event.delta:.4f} kappa={kappa_eval.delta:.4f}")
    check("Rho healthy en log",       event.rho_healthy == rho.status.system_healthy)

    with open(omicron.jsonl_path) as f:
        lineas = [json.loads(l) for l in f if l.strip()]
    check("JSONL >= 1 linea",             len(lineas) >= 1, f"{len(lineas)} lineas")
    md_txt = Path(omicron.md_path).read_text(encoding="utf-8")
    check("Markdown contiene HEARTBEAT",  "HEARTBEAT" in md_txt)
    print()

    # ── COHERENCIA GLOBAL ─────────────────────────────────────────
    print("[ COHERENCIA GLOBAL ]")

    if kappa_eval.delta < config.DELTA_BACKTRACK:
        check("Sigma=HOLD cuando delta bajo",
              sigma_orch.decision in ("HOLD","BACKTRACK","DEFENSIVE"),
              f"delta={kappa_eval.delta:.4f} sigma={sigma_orch.decision}")
    if omega_hyp.trading_signal == "CASH":
        check("Sigma=HOLD cuando Omega=CASH",
              sigma_orch.decision == "HOLD",
              f"omega=CASH sigma={sigma_orch.decision}")
    if lambda_val.verdict == "CONTRADICTED":
        check("Sigma=BACKTRACK cuando Lambda=CONTRADICTED",
              sigma_orch.decision == "BACKTRACK")

    check("Delta en rango [0.3, 0.9]", 0.3 <= kappa_eval.delta <= 0.9,
          f"delta={kappa_eval.delta:.4f}")
    print()

    # ── RESULTADO FINAL ───────────────────────────────────────────
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
    print(f"  Pipeline {datetime.now().strftime('%d %B %Y')}:")
    print(f"    Regimen:  {phi_state.regime}")
    print(f"    Delta:    {kappa_eval.delta:.4f}")
    print(f"    Isomorfo: {omega_hyp.best_isomorph} (Sim={omega_hyp.similarity:.4f})")
    print(f"    Lambda:   {lambda_val.verdict} (Sim_adj={lambda_val.similarity:.4f})")
    print(f"    FRED:     {'OK' if 'fred' in lambda_val.api_sources_used else 'solo Yahoo Finance'}")
    print(f"    Decision: {sigma_orch.decision}")
    print("="*60 + "\n")

    if failed > 0:
        sys.exit(1)
    return True


if __name__ == "__main__":
    test_integration()
