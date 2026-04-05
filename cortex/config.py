"""Configuracion central de Cortex V2. Lee del archivo .env"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Alpaca Paper Trading
    ALPACA_API_KEY: str = os.getenv("ALPACA_API_KEY", "")
    ALPACA_SECRET_KEY: str = os.getenv("ALPACA_SECRET_KEY", "")
    ALPACA_BASE_URL: str = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets/v2")

    # OpenRouter
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

    # Modelos por capa (Plan-and-Execute heterogeneo - seccion 8.10 del paper)
    MODEL_PHI: str = os.getenv("MODEL_PHI", "anthropic/claude-sonnet-4-6")
    MODEL_OMEGA: str = os.getenv("MODEL_OMEGA", "anthropic/claude-opus-4-6")
    MODEL_KAPPA: str = os.getenv("MODEL_KAPPA", "anthropic/claude-haiku-4-5")
    MODEL_XI: str = os.getenv("MODEL_XI", "anthropic/claude-haiku-4-5")
    MODEL_SIGMA: str = os.getenv("MODEL_SIGMA", "anthropic/claude-sonnet-4-6")

    # ─────────────────────────────────────────────────────────────────────────
    # UMBRALES DEL SISTEMA — pre-registrar en OSF antes de iniciar E1
    # ─────────────────────────────────────────────────────────────────────────
    #
    # DELTA_BACKTRACK = 0.65
    #   Sin cambio respecto al paper original.
    #   Justificacion: techo natural del delta en condiciones neutras es 0.73.
    #   0.65 representa 8 puntos por debajo de ese techo — deterioro real, no ruido.
    #   Validado con datos reales del 5 abril 2026: delta=0.5961 -> HOLD_CASH correcto.
    #
    # DELTA_CONSOLIDATE = 0.70  (modificado desde 0.75 del paper original)
    #   Justificacion matematica:
    #   El techo natural del delta con portfolio neutral es:
    #     0.4*0.50 + 0.4*0.82 + 0.2*1.0 = 0.73
    #   Con el umbral original en 0.75, Mu solo consolidaria cuando el portfolio
    #   bate activamente al SPY — lo cual es infrecuente en condiciones normales.
    #   Consecuencia: H5 no seria testeable en E2 si Mu raramente consolida.
    #   Con 0.70, Mu consolida cuando el sistema opera 3 puntos sobre el techo
    #   natural en condiciones neutras (0.73 > 0.70). Hace H5 testeable.
    #   Este cambio se aplica ANTES del pre-registro en OSF, no despues.
    #   Ver docs/PROPUESTA_AJUSTE_UMBRALES.md para justificacion completa.
    #
    DELTA_BACKTRACK: float = 0.65      # Sin cambio. Bien calibrado por datos reales.
    DELTA_CONSOLIDATE: float = 0.70    # Modificado: 0.75 -> 0.70. Ver justificacion arriba.

    SIM_THRESHOLD: float = 0.65        # Similitud minima para activar isomorfo en Omega
    STOP_LOSS_PCT: float = 0.15        # Stop-loss absoluto 15% (del paper)
    CHECKPOINT_HOURS: int = 4          # Checkpoint cada 4 horas (del paper)
    MAX_SUBAGENTS: int = 5             # Maximo 5 subagentes simultaneos (del paper)
    SUBAGENT_TIMEOUT: int = 60         # Timeout 60s por subagente (del paper)

    def validate(self) -> bool:
        """Verifica que las claves esenciales estan configuradas."""
        missing = []
        if not self.ALPACA_API_KEY or self.ALPACA_API_KEY == "PON_TU_NUEVA_KEY_AQUI":
            missing.append("ALPACA_API_KEY")
        if not self.ALPACA_SECRET_KEY or self.ALPACA_SECRET_KEY == "PON_TU_NUEVO_SECRET_AQUI":
            missing.append("ALPACA_SECRET_KEY")
        if not self.OPENROUTER_API_KEY or self.OPENROUTER_API_KEY == "PON_TU_NUEVA_KEY_OPENROUTER_AQUI":
            missing.append("OPENROUTER_API_KEY")
        if missing:
            print(f"[ERROR] Faltan variables en .env: {missing}")
            return False
        print("[OK] Configuracion validada correctamente.")
        return True

config = Config()
