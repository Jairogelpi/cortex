"""Test independiente de la capa Sigma."""
from cortex.market_data import MarketData
from cortex.layers.phi import PhiLayer
from cortex.layers.kappa import KappaLayer
from cortex.layers.omega import OmegaLayer
from cortex.layers.lambda_ import LambdaLayer
from cortex.layers.sigma import SigmaLayer
from cortex.config import config
from cortex.decision_packet import DecisionPacket

def test_sigma():
    print("\n" + "="*55)
    print("  CORTEX V2 - Test Capa Sigma (orquestador)")
    print("="*55 + "\n")

    md = MarketData()
    indicators = md.get_regime_indicators()
    account    = md.get_account()

    print(f"Mercado: VIX={indicators['vix']} | Momentum={indicators['momentum_21d_pct']}% | Regimen={indicators['regime']}")
    print(f"Portfolio: ${account['portfolio_value']:,.2f}\n")

    phi_state  = PhiLayer().factorize(indicators)
    kappa_eval = KappaLayer().evaluate(
        phi_state, account["portfolio_value"],
        initial_value=100_000.0,
        spy_benchmark_return=indicators.get("momentum_21d_pct", 0) / 3.0,
        open_positions=[]
    )
    omega_hyp  = OmegaLayer().generate_hypothesis(phi_state)
    lambda_val = LambdaLayer().validate(omega_hyp, phi_state)

    print(f"Inputs a Sigma:")
    print(f"  Phi:    regimen={phi_state.regime}")
    print(f"  Kappa:  delta={kappa_eval.delta:.4f} decision={kappa_eval.decision}")
    print(f"  Omega:  senal={omega_hyp.trading_signal}")
    print(f"  Lambda: veredicto={lambda_val.verdict}")

    sigma = SigmaLayer()
    orch  = sigma.orchestrate(phi_state, kappa_eval, omega_hyp, lambda_val)

    print(f"\n{orch.summary()}")

    print(f"\n--- Verificaciones ---")
    assert len(orch.active_subagents) <= config.MAX_SUBAGENTS, \
        f"ERROR: {len(orch.active_subagents)} subagentes > MAX={config.MAX_SUBAGENTS}"
    print(f"  Limite subagentes ({config.MAX_SUBAGENTS}): OK ({len(orch.active_subagents)} activos)")

    assert orch.decision in ("HOLD", "EXECUTE", "DEFENSIVE", "BACKTRACK"), \
        f"ERROR: decision desconocida: {orch.decision}"
    print(f"  Decision valida: OK ({orch.decision})")

    packet = DecisionPacket(
        session_id="sigma_test_packet",
        final_action="ABSTAIN",
        trade_action="EXECUTE",
        evidence_coverage=0.25,
        conflict_score=0.90,
    )
    orch_packet = sigma.orchestrate(phi_state, kappa_eval, omega_hyp, lambda_val, decision_packet=packet)
    assert orch_packet.decision == "HOLD", f"ERROR: packet ABSTAIN no bloqueo la decision ({orch_packet.decision})"
    print(f"  Packet ABSTAIN fuerza HOLD: OK ({orch_packet.decision})")

    assert orch.total_duration_seconds < 1.0, \
        f"ERROR: Sigma tardo {orch.total_duration_seconds:.3f}s (debe ser < 1s, es determinista)"
    print(f"  Latencia determinista: OK ({orch.total_duration_seconds:.3f}s < 1s)")

    print(f"\n  Deadlocks detectados: {orch.deadlocks_detected}")
    print(f"  Tareas planificadas:  {len(orch.tasks)}")

    print("\n" + "="*55)
    print("  Sigma OK")
    print("="*55 + "\n")
    return orch

if __name__ == "__main__":
    test_sigma()
