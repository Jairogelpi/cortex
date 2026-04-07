"""
Pipeline Cortex V2 — VERSION ADAPTATIVA (minimos tokens)
OSF: https://osf.io/wdkcx

ARQUITECTURA REVOLUCIONARIA:
    Antes:  Phi(LLM) + Kappa(LLM) + Omega(LLM) + Lambda(LLM) = 4 llamadas, ~2284 tokens
    Ahora:  UnifiedLayer(0-1 LLM) + Kappa(0 LLM) = ruta adaptativa, ~0-80 tokens cuando el mercado es claro

    Reduccion: drástica en dias claros; la revision LLM solo se activa cuando hace falta.

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
from cortex.decision_packet import DecisionPacket, EvidenceItem
from cortex.evidence_ledger import EvidenceLedger
from cortex.memory_retriever import MemoryRetriever
from cortex.novelty_router import NoveltyRouter
from cortex.abstention_policy import AbstentionPolicy
from cortex.verifier import Verifier


def _shadow_regret(packet_action: str, actual_action: str) -> float:
    packet = (packet_action or "HOLD").strip().upper()
    actual = (actual_action or "HOLD").strip().upper()

    if packet == actual:
        return 0.0
    if packet in ("HOLD", "ABSTAIN") and actual in ("HOLD", "DEFENSIVE", "BACKTRACK"):
        return 0.25
    if packet == "BACKTRACK" and actual == "HOLD":
        return 0.5
    if packet == "EXECUTE" and actual in ("HOLD", "DEFENSIVE", "BACKTRACK"):
        return 1.0
    return 0.75


def run_pipeline(session_id: str = None) -> dict:
    if session_id is None:
        session_id = datetime.now().strftime("session_%Y%m%d_%H%M%S")

    token_tracker.reset()

    print("\n" + "="*60)
    print("  CORTEX V2 — Pipeline adaptativo (0-1 llamadas LLM)")
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

    # ── UnifiedLayer: Phi + Omega + Lambda con ruta adaptativa ─────
    print("[ UNIFIED ] Phi+Omega+Lambda (ruta adaptativa 0-1 llamadas LLM)...")
    unified = UnifiedLayer()
    phi_state, omega_hyp, lambda_val = unified.run(indicators, fresh)
    tok_unified = token_tracker.total()
    llm_calls = len(token_tracker.summary()["by_layer"])
    llm_label = "sin llamada LLM" if llm_calls == 0 else f"{llm_calls} llamada{'s' if llm_calls != 1 else ''} LLM"
    print(f"            {omega_hyp.best_isomorph} Sim={omega_hyp.similarity:.4f} -> {lambda_val.verdict}")
    print(f"            Tokens reales: {tok_unified} ({llm_label})")

    # ── Kappa: deterministico (0 tokens LLM) ───────────────────────
    print("[ K ] Kappa deterministico (0 tokens)...")
    kappa_eval = KappaLayer().evaluate(
        phi_state, portfolio_value,
        initial_value=100_000.0,
        spy_benchmark_return=indicators.get("momentum_21d_pct", 0) / 3.0,
        open_positions=[]
    )
    print(f"      delta={kappa_eval.delta:.4f} | {kappa_eval.decision}")

    memory_hits = MemoryRetriever().retrieve(
        {
            "delta": kappa_eval.delta,
            "regime": phi_state.regime,
            "signal": omega_hyp.trading_signal,
        },
        top_k=3,
    )
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(source="market", kind="indicators", value=indicators, weight=1.0, freshness=1.0, note="current_market_state"))
    ledger.add(EvidenceItem(source="fresh", kind="market_data", value=fresh, weight=0.8, freshness=1.0 if fresh.get("sources") else 0.2, note="fresh_market_data"))
    for hit in memory_hits:
        ledger.add(EvidenceItem(source="memory", kind="historical_case", value=hit.to_dict(), weight=hit.score, freshness=0.5, note="similar_session"))

    top_two = sorted(omega_hyp.all_similarities.items(), key=lambda item: -item[1])[:2]
    gap = round(top_two[0][1] - top_two[1][1], 4) if len(top_two) == 2 else 0.0
    evidence_coverage = round(min(1.0, 0.35 + 0.15 * len(fresh.get("sources", [])) + 0.10 * len(memory_hits)), 4)
    conflict_score = round(min(1.0, (len(lambda_val.contradictions) / 4.0) + max(0.0, config.SIM_THRESHOLD - lambda_val.similarity)), 4)

    novelty_router = NoveltyRouter()
    novelty_result = novelty_router.route(
        best_sim=omega_hyp.similarity,
        gap=gap,
        evidence_coverage=evidence_coverage,
        conflict_score=conflict_score,
    )
    verifier = Verifier()
    verification_result = verifier.verify(
        evidence_coverage=evidence_coverage,
        conflict_score=conflict_score,
        llm_used=llm_calls > 0,
    )
    abstention_policy = AbstentionPolicy()
    abstention = abstention_policy.decide(
        evidence_coverage=evidence_coverage,
        conflict_score=conflict_score,
        critic_result="resolved" if lambda_val.verdict != "CONTRADICTED" else "unresolved",
        verification_result=verification_result.status,
    )

    packet_bundle = ledger.build_bundle(
        coverage=evidence_coverage,
        conflict_score=conflict_score,
        novelty_score=novelty_result.novelty_score,
    )
    decision_packet = DecisionPacket(
        session_id=session_id,
        best_hypothesis=omega_hyp.best_isomorph,
        trade_action=lambda_val.action,
        novelty_score=novelty_result.novelty_score,
        conflict_score=conflict_score,
        evidence_coverage=evidence_coverage,
        critic_result="resolved" if lambda_val.verdict != "CONTRADICTED" else "unresolved",
        verification_result=verification_result.status,
        final_action=abstention.action,
        abstain_reason=abstention.reason if abstention.action == "ABSTAIN" else "",
        llm_used=llm_calls > 0,
        token_usage=tok_unified,
        evidence={
            "bundle": packet_bundle.to_dict(),
            "memory_hits": [hit.to_dict() for hit in memory_hits],
            "route": novelty_result.route,
        },
        metadata={"shadow_mode": True, "gap": gap},
    )

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
    sigma_orch = SigmaLayer().orchestrate(phi_state, kappa_eval, omega_hyp, lambda_val, decision_packet=decision_packet)
    print(f"      Decision={sigma_orch.decision}")

    decision_packet.metadata["actual_action"] = sigma_orch.decision
    decision_packet.shadow_agreement = decision_packet.final_action == sigma_orch.decision
    decision_packet.shadow_regret = _shadow_regret(decision_packet.final_action, sigma_orch.decision)

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
        notes=f"Unified pipeline. Tokens={tokens_real}. Contradictions={lambda_val.contradictions[:1]}. Shadow={novelty_result.route}",
        decision_packet=decision_packet,
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
    llm_label = "sin llamada LLM" if len(token_summary["by_layer"]) == 0 else f"{len(token_summary['by_layer'])} llamada{'s' if len(token_summary['by_layer']) != 1 else ''} LLM"
    print(f"  H1   {tokens_real} tokens REALES ({llm_label})")
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
