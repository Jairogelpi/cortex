"""
CAPA LAMBDA - Validacion con herramientas reales — VERSION OPTIMIZADA H1
Cortex V2, Fase 4.

OPTIMIZACION H1:
  _get_reasoning: prompt comprimido al minimo funcional.
  max_tokens: 600 -> 80 (1 frase critica + lista corta contradicciones).
  Sin contexto redundante (Z referencia, fuentes de evidencia,
  senales adicionales ya estan en los ajustes de penalizacion).
  Estimacion ahorro: 930 -> ~250 tokens.

El veredicto (CONFIRMED/CONTRADICTED/UNCERTAIN) ya viene de la similitud
coseno y las penalizaciones matematicas. El LLM solo identifica
contradicciones NO capturadas por las reglas deterministicas.
"""
import time
import json
import re
import numpy as np
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import yfinance as yf
import requests
from openai import OpenAI
from loguru import logger

from cortex.config import config
from cortex.layers.phi import PhiLayer, PhiState
from cortex.layers.omega import OmegaHypothesis, PHYSICAL_ISOMORPHS
from cortex.token_tracker import token_tracker


@dataclass
class LambdaValidation:
    hypothesis_confirmed: bool
    hypothesis_contradicted: bool
    similarity: float
    verdict: str
    action: str
    evidence: dict
    z_fresh: list
    z_reference: list
    additional_signals: dict
    contradictions: list
    reasoning: str
    api_sources_used: list
    api_failures: list
    timestamp: str
    validation_duration_seconds: float

    def summary(self) -> str:
        return (
            f"Lambda | {self.verdict} Sim={self.similarity:.4f} "
            f"fuentes={self.api_sources_used} "
            f"contradicciones={len(self.contradictions)} | {self.reasoning[:80]}"
        )


