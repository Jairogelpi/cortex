"""
CAPA OMEGA - Motor de hipotesis cross-domain
Cortex V2, Fase 3

Fundamentado en Bellmund et al. (Nature Neuroscience 2025).
Omega: (Z1 x ... x Z8)^n -> Z_nuevo donde Sim >= 0.65

Los 5 isomorfos fisicos:
    gas_expansion, compressed_gas, phase_transition,
    overdamped_system, lorenz_attractor

Modelo: Claude Opus 4.6 (UNA sola llamada por sesion).
"""
import json
import re
import numpy as np
from dataclasses import dataclass
from datetime import datetime
from openai import OpenAI
from loguru import logger

from cortex.config import config
from cortex.layers.phi import PhiState
from cortex.token_tracker import token_tracker  # H1: medicion real de tokens

PHYSICAL_ISOMORPHS = {
    "gas_expansion": {
        "description": "Gas ideal en expansion: presion baja, volumen creciente, energia libre",
        "market_analog": "Bull run sostenido (R1_EXPANSION)",
        "regime": "R1_EXPANSION",
        "Z": np.array([0.80, -0.40, -0.30, 0.70, 0.60, -0.70, 0.75, -0.65]),
        "trading_signal": "LONG",
        "instruments": ["SPY", "QQQ"],
        "allocation_pct": 0.80,
        "expected_duration_days": 30,
    },
    "compressed_gas": {
        "description": "Gas comprimido pre-expansion: energia latente acumulada, ruptura inminente",
        "market_analog": "Acumulacion pre-rally (R2_ACCUMULATION)",
        "regime": "R2_ACCUMULATION",
        "Z": np.array([0.10, 0.15, 0.20, 0.40, 0.30, 0.60, 0.15, -0.20]),
        "trading_signal": "LONG_PREPARE",
        "instruments": ["SPY", "IEF"],
        "allocation_pct": 0.50,
        "expected_duration_days": 15,
    },
    "phase_transition": {
        "description": "Transicion de fase: alta energia, cambio estructural en curso",
        "market_analog": "Cambio de regimen alta volatilidad (R3_TRANSITION)",
        "regime": "R3_TRANSITION",
        "Z": np.array([-0.30, 0.75, 0.65, -0.50, -0.20, 0.50, -0.25, 0.70]),
        "trading_signal": "DEFENSIVE",
        "instruments": ["IEF", "TLT"],
        "allocation_pct": 0.30,
        "expected_duration_days": 7,
    },
    "overdamped_system": {
        "description": "Sistema sobre-amortiguado: retorno lento al equilibrio sin oscilacion",
        "market_analog": "Reversion lenta a la media",
        "regime": "R2_ACCUMULATION",
        "Z": np.array([-0.20, 0.10, 0.15, -0.10, -0.30, 0.80, -0.15, 0.10]),
        "trading_signal": "MEAN_REVERSION",
        "instruments": ["SPY"],
        "allocation_pct": 0.40,
        "expected_duration_days": 10,
    },
    "lorenz_attractor": {
        "description": "Atractor de Lorenz: caos determinista, impredecible a corto plazo",
        "market_analog": "Regimen caotico impredecible (R4_CONTRACTION)",
        "regime": "R4_CONTRACTION",
        "Z": np.array([-0.65, 0.85, 0.80, -0.75, -0.55, 0.30, -0.60, 0.90]),
        "trading_signal": "CASH",
        "instruments": [],
        "allocation_pct": 0.00,
        "expected_duration_days": 5,
    },
}


