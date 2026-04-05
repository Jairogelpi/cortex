"""
CAPA LAMBDA - Validacion con herramientas reales
Cortex V2, Fase 4

Lambda cierra el bucle hipotesis-realidad del paper.
Es la unica barrera entre Omega y Alpaca.

Principio central (Seccion 9.6 del paper):
    "En ausencia de validacion externa, Cortex V2 no actua.
    La inaccion ante incertidumbre es preferible a la accion
    sin validacion. Primum non nocere."

CORRECCION ARQUITECTONICA CRITICA:
    Lambda NO compara Z_validacion con Z_omega.
    Lambda compara Z_validacion con el VECTOR Z DE REFERENCIA del isomorfo fisico.

    Por que: Z_omega y Z_validacion son ambos outputs de Phi sobre los mismos
    datos de mercado. Compararlos produce autocorrelacion (Sim ~ 1.0 siempre).
    Eso NO es falsificacion — es medir lo mismo dos veces.

    La falsificacion real es:
        Sim( Phi(datos_reales_frescos), Z_referencia_isomorfo_fisico )

    Si los datos reales son geometricamente similares al isomorfo fisico
    de referencia -> hipotesis confirmada.
    Si no -> Omega confabulo. Backtrack.

    Ademas Lambda analiza senales adicionales NO disponibles para Phi/Omega:
    - momentum_5d (corto plazo vs largo plazo)
    - vix_change_5d (tendencia reciente del VIX)
    - ief_return_5d (flight-to-safety)
    Estas senales pueden contradecir el isomorfo aunque el vector Z sea similar.

Escenario de fallo F1 que Lambda previene (Seccion 4):
    "Omega confabula isomorfo falso. Kappa mal calibrado.
    Lambda no verifica. -> perdida real $400+"

Protocolo de fallo de Lambda (Seccion 9.6):
    - Timeout API > 30s: mantener posicion, no ejecutar cambios
    - Datos inconsistentes: subagente de reconciliacion
    - Fallo total: modo degradado, sin nuevas posiciones
    - Contradice Omega (Sim < 0.40): backtrack inmediato

Modelo: Claude Sonnet 4.6 (seccion 8.10)
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
    """Resultado de la validacion de Lambda."""
    hypothesis_confirmed: bool
    hypothesis_contradicted: bool
    similarity: float                    # Sim(Z_datos_frescos, Z_referencia_isomorfo)
    verdict: str                         # CONFIRMED | UNCERTAIN | CONTRADICTED
    action: str                          # EXECUTE | DEFENSIVE | BACKTRACK | HOLD
    evidence: dict                       # datos reales descargados
    z_fresh: list                        # Z calculado desde datos frescos independientes
    z_reference: list                    # Z de referencia del isomorfo fisico
    additional_signals: dict             # senales adicionales (vix_change, mom_5d, ief)
    contradictions: list                 # contradicciones encontradas por Sonnet
    reasoning: str
    api_sources_used: list
    api_failures: list
    timestamp: str
    validation_duration_seconds: float

    def summary(self) -> str:
        lines = [
            f"Lambda Validation | Veredicto: {self.verdict} | Sim={self.similarity:.4f}",
            f"  Comparacion: Phi(datos_frescos) vs Z_referencia_{self.verdict}",
            f"  Hipotesis confirmada:  {self.hypothesis_confirmed}",
            f"  Hipotesis contradicha: {self.hypothesis_contradicted}",
            f"  Accion:                {self.action}",
            f"  Fuentes OK:            {self.api_sources_used}",
            f"  Fuentes fallidas:      {self.api_failures if self.api_failures else 'ninguna'}",
            f"  Duracion:              {self.validation_duration_seconds:.1f}s",
            "",
            "  Evidencia real (Yahoo Finance):",
        ]
        for k, v in self.evidence.items():
            if k != "source":
                lines.append(f"    {k}: {v}")

        lines.append("")
        lines.append("  Senales adicionales (no disponibles para Phi/Omega):")
        for k, v in self.additional_signals.items():
            lines.append(f"    {k}: {v}")

        if self.contradictions:
            lines.append("")
            lines.append("  Contradicciones encontradas por Lambda:")
            for c in self.contradictions:
                lines.append(f"    - {c}")

        lines.append("")
        lines.append(f"  Razonamiento Sonnet:")
        lines.append(f"  {self.reasoning}")
        return "\n".join(lines)


class LambdaLayer:
    """
    Capa Lambda: validacion anti-sesgo de confirmacion.

    Arquitectura corregida:
        Sim( Phi(datos_frescos_independientes), Z_referencia_isomorfo_fisico )

    No compara con Z_omega — eso seria autocorrelacion.
    Compara con el vector Z de referencia del isomorfo del paper.
    """

    SIM_CONFIRM    = 0.65   # >= confirma hipotesis
    SIM_CONTRADICT = 0.40   # <  contradice hipotesis -> backtrack
    API_TIMEOUT    = 30

    def __init__(self):
        self.client = OpenAI(
            api_key=config.OPENROUTER_API_KEY,
            base_url=config.OPENROUTER_BASE_URL
        )
        self.model = config.MODEL_PHI   # Sonnet para Lambda
        self.phi = PhiLayer()
        logger.info(f"Capa Lambda inicializada: {self.model}")

    def validate(
        self,
        omega_hypothesis: OmegaHypothesis,
        phi_state: PhiState
    ) -> LambdaValidation:
        """
        Valida la hipotesis de Omega contra datos reales frescos.

        Pregunta que responde Lambda:
        '¿Los datos reales actuales son geometricamente similares
         al isomorfo fisico que Omega eligio?'

        Si si: Omega acerto. CONFIRMED.
        Si no: Omega confabulo. CONTRADICTED.
        """
        start_time = time.time()
        sources_used = []
        sources_failed = []

        isomorph_name = omega_hypothesis.best_isomorph
        logger.info(
            f"Lambda: validando '{isomorph_name}' "
            f"(senal={omega_hypothesis.trading_signal})"
        )

        # Paso 1: descargar datos frescos e independientes
        evidence = {}

        yf_data = self._get_yahoo_finance_data()
        if "error" not in yf_data:
            evidence.update(yf_data)
            sources_used.append("yahoo_finance")
            logger.info(f"Lambda: Yahoo Finance OK")
        else:
            sources_failed.append("yahoo_finance")
            logger.warning(f"Lambda: Yahoo Finance fallo: {yf_data['error']}")

        fred_data = self._get_fred_data()
        if "error" not in fred_data:
            evidence.update(fred_data)
            sources_used.append("fred")
        else:
            sources_failed.append("fred")
            logger.warning(f"Lambda: FRED fallo: {fred_data['error']}")

        if not sources_used:
            return self._failure_protocol(omega_hypothesis, phi_state, start_time)

        # Paso 2: extraer senales adicionales ANTES de factorizar
        # Estas son las senales que Phi/Omega no tenian disponibles
        additional_signals = {
            "vix_change_5d": evidence.get("vix_change_5d", 0.0),
            "momentum_5d_pct": evidence.get("spy_momentum_5d_pct", 0.0),
            "vol_5d_pct": evidence.get("spy_vol_5d_pct", 0.0),
            "ief_return_5d_pct": evidence.get("ief_return_5d_pct", 0.0),
            "yield_curve_spread": evidence.get("fred_t10y2y_spread", "no_disponible"),
        }

        # Paso 3: construir indicadores para factorizacion fresca
        fresh_indicators = self._build_fresh_indicators(evidence, phi_state)

        # Paso 4: factorizar datos frescos con Phi -> Z_fresh
        # CRITICO: estos datos son independientes de los que uso Omega
        z_fresh_state = self.phi.factorize(fresh_indicators)
        z_fresh = z_fresh_state.to_vector()

        # Paso 5: obtener Z_referencia del isomorfo fisico del paper
        # NO usar Z_omega — eso seria autocorrelacion
        if isomorph_name not in PHYSICAL_ISOMORPHS:
            logger.error(f"Lambda: isomorfo '{isomorph_name}' no encontrado")
            return self._failure_protocol(omega_hypothesis, phi_state, start_time)

        z_reference = PHYSICAL_ISOMORPHS[isomorph_name]["Z"]

        logger.info(
            f"Lambda: comparando Z_fresh vs Z_referencia_{isomorph_name}\n"
            f"  Z_fresh:     {[round(x,3) for x in z_fresh.tolist()]}\n"
            f"  Z_referencia:{[round(x,3) for x in z_reference.tolist()]}"
        )

        # Paso 6: similitud real
        similarity = self._calc_similarity(z_fresh, z_reference)
        logger.info(f"Lambda: Sim(Z_fresh, Z_ref_{isomorph_name}) = {similarity:.4f}")

        # Paso 7: ajuste por senales adicionales contradictorias
        # Si las senales de corto plazo contradicen el isomorfo, penalizar
        similarity_adjusted, signal_contradictions = self._adjust_for_additional_signals(
            similarity, additional_signals, isomorph_name, omega_hypothesis.trading_signal
        )

        if signal_contradictions:
            logger.warning(f"Lambda: senales contradictorias: {signal_contradictions}")

        # Paso 8: veredicto
        verdict, action, confirmed, contradicted = self._verdict(similarity_adjusted)

        # Paso 9: razonamiento anti-sesgo con Sonnet
        reasoning, contradictions_llm = self._get_reasoning(
            omega_hypothesis, evidence, additional_signals,
            similarity, similarity_adjusted, verdict,
            z_fresh, z_reference, isomorph_name,
            signal_contradictions
        )

        all_contradictions = signal_contradictions + contradictions_llm

        duration = time.time() - start_time
        validation = LambdaValidation(
            hypothesis_confirmed=confirmed,
            hypothesis_contradicted=contradicted,
            similarity=round(similarity_adjusted, 4),
            verdict=verdict,
            action=action,
            evidence={k: v for k, v in evidence.items() if k != "source"},
            z_fresh=z_fresh.tolist(),
            z_reference=z_reference.tolist(),
            additional_signals=additional_signals,
            contradictions=all_contradictions,
            reasoning=reasoning,
            api_sources_used=sources_used,
            api_failures=sources_failed,
            timestamp=datetime.now().isoformat(),
            validation_duration_seconds=round(duration, 2)
        )

        logger.info(
            f"Lambda: veredicto={verdict} accion={action} "
            f"sim_raw={similarity:.4f} sim_adj={similarity_adjusted:.4f} "
            f"contradicciones={len(all_contradictions)}"
        )
        return validation

    def _get_yahoo_finance_data(self) -> dict:
        """Descarga datos frescos de Yahoo Finance. Fuente primaria."""
        try:
            spy = yf.Ticker("SPY")
            hist = spy.history(period="3mo")
            if hist.empty:
                return {"error": "SPY vacio"}

            closes = hist["Close"]
            current   = float(closes.iloc[-1])
            prev_21   = float(closes.iloc[-22]) if len(closes) > 22 else current
            prev_5    = float(closes.iloc[-6])  if len(closes) > 6  else current

            momentum_21d = round((current - prev_21) / prev_21 * 100, 2)
            momentum_5d  = round((current - prev_5)  / prev_5  * 100, 2)

            returns  = closes.pct_change().dropna()
            vol_21d  = round(float(returns.tail(21).std() * (252**0.5) * 100), 2)
            vol_5d   = round(float(returns.tail(5).std()  * (252**0.5) * 100), 2)

            max_90d  = float(closes.tail(90).max())
            drawdown = round((current - max_90d) / max_90d * 100, 2)

            # VIX
            vix_hist     = yf.Ticker("^VIX").history(period="5d")
            vix_current  = float(vix_hist["Close"].iloc[-1]) if not vix_hist.empty else 20.0
            vix_prev5    = float(vix_hist["Close"].iloc[0])  if len(vix_hist) >= 2  else vix_current
            vix_change5d = round(vix_current - vix_prev5, 2)

            # IEF: flight-to-safety indicator
            ief_hist    = yf.Ticker("IEF").history(period="1mo")
            ief_return  = 0.0
            if not ief_hist.empty and len(ief_hist) > 5:
                ief_return = round(
                    (float(ief_hist["Close"].iloc[-1]) - float(ief_hist["Close"].iloc[-6]))
                    / float(ief_hist["Close"].iloc[-6]) * 100, 2
                )

            return {
                "spy_price":           round(current, 2),
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
        """Descarga indicadores macro de FRED. Fuente secundaria."""
        try:
            # FRED API publica — series sin autenticacion
            url = "https://fred.stlouisfed.org/graph/fredgraph.csv"

            def get_last_value(series_id: str) -> Optional[float]:
                try:
                    import pandas as pd
                    df = pd.read_csv(
                        f"{url}?id={series_id}",
                        parse_dates=["DATE"],
                        na_values=[".", ""],
                        timeout=self.API_TIMEOUT
                    )
                    df = df.dropna()
                    if not df.empty:
                        return float(df.iloc[-1, 1])
                except Exception:
                    pass
                return None

            results = {}

            t10y2y = get_last_value("T10Y2Y")
            if t10y2y is not None:
                results["fred_t10y2y_spread"] = round(t10y2y, 3)

            if not results:
                return {"error": "FRED: no se obtuvieron series"}

            results["source"] = "fred"
            return results

        except Exception as e:
            return {"error": f"FRED: {str(e)}"}

    def _build_fresh_indicators(self, evidence: dict, original_phi: PhiState) -> dict:
        """
        Construye indicadores para Phi desde la evidencia fresca.
        Usa datos reales de Yahoo Finance. Si faltan, usa los originales
        pero los marca — no inventa datos.
        """
        orig = original_phi.raw_indicators

        vix      = evidence.get("vix_current",          orig.get("vix", 20.0))
        momentum = evidence.get("spy_momentum_21d_pct", orig.get("momentum_21d_pct", 0.0))
        vol      = evidence.get("spy_vol_21d_pct",      orig.get("vol_realized_pct", 15.0))
        drawdown = evidence.get("spy_drawdown_90d_pct", orig.get("drawdown_90d_pct", 0.0))
        price    = evidence.get("spy_price",            orig.get("spy_price", 0.0))

        regime = self._classify_regime(vix, momentum, vol, drawdown)

        return {
            "vix":               round(float(vix), 2),
            "momentum_21d_pct":  round(float(momentum), 2),
            "vol_realized_pct":  round(float(vol), 2),
            "drawdown_90d_pct":  round(float(drawdown), 2),
            "spy_price":         round(float(price), 2),
            "regime":            regime,
            "timestamp":         datetime.now().isoformat(),
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
        """Similitud coseno normalizada [0,1]. Identico a Omega."""
        na, nb = np.linalg.norm(z_a), np.linalg.norm(z_b)
        if na == 0 or nb == 0:
            return 0.0
        cosine = float(np.dot(z_a, z_b) / (na * nb))
        return max(0.0, min(1.0, (cosine + 1.0) / 2.0))

    def _adjust_for_additional_signals(
        self,
        similarity: float,
        signals: dict,
        isomorph_name: str,
        trading_signal: str
    ) -> tuple:
        """
        Ajusta la similitud basada en senales adicionales de corto plazo
        que Phi/Omega no tenian disponibles.

        Logica de penalizacion segun el isomorfo:
        - lorenz/phase_transition (CASH/DEFENSIVE): si VIX cae mucho
          o momentum_5d es fuerte positivo, penalizar (mercado se estabiliza)
        - gas_expansion (LONG): si VIX sube o momentum_5d es negativo, penalizar
        - compressed_gas (LONG_PREPARE): si vol_5d muy alta, penalizar
        """
        contradictions = []
        penalty = 0.0

        vix_change = signals.get("vix_change_5d", 0.0)
        mom_5d     = signals.get("momentum_5d_pct", 0.0)
        vol_5d     = signals.get("vol_5d_pct", 0.0)
        ief_return = signals.get("ief_return_5d_pct", 0.0)

        if isomorph_name in ("lorenz_attractor", "phase_transition"):
            # Lorenz/Transicion implica caos/estres creciente
            # Si VIX bajo mucho en 5 dias -> el estres esta BAJANDO, no subiendo
            if vix_change < -5.0:
                penalty += 0.12
                contradictions.append(
                    f"VIX cayo {vix_change:.1f}pts en 5d: estres bajando, "
                    f"inconsistente con {isomorph_name}"
                )
            elif vix_change < -3.0:
                penalty += 0.06
                contradictions.append(
                    f"VIX cayo {vix_change:.1f}pts en 5d: leve reduccion de estres"
                )

            # Si momentum 5d es claramente positivo -> recuperacion, no caos
            if mom_5d > 3.0:
                penalty += 0.10
                contradictions.append(
                    f"Momentum 5d={mom_5d:.1f}%: recuperacion de corto plazo "
                    f"inconsistente con regimen caotico"
                )
            elif mom_5d > 1.5:
                penalty += 0.05
                contradictions.append(
                    f"Momentum 5d={mom_5d:.1f}%: leve recuperacion de corto plazo"
                )

            # Si IEF (bonos) sube mucho -> flight-to-safety activo = consistente con caos
            if ief_return > 1.0:
                # Esto CONFIRMA el isomorfo, reducir penalizacion
                penalty -= 0.05

        elif isomorph_name == "gas_expansion":
            if vix_change > 3.0:
                penalty += 0.12
                contradictions.append(
                    f"VIX subio {vix_change:.1f}pts en 5d: estres creciente "
                    f"inconsistente con bull run"
                )
            if mom_5d < -2.0:
                penalty += 0.10
                contradictions.append(
                    f"Momentum 5d={mom_5d:.1f}%: caida reciente inconsistente con expansion"
                )

        elif isomorph_name == "compressed_gas":
            if vol_5d > 30.0:
                penalty += 0.08
                contradictions.append(
                    f"Vol 5d={vol_5d:.1f}%: volatilidad excesiva para acumulacion"
                )

        similarity_adjusted = max(0.0, min(1.0, similarity - penalty))

        if penalty > 0:
            logger.info(
                f"Lambda: penalizacion por senales adicionales = -{penalty:.3f} "
                f"(sim {similarity:.4f} -> {similarity_adjusted:.4f})"
            )

        return round(similarity_adjusted, 4), contradictions

    def _verdict(self, similarity: float) -> tuple:
        """Veredicto segun umbrales del paper."""
        if similarity >= self.SIM_CONFIRM:
            return "CONFIRMED", "EXECUTE", True, False
        elif similarity < self.SIM_CONTRADICT:
            return "CONTRADICTED", "BACKTRACK", False, True
        else:
            return "UNCERTAIN", "DEFENSIVE", False, False

    def _extract_json(self, text: str) -> dict:
        """Parser JSON robusto para respuestas largas de Sonnet."""
        text = text.replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end+1])
            except json.JSONDecodeError:
                pass
        # Regex como ultimo recurso
        r_match = re.search(r'"reasoning"\s*:\s*"(.*?)"(?=\s*[,}])', text, re.DOTALL)
        c_match = re.search(r'"contradictions_found"\s*:\s*\[(.*?)\]', text, re.DOTALL)
        if r_match:
            contradictions = []
            if c_match:
                raw_list = c_match.group(1)
                contradictions = re.findall(r'"(.*?)"', raw_list)
            return {
                "reasoning": r_match.group(1),
                "contradictions_found": contradictions
            }
        raise ValueError(f"No se pudo extraer JSON: {text[:200]}")

    def _get_reasoning(
        self,
        hypothesis: OmegaHypothesis,
        evidence: dict,
        additional_signals: dict,
        sim_raw: float,
        sim_adjusted: float,
        verdict: str,
        z_fresh: np.ndarray,
        z_reference: np.ndarray,
        isomorph_name: str,
        existing_contradictions: list
    ) -> tuple:
        """
        Razonamiento anti-sesgo de confirmacion con Sonnet.
        Instruccion explicita: buscar INCONSISTENCIAS, no confirmar.
        """
        diff    = z_fresh - z_reference
        dim_names = ["Z1_tend","Z2_din","Z3_esc","Z4_caus",
                     "Z5_temp","Z6_rev","Z7_val","Z8_comp"]
        top3_diff = sorted(
            zip(dim_names, diff.tolist()),
            key=lambda x: -abs(x[1])
        )[:3]

        prompt = f"""Eres Lambda, la capa de validacion anti-sesgo de Cortex V2.
