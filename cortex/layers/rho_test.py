"""Test independiente de la capa Rho."""
from cortex.market_data import MarketData
from cortex.layers.rho import RhoLayer
from cortex.config import config

def test_rho():
    print("\n" + "="*55)
    print("  CORTEX V2 - Test Capa Rho (fiabilidad)")
    print("="*55 + "\n")

    md      = MarketData()
    account = md.get_account()
    indicators = md.get_regime_indicators()
    portfolio_value = account["portfolio_value"]

    print(f"Portfolio: ${portfolio_value:,.2f}")
    print(f"Regimen: {indicators['regime']}\n")

    rho = RhoLayer()
    print(f"Estado inicial de Rho:")
    print(rho.status.summary())

    # Test 1: stop-loss con portfolio intacto
    print(f"\n--- Test 1: Stop-loss con portfolio intacto ---")
    triggered = rho.check_stop_loss(portfolio_value)
    print(f"  Portfolio: ${portfolio_value:,.2f}")
    print(f"  Drawdown:  {rho.status.current_drawdown_pct:.2f}%")
    print(f"  Stop-loss activado: {triggered}")
    assert not triggered, "ERROR: stop-loss no deberia activarse con portfolio intacto"
    print(f"  OK: stop-loss correcto")

    # Test 2: stop-loss simulado con perdida > 15%
    print(f"\n--- Test 2: Stop-loss con perdida simulada > 15% ---")
    portfolio_crisis = 84_000.0  # -16% sobre 100K
    rho2 = RhoLayer()
    triggered2 = rho2.check_stop_loss(portfolio_crisis)
    print(f"  Portfolio simulado: ${portfolio_crisis:,.2f}")
    print(f"  Drawdown:           {rho2.status.current_drawdown_pct:.2f}%")
    print(f"  Stop-loss activado: {triggered2}")
    assert triggered2, "ERROR: stop-loss deberia activarse con -16%"
    print(f"  OK: stop-loss activado correctamente a -16%")

    # Test 3: guardar checkpoint
    print(f"\n--- Test 3: Guardar checkpoint ---")
    ckpt = rho.save_checkpoint(
        portfolio_value=portfolio_value,
        delta=0.5966,
        regime=indicators["regime"],
        trading_signal="CASH",
        open_positions=[],
        session_id="test_session"
    )
    print(f"  Checkpoint guardado: {ckpt.checkpoint_id}")
    print(f"  Delta:     {ckpt.delta:.4f}")
    print(f"  Estable:   {ckpt.is_stable} (esperado: False porque delta < {config.DELTA_CONSOLIDATE})")
    assert not ckpt.is_stable, "ERROR: checkpoint no deberia ser estable con delta=0.5966"
    print(f"  OK: checkpoint no estable correctamente")

    # Test 4: checkpoint estable
    print(f"\n--- Test 4: Checkpoint estable (delta >= 0.70) ---")
    ckpt_stable = rho.save_checkpoint(
        portfolio_value=100_500.0,
        delta=0.72,
        regime="R1_EXPANSION",
        trading_signal="LONG",
        open_positions=["SPY"],
        session_id="test_session"
    )
    print(f"  Checkpoint guardado: {ckpt_stable.checkpoint_id}")
    print(f"  Delta:     {ckpt_stable.delta:.4f}")
    print(f"  Estable:   {ckpt_stable.is_stable} (esperado: True porque delta >= {config.DELTA_CONSOLIDATE})")
    assert ckpt_stable.is_stable, "ERROR: checkpoint deberia ser estable con delta=0.72"
    print(f"  OK: checkpoint estable correctamente")

    # Test 5: recuperar ultimo estable
    print(f"\n--- Test 5: Recuperar ultimo checkpoint estable ---")
    last_stable = rho.get_last_stable_checkpoint()
    if last_stable:
        print(f"  Ultimo estable: {last_stable.checkpoint_id}")
        print(f"  Delta:  {last_stable.delta:.4f}")
        print(f"  Regimen: {last_stable.regime}")
        print(f"  OK: backtrack tiene un estado al que volver")
    else:
        print(f"  Sin checkpoint estable todavia (normal al inicio)")

    print(f"\nEstado final de Rho:")
    print(rho.status.summary())

    print("\n" + "="*55)
    print("  Rho OK")
    print("="*55 + "\n")
    return rho

if __name__ == "__main__":
    test_rho()
