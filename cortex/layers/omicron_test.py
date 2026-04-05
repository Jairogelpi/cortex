"""Test independiente de la capa Omicron."""
from datetime import datetime
from cortex.market_data import MarketData
from cortex.layers.phi import PhiLayer
from cortex.layers.kappa import KappaLayer
from cortex.layers.omega import OmegaLayer
from cortex.layers.lambda_ import LambdaLayer
from cortex.layers.sigma import SigmaLayer
from cortex.layers.rho import RhoLayer
from cortex.layers.tau import TauLayer
from cortex.layers.omicron import OmicronLayer

def test_omicron():
    print("\n" + "="*55)
    print("  CORTEX V2 - Test Capa Omicron (observabilidad)")
    print("="*55 + "\n")

    session_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Pipeline completo para tener todos los inputs
    md = MarketData()
    indicators = md.get_regime_indicators()
    account    = md.get_account()
    portfolio_value = account["portfolio_value"]

    phi_state  = PhiLayer().factorize(indicators)
    kappa_eval = KappaLayer().evaluate(
        phi_state, portfolio_value,
        initial_value=100_000.0,
        spy_benchmark_return=indicators.get("momentum_21d_pct", 0) / 3.0,
        open_positions=[]
    )
    omega_hyp  = OmegaLayer().generate_hypothesis(phi_state)
    lambda_val = LambdaLayer().validate(omega_hyp, phi_state)
    sigma_orch = SigmaLayer().orchestrate(phi_state, kappa_eval, omega_hyp, lambda_val)

    rho = RhoLayer()
    rho.check_stop_loss(portfolio_value)
    rho.save_checkpoint(
        portfolio_value, kappa_eval.delta,
        phi_state.regime, omega_hyp.trading_signal,
        [], session_id
    )

    tau_dec = TauLayer().evaluate(
        sigma_orch.decision, omega_hyp.trading_signal,
        portfolio_value, omega_hyp.allocation_pct, True
    )

    # Omicron
    print(f"Inicializando Omicron: sesion={session_id}")
    omicron = OmicronLayer(session_id=session_id)

    # Test 1: registrar evento HEARTBEAT
    print("\n--- Test 1: Registrar HEARTBEAT ---")
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
        notes="Test Omicron"
    )
    print(f"  Evento: {event.event_type}")
    print(f"  Delta:  {event.delta:.4f}")
    print(f"  Regimen: {event.regime}")
    print(f"  Sigma:  {event.sigma_decision}")
    print(f"  Tau OK: {event.tau_approved}")
    print(f"  Rho OK: {event.rho_healthy}")
    assert event.event_type == "HEARTBEAT"
    assert event.delta == kappa_eval.delta
    print("  OK\n")

    # Test 2: verificar que se escribio en JSONL
    print("--- Test 2: Verificar log JSONL ---")
    import json
    from pathlib import Path
    jsonl_path = Path(omicron.jsonl_path)
    assert jsonl_path.exists(), f"ERROR: no se creo {jsonl_path}"
    with open(jsonl_path) as f:
        lines = [json.loads(l) for l in f if l.strip()]
    last = lines[-1]
    assert last["session_id"] == session_id
    assert last["delta"] == event.delta
    print(f"  Log JSONL: {jsonl_path}")
    print(f"  Lineas totales: {len(lines)}")
    print(f"  Ultimo evento: {last['event_type']} delta={last['delta']:.4f}")
    print("  OK\n")

    # Test 3: verificar Markdown
    print("--- Test 3: Verificar log Markdown ---")
    md_path = Path(omicron.md_path)
    assert md_path.exists(), f"ERROR: no se creo {md_path}"
    content = md_path.read_text(encoding="utf-8")
    assert "HEARTBEAT" in content
    assert f"{event.delta:.4f}" in content
    print(f"  Log Markdown: {md_path}")
    print(f"  Contiene HEARTBEAT: OK")
    print(f"  Contiene delta={event.delta:.4f}: OK\n")

    # Test 4: resumen de sesion
    print("--- Test 4: Resumen de sesion ---")
    summary = omicron.get_session_summary()
    print(f"  Eventos totales:  {summary['total_events']}")
    print(f"  Delta medio:      {summary['delta_mean']:.4f}")
    print(f"  Backtracks:       {summary['backtracks']}")
    print(f"  Regimenes vistos: {summary['regimes_seen']}")
    assert summary["total_events"] >= 1
    assert summary["backtracks"] == 0, "ERROR: no deberia haber backtracks en el test"
    print("  OK\n")

    # Test 5: formato Markdown correcto para GitHub
    print("--- Test 5: Formato del diario para GitHub ---")
    md_line = event.to_markdown_line()
    print(f"  Linea Markdown:")
    print(f"  {md_line}")
    assert md_line.startswith("|")
    assert md_line.endswith("|")
    assert str(int(portfolio_value)) in md_line
    print("  OK: formato correcto para GitHub\n")

    print("="*55)
    print("  Omicron OK")
    print("="*55 + "\n")
    return omicron

if __name__ == "__main__":
    test_omicron()
