"""
CAPA LAMBDA - Validacion con herramientas reales
Cortex V2, Fase 4 — versión final con todos los fixes reales.

Arquitectura:
    Sim( Phi(datos_frescos_independientes), Z_referencia_isomorfo_fisico )

Fixes aplicados:
    1. FRED: no usa parse_dates — lee raw y filtra por columna posicion
    2. Penalizaciones calibradas hasta -0.55 para CONTRADICTED real
    3. Phi temperatura=0.0 en Lambda interna para reproducibilidad
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
        lines = [
            f"Lambda Validation | Veredicto: {self.verdict} | Sim={self.similarity:.4f}",
            f"  Confirmada: {self.hypothesis_confirmed} | Contradicha: {self.hypothesis_contradicted}",
            f"  Accion: {self.action}",
            f"  Fuentes OK: {self.api_sources_used} | Fallidas: {self.api_failures or 'ninguna'}",
            f"  Duracion: {self.validation_duration_seconds:.1f}s",
            "",
            "  Evidencia real:",
        ]
        for k, v in self.evidence.items():
            if k != "source":
                lines.append(f"    {k}: {v}")
        lines.append("\n  Senales adicionales:")
        for k, v in self.additional_signals.items():
            lines.append(f"    {k}: {v}")
        if self.contradictions:
            lines.append("\n  Contradicciones:")
            for c in self.contradictions:
                lines.append(f"    - {c}")
        lines.append(f"\n  Razonamiento: {self.reasoning}")
        return "\n".join(lines)


class LambdaLayer:

    SIM_CONFIRM    = 0.65
    SIM_CONTRADICT = 0.40
    API_TIMEOUT         = 30
    FRED_CONNECT_TIMEOUT = 5
    FRED_READ_TIMEOUT    = 10

    def __init__(self):
        self.client = OpenAI(
            api_key=config.OPENROUTER_API_KEY,
            base_url=config.OPENROUTER_BASE_URL
        )
        self.model = config.MODEL_PHI
        self.phi   = PhiLayer(temperature=0.0)  # FIX 3: reproducible
        logger.info(f"Capa Lambda inicializada: {self.model}")

    def validate(self, omega_hypothesis: OmegaHypothesis, phi_state: PhiState) -> LambdaValidation:
        start_time    = time.time()
        sources_used  = []
        sources_failed = []
        isomorph_name = omega_hypothesis.best_isomorph

        logger.info(f"Lambda: validando '{isomorph_name}' (senal={omega_hypothesis.trading_signal})")

        evidence = {}
        yf_data  = self._get_yahoo_finance_data()
        if "error" not in yf_data:
            evidence.update(yf_data)
            sources_used.append("yahoo_finance")
            logger.info("Lambda: Yahoo Finance OK")
        else:
            sources_failed.append("yahoo_finance")
            logger.warning(f"Lambda: Yahoo Finance fallo: {yf_data['error']}")

        fred_data = self._get_fred_data()
        if not isinstance(fred_data, dict):
            fred_data = {"error": "Invalid FRED response"}
        if "error" not in fred_data:
            evidence.update(fred_data)
            sources_used.append("fred")
            logger.info(f"Lambda: FRED OK — {[k for k in fred_data if k != 'source']}")
        else:
            sources_failed.append("fred")
            logger.info(
                f"Lambda: FRED unavailable (secondary source): {fred_data.get('error', 'Unknown error')}"
            )

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
            omega_hypothesis, evidence, additional_signals,
            similarity, similarity_adj, verdict,
            z_fresh, z_reference, isomorph_name, sig_contradictions
        )

        duration   = time.time() - start_time
        validation = LambdaValidation(
            hypothesis_confirmed=confirmed,
            hypothesis_contradicted=contradicted,
            similarity=round(similarity_adj, 4),
            verdict=verdict,
            action=action,
            evidence={k: v for k, v in evidence.items() if k != "source"},
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
            spy  = yf.Ticker("SPY")
            hist = spy.history(period="3mo")
            if hist.empty:
                return {"error": "SPY vacio"}

            closes       = hist["Close"]
            current      = float(closes.iloc[-1])
            prev_21      = float(closes.iloc[-22]) if len(closes) > 22 else current
            prev_5       = float(closes.iloc[-6])  if len(closes) > 6  else current
            momentum_21d = round((current - prev_21) / prev_21 * 100, 2)
            momentum_5d  = round((current - prev_5)  / prev_5  * 100, 2)

            returns = closes.pct_change().dropna()
            vol_21d = round(float(returns.tail(21).std() * (252**0.5) * 100), 2)
            vol_5d  = round(float(returns.tail(5).std()  * (252**0.5) * 100), 2)

            max_90d  = float(closes.tail(90).max())
            drawdown = round((current - max_90d) / max_90d * 100, 2)

            vix_hist     = yf.Ticker("^VIX").history(period="5d")
            vix_current  = float(vix_hist["Close"].iloc[-1]) if not vix_hist.empty else 20.0
            vix_prev5    = float(vix_hist["Close"].iloc[0])  if len(vix_hist) >= 2  else vix_current
            vix_change5d = round(vix_current - vix_prev5, 2)

            ief_hist   = yf.Ticker("IEF").history(period="1mo")
            ief_return = 0.0
            if not ief_hist.empty and len(ief_hist) > 5:
                ief_return = round(
                    (float(ief_hist["Close"].iloc[-1]) - float(ief_hist["Close"].iloc[-6]))
                    / float(ief_hist["Close"].iloc[-6]) * 100, 2
                )

            return {
                "spy_price":            round(current, 2),
                "spy_momentum_21d_pct": momentum_21d,
                "spy_momentum_5d_pct":  momentum_5d,
                "spy_vol_21d_pct":      vol_21d,
                "spy_vol_5d_pct":       vol_5d,
                "spy_drawdown_90d_pct": drawdown,
                "vix_current":          vix_current,
                "vix_change_5d":        vix_change5d,
                "ief_return_5d_pct":    ief_return,
                "source":               "yahoo_finance"
            }
        except Exception as e:
            return {"error": str(e)}

    def _get_fred_data(self) -> dict:
        """
        FIX 1: Multiples estrategias para FRED.
        El error anterior era usar parse_dates con nombre de columna incorrecto.
        Ahora se lee raw y se filtra por posicion de columna.
        """
        results = {}
        for series_id, field_name in [("T10Y2Y", "fred_t10y2y_spread"),
                                       ("VIXCLS",  "fred_vix_close")]:
            v = self._fetch_fred_csv_raw(series_id)
            if v is None:
                v = self._fetch_fred_json(series_id)
            if v is not None:
                results[field_name] = round(v, 3)

        if not results:
            return {"error": "FRED: no se obtuvieron series con ninguna estrategia"}

        results["source"] = "fred"
        return results

    def _fetch_fred_csv_raw(self, series_id: str) -> Optional[float]:
        """
        FIX: lee el CSV de FRED sin parse_dates.
        El error anterior era: 'Missing column provided to parse_dates: DATE'
        porque a veces FRED devuelve el header en lowercase o con espacios.
        Solucion: leer sin parse_dates y filtrar por posicion de columna.
        """
        try:
            import pandas as pd
            from io import StringIO
            url      = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
            headers  = {"User-Agent": "CortexV2/1.0 (research)"}
            response = requests.get(
                url,
                headers=headers,
                timeout=(self.FRED_CONNECT_TIMEOUT, self.FRED_READ_TIMEOUT)
            )
            if response.status_code != 200:
                return None
            # Leer sin parse_dates — evita el error de columna DATE
            df = pd.read_csv(
                StringIO(response.text),
                na_values=[".", ""]
            )
            if df.empty or df.shape[1] < 2:
                return None
            # La segunda columna es el valor numerico
            col_valor = df.columns[1]
            df_clean  = df.dropna(subset=[col_valor])
            if df_clean.empty:
                return None
            return float(df_clean.iloc[-1][col_valor])
        except Exception as e:
            logger.debug(f"FRED CSV raw {series_id} fallo: {e}")
            return None

    def _fetch_fred_json(self, series_id: str) -> Optional[float]:
        try:
            api_key = (config.FRED_API_KEY or "").strip()
            if not api_key:
                return None
            url    = "https://api.stlouisfed.org/fred/series/observations"
            params = {
                "series_id": series_id,
                "api_key":   api_key,
                "file_type": "json",
                "limit":     3,
                "sort_order":"desc"
            }
            response = requests.get(
                url,
                params=params,
                timeout=(self.FRED_CONNECT_TIMEOUT, self.FRED_READ_TIMEOUT)
            )
            if response.status_code != 200:
                return None
            obs = [o for o in response.json().get("observations", [])
                   if o.get("value", ".") != "."]
            if obs:
                return float(obs[0]["value"])
        except Exception as e:
            logger.debug(f"FRED JSON {series_id} fallo: {e}")
        return None

    def _build_fresh_indicators(self, evidence: dict, original_phi: PhiState) -> dict:
        orig     = original_phi.raw_indicators
        vix      = evidence.get("vix_current",          orig.get("vix", 20.0))
        momentum = evidence.get("spy_momentum_21d_pct", orig.get("momentum_21d_pct", 0.0))
        vol      = evidence.get("spy_vol_21d_pct",      orig.get("vol_realized_pct", 15.0))
        drawdown = evidence.get("spy_drawdown_90d_pct", orig.get("drawdown_90d_pct", 0.0))
        price    = evidence.get("spy_price",            orig.get("spy_price", 0.0))
        regime   = self._classify_regime(float(vix), float(momentum), float(vol), float(drawdown))
        return {
            "vix":              round(float(vix), 2),
            "momentum_21d_pct": round(float(momentum), 2),
            "vol_realized_pct": round(float(vol), 2),
            "drawdown_90d_pct": round(float(drawdown), 2),
            "spy_price":        round(float(price), 2),
            "regime":           regime,
            "timestamp":        datetime.now().isoformat(),
        }

    def _classify_regime(self, vix, momentum, vol, drawdown) -> str:
        if vix > 35 and momentum < -5 and drawdown < -15:
            return "R4_CONTRACTION"
        elif vix > 28:
            return "R3_TRANSITION"
        elif 20 <= vix <= 28 and abs(momentum) <= 2:
            return "R2_ACCUMULATION"
        elif vix < 20 and momentum > 0 and vol < 15:
            return "R1_EXPANSION"
        return "INDETERMINATE"

    def _calc_similarity(self, z_a: np.ndarray, z_b: np.ndarray) -> float:
        na, nb = np.linalg.norm(z_a), np.linalg.norm(z_b)
        if na == 0 or nb == 0:
            return 0.0
        cosine = float(np.dot(z_a, z_b) / (na * nb))
        return max(0.0, min(1.0, (cosine + 1.0) / 2.0))

    def _adjust_for_additional_signals(self, similarity, signals, isomorph_name, trading_signal):
        """FIX 2: penalizaciones calibradas para CONTRADICTED real."""
        contradictions = []
        penalty        = 0.0

        vix_change = signals.get("vix_change_5d", 0.0)
        mom_5d     = signals.get("momentum_5d_pct", 0.0)
        vol_5d     = signals.get("vol_5d_pct", 0.0)
        ief_return = signals.get("ief_return_5d_pct", 0.0)

        if isomorph_name in ("lorenz_attractor", "phase_transition"):
            if vix_change < -8.0:
                penalty += 0.30
                contradictions.append(
                    f"VIX cayo {vix_change:.1f}pts en 5d: descompresion severa, "
                    f"incompatible con regimen caotico activo")
            elif vix_change < -5.0:
                penalty += 0.18
                contradictions.append(
                    f"VIX cayo {vix_change:.1f}pts en 5d: estres bajando, "
                    f"inconsistente con {isomorph_name}")
            elif vix_change < -3.0:
                penalty += 0.09
                contradictions.append(f"VIX cayo {vix_change:.1f}pts en 5d: leve reduccion de estres")

            if mom_5d > 4.0:
                penalty += 0.20
                contradictions.append(f"Momentum 5d={mom_5d:.1f}%: recuperacion fuerte, incompatible con caos")
            elif mom_5d > 2.0:
                penalty += 0.10
                contradictions.append(f"Momentum 5d={mom_5d:.1f}%: recuperacion moderada de corto plazo")
            elif mom_5d > 1.0:
                penalty += 0.05
                contradictions.append(f"Momentum 5d={mom_5d:.1f}%: leve recuperacion de corto plazo")

            if ief_return > 1.5:
                penalty -= 0.08
            elif ief_return > 0.5:
                penalty -= 0.04
            if vol_5d > 25.0:
                penalty -= 0.05

        elif isomorph_name == "gas_expansion":
            if vix_change > 4.0:
                penalty += 0.20
                contradictions.append(f"VIX subio {vix_change:.1f}pts: estres creciente, incompatible con bull run")
            elif vix_change > 2.0:
                penalty += 0.10
                contradictions.append(f"VIX subio {vix_change:.1f}pts: deterioro de condiciones")

            if mom_5d < -3.0:
                penalty += 0.20
                contradictions.append(f"Momentum 5d={mom_5d:.1f}%: caida reciente, incompatible con expansion")
            elif mom_5d < -1.0:
                penalty += 0.08
                contradictions.append(f"Momentum 5d={mom_5d:.1f}%: debilidad de corto plazo")

        elif isomorph_name == "compressed_gas":
            if vol_5d > 30.0:
                penalty += 0.12
                contradictions.append(f"Vol 5d={vol_5d:.1f}%: volatilidad excesiva para acumulacion")

        penalty = max(-0.10, min(0.55, penalty))
        similarity_adjusted = max(0.0, min(1.0, similarity - penalty))

        if abs(penalty) > 0.01:
            logger.info(
                f"Lambda: penalizacion neta={penalty:+.3f} "
                f"(sim {similarity:.4f} -> {similarity_adjusted:.4f})"
            )

        return round(similarity_adjusted, 4), contradictions

    def _verdict(self, similarity):
        if similarity >= self.SIM_CONFIRM:
            return "CONFIRMED", "EXECUTE", True, False
        elif similarity < self.SIM_CONTRADICT:
            return "CONTRADICTED", "BACKTRACK", False, True
        else:
            return "UNCERTAIN", "DEFENSIVE", False, False

    def _extract_json(self, text):
        text = text.replace("```json","").replace("```","").strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        s, e = text.find("{"), text.rfind("}")
        if s != -1 and e != -1 and e > s:
            try:
                return json.loads(text[s:e+1])
            except json.JSONDecodeError:
                pass
        r = re.search(r'"reasoning"\s*:\s*"(.*?)"(?=\s*[,}])', text, re.DOTALL)
        c = re.search(r'"contradictions_found"\s*:\s*\[(.*?)\]', text, re.DOTALL)
        if r:
            return {"reasoning": r.group(1),
                    "contradictions_found": re.findall(r'"(.*?)"', c.group(1)) if c else []}
        raise ValueError(f"No se pudo extraer JSON: {text[:200]}")

    def _get_reasoning(self, hypothesis, evidence, additional_signals,
                       sim_raw, sim_adj, verdict, z_fresh, z_reference,
                       isomorph_name, existing_contradictions):
        diff      = z_fresh - z_reference
        dim_names = ["Z1_tend","Z2_din","Z3_esc","Z4_caus","Z5_temp","Z6_rev","Z7_val","Z8_comp"]
        top3      = sorted(zip(dim_names, diff.tolist()), key=lambda x: -abs(x[1]))[:3]

        prompt = f"""Eres Lambda, la capa de validacion anti-sesgo de Cortex V2.
