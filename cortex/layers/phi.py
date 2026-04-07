"""
CAPA PHI - Factorizador de estado — VERSION OPTIMIZADA H1
Cortex V2, Fase 1

OPTIMIZACION H1:
  Prompt reducido al minimo funcional.
  max_tokens: 300 -> 80 (solo necesitamos 8 floats en JSON)
  Sin campo "reasoning" en el output — no aporta a la decision.
  Estimacion ahorro: 460 -> ~200 tokens.

El valor de Phi es la factorizacion Z, no la explicacion de por que.
"""
import json
import numpy as np
from dataclasses import dataclass
from openai import OpenAI
from loguru import logger

from cortex.config import config
from cortex.token_tracker import token_tracker


@dataclass
class PhiState:
    Z1_estructura: float
    Z2_dinamica: float
    Z3_escala: float
    Z4_causalidad: float
    Z5_temporalidad: float
    Z6_reversibilidad: float
    Z7_valencia: float
    Z8_complejidad: float
    regime: str
    confidence: float
    raw_indicators: dict

    def to_vector(self) -> np.ndarray:
        return np.array([
            self.Z1_estructura, self.Z2_dinamica, self.Z3_escala,
            self.Z4_causalidad, self.Z5_temporalidad, self.Z6_reversibilidad,
            self.Z7_valencia, self.Z8_complejidad
        ])

    def check_orthogonality(self, threshold: float = 0.15) -> dict:
        z = self.to_vector()
        pairs = [(i+1,j+1,round(abs(z[i]-z[j]),4))
                 for i in range(len(z)) for j in range(i+1,len(z))
                 if abs(z[i]-z[j]) < threshold]
        return {
            "orthogonality_ok": len(pairs) == 0,
            "pairs_too_similar": pairs,
            "z_variance": round(float(np.var(z)), 4),
            "z_spread":   round(float(np.max(z) - np.min(z)), 4)
        }

    def summary(self) -> str:
        orth = self.check_orthogonality()
        return (
            f"Phi | {self.regime} conf={self.confidence:.2f} "
            f"Z=[{','.join(f'{v:+.2f}' for v in self.to_vector())}] "
            f"orth={'OK' if orth['orthogonality_ok'] else 'REVISAR'}"
        )


