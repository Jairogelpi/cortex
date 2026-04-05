"""
CAPA OMEGA - Motor de hipotesis cross-domain
Cortex V2, Fase 3

Fundamentado en Bellmund et al. (Nature Neuroscience 2025):
el cortex entorrinal reutiliza el mismo codigo hexagonal de grid cells
para espacios financieros, fisicos y sociales. El cerebro no tiene
un modulo separado para cada dominio -- reutiliza el mismo codigo
geometrico para detectar patrones estructurales en cualquier espacio.

Formulacion exacta del paper (Seccion 2.1):
    Omega: (Z1 x ... x Z8)^n -> Z_nuevo
    donde Sim(Z_mercado, Z_fisico) >= 0.65

Los 5 isomorfos fisicos del paper:
    1. Gas en expansion          <-> Bull run sostenido
    2. Gas comprimido            <-> Acumulacion pre-rally
    3. Transicion de fase        <-> Cambio de regimen alta volatilidad
    4. Sistema sobre-amortiguado <-> Reversion lenta a la media
    5. Atractor de Lorenz        <-> Regimen caotico impredecible

Riesgo principal (Seccion 2, tabla):
    Confabulacion de isomorfos falsos (PHANTOM, NeurIPS 2025)

Mitigacion:
    Umbral Sim >= 0.65, validacion por Lambda, H4 mide F1-score.

Modelo: Claude Opus 4.6 (UNA sola llamada por cambio de regimen).
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


# ─────────────────────────────────────────────────────────────────
# Vectores Z de referencia para los 5 isomorfos fisicos del paper.
# Calibrados segun definiciones formales R1-R4 (Seccion 9.3).
# Orden: Z1 Z2 Z3 Z4 Z5 Z6 Z7 Z8
# ─────────────────────────────────────────────────────────────────
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
    """Hipotesis generada por Omega para el estado actual del mercado."""
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
            f"  Umbral 0.65 superado: {self.threshold_met}",
            f"  Senal de trading:     {self.trading_signal}",
            f"  Instrumentos:         {self.instruments if self.instruments else 'ninguno (CASH)'}",
            f"  Asignacion:           {self.allocation_pct*100:.0f}% del portfolio",
            f"  Analogia fisica:      {self.physical_description}",
            f"  Analogia mercado:     {self.market_analog}",
            f"  Confianza Omega:      {self.confidence:.4f}",
            "",
            "  Similitudes con todos los isomorfos:",
        ]
        for name, sim in sorted(self.all_similarities.items(), key=lambda x: -x[1]):
            marker = " <-- ELEGIDO" if name == self.best_isomorph else ""
            lines.append(f"    {name:<25} Sim={sim:.4f}{marker}")
        lines.append("")
        lines.append(f"  Razonamiento Opus:")
        lines.append(f"  {self.llm_reasoning}")
        return "\n".join(lines)


class OmegaLayer:
    """
    Capa Omega: motor de hipotesis cross-domain.

    Pipeline:
    1. Calcular similitud coseno entre Z_mercado y cada Z_fisico
    2. Seleccionar el isomorfo con mayor similitud
    3. Si Sim >= 0.65: generar hipotesis con Claude Opus
    4. Si ningun Sim >= 0.65: hipotesis defensiva (CASH)
    """

    SIM_THRESHOLD = config.SIM_THRESHOLD  # 0.65, del paper

    def __init__(self):
        self.client = OpenAI(
            api_key=config.OPENROUTER_API_KEY,
            base_url=config.OPENROUTER_BASE_URL
        )
        self.model = config.MODEL_OMEGA  # claude-opus-4-6
        logger.info(f"Capa Omega inicializada: {self.model}")

    def generate_hypothesis(self, phi_state: PhiState) -> OmegaHypothesis:
        """Genera hipotesis comparando Z_mercado con los 5 isomorfos fisicos."""
        z_market = phi_state.to_vector()
        similarities = self._calc_similarities(z_market)

        best_name = max(similarities, key=similarities.get)
        best_sim = similarities[best_name]
        threshold_met = best_sim >= self.SIM_THRESHOLD

        logger.info(
            f"Omega similitudes: {best_name}={best_sim:.4f} "
            f"(umbral={'OK' if threshold_met else 'NO ALCANZADO'})"
        )

        if threshold_met:
            return self._generate_with_opus(
                phi_state, z_market, best_name, best_sim, similarities
            )
        else:
            return self._defensive_hypothesis(
                phi_state, z_market, best_name, best_sim, similarities
            )

    def _calc_similarities(self, z_market: np.ndarray) -> dict:
        """
        Similitud coseno normalizada entre Z_mercado y cada Z_fisico.
        Rango [0, 1]. Umbral de activacion: 0.65.
        """
        norm_market = np.linalg.norm(z_market)
        if norm_market == 0:
            return {name: 0.0 for name in PHYSICAL_ISOMORPHS}

        similarities = {}
        for name, iso in PHYSICAL_ISOMORPHS.items():
            z_ref = iso["Z"]
            norm_ref = np.linalg.norm(z_ref)
            if norm_ref == 0:
                similarities[name] = 0.0
                continue
            cosine = float(np.dot(z_market, z_ref) / (norm_market * norm_ref))
            similarities[name] = round((cosine + 1.0) / 2.0, 4)

        return similarities

    def _extract_json(self, text: str) -> dict:
        """
        Extrae JSON del texto de respuesta del LLM de forma robusta.
        Opus a veces incluye texto antes o despues del JSON.
        Estrategia: buscar el primer '{' y el ultimo '}' validos.
        """
        # Limpiar backticks de markdown
        text = text.replace("```json", "").replace("```", "").strip()

        # Intentar parse directo primero
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Buscar el bloque JSON por posicion de llaves
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = text[start:end + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass

        # Ultimo recurso: extraer con regex los campos clave
        reasoning_match = re.search(r'"reasoning"\s*:\s*"(.*?)"(?=\s*[,}])', text, re.DOTALL)
        confidence_match = re.search(r'"confidence_adjustment"\s*:\s*([-\d.]+)', text)
        risk_match = re.search(r'"risk_note"\s*:\s*"(.*?)"(?=\s*[,}])', text, re.DOTALL)

        if reasoning_match:
            return {
                "reasoning": reasoning_match.group(1),
                "confidence_adjustment": float(confidence_match.group(1)) if confidence_match else 0.0,
                "risk_note": risk_match.group(1) if risk_match else ""
            }

        raise ValueError(f"No se pudo extraer JSON de la respuesta: {text[:200]}")

    def _generate_with_opus(
        self,
        phi_state: PhiState,
        z_market: np.ndarray,
        best_name: str,
        best_sim: float,
        similarities: dict
    ) -> OmegaHypothesis:
        """Genera hipotesis de trading con Claude Opus (UNA llamada por regimen)."""
        iso = PHYSICAL_ISOMORPHS[best_name]
        ind = phi_state.raw_indicators

        prompt = f"""Eres la capa Omega de Cortex V2, el motor de hipotesis cross-domain.
