"""
CORTEX UNIFIED LAYER — Phi + Omega + Lambda en UNA sola llamada LLM
Cortex V2 | OSF: https://osf.io/wdkcx

REVOLUCION H1:
  Antes: 3 llamadas LLM separadas (Phi=460, Omega=722, Lambda=930 = 2112 tokens)
  Ahora: 1 llamada LLM unificada (~300-400 tokens total)

Arquitectura:
  1. Phi deterministico: calcula Z1-Z8 base con formulas matematicas (0 tokens)
  2. [UNA LLAMADA] UnifiedLayer: recibe Z_base + datos mercado frescos y devuelve:
       - Z_ajustado: refinamiento semantico del vector Z
       - isomorph: cual de los 5 isomorfos es el mejor
       - sim_adjustment: ajuste fino de similitud coseno
       - contradiction: si hay alguna contradiccion estructural clave
  3. Kappa deterministico: calcula delta con formula (0 tokens)
  4. Todo lo demas: deterministico

Por que funciona:
  Phi, Omega y Lambda comparten exactamente los mismos datos de entrada.
  Hacerlos en llamadas separadas es redundante. El LLM puede hacer los
  tres ajustes semanticos en un solo contexto, con menos tokens totales
  porque no se repite el contexto de mercado tres veces.

Tokens estimados:
  Input: ~180 (indicadores + Z_base + datos frescos compactos)
  Output: ~80 (JSON con Z_adj + isomorph + contradiction)
  Total: ~260 tokens vs 2112 anterior = 88% reduccion
"""
import json
import time
import numpy as np
from datetime import datetime
from typing import Optional, Tuple
import yfinance as yf
import requests
from openai import OpenAI
from loguru import logger

from cortex.config import config
from cortex.token_tracker import token_tracker
from cortex.layers.phi import PhiState, PhiLayer
from cortex.layers.omega import OmegaHypothesis, PHYSICAL_ISOMORPHS
from cortex.layers.lambda_ import LambdaValidation


def _cosine_sim(z_a: np.ndarray, z_b: np.ndarray) -> float:
    na, nb = np.linalg.norm(z_a), np.linalg.norm(z_b)
    if na == 0 or nb == 0:
        return 0.0
    return max(0.0, min(1.0, (float(np.dot(z_a, z_b) / (na * nb)) + 1.0) / 2.0))


def _get_market_data_fresh() -> dict:
    """Obtiene datos frescos de Yahoo Finance y FRED (igual que Lambda antes)."""
    result = {"spy_momentum_5d_pct": 0.0, "vix_change_5d": 0.0,
              "ief_return_5d_pct": 0.0, "sources": []}
    try:
        spy = yf.Ticker("SPY").history(period="3mo")
        if not spy.empty:
            c = spy["Close"]
            cur = float(c.iloc[-1])
            result["spy_momentum_5d_pct"] = round((cur - float(c.iloc[-6])) / float(c.iloc[-6]) * 100, 2) if len(c) > 6 else 0.0
            result["spy_drawdown_90d_pct"] = round((cur - float(c.tail(90).max())) / float(c.tail(90).max()) * 100, 2)
            result["sources"].append("yahoo")
        vix = yf.Ticker("^VIX").history(period="5d")
        if not vix.empty and len(vix) >= 2:
            result["vix_change_5d"] = round(float(vix["Close"].iloc[-1]) - float(vix["Close"].iloc[0]), 2)
        ief = yf.Ticker("IEF").history(period="1mo")
        if not ief.empty and len(ief) > 5:
            result["ief_return_5d_pct"] = round(
                (float(ief["Close"].iloc[-1]) - float(ief["Close"].iloc[-6])) / float(ief["Close"].iloc[-6]) * 100, 2)
    except Exception as e:
        logger.debug(f"Unified fresh data error: {e}")
    return result


