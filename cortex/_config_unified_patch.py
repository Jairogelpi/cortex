    # UnifiedLayer adaptativa — umbrales de ruta
    #
    # REVIEW_ENABLED: activa/desactiva la revision LLM
    # REVIEW_SIM_MIN: similitud minima para considerar revision (debajo: fallback directo)
    # REVIEW_HIGH_SIM: similitud suficientemente alta para omitir revision (camino rapido)
    #   0.86 -> si sim >= 0.86 y gap >= 0.03, la senal es clara: 0 tokens
    # REVIEW_GAP_MIN: gap minimo entre top-1 y top-2 para camino rapido
    #   0.03 -> diferencia de 3pts entre isomorfos ya es discriminante
    # REVIEW_MAX_TOKENS: tokens maximos del output de la revision
    #   20 -> solo "same" o nombre del isomorfo + una palabra de contradiccion
    UNIFIED_REVIEW_ENABLED: bool = os.getenv("UNIFIED_REVIEW_ENABLED", "1").lower() not in ("0", "false", "no")
    UNIFIED_REVIEW_SIM_MIN: float = float(os.getenv("UNIFIED_REVIEW_SIM_MIN", "0.65"))
    UNIFIED_REVIEW_HIGH_SIM: float = float(os.getenv("UNIFIED_REVIEW_HIGH_SIM", "0.86"))
    UNIFIED_REVIEW_GAP_MIN: float = float(os.getenv("UNIFIED_REVIEW_GAP_MIN", "0.03"))
    UNIFIED_REVIEW_MAX_TOKENS: int = int(os.getenv("UNIFIED_REVIEW_MAX_TOKENS", "20"))
    UNIFIED_PROJECT_BLEND_MIN: float = float(os.getenv("UNIFIED_PROJECT_BLEND_MIN", "0.04"))
    UNIFIED_PROJECT_BLEND_MAX: float = float(os.getenv("UNIFIED_PROJECT_BLEND_MAX", "0.18"))
