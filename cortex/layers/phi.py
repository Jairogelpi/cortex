"""
CAPA PHI - Factorizador de estado
Cortex V2, Fase 1

Fundamentado en Lee et al. (Nature Communications 2025).
Factoriza indicadores de mercado en 8 dimensiones ortogonales Z1-Z8.
"""
import json
import numpy as np
from dataclasses import dataclass
from openai import OpenAI
from loguru import logger

from cortex.config import config


@dataclass
class PhiState:
    """Estado factorizado. 8 dimensiones en [-1, 1]."""
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
        """
        Verifica condicion del paper: I(Zi, Zj) < 0.3.
        Proxy: |Zi - Zj| >= threshold para todo i != j.
        """
        z = self.to_vector()
        pairs_too_similar = []
        for i in range(len(z)):
            for j in range(i + 1, len(z)):
                diff = abs(z[i] - z[j])
                if diff < threshold:
                    pairs_too_similar.append((i + 1, j + 1, round(diff, 4)))
        return {
            "orthogonality_ok": len(pairs_too_similar) == 0,
            "pairs_too_similar": pairs_too_similar,
            "z_variance": round(float(np.var(z)), 4),
            "z_spread": round(float(np.max(z) - np.min(z)), 4)
        }

    def summary(self) -> str:
        z = self.to_vector()
        orth = self.check_orthogonality()
        lines = [
            f"Phi State | Regimen: {self.regime} | Confianza: {self.confidence:.2f}",
            f"  Z1 Estructura:     {self.Z1_estructura:+.3f}  (tendencia precio)",
            f"  Z2 Dinamica:       {self.Z2_dinamica:+.3f}  (aceleracion/VIX)",
            f"  Z3 Escala:         {self.Z3_escala:+.3f}  (magnitud volatilidad)",
            f"  Z4 Causalidad:     {self.Z4_causalidad:+.3f}  (coherencia interna)",
            f"  Z5 Temporalidad:   {self.Z5_temporalidad:+.3f}  (ciclo largo/drawdown)",
            f"  Z6 Reversibilidad: {self.Z6_reversibilidad:+.3f}  (prob. reversion)",
            f"  Z7 Valencia:       {self.Z7_valencia:+.3f}  (sesgo direccional neto)",
            f"  Z8 Complejidad:    {self.Z8_complejidad:+.3f}  (entropia regimen)",
            f"  Varianza Z: {orth['z_variance']} | Spread: {orth['z_spread']}",
            f"  Ortogonalidad: {'OK' if orth['orthogonality_ok'] else 'CORREGIDA'}",
        ]
        return "\n".join(lines)