def _deterministic_penalties(sims: dict, fresh: dict, best_name: str) -> Tuple[float, list]:
    """
    Penalizaciones deterministicas de Lambda — sin LLM.
    Exactamente las mismas reglas de _adjust_for_additional_signals.
    """
    contradictions = []
    penalty = 0.0
    vix_ch = fresh.get("vix_change_5d", 0.0)
    mom5d  = fresh.get("spy_momentum_5d_pct", 0.0)
    ief    = fresh.get("ief_return_5d_pct", 0.0)

    if best_name in ("lorenz_attractor", "phase_transition"):
        if vix_ch < -8.0:   penalty += 0.30; contradictions.append(f"VIX -{abs(vix_ch):.1f}pts: descompresion severa")
        elif vix_ch < -5.0: penalty += 0.18; contradictions.append(f"VIX -{abs(vix_ch):.1f}pts: estres bajando")
        elif vix_ch < -3.0: penalty += 0.09; contradictions.append(f"VIX -{abs(vix_ch):.1f}pts: leve mejora")
        if mom5d > 4.0:   penalty += 0.20; contradictions.append(f"Mom5d={mom5d:.1f}%: recuperacion fuerte")
        elif mom5d > 2.0: penalty += 0.10; contradictions.append(f"Mom5d={mom5d:.1f}%: recuperacion moderada")
        elif mom5d > 1.0: penalty += 0.05; contradictions.append(f"Mom5d={mom5d:.1f}%: leve recuperacion")
        if ief > 1.5:  penalty -= 0.08
        elif ief > 0.5: penalty -= 0.04
    elif best_name == "gas_expansion":
        if vix_ch > 4.0:   penalty += 0.20; contradictions.append(f"VIX +{vix_ch:.1f}pts: estres creciente")
        elif vix_ch > 2.0: penalty += 0.10; contradictions.append(f"VIX +{vix_ch:.1f}pts: deterioro")
        if mom5d < -3.0:   penalty += 0.20; contradictions.append(f"Mom5d={mom5d:.1f}%: caida reciente")
        elif mom5d < -1.0: penalty += 0.08; contradictions.append(f"Mom5d={mom5d:.1f}%: debilidad")

    return max(-0.10, min(0.55, penalty)), contradictions


