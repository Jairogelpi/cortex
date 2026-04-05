"""Test independiente de la capa Tau."""
from cortex.layers.tau import TauLayer, IRREVERSIBLE_ACTIONS
from cortex.config import config

def test_tau():
    print("\n" + "="*55)
    print("  CORTEX V2 - Test Capa Tau (governance)")
    print("="*55 + "\n")

    tau = TauLayer()

    # Test 1: HOLD — no requiere aprobacion
    print("--- Test 1: Decision HOLD (no hay accion) ---")
    dec = tau.evaluate("HOLD", "CASH", 100_000.0, 0.0, is_paper_trading=True)
    print(f"  {dec.summary()}")
    assert dec.approved, "ERROR: HOLD debe estar aprobado"
    assert not dec.requires_human, "ERROR: HOLD no requiere humano"
    assert dec.action == "HOLD_NO_ACTION"
    print("  OK\n")

    # Test 2: EXECUTE con posicion grande (> 5%) — requiere humano en real
    print("--- Test 2: EXECUTE con posicion > 5% del portfolio ---")
    dec2 = tau.evaluate("EXECUTE", "LONG", 100_000.0, 0.80, is_paper_trading=True)
    print(f"  {dec2.summary()}")
    assert dec2.approved, "ERROR: debe aprobarse en paper trading"
    assert dec2.requires_human, "ERROR: debe requerir humano (>5% del portfolio)"
    assert dec2.action == "POSITION_CHANGE_LARGE"
    print("  OK (aprobado en paper, requeriria humano en real)\n")

    # Test 3: misma accion en trading real — debe bloquearse
    print("--- Test 3: EXECUTE > 5% en trading REAL (debe bloquearse) ---")
    dec3 = tau.evaluate("EXECUTE", "LONG", 100_000.0, 0.80, is_paper_trading=False)
    print(f"  {dec3.summary()}")
    assert not dec3.approved, "ERROR: debe bloquearse en trading real"
    assert dec3.requires_human, "ERROR: debe requerir humano"
    print("  OK (bloqueado en trading real)\n")

    # Test 4: BACKTRACK — auto-aprobado
    print("--- Test 4: BACKTRACK (auto-aprobado) ---")
    dec4 = tau.evaluate("BACKTRACK", "CASH", 100_000.0, 0.0, is_paper_trading=True)
    print(f"  {dec4.summary()}")
    assert dec4.approved, "ERROR: BACKTRACK debe aprobarse"
    assert dec4.action == "BACKTRACK"
    print("  OK\n")

    # Test 5: tools de scope
    print("--- Test 5: Tools permitidas por scope ---")
    dec5 = tau.evaluate("HOLD", "CASH", 100_000.0, 0.0, is_paper_trading=True)
    print(f"  Senal CASH - Tools permitidas: {sorted(dec5.allowed_tools)}")
    assert "market_data" in dec5.allowed_tools
    assert "order_validator" not in dec5.allowed_tools, \
        "ERROR: order_validator no debe estar disponible con senal CASH"
    print("  OK: scope de tools correcto para CASH\n")

    dec6 = tau.evaluate("EXECUTE", "LONG", 100_000.0, 0.03, is_paper_trading=True)
    print(f"  Senal LONG - Tools permitidas: {sorted(dec6.allowed_tools)}")
    assert "order_validator" in dec6.allowed_tools
    assert "equity_data" in dec6.allowed_tools
    print("  OK: scope de tools correcto para LONG")

    print("\n" + "="*55)
    print("  Tau OK")
    print("="*55 + "\n")

if __name__ == "__main__":
    test_tau()