Tu fundamento: Bellmund et al. (Nature Neuroscience 2025) - el cortex entorrinal
reutiliza el mismo codigo hexagonal para espacios fisicos y financieros.

ESTADO DEL MERCADO (vector Z factorizado por Phi):
Z1(tendencia)={z_market[0]:+.3f}  Z2(dinamica)={z_market[1]:+.3f}  Z3(escala)={z_market[2]:+.3f}  Z4(causalidad)={z_market[3]:+.3f}
Z5(temporalidad)={z_market[4]:+.3f}  Z6(reversibilidad)={z_market[5]:+.3f}  Z7(valencia)={z_market[6]:+.3f}  Z8(complejidad)={z_market[7]:+.3f}

Datos brutos: VIX={ind.get('vix')} | Momentum21d={ind.get('momentum_21d_pct')}% | Vol={ind.get('vol_realized_pct')}% | SPY=${ind.get('spy_price')} | Regimen={phi_state.regime}

ISOMORFO MAS SIMILAR (Sim={best_sim:.4f}):
Nombre: {best_name}
Sistema fisico: {iso['description']}
Analogia de mercado: {iso['market_analog']}
Vector Z referencia: {iso['Z'].tolist()}

SIMILITUDES CON TODOS LOS ISOMORFOS:
{chr(10).join(f'  {n}: {s:.4f}' for n, s in sorted(similarities.items(), key=lambda x: -x[1]))}

TAREA: Explica en 2-3 frases cientificas y precisas:
1. Por que el estado actual del mercado es isomorfo a "{best_name}"
2. Que implica esta analogia para los proximos {iso['expected_duration_days']} dias
3. Menciona los valores Z especificos que justifican el isomorfo

Responde SOLO con este JSON (sin texto antes ni despues, sin markdown):
{{"reasoning": "tu analisis de 2-3 frases", "confidence_adjustment": 0.0, "risk_note": "principal riesgo de confabulacion"}}