class PhiLayer:
    MIN_SEPARATION = 0.18

    def __init__(self, temperature: float = 0.1):
        self.client = OpenAI(
            api_key=config.OPENROUTER_API_KEY,
            base_url=config.OPENROUTER_BASE_URL,
            timeout=config.OPENROUTER_TIMEOUT_SECONDS,
            max_retries=config.OPENROUTER_MAX_RETRIES,
        )
        self.model       = config.MODEL_PHI
        self.temperature = temperature
        logger.info(f"Capa Phi inicializada: {self.model} (temperature={temperature})")

    def factorize(self, indicators: dict) -> PhiState:
        base      = self._factorize_deterministic(indicators)
        refined   = self._refine_with_llm(indicators, base)
        separated = self._enforce_separation(refined)
        state     = self._build_state(separated, indicators, base["confidence"])
        logger.info(f"Phi: regimen={state.regime}, confianza={state.confidence:.2f}, var={np.var(state.to_vector()):.4f}")
        return state

    def _factorize_deterministic(self, ind: dict) -> dict:
        vix      = ind.get("vix", 20.0)
        momentum = ind.get("momentum_21d_pct", 0.0)
        vol      = ind.get("vol_realized_pct", 15.0)
        drawdown = ind.get("drawdown_90d_pct", 0.0)
        regime   = ind.get("regime", "INDETERMINATE")

        z1 = float(np.clip(momentum / 8.0, -1, 1))
        z2 = float(np.clip((vix - 20.0) / 22.0, -1, 1))
        z3 = float(np.clip((vol - 12.0) / 18.0, -1, 1))
        sign_mom = np.sign(momentum) if abs(momentum) > 0.5 else 0
        z4 = float(np.clip(sign_mom * (vol / 25.0), -1, 1))
        z5 = float(np.clip(drawdown / -35.0, -1, 1))
        if vix > 35:    z6 = 0.85
        elif vix > 28:  z6 = 0.45
        elif vix > 22:  z6 = 0.10
        elif vix < 14:  z6 = -0.65
        else:           z6 = -0.20
        z7 = float(np.clip(
            0.45*(momentum/8.0)+0.30*(drawdown/-35.0)+0.25*(-(vix-20.0)/22.0), -1, 1))
        z8 = {"R1_EXPANSION":-0.70,"R2_ACCUMULATION":-0.25,
              "R4_CONTRACTION":+0.40,"R3_TRANSITION":+0.72,"INDETERMINATE":+0.92}.get(regime,0.92)
        conf = {"R1_EXPANSION":0.85,"R2_ACCUMULATION":0.75,
                "R3_TRANSITION":0.70,"R4_CONTRACTION":0.75,"INDETERMINATE":0.45}.get(regime,0.45)
        return {"Z1":round(z1,3),"Z2":round(z2,3),"Z3":round(z3,3),"Z4":round(z4,3),
                "Z5":round(z5,3),"Z6":round(z6,3),"Z7":round(z7,3),"Z8":round(z8,3),
                "confidence":conf}

    def _refine_with_llm(self, indicators: dict, base: dict) -> dict:
        if self.temperature == 0.0:
            logger.debug("Phi LLM omitido: temperature=0.0")
            return {k: base[k] for k in ["Z1","Z2","Z3","Z4","Z5","Z6","Z7","Z8"]}

        # PROMPT ULTRACOMPACTO: solo datos esenciales, JSON de 8 numeros, sin razonamiento
        prompt = (
            f"Phi Cortex V2. Ajusta Z1-Z8 en [-1,1] segun mercado. "
            f"VIX={indicators.get('vix')} Mom={indicators.get('momentum_21d_pct')}% "
            f"Vol={indicators.get('vol_realized_pct')}% DD={indicators.get('drawdown_90d_pct')}% "
            f"Reg={indicators.get('regime')}\n"
            f"Base: Z1={base['Z1']} Z2={base['Z2']} Z3={base['Z3']} Z4={base['Z4']} "
            f"Z5={base['Z5']} Z6={base['Z6']} Z7={base['Z7']} Z8={base['Z8']}\n"
            f"Cada Zi separado >=0.18. Solo JSON: "
            f'{{"Z1":0.0,"Z2":0.0,"Z3":0.0,"Z4":0.0,"Z5":0.0,"Z6":0.0,"Z7":0.0,"Z8":0.0}}'
        )
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=80,   # OPTIMIZACION: 300 -> 80 (solo 8 floats en JSON ~60 tokens)
                temperature=self.temperature
            )
            token_tracker.add("phi", resp.usage.prompt_tokens, resp.usage.completion_tokens)
            raw  = resp.choices[0].message.content.strip().replace("```json","").replace("```","")
            s,e  = raw.find("{"), raw.rfind("}")
            data = json.loads(raw[s:e+1]) if s!=-1 else {}
            logger.info(f"Phi LLM: Z=[{','.join(f'{float(data.get(k,base[k])):+.2f}' for k in ['Z1','Z2','Z3','Z4','Z5','Z6','Z7','Z8'])}]")
            return {k: float(data.get(k, base[k])) for k in ["Z1","Z2","Z3","Z4","Z5","Z6","Z7","Z8"]}
        except Exception as e:
            logger.warning(f"Phi LLM fallback: {e}")
            return {k: base[k] for k in ["Z1","Z2","Z3","Z4","Z5","Z6","Z7","Z8"]}

    def _enforce_separation(self, z_dict: dict) -> dict:
        keys = ["Z1","Z2","Z3","Z4","Z5","Z6","Z7","Z8"]
        z    = np.array([z_dict[k] for k in keys])
        for _ in range(20):
            changed = False
            for i in range(len(z)):
                for j in range(i+1, len(z)):
                    diff = z[j] - z[i]
                    if abs(diff) < self.MIN_SEPARATION:
                        push = (self.MIN_SEPARATION - abs(diff)) / 2.0 + 0.01
                        if diff >= 0: z[i] -= push; z[j] += push
                        else:         z[i] += push; z[j] -= push
                        z[i] = float(np.clip(z[i], -1.0, 1.0))
                        z[j] = float(np.clip(z[j], -1.0, 1.0))
                        changed = True
            if not changed:
                break
        return {keys[i]: round(float(z[i]),3) for i in range(len(keys))}

    def _build_state(self, z, indicators, confidence):
        return PhiState(
            Z1_estructura=z["Z1"], Z2_dinamica=z["Z2"],
            Z3_escala=z["Z3"],     Z4_causalidad=z["Z4"],
            Z5_temporalidad=z["Z5"],Z6_reversibilidad=z["Z6"],
            Z7_valencia=z["Z7"],   Z8_complejidad=z["Z8"],
            regime=indicators.get("regime","INDETERMINATE"),
            confidence=confidence,
            raw_indicators=indicators
        )

if __name__ == "__main__":
    from cortex.market_data import MarketData
    md = MarketData()
    phi = PhiLayer()
    state = phi.factorize(md.get_regime_indicators())
    print(state.summary())
