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

    # Modelos por capa (Plan-and-Execute heterogeneo — Seccion 8.10 del paper)
    MODEL_PHI: str = os.getenv("MODEL_PHI", "anthropic/claude-sonnet-4-6")
    MODEL_OMEGA: str = os.getenv("MODEL_OMEGA", "anthropic/claude-opus-4-6")
    MODEL_KAPPA: str = os.getenv("MODEL_KAPPA", "anthropic/claude-haiku-4-5")
    MODEL_XI: str = os.getenv("MODEL_XI", "anthropic/claude-haiku-4-5")
    MODEL_SIGMA: str = os.getenv("MODEL_SIGMA", "anthropic/claude-sonnet-4-6")

    # ─────────────────────────────────────────────────────────────────────────
    # UMBRALES PRE-REGISTRADOS EN OSF — https://osf.io/wdkcx
    # Fecha de pre-registro: 5 de abril de 2026
    # INMUTABLES desde esta fecha. Cualquier cambio invalida el experimento.
    # ─────────────────────────────────────────────────────────────────────────

    # DELTA_BACKTRACK = 0.65
    #   Sin cambio respecto al paper original.
    #   Si delta < 0.65 con posiciones abiertas -> backtrack al ultimo estable.
    #   Validado: delta=0.5961 el 5/04/2026 -> HOLD_CASH correcto.
    #
    DELTA_BACKTRACK: float = 0.65

    # DELTA_CONSOLIDATE = 0.70
    #   Ajustado de 0.75 a 0.70 ANTES del pre-registro OSF.
    #   Justificacion matematica: techo natural delta en condiciones neutras
    #   es 0.73 = 0.4*0.50 + 0.4*0.82 + 0.2*1.0. Con 0.75, Mu nunca
    #   consolidaria en condiciones normales. Con 0.70, consolida cuando el
    #   sistema opera 3 puntos sobre el techo natural. H5 es testeable.
    #   Ver docs/CHANGELOG_UMBRALES.md y docs/PROPUESTA_AJUSTE_UMBRALES.md.
    #
    DELTA_CONSOLIDATE: float = 0.70

    # SIM_THRESHOLD = 0.65
    #   Similitud coseno minima para activar un isomorfo en Omega.
    #   Por debajo: modo defensivo 100% cash.
    #
    SIM_THRESHOLD: float = 0.65

    # STOP_LOSS_PCT = 0.15
    #   Stop-loss absoluto del 15% sobre capital inicial ($100K).
    #   Si portfolio <= $85K, sistema se detiene y espera revision humana.
    #   Validado: test con $84K activa stop-loss correctamente.
    #
    STOP_LOSS_PCT: float = 0.15

    # ─────────────────────────────────────────────────────────────────────────

    CHECKPOINT_HOURS: int = 4          # Checkpoint cada 4 horas
    MAX_SUBAGENTS: int = 5             # Maximo 5 subagentes simultaneos
    SUBAGENT_TIMEOUT: int = 60         # Timeout 60s por subagente

    # Pre-registro OSF — referencia permanente
    OSF_PREREGISTRATION: str = "https://osf.io/wdkcx"
    OSF_DATE: str = "2026-04-05"

    def validate(self) -> bool:
        missing = []
        if not self.ALPACA_API_KEY:
            missing.append("ALPACA_API_KEY")
        if not self.ALPACA_SECRET_KEY:
            missing.append("ALPACA_SECRET_KEY")
        if not self.OPENROUTER_API_KEY:
            missing.append("OPENROUTER_API_KEY")
        if missing:
            print(f"[ERROR] Faltan variables en .env: {missing}")
            return False
        print("[OK] Configuracion validada.")
        print(f"[OK] Pre-registro OSF: {self.OSF_PREREGISTRATION}")
        return True

config = Config()