class UnifiedLayer:
    """
    Una sola llamada LLM reemplaza Phi-LLM + Omega + Lambda-LLM.

    Input: indicadores de mercado + Z_base deterministico + datos frescos
    Output: Z_ajustado + isomorfo elegido + contradiccion clave (si existe)

    El modelo recibe TODO el contexto necesario de una vez.
    Sin repeticion de datos entre capas.
    """
    SIM_CONFIRM    = 0.65
    SIM_CONTRADICT = 0.40

    def __init__(self):
        self.client = OpenAI(
            api_key=config.OPENROUTER_API_KEY,
            base_url=config.OPENROUTER_BASE_URL,
            timeout=config.OPENROUTER_TIMEOUT_SECONDS,
            max_retries=config.OPENROUTER_MAX_RETRIES,
        )
        # Usamos Sonnet — Opus es excesivo para esta tarea unificada compacta
        self.model = config.MODEL_PHI
        logger.info(f"UnifiedLayer inicializada: {self.model} (1 llamada LLM)")

    def run(self, indicators: dict, fresh: dict
            ) -> Tuple[PhiState, OmegaHypothesis, LambdaValidation]:
        """
        Ejecuta Phi+Omega+Lambda en una sola llamada LLM.
        Retorna los mismos tipos que antes para compatibilidad total con el pipeline.
        """
        t0 = time.time()

        # --- PASO 1: Phi deterministico (0 tokens) ---
        phi_det = PhiLayer(temperature=0.0)  # temperatura 0 = deterministico, sin LLM
        phi_state = phi_det.factorize(indicators)
        z_base = phi_state.to_vector()

        # --- PASO 2: Similitudes coseno (deterministico) ---
        sims = {n: round(_cosine_sim(z_base, iso["Z"]), 4)
                for n, iso in PHYSICAL_ISOMORPHS.items()}
        best_name = max(sims, key=sims.get)
        best_sim  = sims[best_name]
        second    = sorted(sims.items(), key=lambda x: -x[1])[1]

        # --- PASO 3: Penalizaciones deterministicas Lambda (0 tokens) ---
        penalty, det_contradictions = _deterministic_penalties(sims, fresh, best_name)
        sim_adj = round(max(0.0, min(1.0, best_sim - penalty)), 4)

        # --- PASO 4: UNA sola llamada LLM para todo el refinamiento semantico ---
        # Solo si la similitud es suficiente para que valga la pena
        llm_reasoning   = f"{best_name} Sim={sim_adj:.3f}"
        extra_contradiction = ""
        z_final = z_base.copy()

        if best_sim >= config.SIM_THRESHOLD:
            z_adj, reasoning, extra = self._single_llm_call(
                indicators, z_base, sims, best_name, best_sim, second, fresh, sim_adj
            )
            z_final = z_adj
            llm_reasoning = reasoning
            extra_contradiction = extra

            # Rebuild phi_state con Z ajustado
            phi_state = self._rebuild_phi(z_final, indicators, phi_state.confidence)

        # --- PASO 5: Construir resultados compatibles con el pipeline ---
        iso_data = PHYSICAL_ISOMORPHS[best_name]

        omega_hyp = OmegaHypothesis(
            best_isomorph=best_name,
            similarity=best_sim,
            threshold_met=best_sim >= config.SIM_THRESHOLD,
            trading_signal=iso_data["trading_signal"],
            instruments=iso_data["instruments"],
            allocation_pct=iso_data["allocation_pct"],
            physical_description=iso_data["description"],
            market_analog=iso_data["market_analog"],
            all_similarities=sims,
            llm_reasoning=llm_reasoning,
            confidence=sim_adj,
            timestamp=datetime.now().isoformat(),
            z_market=z_final.tolist()
        )

        if best_sim < config.SIM_THRESHOLD:
            verdict, action, confirmed, contradicted = "LAMBDA_OFFLINE", "HOLD", False, False
        elif sim_adj >= self.SIM_CONFIRM:
            verdict, action, confirmed, contradicted = "CONFIRMED", "EXECUTE", True, False
        elif sim_adj < self.SIM_CONTRADICT:
            verdict, action, confirmed, contradicted = "CONTRADICTED", "BACKTRACK", False, True
        else:
            verdict, action, confirmed, contradicted = "UNCERTAIN", "DEFENSIVE", False, False

        all_contradictions = det_contradictions
        if extra_contradiction:
            all_contradictions.append(extra_contradiction)

        lambda_val = LambdaValidation(
            hypothesis_confirmed=confirmed,
            hypothesis_contradicted=contradicted,
            similarity=sim_adj,
            verdict=verdict,
            action=action,
            evidence=fresh,
            z_fresh=z_final.tolist(),
            z_reference=PHYSICAL_ISOMORPHS[best_name]["Z"].tolist(),
            additional_signals={
                "vix_change_5d":   fresh.get("vix_change_5d", 0.0),
                "momentum_5d_pct": fresh.get("spy_momentum_5d_pct", 0.0),
            },
            contradictions=all_contradictions,
            reasoning=llm_reasoning,
            api_sources_used=fresh.get("sources", []),
            api_failures=[],
            timestamp=datetime.now().isoformat(),
            validation_duration_seconds=round(time.time() - t0, 2)
        )

        logger.info(
            f"Unified: {best_name} Sim={best_sim:.4f}->adj={sim_adj:.4f} "
            f"{verdict} contradicciones={len(all_contradictions)}"
        )
        return phi_state, omega_hyp, lambda_val

    def _single_llm_call(self, indicators, z_base, sims, best_name,
                          best_sim, second, fresh, sim_adj):
        """
        LA llamada revolucionaria: hace el trabajo de Phi-LLM + Omega + Lambda-LLM
        en UN solo prompt compacto.

        Input (~180 tokens):
          - Datos de mercado en 1 linea
          - Z_base en 1 linea (8 numeros)
          - Top 2 isomorfos y sus similitudes
          - Penalizacion ya calculada y contradiciones deterministicas

        Output (~80 tokens):
          - Z_ajustado (8 numeros, ajuste semantico fino)
          - Confirmacion del isomorfo (o cambio si hay razon fuerte)
          - 1 contradiccion no obvia (o vacio)

        TOTAL: ~260 tokens vs 2112 anterior
        """
        iso = PHYSICAL_ISOMORPHS[best_name]
        vix_ch = fresh.get("vix_change_5d", 0.0)
        mom5d  = fresh.get("spy_momentum_5d_pct", 0.0)

        # Prompt minimo: contexto en 4 lineas, output en 1 JSON compacto
        prompt = (
            f"Cortex V2 unified analysis. Market: "
            f"VIX={indicators.get('vix')} Mom21d={indicators.get('momentum_21d_pct')}% "
            f"Vol={indicators.get('vol_realized_pct')}% DD={indicators.get('drawdown_90d_pct')}% "
            f"Reg={indicators.get('regime')} VIXch5d={vix_ch:+.1f} Mom5d={mom5d:+.1f}%\n"
            f"Z_base=[{','.join(f'{v:+.2f}' for v in z_base)}]\n"
            f"Best={best_name}(sim={best_sim:.3f}) 2nd={second[0]}({second[1]:.3f}) "
            f"sim_adj={sim_adj:.3f} (penalty={best_sim-sim_adj:+.3f})\n"
            f"Tasks: 1)Adjust Z if needed(sep>=0.18) "
            f"2)Confirm isomorph or change if strong reason "
            f"3)Any non-obvious structural contradiction?\n"
            f'JSON only: {{"Z":[z1,z2,z3,z4,z5,z6,z7,z8],"iso":"{best_name}","x":"contradiction or empty"}}'
        )

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=120,  # 8 floats + iso name + 1 frase = ~100 tokens
                temperature=0.1
            )
            token_tracker.add("unified", resp.usage.prompt_tokens, resp.usage.completion_tokens)

            raw  = resp.choices[0].message.content.strip().replace("```json","").replace("```","")
            s, e = raw.find("{"), raw.rfind("}")
            data = json.loads(raw[s:e+1]) if s != -1 else {}

            # Z ajustado
            z_list = data.get("Z", z_base.tolist())
            if isinstance(z_list, list) and len(z_list) == 8:
                z_adj = np.array([float(v) for v in z_list])
                z_adj = np.clip(z_adj, -1.0, 1.0)
                # Enforce separation minima
                z_adj = _enforce_separation(z_adj)
            else:
                z_adj = z_base.copy()

            # Isomorfo (puede cambiar si el LLM tiene razon fuerte)
            iso_result = data.get("iso", best_name)
            if iso_result not in PHYSICAL_ISOMORPHS:
                iso_result = best_name

            reasoning = f"{iso_result} Sim={sim_adj:.3f} (unified)"
            extra = str(data.get("x", "")).strip()
            if extra.lower() in ("", "none", "null", "empty", "ninguna", "no"):
                extra = ""

            logger.info(f"Unified LLM: iso={iso_result} Z_adj=[{','.join(f'{v:+.2f}' for v in z_adj)}] extra={extra[:60]}")
            return z_adj, reasoning, extra

        except Exception as e:
            logger.warning(f"Unified LLM fallback: {e}")
            return z_base.copy(), f"{best_name} Sim={sim_adj:.3f} (fallback)", ""

    def _rebuild_phi(self, z_final, indicators, confidence) -> PhiState:
        keys = ["Z1","Z2","Z3","Z4","Z5","Z6","Z7","Z8"]
        z_dict = {keys[i]: round(float(z_final[i]), 3) for i in range(8)}
        return PhiState(
            Z1_estructura=z_dict["Z1"], Z2_dinamica=z_dict["Z2"],
            Z3_escala=z_dict["Z3"],     Z4_causalidad=z_dict["Z4"],
            Z5_temporalidad=z_dict["Z5"],Z6_reversibilidad=z_dict["Z6"],
            Z7_valencia=z_dict["Z7"],   Z8_complejidad=z_dict["Z8"],
            regime=indicators.get("regime","INDETERMINATE"),
            confidence=confidence,
            raw_indicators=indicators
        )


def _enforce_separation(z: np.ndarray, min_sep: float = 0.18) -> np.ndarray:
    z = z.copy()
    for _ in range(20):
        changed = False
        for i in range(len(z)):
            for j in range(i+1, len(z)):
                diff = z[j] - z[i]
                if abs(diff) < min_sep:
                    push = (min_sep - abs(diff)) / 2.0 + 0.01
                    if diff >= 0: z[i] -= push; z[j] += push
                    else:         z[i] += push; z[j] -= push
                    z[i] = float(np.clip(z[i], -1.0, 1.0))
                    z[j] = float(np.clip(z[j], -1.0, 1.0))
                    changed = True
        if not changed:
            break
    return z
