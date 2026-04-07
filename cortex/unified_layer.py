"""
CORTEX UNIFIED LAYER — Phi + Omega + Lambda con ruta adaptativa
Cortex V2 | OSF: https://osf.io/wdkcx

REVOLUCION H1:
    Antes: 3 llamadas LLM separadas (Phi=460, Omega=722, Lambda=930 = 2112 tokens)
    Ahora: 0-1 llamada LLM compacta, solo si hay ambiguedad real.

    Con los umbrales optimizados (HIGH_SIM=0.86, GAP_MIN=0.03):
    - Dias claros (sim>0.86 y gap>0.03): 0 tokens LLM
    - Dias ambiguos: revision telegrama ~75 tokens

    H1 esperada:
    - Dias claros:  A=0 / B=400 -> ratio=0.0x (PASS)
    - Dias ambiguos: A~75 / B=400 -> ratio=0.19x (PASS)
    - Media esperada: <<0.45x (objetivo pre-registrado)
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


def _deterministic_penalties(fresh: dict, best_name: str) -> Tuple[float, list]:
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


class UnifiedLayer:
    SIM_CONFIRM      = 0.65
    SIM_CONTRADICT   = 0.40
    REVIEW_SIM_MIN   = config.UNIFIED_REVIEW_SIM_MIN    # 0.65
    REVIEW_HIGH_SIM  = config.UNIFIED_REVIEW_HIGH_SIM   # 0.86 (optimizado)
    REVIEW_GAP_MIN   = config.UNIFIED_REVIEW_GAP_MIN    # 0.03 (optimizado)
    REVIEW_MAX_TOKENS = config.UNIFIED_REVIEW_MAX_TOKENS # 20
    PROJECT_BLEND_MIN = config.UNIFIED_PROJECT_BLEND_MIN
    PROJECT_BLEND_MAX = config.UNIFIED_PROJECT_BLEND_MAX

    def __init__(self):
        self.client = OpenAI(
            api_key=config.OPENROUTER_API_KEY,
            base_url=config.OPENROUTER_BASE_URL,
            timeout=config.OPENROUTER_TIMEOUT_SECONDS,
            max_retries=config.OPENROUTER_MAX_RETRIES,
        )
        self.model = config.MODEL_PHI
        logger.info(f"UnifiedLayer: {self.model} (HIGH_SIM={self.REVIEW_HIGH_SIM} GAP_MIN={self.REVIEW_GAP_MIN})")

    def _calc_similarities(self, z_market: np.ndarray) -> dict:
        norm_m = np.linalg.norm(z_market)
        if norm_m == 0:
            return {n: 0.0 for n in PHYSICAL_ISOMORPHS}
        sims = {}
        for name, iso in PHYSICAL_ISOMORPHS.items():
            z_ref  = iso["Z"]
            norm_r = np.linalg.norm(z_ref)
            cos    = float(np.dot(z_market, z_ref) / (norm_m * norm_r)) if norm_r else 0.0
            sims[name] = round((cos + 1.0) / 2.0, 4)
        return sims

    def _needs_llm_review(self, best_sim, gap, penalty, contradictions) -> bool:
        """
        Decide si hace falta revision LLM.
        Con HIGH_SIM=0.86 y GAP_MIN=0.03:
          - R1_EXPANSION (gas_expansion, sim~0.92, gap~0.15): camino rapido
          - Lorenz claro (sim~0.96, gap~0.05): camino rapido
          - Frontera gas/lorenz (gap<0.03): revision
          - INDETERMINATE con 2+ contradicciones: revision
        """
        if not config.UNIFIED_REVIEW_ENABLED:
            return False
        if best_sim < self.REVIEW_SIM_MIN:
            return False
        # Camino rapido: senal clara y sin conflicto
        if (best_sim >= self.REVIEW_HIGH_SIM
                and gap >= self.REVIEW_GAP_MIN
                and penalty < 0.12
                and len(contradictions) <= 1):
            return False
        # Revision: gap pequeno o conflicto real
        return gap < self.REVIEW_GAP_MIN or len(contradictions) >= 2 or penalty >= 0.15

    def _compact_market_snapshot(self, indicators: dict, fresh: dict) -> str:
        return (
            f"V={float(indicators.get('vix',0.0)):.1f} "
            f"M21={float(indicators.get('momentum_21d_pct',0.0)):+.1f} "
            f"R={indicators.get('regime','IND')} "
            f"V5={float(fresh.get('vix_change_5d',0.0)):+.1f} "
            f"M5={float(fresh.get('spy_momentum_5d_pct',0.0)):+.1f}"
        )

    def _compact_z_deltas(self, z_base: np.ndarray, target_name: str) -> str:
        z_ref  = PHYSICAL_ISOMORPHS[target_name]["Z"]
        diff   = z_base - z_ref
        labels = ["Z1","Z2","Z3","Z4","Z5","Z6","Z7","Z8"]
        top2   = sorted(zip(labels, diff.tolist()), key=lambda x: -abs(x[1]))[:2]
        return " ".join(f"{n}={v:+.2f}" for n, v in top2)

    def _projection_strength(self, best_sim, gap, review_needed) -> float:
        sim_term = max(0.0, min(1.0,
            (best_sim - self.REVIEW_SIM_MIN) / max(self.REVIEW_HIGH_SIM - self.REVIEW_SIM_MIN, 1e-6)))
        gap_term = max(0.0, min(1.0, gap / max(self.REVIEW_GAP_MIN, 1e-6)))
        blend = self.PROJECT_BLEND_MIN + 0.08*sim_term + 0.04*gap_term
        if review_needed:
            blend += 0.04
        return max(self.PROJECT_BLEND_MIN, min(self.PROJECT_BLEND_MAX, blend))

    def _project_vector(self, z_base, target_name, best_sim, gap, review_needed) -> np.ndarray:
        target = PHYSICAL_ISOMORPHS[target_name]["Z"]
        blend  = self._projection_strength(best_sim, gap, review_needed)
        z_proj = (1.0 - blend) * z_base + blend * target
        return _enforce_separation(np.clip(z_proj, -1.0, 1.0))

    def _normalize_review_iso(self, iso_name: str, fallback: str) -> str:
        candidate = str(iso_name or "").strip()
        if candidate.lower() in {"","same","keep","best","top1","null","none","empty"}:
            return fallback
        return candidate if candidate in PHYSICAL_ISOMORPHS else fallback

    def _single_llm_review(self, indicators, z_base, best_name, best_sim,
                            second_name, second_sim, sim_adj, fresh, gap, penalty):
        """
        Revision LLM minima — prompt telegrama, 0 JSON template.
        Input: ~55 tokens. Output: max 20 tokens. Total: ~75 tokens.
        Potencia preservada: el LLM puede cambiar el isomorfo si detecta algo real.
        """
        snapshot = self._compact_market_snapshot(indicators, fresh)
        z_deltas = self._compact_z_deltas(z_base, best_name)

        # Prompt telegrama: sin JSON template, sin ejemplos, formato libre
        # El modelo responde "same" o nombre del isomorfo + opcional 1 palabra
        prompt = (
            f"top={best_name}({best_sim:.2f}) 2nd={second_name}({second_sim:.2f}) "
            f"gap={gap:.2f} pen={penalty:+.2f} {snapshot} dZ={z_deltas} "
            f"iso? extra?"
        )

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.REVIEW_MAX_TOKENS,
                temperature=0.0
            )
            token_tracker.add("unified", resp.usage.prompt_tokens, resp.usage.completion_tokens)

            raw = resp.choices[0].message.content.strip()
            logger.info(f"Unified review raw: '{raw[:60]}'")

            # Parse flexible: JSON o texto libre
            iso_result    = best_name
            contradiction = ""

            s = raw.find("{"); e = raw.rfind("}")
            if s != -1 and e > s:
                try:
                    data = json.loads(raw[s:e+1])
                    iso_result    = self._normalize_review_iso(data.get("iso","same"), best_name)
                    contradiction = str(data.get("x","")).strip()
                except Exception:
                    pass
            else:
                # Texto libre: primera palabra = isomorfo o "same"
                parts = raw.split(None, 1)
                if parts:
                    iso_result = self._normalize_review_iso(parts[0].strip(".,;:"), best_name)
                if len(parts) > 1:
                    contradiction = parts[1].strip()[:60]

            if contradiction.lower() in ("","none","null","-","no","ninguna"):
                contradiction = ""

            logger.info(f"Unified review: iso={iso_result} x='{contradiction[:40]}'")
            return {"iso": iso_result, "contradiction": contradiction}

        except Exception as e:
            logger.warning(f"Unified review fallback: {e}")
            return {"iso": best_name, "contradiction": ""}

    def _rebuild_phi(self, z_final, indicators, confidence) -> PhiState:
        keys = ["Z1","Z2","Z3","Z4","Z5","Z6","Z7","Z8"]
        z_d  = {keys[i]: round(float(z_final[i]),3) for i in range(8)}
        return PhiState(
            Z1_estructura=z_d["Z1"], Z2_dinamica=z_d["Z2"],
            Z3_escala=z_d["Z3"],     Z4_causalidad=z_d["Z4"],
            Z5_temporalidad=z_d["Z5"],Z6_reversibilidad=z_d["Z6"],
            Z7_valencia=z_d["Z7"],   Z8_complejidad=z_d["Z8"],
            regime=indicators.get("regime","INDETERMINATE"),
            confidence=confidence,
            raw_indicators=indicators
        )

    def run(self, indicators: dict, fresh: dict
            ) -> Tuple[PhiState, OmegaHypothesis, LambdaValidation]:
        t0 = time.time()

        # Paso 1: Phi deterministico (0 tokens)
        phi_state = PhiLayer(temperature=0.0).factorize(indicators)
        z_base    = phi_state.to_vector()

        # Paso 2: Similitudes coseno (0 tokens)
        sims        = self._calc_similarities(z_base)
        best_name   = max(sims, key=sims.get)
        best_sim    = sims[best_name]
        second_name, second_sim = sorted(sims.items(), key=lambda x: -x[1])[1]

        # Paso 3: Penalizaciones deterministicas (0 tokens)
        penalty, det_contradictions = _deterministic_penalties(fresh, best_name)
        sim_adj = round(max(0.0, min(1.0, best_sim - penalty)), 4)
        gap     = round(best_sim - second_sim, 4)

        # Paso 4: Ruta adaptativa
        review_needed = self._needs_llm_review(best_sim, gap, penalty, det_contradictions)
        target_name       = best_name
        extra_contradiction = ""

        if review_needed:
            review = self._single_llm_review(
                indicators, z_base, best_name, best_sim,
                second_name, second_sim, sim_adj, fresh, gap, penalty
            )
            target_name         = review["iso"]
            extra_contradiction = review["contradiction"]
            logger.info(f"Unified: LLM review activado (gap={gap:.3f} pen={penalty:+.3f} contra={len(det_contradictions)})")
        else:
            logger.info(f"Unified: camino rapido (gap={gap:.3f} sim={best_sim:.3f} contra={len(det_contradictions)})")

        # Paso 5: Vector final y resultados
        z_final   = self._project_vector(z_base, target_name, best_sim, gap, review_needed)
        phi_state = self._rebuild_phi(z_final, indicators, phi_state.confidence)

        final_sims  = self._calc_similarities(z_final)
        best_name   = max(final_sims, key=final_sims.get)
        best_sim    = final_sims[best_name]
        second_name, second_sim = sorted(final_sims.items(), key=lambda x: -x[1])[1]
        penalty, det_contradictions = _deterministic_penalties(fresh, best_name)
        sim_adj     = round(max(0.0, min(1.0, best_sim - penalty)), 4)

        iso_data = PHYSICAL_ISOMORPHS[best_name]

        omega_hyp = OmegaHypothesis(
            best_isomorph=best_name, similarity=best_sim,
            threshold_met=best_sim >= config.SIM_THRESHOLD,
            trading_signal=iso_data["trading_signal"],
            instruments=iso_data["instruments"],
            allocation_pct=iso_data["allocation_pct"],
            physical_description=iso_data["description"],
            market_analog=iso_data["market_analog"],
            all_similarities=final_sims,
            llm_reasoning=f"{best_name} Sim={sim_adj:.3f} {'(review)' if review_needed else '(fast)'}",
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

        all_contradictions = det_contradictions[:]
        if extra_contradiction:
            all_contradictions.append(extra_contradiction)

        lambda_val = LambdaValidation(
            hypothesis_confirmed=confirmed, hypothesis_contradicted=contradicted,
            similarity=sim_adj, verdict=verdict, action=action,
            evidence=fresh,
            z_fresh=z_final.tolist(),
            z_reference=PHYSICAL_ISOMORPHS[best_name]["Z"].tolist(),
            additional_signals={
                "vix_change_5d":   fresh.get("vix_change_5d", 0.0),
                "momentum_5d_pct": fresh.get("spy_momentum_5d_pct", 0.0),
            },
            contradictions=all_contradictions,
            reasoning=omega_hyp.llm_reasoning,
            api_sources_used=fresh.get("sources", []),
            api_failures=[],
            timestamp=datetime.now().isoformat(),
            validation_duration_seconds=round(time.time() - t0, 2)
        )

        tok = token_tracker.total()
        logger.info(
            f"Unified done: {best_name} Sim={best_sim:.4f} adj={sim_adj:.4f} "
            f"{verdict} tokens={tok} {'LLM' if review_needed else 'FAST'}"
        )
        return phi_state, omega_hyp, lambda_val