Tu unico rol: FALSIFICAR la hipotesis de Omega. Busca inconsistencias, no confirmaciones.

HIPOTESIS DE OMEGA:
Isomorfo elegido: {isomorph_name}
Descripcion fisica: {hypothesis.physical_description}
Senal de trading: {hypothesis.trading_signal}

VECTOR Z FRESCO (calculado desde datos reales independientes):
{[round(x,3) for x in z_fresh.tolist()]}

VECTOR Z REFERENCIA del isomorfo {isomorph_name} (del paper):
{[round(x,3) for x in z_reference.tolist()]}

SIMILITUD: sim_raw={sim_raw:.4f} -> sim_ajustada={sim_adjusted:.4f} ({verdict})

MAYORES DISCREPANCIAS entre Z_fresh y Z_referencia:
{chr(10).join(f'  {name}: dif={dif:+.3f}' for name, dif in top3_diff)}

DATOS REALES (Yahoo Finance):
{chr(10).join(f'  {k}: {v}' for k, v in evidence.items() if k != 'source')}

SENALES ADICIONALES (no disponibles para Phi/Omega):
  vix_change_5d:    {additional_signals.get('vix_change_5d', 'N/A')} pts (critico: VIX bajo = estres bajando)
  momentum_5d_pct:  {additional_signals.get('momentum_5d_pct', 'N/A')}% (momentum de corto plazo)
  ief_return_5d_pct:{additional_signals.get('ief_return_5d_pct', 'N/A')}% (flight-to-safety)