class LambdaLayer:
    SIM_CONFIRM     = 0.65
    SIM_CONTRADICT  = 0.40
    FRED_CONNECT_TIMEOUT = 10
    FRED_READ_TIMEOUT    = 30

    def __init__(self):
        self.client = OpenAI(
            api_key=config.OPENROUTER_API_KEY,
            base_url=config.OPENROUTER_BASE_URL,
            timeout=config.OPENROUTER_TIMEOUT_SECONDS,
            max_retries=config.OPENROUTER_MAX_RETRIES,
        )
        self.model = config.MODEL_PHI
        self.phi   = PhiLayer(temperature=0.0)
        logger.info(f"Capa Lambda inicializada: {self.model}")

    def validate(self, omega_hypothesis: OmegaHypothesis, phi_state: PhiState) -> LambdaValidation:
        start_time     = time.time()
        sources_used   = []
        sources_failed = []
        isomorph_name  = omega_hypothesis.best_isomorph

        logger.info(f"Lambda: validando '{isomorph_name}' (senal={omega_hypothesis.trading_signal})")

        evidence = {}
        yf_data  = self._get_yahoo_finance_data()
        if "error" not in yf_data:
            evidence.update(yf_data);  sources_used.append("yahoo_finance")
            logger.info("Lambda: Yahoo Finance OK")
        else:
            sources_failed.append("yahoo_finance")
            logger.warning(f"Lambda: Yahoo Finance fallo: {yf_data['error']}")

        fred_data = self._get_fred_data()
        if isinstance(fred_data, dict) and "error" not in fred_data:
            evidence.update(fred_data);  sources_used.append("fred")
            logger.info(f"Lambda: FRED OK — {[k for k in fred_data if k != 'source']}")
        else:
            sources_failed.append("fred")

        if not sources_used:
            return self._failure_protocol(omega_hypothesis, phi_state, start_time)

        additional_signals = {
            "vix_change_5d":     evidence.get("vix_change_5d", 0.0),
            "momentum_5d_pct":   evidence.get("spy_momentum_5d_pct", 0.0),
            "vol_5d_pct":        evidence.get("spy_vol_5d_pct", 0.0),
            "ief_return_5d_pct": evidence.get("ief_return_5d_pct", 0.0),
            "yield_curve_spread":evidence.get("fred_t10y2y_spread", "no_disponible"),
        }

        fresh_ind   = self._build_fresh_indicators(evidence, phi_state)
        z_fresh     = self.phi.factorize(fresh_ind).to_vector()

        if isomorph_name not in PHYSICAL_ISOMORPHS:
            return self._failure_protocol(omega_hypothesis, phi_state, start_time)

        z_reference = PHYSICAL_ISOMORPHS[isomorph_name]["Z"]

        logger.info(
            f"Lambda: comparando Z_fresh vs Z_referencia_{isomorph_name}\n"
            f"  Z_fresh:     {[round(x,3) for x in z_fresh.tolist()]}\n"
            f"  Z_referencia:{[round(x,3) for x in z_reference.tolist()]}"
        )

        similarity = self._calc_similarity(z_fresh, z_reference)
        logger.info(f"Lambda: Sim(Z_fresh, Z_ref_{isomorph_name}) = {similarity:.4f}")

        similarity_adj, sig_contradictions = self._adjust_for_additional_signals(
            similarity, additional_signals, isomorph_name, omega_hypothesis.trading_signal
        )
        if sig_contradictions:
            logger.warning(f"Lambda: senales contradictorias: {sig_contradictions}")

        verdict, action, confirmed, contradicted = self._verdict(similarity_adj)

        reasoning, contra_llm = self._get_reasoning(
            isomorph_name, z_fresh, z_reference,
            similarity, similarity_adj, verdict, sig_contradictions
        )

        duration   = time.time() - start_time
        validation = LambdaValidation(
            hypothesis_confirmed=confirmed,
            hypothesis_contradicted=contradicted,
            similarity=round(similarity_adj, 4),
            verdict=verdict, action=action,
            evidence={k:v for k,v in evidence.items() if k!="source"},
            z_fresh=z_fresh.tolist(),
            z_reference=z_reference.tolist(),
            additional_signals=additional_signals,
            contradictions=sig_contradictions + contra_llm,
            reasoning=reasoning,
            api_sources_used=sources_used,
            api_failures=sources_failed,
            timestamp=datetime.now().isoformat(),
            validation_duration_seconds=round(duration, 2)
        )
        logger.info(
            f"Lambda: veredicto={verdict} accion={action} "
            f"sim_raw={similarity:.4f} sim_adj={similarity_adj:.4f} "
            f"fuentes={sources_used} contradicciones={len(validation.contradictions)}"
        )
        return validation

    def _get_yahoo_finance_data(self) -> dict:
        try:
            spy    = yf.Ticker("SPY")
            hist   = spy.history(period="3mo")
            if hist.empty:
                return {"error": "SPY vacio"}
            closes       = hist["Close"]
            current      = float(closes.iloc[-1])
            prev_21      = float(closes.iloc[-22]) if len(closes)>22 else current
            prev_5       = float(closes.iloc[-6])  if len(closes)>6  else current
            momentum_21d = round((current-prev_21)/prev_21*100, 2)
            momentum_5d  = round((current-prev_5)/prev_5*100, 2)
            returns      = closes.pct_change().dropna()
            vol_21d      = round(float(returns.tail(21).std()*(252**0.5)*100), 2)
            vol_5d       = round(float(returns.tail(5).std()*(252**0.5)*100), 2)
            max_90d      = float(closes.tail(90).max())
            drawdown     = round((current-max_90d)/max_90d*100, 2)
            vix_h        = yf.Ticker("^VIX").history(period="5d")
            vix_c        = float(vix_h["Close"].iloc[-1]) if not vix_h.empty else 20.0
            vix_p5       = float(vix_h["Close"].iloc[0])  if len(vix_h)>=2 else vix_c
            ief_h        = yf.Ticker("IEF").history(period="1mo")
            ief_ret      = 0.0
            if not ief_h.empty and len(ief_h)>5:
                ief_ret = round((float(ief_h["Close"].iloc[-1])-float(ief_h["Close"].iloc[-6]))/float(ief_h["Close"].iloc[-6])*100, 2)
            return {
                "spy_price":round(current,2), "spy_momentum_21d_pct":momentum_21d,
                "spy_momentum_5d_pct":momentum_5d, "spy_vol_21d_pct":vol_21d,
                "spy_vol_5d_pct":vol_5d, "spy_drawdown_90d_pct":drawdown,
                "vix_current":vix_c, "vix_change_5d":round(vix_c-vix_p5,2),
                "ief_return_5d_pct":ief_ret, "source":"yahoo_finance"
            }
        except Exception as e:
            return {"error": str(e)}

    def _get_fred_data(self) -> dict:
        results = {}
        for sid, fn in [("T10Y2Y","fred_t10y2y_spread"),("VIXCLS","fred_vix_close")]:
            v = self._fetch_fred_csv_raw(sid)
            if v is None: v = self._fetch_fred_json(sid)
            if v is not None: results[fn] = round(v, 3)
        if not results: return {"error": "FRED: sin datos"}
        results["source"] = "fred"
        return results

    def _fetch_fred_csv_raw(self, series_id):
        try:
            import pandas as pd
            from io import StringIO
            r = requests.get(
                f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}",
                headers={"User-Agent":"CortexV2/1.0"},
                timeout=(self.FRED_CONNECT_TIMEOUT, self.FRED_READ_TIMEOUT)
            )
            if r.status_code != 200: return None
            df = pd.read_csv(StringIO(r.text), na_values=[".",""]).dropna(subset=[pd.read_csv(StringIO(r.text),na_values=[".",""]).columns[1]])
            return float(df.iloc[-1][df.columns[1]]) if not df.empty else None
        except Exception as e:
            logger.debug(f"FRED CSV {series_id}: {e}"); return None

    def _fetch_fred_json(self, series_id):
        try:
            api_key = (config.FRED_API_KEY or "").strip()
            if not api_key: return None
            r = requests.get("https://api.stlouisfed.org/fred/series/observations",
                params={"series_id":series_id,"api_key":api_key,"file_type":"json","limit":3,"sort_order":"desc"},
                timeout=(self.FRED_CONNECT_TIMEOUT, self.FRED_READ_TIMEOUT))
            obs = [o for o in r.json().get("observations",[]) if o.get("value",".") != "."]
            return float(obs[0]["value"]) if obs else None
        except: return None

    def _build_fresh_indicators(self, evidence, original_phi):
        orig = original_phi.raw_indicators
        vix  = evidence.get("vix_current",          orig.get("vix",20.0))
        mom  = evidence.get("spy_momentum_21d_pct",  orig.get("momentum_21d_pct",0.0))
        vol  = evidence.get("spy_vol_21d_pct",       orig.get("vol_realized_pct",15.0))
        dd   = evidence.get("spy_drawdown_90d_pct",  orig.get("drawdown_90d_pct",0.0))
        px   = evidence.get("spy_price",             orig.get("spy_price",0.0))
        reg  = self._classify_regime(float(vix),float(mom),float(vol),float(dd))
        return {"vix":round(float(vix),2),"momentum_21d_pct":round(float(mom),2),
                "vol_realized_pct":round(float(vol),2),"drawdown_90d_pct":round(float(dd),2),
                "spy_price":round(float(px),2),"regime":reg,"timestamp":datetime.now().isoformat()}

    def _classify_regime(self, vix, momentum, vol, drawdown):
        if vix>35 and momentum<-5 and drawdown<-15: return "R4_CONTRACTION"
        elif vix>28: return "R3_TRANSITION"
        elif 20<=vix<=28 and abs(momentum)<=2: return "R2_ACCUMULATION"
        elif vix<20 and momentum>0 and vol<15: return "R1_EXPANSION"
        return "INDETERMINATE"

    def _calc_similarity(self, z_a, z_b):
        na,nb = np.linalg.norm(z_a), np.linalg.norm(z_b)
        if na==0 or nb==0: return 0.0
        return max(0.0, min(1.0, (float(np.dot(z_a,z_b)/(na*nb))+1.0)/2.0))

    def _adjust_for_additional_signals(self, similarity, signals, isomorph_name, trading_signal):
        contradictions = []
        penalty = 0.0
        vix_change = signals.get("vix_change_5d",0.0)
        mom_5d     = signals.get("momentum_5d_pct",0.0)
        vol_5d     = signals.get("vol_5d_pct",0.0)
        ief_return = signals.get("ief_return_5d_pct",0.0)

        if isomorph_name in ("lorenz_attractor","phase_transition"):
            if vix_change<-8.0:   penalty+=0.30; contradictions.append(f"VIX -{abs(vix_change):.1f}pts 5d: descompresion severa")
            elif vix_change<-5.0: penalty+=0.18; contradictions.append(f"VIX -{abs(vix_change):.1f}pts 5d: estres bajando")
            elif vix_change<-3.0: penalty+=0.09; contradictions.append(f"VIX -{abs(vix_change):.1f}pts 5d: leve mejora")
            if mom_5d>4.0:   penalty+=0.20; contradictions.append(f"Mom5d={mom_5d:.1f}%: recuperacion fuerte")
            elif mom_5d>2.0: penalty+=0.10; contradictions.append(f"Mom5d={mom_5d:.1f}%: recuperacion moderada")
            elif mom_5d>1.0: penalty+=0.05; contradictions.append(f"Mom5d={mom_5d:.1f}%: leve recuperacion")
            if ief_return>1.5: penalty-=0.08
            elif ief_return>0.5: penalty-=0.04
            if vol_5d>25.0: penalty-=0.05
        elif isomorph_name=="gas_expansion":
            if vix_change>4.0:   penalty+=0.20; contradictions.append(f"VIX +{vix_change:.1f}pts: estres creciente")
            elif vix_change>2.0: penalty+=0.10; contradictions.append(f"VIX +{vix_change:.1f}pts: deterioro")
            if mom_5d<-3.0:   penalty+=0.20; contradictions.append(f"Mom5d={mom_5d:.1f}%: caida reciente")
            elif mom_5d<-1.0: penalty+=0.08; contradictions.append(f"Mom5d={mom_5d:.1f}%: debilidad")
        elif isomorph_name=="compressed_gas":
            if vol_5d>30.0: penalty+=0.12; contradictions.append(f"Vol5d={vol_5d:.1f}%: excesiva para acumulacion")

        penalty  = max(-0.10, min(0.55, penalty))
        sim_adj  = max(0.0, min(1.0, similarity-penalty))
        if abs(penalty)>0.01:
            logger.info(f"Lambda: penalizacion={penalty:+.3f} (sim {similarity:.4f}->{sim_adj:.4f})")
        return round(sim_adj,4), contradictions

    def _verdict(self, similarity):
        if similarity>=self.SIM_CONFIRM:    return "CONFIRMED",    "EXECUTE",   True,  False
        elif similarity<self.SIM_CONTRADICT: return "CONTRADICTED", "BACKTRACK", False, True
        return "UNCERTAIN", "DEFENSIVE", False, False

    def _get_reasoning(self, isomorph_name, z_fresh, z_reference,
                       sim_raw, sim_adj, verdict, existing_contradictions):
        """
        OPTIMIZACION H1: prompt minimo. Solo necesitamos que el LLM identifique
        contradicciones estructurales NO capturadas por las reglas deterministicas.
        El veredicto ya esta calculado — el LLM no lo cambia.
        max_tokens: 600 -> 80
        """
        diff   = z_fresh - z_reference
        top3   = sorted(zip(["Z1","Z2","Z3","Z4","Z5","Z6","Z7","Z8"], diff.tolist()),
                        key=lambda x: -abs(x[1]))[:3]
        discr  = " ".join(f"{n}={d:+.2f}" for n,d in top3)

        # Prompt ultracompacto: solo lo estrictamente necesario
        prompt = (
            f"Lambda Cortex V2. {isomorph_name} Sim={sim_adj:.3f} {verdict}. "
            f"Discrepancias Z: {discr}. "
            f"Contradicciones ya detectadas: {len(existing_contradictions)}.\n"
            f'Identifica 1 contradiccion estructural NO obvia. '
            f'Solo JSON: {{"r":"1 frase","c":[]}}'
        )
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role":"user","content":prompt}],
                max_tokens=80,   # OPTIMIZACION: 600 -> 80
                temperature=0.0
            )
            token_tracker.add("lambda", resp.usage.prompt_tokens, resp.usage.completion_tokens)

            raw  = resp.choices[0].message.content.strip().replace("```json","").replace("```","")
            s,e  = raw.find("{"), raw.rfind("}")
            data = json.loads(raw[s:e+1]) if s!=-1 else {}
            reasoning      = data.get("r", data.get("reasoning", f"Sim={sim_adj:.4f} {verdict}"))
            contradictions = data.get("c", data.get("contradictions_found", []))
            if isinstance(contradictions, list):
                contradictions = [str(x) for x in contradictions if x]
            if not contradictions and verdict == "CONTRADICTED":
                contradictions = [f"Z mismatch: {discr}"]
            logger.info(f"Lambda Sonnet: {reasoning[:80]}")
            return reasoning, contradictions
        except Exception as e:
            logger.warning(f"Lambda reasoning fallback: {e}")
            fallback_contradictions = [f"Z mismatch: {discr}"] if verdict == "CONTRADICTED" else []
            return f"Sim={sim_adj:.4f} {verdict}. Discrepancias: {discr}.", fallback_contradictions

    def _failure_protocol(self, hypothesis, phi_state, start_time):
        return LambdaValidation(
            hypothesis_confirmed=False, hypothesis_contradicted=False,
            similarity=0.0, verdict="LAMBDA_OFFLINE", action="HOLD",
            evidence={"error":"todas las fuentes fallaron"},
            z_fresh=[0.0]*8,
            z_reference=list(PHYSICAL_ISOMORPHS.get(hypothesis.best_isomorph,{}).get("Z",np.zeros(8)).tolist()),
            additional_signals={}, contradictions=[],
            reasoning="Lambda offline. Sin validacion externa no se actua.",
            api_sources_used=[], api_failures=["yahoo_finance","fred"],
            timestamp=datetime.now().isoformat(),
            validation_duration_seconds=round(time.time()-start_time,2)
        )

if __name__ == "__main__":
    from cortex.market_data import MarketData
    from cortex.layers.phi import PhiLayer
    from cortex.layers.omega import OmegaLayer
    md  = MarketData()
    ind = md.get_regime_indicators()
    phi = PhiLayer().factorize(ind)
    hyp = OmegaLayer().generate_hypothesis(phi)
    lam = LambdaLayer().validate(hyp, phi)
    print(lam.summary())
