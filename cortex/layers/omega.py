"""
CAPA OMEGA - Motor de hipotesis cross-domain — VERSION OPTIMIZADA H1
Cortex V2, Fase 3

OPTIMIZACION H1:
  Prompt comprimido: eliminados campos redundantes (Z referencia,
  descripcion larga, analogia). Omega ya sabe el isomorfo por similitud
  coseno — el LLM solo necesita confirmar con 1 frase.
  max_tokens: 500 -> 60 (solo 1 frase de razonamiento + confidence_adj)
  Sin campo risk_note — ya esta en el log de warning de similitudes.
  Estimacion ahorro: 722 -> ~250 tokens.
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
from cortex.token_tracker import token_tracker

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
            f"Omega | {self.best_isomorph} Sim={self.similarity:.4f} -> {self.trading_signal}",
            "  Sims: " + " ".join(f"{n[:8]}={s:.3f}" for n,s in
                sorted(self.all_similarities.items(), key=lambda x:-x[1])),
            f"  {self.llm_reasoning}",
        ]
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
        logger.info(f"Capa Omega inicializada: {self.model}")

    def generate_hypothesis(self, phi_state: PhiState) -> OmegaHypothesis:
        z_market     = phi_state.to_vector()
        similarities = self._calc_similarities(z_market)
        best_name    = max(similarities, key=similarities.get)
        best_sim     = similarities[best_name]
        threshold    = best_sim >= self.SIM_THRESHOLD

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
            z_ref  = iso["Z"]
            norm_r = np.linalg.norm(z_ref)
            cos    = float(np.dot(z_market, z_ref)/(norm_m*norm_r)) if norm_r else 0.0
            sims[name] = round((cos+1.0)/2.0, 4)
        return sims

    def _generate_with_opus(self, phi_state, z_market, best_name, best_sim, similarities):
        iso = PHYSICAL_ISOMORPHS[best_name]
        ind = phi_state.raw_indicators

        # PROMPT ULTRACOMPACTO: solo los datos que Opus necesita para confirmar
        # Eliminado: Z referencia (Opus lo sabe), descripcion larga, risk_note
        # El campo reasoning es 1 frase, no 2-3
        prompt = (
            f"Omega Cortex V2. Isomorfo={best_name} Sim={best_sim:.3f}. "
            f"Z=[{','.join(f'{v:+.2f}' for v in z_market)}] "
            f"VIX={ind.get('vix')} Mom={ind.get('momentum_21d_pct')}% Reg={phi_state.regime}\n"
            f"2do mejor: {sorted(similarities.items(),key=lambda x:-x[1])[1][0]}="
            f"{sorted(similarities.items(),key=lambda x:-x[1])[1][1]:.3f}\n"
            f'Solo JSON: {{"r":"1 frase por que isomorfo correcto","c":0.0}}'
        )
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=60,   # OPTIMIZACION: 500 -> 60 (1 frase + c float)
                temperature=0.1
            )
            token_tracker.add("omega", resp.usage.prompt_tokens, resp.usage.completion_tokens)

            raw  = resp.choices[0].message.content.strip().replace("```json","").replace("```","")
            s,e  = raw.find("{"), raw.rfind("}")
            data = json.loads(raw[s:e+1]) if s!=-1 else {}

            reasoning = data.get("r", data.get("reasoning", best_name))
            conf_adj  = float(data.get("c", data.get("confidence_adjustment", 0.0)))
            confidence = max(0.0, min(1.0, best_sim + conf_adj))

            logger.info(f"Omega Opus: {reasoning[:80]}")
            return OmegaHypothesis(
                best_isomorph=best_name, similarity=best_sim,
                threshold_met=True,
                trading_signal=iso["trading_signal"],
                instruments=iso["instruments"],
                allocation_pct=iso["allocation_pct"],
                physical_description=iso["description"],
                market_analog=iso["market_analog"],
                all_similarities=similarities,
                llm_reasoning=reasoning,
                confidence=confidence,
                timestamp=datetime.now().isoformat(),
                z_market=z_market.tolist()
            )
        except Exception as e:
            logger.warning(f"Omega fallback: {e}")
            return OmegaHypothesis(
                best_isomorph=best_name, similarity=best_sim,
                threshold_met=True,
                trading_signal=iso["trading_signal"],
                instruments=iso["instruments"],
                allocation_pct=iso["allocation_pct"],
                physical_description=iso["description"],
                market_analog=iso["market_analog"],
                all_similarities=similarities,
                llm_reasoning=f"Sim={best_sim:.4f} (fallback)",
                confidence=round(best_sim*0.8, 4),
                timestamp=datetime.now().isoformat(),
                z_market=z_market.tolist()
            )

    def _defensive_hypothesis(self, phi_state, z_market, best_name, best_sim, similarities):
        logger.warning(f"Omega: ningun isomorfo >= {self.SIM_THRESHOLD}. Mejor={best_name}={best_sim:.4f}")
        return OmegaHypothesis(
            best_isomorph=best_name, similarity=best_sim,
            threshold_met=False, trading_signal="CASH",
            instruments=[], allocation_pct=0.0,
            physical_description="Ningun isomorfo suficiente",
            market_analog="Regimen sin precedente",
            all_similarities=similarities,
            llm_reasoning=f"Sim<{self.SIM_THRESHOLD}. Modo defensivo.",
            confidence=0.0,
            timestamp=datetime.now().isoformat(),
            z_market=z_market.tolist()
        )

if __name__ == "__main__":
    from cortex.market_data import MarketData
    from cortex.layers.phi import PhiLayer
    md = MarketData()
    hyp = OmegaLayer().generate_hypothesis(PhiLayer().factorize(md.get_regime_indicators()))
    print(hyp.summary())