confidence_adjustment: entre -0.2 y +0.2 segun tu confianza en el isomorfo."""

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.1
            )
            raw = resp.choices[0].message.content
            logger.debug(f"Opus raw response: {raw[:300]}")

            data = self._extract_json(raw)

            reasoning = data.get("reasoning", "Sin razonamiento")
            confidence_adj = float(data.get("confidence_adjustment", 0.0))
            risk_note = data.get("risk_note", "")

            confidence = max(0.0, min(1.0, best_sim + confidence_adj))

            logger.info(f"Omega Opus: {reasoning[:120]}...")
            if risk_note:
                logger.warning(f"Omega riesgo: {risk_note}")

            full_reasoning = reasoning
            if risk_note:
                full_reasoning += f" | RIESGO: {risk_note}"

            return OmegaHypothesis(
                best_isomorph=best_name,
                similarity=best_sim,
                threshold_met=True,
                trading_signal=iso["trading_signal"],
                instruments=iso["instruments"],
                allocation_pct=iso["allocation_pct"],
                physical_description=iso["description"],
                market_analog=iso["market_analog"],
                all_similarities=similarities,
                llm_reasoning=full_reasoning,
                confidence=round(confidence, 4),
                timestamp=datetime.now().isoformat(),
                z_market=z_market.tolist()
            )

        except Exception as e:
            logger.error(f"Omega Opus error: {e}. Usando senal base del isomorfo.")
            return OmegaHypothesis(
                best_isomorph=best_name,
                similarity=best_sim,
                threshold_met=True,
                trading_signal=iso["trading_signal"],
                instruments=iso["instruments"],
                allocation_pct=iso["allocation_pct"],
                physical_description=iso["description"],
                market_analog=iso["market_analog"],
                all_similarities=similarities,
                llm_reasoning=(
                    f"Fallback determinista (error LLM: {str(e)[:60]}). "
                    f"Isomorfo={best_name}, Sim={best_sim:.4f}. "
                    f"Senal base activada por similitud coseno."
                ),
                confidence=round(best_sim * 0.8, 4),
                timestamp=datetime.now().isoformat(),
                z_market=z_market.tolist()
            )

    def _defensive_hypothesis(
        self,
        phi_state: PhiState,
        z_market: np.ndarray,
        best_name: str,
        best_sim: float,
        similarities: dict
    ) -> OmegaHypothesis:
        """
        Hipotesis defensiva cuando ningun isomorfo supera Sim >= 0.65.
        El paper (Seccion 6.3) especifica: modo defensivo 100% cash.
        No es un fallo -- es el comportamiento correcto.
        """
        logger.warning(
            f"Omega: ningun isomorfo >= 0.65. "
            f"Mejor: {best_name}={best_sim:.4f}. MODO DEFENSIVO."
        )
        return OmegaHypothesis(
            best_isomorph=best_name,
            similarity=best_sim,
            threshold_met=False,
            trading_signal="CASH",
            instruments=[],
            allocation_pct=0.0,
            physical_description="Ningun isomorfo con similitud suficiente (Sim < 0.65)",
            market_analog="Regimen sin precedente en los 5 isomorfos del paper",
            all_similarities=similarities,
            llm_reasoning=(
                f"Ningun isomorfo alcanza Sim >= {self.SIM_THRESHOLD}. "
                f"Mejor: '{best_name}' con Sim={best_sim:.4f}. "
                f"Seccion 6.3 del paper: modo defensivo 100% cash."
            ),
            confidence=0.0,
            timestamp=datetime.now().isoformat(),
            z_market=z_market.tolist()
        )


def test_omega():
    """Prueba la capa Omega con datos reales del mercado."""
    from cortex.market_data import MarketData
    from cortex.layers.phi import PhiLayer

    print("\n" + "="*55)
    print("  CORTEX V2 - Test Capa Omega (motor de hipotesis)")
    print("="*55 + "\n")

    md = MarketData()
    indicators = md.get_regime_indicators()
    print(f"Mercado: VIX={indicators['vix']} | Momentum={indicators['momentum_21d_pct']}% | Regimen={indicators['regime']}\n")

    phi = PhiLayer()
    phi_state = phi.factorize(indicators)
    print(phi_state.summary())

    print("\nGenerando hipotesis con Omega (Claude Opus)...\n")
    omega = OmegaLayer()
    hypothesis = omega.generate_hypothesis(phi_state)

    print(hypothesis.summary())

    print("\n--- Decision del sistema ---")
    if not hypothesis.threshold_met:
        print(f"  MODO DEFENSIVO: ningun isomorfo con Sim >= 0.65")
        print(f"  100% cash hasta que el regimen sea identificable")
    elif hypothesis.trading_signal == "CASH":
        print(f"  CASH: isomorfo Lorenz detectado (caos determinista)")
        print(f"  El sistema no toma posiciones en regimen caotico")
    elif hypothesis.trading_signal == "DEFENSIVE":
        print(f"  DEFENSIVO: transicion de fase detectada")
        print(f"  Instrumentos defensivos: {hypothesis.instruments}")
        print(f"  Asignacion: {hypothesis.allocation_pct*100:.0f}% del portfolio")
    else:
        print(f"  SENAL: {hypothesis.trading_signal}")
        print(f"  Instrumentos: {hypothesis.instruments}")
        print(f"  Asignacion: {hypothesis.allocation_pct*100:.0f}%")
        print(f"  Confianza: {hypothesis.confidence:.4f}")

    print(f"\n  IMPORTANTE: hipotesis pendiente de validacion por Lambda")
    print(f"  Ninguna orden se ejecuta en Alpaca sin pasar por Lambda + Tau")

    print("\n" + "="*55)
    print("  Omega OK -> Siguiente: capa Lambda (validacion real)")
    print("="*55 + "\n")
    return hypothesis


if __name__ == "__main__":
    test_omega()
