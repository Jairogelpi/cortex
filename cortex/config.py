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
    OPENROUTER_TIMEOUT_SECONDS: int = int(os.getenv("OPENROUTER_TIMEOUT_SECONDS", "90"))
    OPENROUTER_MAX_RETRIES: int = int(os.getenv("OPENROUTER_MAX_RETRIES", "1"))

    # FRED (opcional)
    FRED_API_KEY: str = os.getenv("FRED_API_KEY", "")

    # Modelos por capa
    MODEL_PHI: str    = os.getenv("MODEL_PHI",   "anthropic/claude-sonnet-4-6")
    MODEL_OMEGA: str  = os.getenv("MODEL_OMEGA",  "anthropic/claude-opus-4-6")
    MODEL_KAPPA: str  = os.getenv("MODEL_KAPPA",  "anthropic/claude-haiku-4-5")
    MODEL_XI: str     = os.getenv("MODEL_XI",     "anthropic/claude-haiku-4-5")
    MODEL_SIGMA: str  = os.getenv("MODEL_SIGMA",  "anthropic/claude-sonnet-4-6")

    # ─────────────────────────────────────────────────────────────────────────
    # UMBRALES PRE-REGISTRADOS EN OSF — https://osf.io/wdkcx
    # Fecha de pre-registro: 5 de abril de 2026
    # INMUTABLES desde esta fecha.
    # ─────────────────────────────────────────────────────────────────────────
    DELTA_BACKTRACK: float   = 0.65
    DELTA_CONSOLIDATE: float = 0.70
    SIM_THRESHOLD: float     = 0.65
    STOP_LOSS_PCT: float     = 0.15

    # ─────────────────────────────────────────────────────────────────────────
    # UNIFIED LAYER — ruta adaptativa (no pre-registrada, parametros de ingenieria)
    #
    # Logica de ruta:
    #   sim >= HIGH_SIM  AND  gap >= GAP_MIN  => camino rapido (0 tokens)
    #   de lo contrario, si sim >= SIM_MIN    => revision LLM compacta
    #
    # Con HIGH_SIM=0.86 y GAP_MIN=0.03:
    #   - Dias claros (R1_EXPANSION puro, Lorenz puro): 0 tokens
    #   - Dias ambiguos (frontera gas/lorenz, regimen indeterminate): revision compacta
    #
    # MAX_TOKENS=20: el output es "same" o nombre del isomorfo + token de contradiccion
    # ─────────────────────────────────────────────────────────────────────────
    UNIFIED_REVIEW_ENABLED: bool    = os.getenv("UNIFIED_REVIEW_ENABLED", "1").lower() not in ("0","false","no")
    UNIFIED_REVIEW_SIM_MIN: float   = float(os.getenv("UNIFIED_REVIEW_SIM_MIN",  "0.65"))
    UNIFIED_REVIEW_HIGH_SIM: float  = float(os.getenv("UNIFIED_REVIEW_HIGH_SIM", "0.86"))
    UNIFIED_REVIEW_GAP_MIN: float   = float(os.getenv("UNIFIED_REVIEW_GAP_MIN",  "0.03"))
    UNIFIED_REVIEW_MAX_TOKENS: int  = int(os.getenv("UNIFIED_REVIEW_MAX_TOKENS", "20"))
    UNIFIED_PROJECT_BLEND_MIN: float = float(os.getenv("UNIFIED_PROJECT_BLEND_MIN","0.04"))
    UNIFIED_PROJECT_BLEND_MAX: float = float(os.getenv("UNIFIED_PROJECT_BLEND_MAX","0.18"))

    # ─────────────────────────────────────────────────────────────────────────

    CHECKPOINT_HOURS: int   = 4
    MAX_SUBAGENTS: int      = 5
    SUBAGENT_TIMEOUT: int   = 60

    OSF_PREREGISTRATION: str = "https://osf.io/wdkcx"
    OSF_DATE: str            = "2026-04-05"

    def validate(self) -> bool:
        missing = []
        if not self.ALPACA_API_KEY:    missing.append("ALPACA_API_KEY")
        if not self.ALPACA_SECRET_KEY: missing.append("ALPACA_SECRET_KEY")
        if not self.OPENROUTER_API_KEY: missing.append("OPENROUTER_API_KEY")
        if missing:
            print(f"[ERROR] Faltan variables en .env: {missing}")
            return False
        print("[OK] Configuracion validada.")
        print(f"[OK] Pre-registro OSF: {self.OSF_PREREGISTRATION}")
        return True

config = Config()