@dataclass
class OmegaHypothesis:
    best_isomorph: str
    similarity: float
    threshold_met: bool
    trading_signal: str
    instruments: list
    allocation_pct: float
    physical_description: str
    market_analog: str
    all_similarities: dict
    llm_reasoning: str
    confidence: float
    timestamp: str
    z_market: list

    def summary(self) -> str:
        lines = [
            f"Omega Hypothesis | Isomorfo: {self.best_isomorph} | Sim={self.similarity:.4f}",
            f"  Umbral 0.65: {self.threshold_met} | Senal: {self.trading_signal}",
            f"  Instrumentos: {self.instruments if self.instruments else 'ninguno (CASH)'}",
            f"  Asignacion: {self.allocation_pct*100:.0f}% | Confianza: {self.confidence:.4f}",
            "",
            "  Similitudes:",
        ]
        for name, sim in sorted(self.all_similarities.items(), key=lambda x: -x[1]):
            marker = " <- ELEGIDO" if name == self.best_isomorph else ""
            lines.append(f"    {name:<25} {sim:.4f}{marker}")
        lines.append(f"\n  Razonamiento: {self.llm_reasoning}")
        return "\n".join(lines)


class OmegaLayer:
    SIM_THRESHOLD = config.SIM_THRESHOLD

    def __init__(self):
        self.client = OpenAI(
            api_key=config.OPENROUTER_API_KEY,
            base_url=config.OPENROUTER_BASE_URL,
            timeout=config.OPENROUTER_TIMEOUT_SECONDS,
            max_retries=config.OPENROUTER_MAX_RETRIES,
        )
        self.model = config.MODEL_OMEGA
        logger.info(
            f"Capa Omega inicializada: {self.model} "
            f"(timeout={config.OPENROUTER_TIMEOUT_SECONDS}s)"
        )

    def generate_hypothesis(self, phi_state: PhiState) -> OmegaHypothesis:
        z_market    = phi_state.to_vector()
        similarities = self._calc_similarities(z_market)
        best_name   = max(similarities, key=similarities.get)
        best_sim    = similarities[best_name]
        threshold   = best_sim >= self.SIM_THRESHOLD

        logger.info(f"Omega similitudes: {best_name}={best_sim:.4f} (umbral={'OK' if threshold else 'NO'})")

        if threshold:
            return self._generate_with_opus(phi_state, z_market, best_name, best_sim, similarities)
        return self._defensive_hypothesis(phi_state, z_market, best_name, best_sim, similarities)

    def _calc_similarities(self, z_market: np.ndarray) -> dict:
        norm_m = np.linalg.norm(z_market)
        if norm_m == 0:
            return {n: 0.0 for n in PHYSICAL_ISOMORPHS}
        sims = {}
        for name, iso in PHYSICAL_ISOMORPHS.items():
            z_ref   = iso["Z"]
            norm_r  = np.linalg.norm(z_ref)
            cosine  = float(np.dot(z_market, z_ref) / (norm_m * norm_r)) if norm_r else 0.0
            sims[name] = round((cosine + 1.0) / 2.0, 4)
        return sims

    def _extract_json(self, text: str) -> dict:
        text = text.replace("```json","").replace("```","").strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        s, e = text.find("{"), text.rfind("}")
        if s != -1 and e > s:
            try:
                return json.loads(text[s:e+1])
            except json.JSONDecodeError:
                pass
        m = re.search(r'"reasoning"\s*:\s*"(.*?)"(?=\s*[,}])', text, re.DOTALL)
        if m:
            cm = re.search(r'"confidence_adjustment"\s*:\s*([-\d.]+)', text)
            rm = re.search(r'"risk_note"\s*:\s*"(.*?)"(?=\s*[,}])', text, re.DOTALL)
            return {
                "reasoning": m.group(1),
                "confidence_adjustment": float(cm.group(1)) if cm else 0.0,
                "risk_note": rm.group(1) if rm else ""
            }
        raise ValueError(f"No se pudo extraer JSON: {text[:200]}")

    def _generate_with_opus(self, phi_state, z_market, best_name, best_sim, similarities):
        iso = PHYSICAL_ISOMORPHS[best_name]
        ind = phi_state.raw_indicators

        prompt = f"""Eres la capa Omega de Cortex V2 (Bellmund et al. NatNeurosci 2025).

ESTADO DEL MERCADO (vector Z):
Z1={z_market[0]:+.3f} Z2={z_market[1]:+.3f} Z3={z_market[2]:+.3f} Z4={z_market[3]:+.3f}
Z5={z_market[4]:+.3f} Z6={z_market[5]:+.3f} Z7={z_market[6]:+.3f} Z8={z_market[7]:+.3f}
VIX={ind.get('vix')} | Mom21d={ind.get('momentum_21d_pct')}% | Regimen={phi_state.regime}

ISOMORFO MEJOR (Sim={best_sim:.4f}): {best_name}
Descripcion: {iso['description']}
Z referencia: {iso['Z'].tolist()}

Similitudes: {', '.join(f'{n}={s:.3f}' for n,s in sorted(similarities.items(), key=lambda x: -x[1]))}

Explica en 2-3 frases por que el mercado es isomorfo a {best_name}.
Responde SOLO JSON:
{{"reasoning":"2-3 frases","confidence_adjustment":0.0,"risk_note":"riesgo de confabulacion"}}"""

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.1
            )
            # H1: registrar tokens reales de Omega (llamada mas costosa — Opus)
            token_tracker.add("omega", resp.usage.prompt_tokens, resp.usage.completion_tokens)

            raw  = resp.choices[0].message.content
            logger.debug(f"Opus raw response: {raw[:300]}")
            data = self._extract_json(raw)

            reasoning      = data.get("reasoning", "Sin razonamiento")
            confidence_adj = float(data.get("confidence_adjustment", 0.0))
            risk_note      = data.get("risk_note", "")
            confidence     = max(0.0, min(1.0, best_sim + confidence_adj))

            logger.info(f"Omega Opus: {reasoning[:120]}...")
            if risk_note:
                logger.warning(f"Omega riesgo: {risk_note}")

            return OmegaHypothesis(
                best_isomorph=best_name, similarity=best_sim,
                threshold_met=True,
                trading_signal=iso["trading_signal"],
                instruments=iso["instruments"],
                allocation_pct=iso["allocation_pct"],
                physical_description=iso["description"],
                market_analog=iso["market_analog"],
                all_similarities=similarities,
                llm_reasoning=reasoning + (f" | RIESGO: {risk_note}" if risk_note else ""),
                confidence=confidence,
                timestamp=datetime.now().isoformat(),
                z_market=z_market.tolist()
            )
        except Exception as e:
            logger.warning(f"Omega Opus fallback: {e}")
            return OmegaHypothesis(
                best_isomorph=best_name, similarity=best_sim,
                threshold_met=True,
                trading_signal=iso["trading_signal"],
                instruments=iso["instruments"],
                allocation_pct=iso["allocation_pct"],
                physical_description=iso["description"],
                market_analog=iso["market_analog"],
                all_similarities=similarities,
                llm_reasoning=f"Fallback determinista ({str(e)[:60]}). Sim={best_sim:.4f}.",
                confidence=round(best_sim * 0.8, 4),
                timestamp=datetime.now().isoformat(),
                z_market=z_market.tolist()
            )

    def _defensive_hypothesis(self, phi_state, z_market, best_name, best_sim, similarities):
        logger.warning(f"Omega: ningun isomorfo >= 0.65. Mejor: {best_name}={best_sim:.4f}. DEFENSIVO.")
        return OmegaHypothesis(
            best_isomorph=best_name, similarity=best_sim,
            threshold_met=False,
            trading_signal="CASH", instruments=[], allocation_pct=0.0,
            physical_description="Ningun isomorfo con similitud suficiente",
            market_analog="Regimen sin precedente en los 5 isomorfos",
            all_similarities=similarities,
            llm_reasoning=f"Ningun isomorfo >= {self.SIM_THRESHOLD}. Modo defensivo (Seccion 6.3).",
            confidence=0.0,
            timestamp=datetime.now().isoformat(),
            z_market=z_market.tolist()
        )


def test_omega():
    from cortex.market_data import MarketData
    from cortex.layers.phi import PhiLayer
    md    = MarketData()
    phi   = PhiLayer()
    omega = OmegaLayer()
    hyp   = omega.generate_hypothesis(phi.factorize(md.get_regime_indicators()))
    print(hyp.summary())
    return hyp

if __name__ == "__main__":
    test_omega()