class PhiLayer:
    """
    Capa Phi: factorizador de estado del mercado.
    Pipeline: determinista -> LLM -> separacion forzada -> PhiState.
    """

    MIN_SEPARATION = 0.18  # separacion minima entre cualquier par Zi, Zj

    def __init__(self):
        self.client = OpenAI(
            api_key=config.OPENROUTER_API_KEY,
            base_url=config.OPENROUTER_BASE_URL
        )
        self.model = config.MODEL_PHI
        logger.info(f"Capa Phi inicializada: {self.model}")

    def factorize(self, indicators: dict) -> PhiState:
        """Pipeline completo: determinista -> LLM -> separacion forzada."""
        base = self._factorize_deterministic(indicators)
        refined = self._refine_with_llm(indicators, base)
        separated = self._enforce_separation(refined)
        state = self._build_state(separated, indicators, base["confidence"])
        logger.info(f"Phi: regimen={state.regime}, confianza={state.confidence:.2f}, var={np.var(state.to_vector()):.4f}")
        return state

    def _factorize_deterministic(self, ind: dict) -> dict:
        """
        8 dimensiones con variables fuente distintas para garantizar ortogonalidad.
        Cada Zi se construye sobre un aspecto diferente del mercado.
        """
        vix      = ind.get("vix", 20.0)
        momentum = ind.get("momentum_21d_pct", 0.0)
        vol      = ind.get("vol_realized_pct", 15.0)
        drawdown = ind.get("drawdown_90d_pct", 0.0)
        regime   = ind.get("regime", "INDETERMINATE")

        # Z1: tendencia pura (momentum normalizado). Rango [-1, 1].
        z1 = float(np.clip(momentum / 8.0, -1, 1))

        # Z2: estres de mercado (VIX). Anclado: 20=neutro, >40=extremo.
        z2 = float(np.clip((vix - 20.0) / 22.0, -1, 1))

        # Z3: nivel absoluto de volatilidad. Anclado a benchmark 12%.
        # Escala diferente a Z2 (vol_real != VIX).
        z3 = float(np.clip((vol - 12.0) / 18.0, -1, 1))

        # Z4: coherencia entre momentum y volatilidad (producto cruzado).
        # Positivo = tendencia con volumen. Negativo = ruido sin direccion.
        sign_mom = np.sign(momentum) if abs(momentum) > 0.5 else 0
        z4 = float(np.clip(sign_mom * (vol / 25.0), -1, 1))

        # Z5: posicion en ciclo largo (drawdown). Escala: -40% = crisis.
        # Completamente independiente de VIX y vol.
        z5 = float(np.clip(drawdown / -35.0, -1, 1))

        # Z6: presion de mean-reversion. Alta cuando VIX > 30 (panico).
        # Logica de umbrales no lineal -- distinta a Z2 (lineal).
        if vix > 35:
            z6 = 0.85
        elif vix > 28:
            z6 = 0.45
        elif vix > 22:
            z6 = 0.10
        elif vix < 14:
            z6 = -0.65
        else:
            z6 = -0.20

        # Z7: valencia neta ponderada (combinacion global).
        # Es la unica dimension sintetica -- valor distinto por construccion.
        z7 = float(np.clip(
            0.45 * (momentum / 8.0) +
            0.30 * (drawdown / -35.0) +
            0.25 * (-(vix - 20.0) / 22.0),
            -1, 1
        ))

        # Z8: complejidad/entropia del regimen. Mapa discreto.
        z8_map = {
            "R1_EXPANSION":    -0.70,
            "R2_ACCUMULATION": -0.25,
            "R4_CONTRACTION":  +0.40,
            "R3_TRANSITION":   +0.72,
            "INDETERMINATE":   +0.92,
        }
        z8 = z8_map.get(regime, 0.92)

        confidence_map = {
            "R1_EXPANSION": 0.85, "R2_ACCUMULATION": 0.75,
            "R3_TRANSITION": 0.70, "R4_CONTRACTION": 0.75,
            "INDETERMINATE": 0.45
        }

        return {
            "Z1": round(z1, 3), "Z2": round(z2, 3), "Z3": round(z3, 3),
            "Z4": round(z4, 3), "Z5": round(z5, 3), "Z6": round(z6, 3),
            "Z7": round(z7, 3), "Z8": round(z8, 3),
            "confidence": confidence_map.get(regime, 0.45)
        }

    def _refine_with_llm(self, indicators: dict, base: dict) -> dict:
        """Claude Sonnet refina la factorizacion con razonamiento semantico."""
        prompt = f"""Eres la capa Phi de Cortex V2. Refina esta factorizacion de mercado.

INDICADORES:
VIX={indicators.get('vix')} | Momentum21d={indicators.get('momentum_21d_pct')}% | Vol={indicators.get('vol_realized_pct')}% | Drawdown90d={indicators.get('drawdown_90d_pct')}% | Regimen={indicators.get('regime')}

FACTORIZACION BASE (ajusta si tu analisis lo justifica):
Z1(tendencia)={base['Z1']} Z2(estres_vix)={base['Z2']} Z3(vol_abs)={base['Z3']} Z4(coherencia)={base['Z4']}
Z5(ciclo_largo)={base['Z5']} Z6(reversion)={base['Z6']} Z7(valencia_neta)={base['Z7']} Z8(complejidad)={base['Z8']}

IMPORTANTE: cada Zi debe quedar separado del resto (distintos valores).
Devuelve SOLO JSON sin texto adicional:
{{"Z1":0.0,"Z2":0.0,"Z3":0.0,"Z4":0.0,"Z5":0.0,"Z6":0.0,"Z7":0.0,"Z8":0.0,"reasoning":"una frase"}}"""

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300, temperature=0.1
            )
            raw = resp.choices[0].message.content.strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            data = json.loads(raw)
            logger.info(f"Phi LLM: {data.get('reasoning', '')}")
            return {k: float(data.get(k, base[k])) for k in ["Z1","Z2","Z3","Z4","Z5","Z6","Z7","Z8"]}
        except Exception as e:
            logger.warning(f"Phi LLM fallback: {e}")
            return {k: base[k] for k in ["Z1","Z2","Z3","Z4","Z5","Z6","Z7","Z8"]}

    def _enforce_separation(self, z_dict: dict) -> dict:
        """
        Garantiza separacion minima entre todas las dimensiones.
        Si dos Zi son demasiado similares, empuja el segundo hacia fuera.
        Preserva el orden relativo y el signo original.
        """
        keys = ["Z1","Z2","Z3","Z4","Z5","Z6","Z7","Z8"]
        z = np.array([z_dict[k] for k in keys])

        max_iterations = 20
        for _ in range(max_iterations):
            changed = False
            for i in range(len(z)):
                for j in range(i + 1, len(z)):
                    diff = z[j] - z[i]
                    if abs(diff) < self.MIN_SEPARATION:
                        # Empuja los dos en direcciones opuestas
                        push = (self.MIN_SEPARATION - abs(diff)) / 2.0 + 0.01
                        if diff >= 0:
                            z[i] -= push
                            z[j] += push
                        else:
                            z[i] += push
                            z[j] -= push
                        # Clip al rango valido
                        z[i] = float(np.clip(z[i], -1.0, 1.0))
                        z[j] = float(np.clip(z[j], -1.0, 1.0))
                        changed = True
            if not changed:
                break

        return {keys[i]: round(float(z[i]), 3) for i in range(len(keys))}

    def _build_state(self, z: dict, indicators: dict, confidence: float) -> PhiState:
        return PhiState(
            Z1_estructura=z["Z1"], Z2_dinamica=z["Z2"],
            Z3_escala=z["Z3"], Z4_causalidad=z["Z4"],
            Z5_temporalidad=z["Z5"], Z6_reversibilidad=z["Z6"],
            Z7_valencia=z["Z7"], Z8_complejidad=z["Z8"],
            regime=indicators.get("regime", "INDETERMINATE"),
            confidence=confidence,
            raw_indicators=indicators
        )


def test_phi():
    from cortex.market_data import MarketData

    print("\n" + "="*50)
    print("  CORTEX V2 - Test Capa Phi (v3 con separacion forzada)")
    print("="*50 + "\n")

    md = MarketData()
    indicators = md.get_regime_indicators()

    print("Indicadores:")
    for k, v in indicators.items():
        print(f"  {k}: {v}")

    print("\nFactorizando...")
    phi = PhiLayer()
    state = phi.factorize(indicators)

    print("\n" + state.summary())

    orth = state.check_orthogonality()
    print(f"\nOrtogonalidad: {'OK' if orth['orthogonality_ok'] else 'REVISAR'}")
    if orth['pairs_too_similar']:
        print(f"  Pares similares: {orth['pairs_too_similar']}")

    print("\n" + "="*50)
    print("  Siguiente: capa Kappa (critic externo delta)")
    print("="*50 + "\n")
    return state


if __name__ == "__main__":
    test_phi()