Tu unico rol: FALSIFICAR la hipotesis de Omega. Busca inconsistencias, no confirmaciones.

HIPOTESIS: {isomorph_name} | Senal: {hypothesis.trading_signal}

Z_FRESH: {[round(x,3) for x in z_fresh.tolist()]}
Z_REF_{isomorph_name}: {[round(x,3) for x in z_reference.tolist()]}
Sim_raw={sim_raw:.4f} -> Sim_adj={sim_adj:.4f} | VEREDICTO: {verdict}

MAYORES DISCREPANCIAS:
{chr(10).join(f'  {n}: dif={d:+.3f}' for n, d in top3)}

DATOS REALES:
{chr(10).join(f'  {k}: {v}' for k, v in evidence.items() if k != 'source')}

SENALES ADICIONALES:
  vix_change_5d: {additional_signals.get('vix_change_5d', 'N/A')} pts
  momentum_5d:   {additional_signals.get('momentum_5d_pct', 'N/A')}%
  ief_return_5d: {additional_signals.get('ief_return_5d_pct', 'N/A')}%

CONTRADICCIONES YA DETECTADAS:
{chr(10).join(f'  - {c}' for c in existing_contradictions) if existing_contradictions else '  ninguna'}

Devuelve SOLO JSON:
{{"reasoning": "analisis critico 3-4 frases con datos especificos", "contradictions_found": []}}"""

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=600,
                temperature=0.0
            )
            data          = self._extract_json(resp.choices[0].message.content)
            reasoning     = data.get("reasoning", "")
            contradictions= data.get("contradictions_found", [])
            logger.info(f"Lambda Sonnet: {reasoning[:120]}...")
            return reasoning, contradictions
        except Exception as e:
            logger.warning(f"Lambda reasoning fallback: {e}")
            return (
                f"Sim_raw={sim_raw:.4f} sim_adj={sim_adj:.4f} ({verdict}). "
                f"Top discrepancias: {', '.join(f'{n}={d:+.3f}' for n,d in top3)}.",
                []
            )

    def _failure_protocol(self, hypothesis, phi_state, start_time):
        return LambdaValidation(
            hypothesis_confirmed=False,
            hypothesis_contradicted=False,
            similarity=0.0,
            verdict="LAMBDA_OFFLINE",
            action="HOLD",
            evidence={"error": "todas las fuentes fallaron"},
            z_fresh=[0.0]*8,
            z_reference=list(
                PHYSICAL_ISOMORPHS.get(hypothesis.best_isomorph, {})
                .get("Z", np.zeros(8)).tolist()
            ),
            additional_signals={},
            contradictions=[],
            reasoning="Lambda offline. Sin validacion externa no se actua.",
            api_sources_used=[],
            api_failures=["yahoo_finance", "fred"],
            timestamp=datetime.now().isoformat(),
            validation_duration_seconds=round(time.time() - start_time, 2)
        )


def test_lambda():
    from cortex.market_data import MarketData
    from cortex.layers.phi import PhiLayer
    from cortex.layers.omega import OmegaLayer

    print("\n" + "="*55)
    print("  CORTEX V2 - Test Capa Lambda")
    print("="*55 + "\n")

    md         = MarketData()
    indicators = md.get_regime_indicators()
    print(f"Mercado: VIX={indicators['vix']} | Momentum={indicators['momentum_21d_pct']}% | Regimen={indicators['regime']}\n")

    phi_state  = PhiLayer().factorize(indicators)
    hypothesis = OmegaLayer().generate_hypothesis(phi_state)
    print(f"Hipotesis: {hypothesis.best_isomorph} (Sim={hypothesis.similarity:.4f}) -> {hypothesis.trading_signal}\n")

    validation = LambdaLayer().validate(hypothesis, phi_state)
    print(validation.summary())

    print("\n" + "="*55)
    print("  Lambda OK")
    print("="*55 + "\n")
    return validation


if __name__ == "__main__":
    test_lambda()