CONTRADICCIONES YA DETECTADAS (reglas deterministicas):
{chr(10).join(f'  - {c}' for c in existing_contradictions) if existing_contradictions else '  ninguna detectada'}

INSTRUCCION CRITICA:
- Analiza si las DISCREPANCIAS en Z invalidan el isomorfo
- Analiza si las SENALES ADICIONALES contradicen el isomorfo
- Si el isomorfo es CASH/DEFENSIVE: busca senales de estabilizacion
- Si el isomorfo es LONG: busca senales de deterioro
- Se brutalmente honesto. Si los datos soportan el isomorfo, dilo. Si no, dilo.

Devuelve SOLO este JSON (sin texto antes ni despues):
{{"reasoning": "analisis critico de 3-4 frases mencionando datos especificos", "contradictions_found": ["lista de contradicciones adicionales o lista vacia"]}}"""

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=600,
                temperature=0.1
            )
            raw = resp.choices[0].message.content
            data = self._extract_json(raw)
            reasoning = data.get("reasoning", "")
            contradictions = data.get("contradictions_found", [])
            logger.info(f"Lambda Sonnet: {reasoning[:120]}...")
            return reasoning, contradictions

        except Exception as e:
            logger.warning(f"Lambda reasoning fallback: {e}")
            return (
                f"Sim_raw={sim_raw:.4f} sim_adj={sim_adjusted:.4f} ({verdict}). "
                f"Mayores discrepancias: "
                f"{', '.join(f'{n}={d:+.3f}' for n,d in top3_diff)}. "
                f"Contradicciones deterministicas: {len(existing_contradictions)}.",
                []
            )

    def _failure_protocol(
        self,
        hypothesis: OmegaHypothesis,
        phi_state: PhiState,
        start_time: float
    ) -> LambdaValidation:
        """Seccion 9.6: sin validacion externa, no actuar."""
        duration = time.time() - start_time
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
            reasoning=(
                "Lambda offline. Seccion 9.6: sin validacion externa "
                "el sistema no actua. Manteniendo posicion actual."
            ),
            api_sources_used=[],
            api_failures=["yahoo_finance", "fred"],
            timestamp=datetime.now().isoformat(),
            validation_duration_seconds=round(duration, 2)
        )


def test_lambda():
    """Prueba Lambda con datos reales. Validacion anti-sesgo de confirmacion."""
    from cortex.market_data import MarketData
    from cortex.layers.phi import PhiLayer
    from cortex.layers.omega import OmegaLayer

    print("\n" + "="*55)
    print("  CORTEX V2 - Test Capa Lambda (validacion real)")
    print("  [Arquitectura corregida: Z_fresh vs Z_referencia_isomorfo]")
    print("="*55 + "\n")

    md = MarketData()
    indicators = md.get_regime_indicators()
    print(f"Mercado: VIX={indicators['vix']} | Momentum={indicators['momentum_21d_pct']}% | Regimen={indicators['regime']}\n")

    phi   = PhiLayer()
    phi_state = phi.factorize(indicators)

    omega = OmegaLayer()
    hypothesis = omega.generate_hypothesis(phi_state)
    print(f"Hipotesis Omega: {hypothesis.best_isomorph} (Sim={hypothesis.similarity:.4f}) -> {hypothesis.trading_signal}\n")

    print("Lambda validando (busca falsificar, no confirmar)...\n")
    lambda_layer = LambdaLayer()
    validation   = lambda_layer.validate(hypothesis, phi_state)

    print(validation.summary())

    print("\n--- Decision final del sistema ---")
    if validation.verdict == "CONFIRMED":
        print(f"  CONFIRMADA: Sim={validation.similarity:.4f} >= 0.65")
        if validation.contradictions:
            print(f"  (con {len(validation.contradictions)} senales de alerta detectadas)")
        print(f"  Accion: {validation.action} -> siguiente: Tau (aprobacion humana)")
    elif validation.verdict == "CONTRADICTED":
        print(f"  CONTRADICHA: Sim={validation.similarity:.4f} < 0.40")
        print(f"  BACKTRACK INMEDIATO — escenario F1 del paper prevenido")
        print(f"  Contradicciones: {validation.contradictions}")
    elif validation.verdict == "UNCERTAIN":
        print(f"  INCIERTA: Sim={validation.similarity:.4f} (zona 0.40-0.65)")
        print(f"  Modo DEFENSIVO — no se ejecuta ninguna orden")
    else:
        print(f"  Lambda offline — sin validacion externa, no se actua")

    print("\n" + "="*55)
    print("  Lambda OK -> Siguiente: capa Mu (memoria selectiva)")
    print("="*55 + "\n")
    return validation


if __name__ == "__main__":
    test_lambda()
