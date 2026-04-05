"""
CAPA TAU - Control de herramientas y governance
Cortex V2, Fase 8

Del paper (Seccion 2.2):
    Gobierno de acciones irreversibles.
    Aprobacion humana para acciones irreversibles.
    Bloqueo de tools fuera de scope.

Analogia del paper: HITL (Human-In-The-Loop).
Fundamento: AutoHarness (MIT, 2026) governance rules.

Del paper (Seccion 8):
    "Ninguna compra, venta, o cambio de posicion > 5% del portfolio
    se ejecuta sin validacion de Lambda y aprobacion de Tau."

Escenario F3 prevenido:
    Tau no bloquea. Sigma no requiere aprobacion.
    Compra/venta irreversible. Perdida irreparable.
    Mitigacion: governance rules, aprobacion humana para
    acciones irreversibles en E2.

Carnegie Mellon (febrero 2026):
    Agentes exhiben comportamiento inseguro en 51-72% de tareas
    en sesiones multi-turno. Tau es necesidad de seguridad, no mejora.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from loguru import logger

from cortex.config import config


# Acciones que requieren aprobacion humana (del paper)
IRREVERSIBLE_ACTIONS = {
    "MARKET_BUY",
    "MARKET_SELL",
    "POSITION_CHANGE_LARGE",  # > 5% del portfolio
    "STOP_LOSS_MODIFY",
    "LEVERAGE_INCREASE",
}

# Tools permitidas por scope (del paper, AutoHarness governance)
ALLOWED_TOOLS_BY_SIGNAL = {
    "CASH":          {"market_data", "regime_monitor"},
    "HOLD":          {"market_data", "regime_monitor"},
    "DEFENSIVE":     {"market_data", "regime_monitor", "bond_data"},
    "LONG":          {"market_data", "regime_monitor", "equity_data", "order_validator"},
    "LONG_PREPARE":  {"market_data", "regime_monitor", "equity_data"},
    "MEAN_REVERSION":{"market_data", "regime_monitor", "equity_data", "order_validator"},
    "BACKTRACK":     {"market_data", "checkpoint_reader"},
}


@dataclass
class TauDecision:
    """Decision de governance de Tau."""
    approved: bool
    action: str
    reason: str
    requires_human: bool
    blocked_tools: list
    allowed_tools: list
    timestamp: str

    def summary(self) -> str:
        status = "APROBADA" if self.approved else "BLOQUEADA"
        lines = [
            f"Tau Decision | {status} | Accion: {self.action}",
            f"  Requiere humano:  {self.requires_human}",
            f"  Tools permitidas: {self.allowed_tools}",
            f"  Tools bloqueadas: {self.blocked_tools}",
            f"  Razon:            {self.reason}",
        ]
        return "\n".join(lines)


class TauLayer:
    """
    Capa Tau: governance y control de herramientas.

    Dos funciones del paper:
    1. Bloquear acciones irreversibles hasta aprobacion humana
    2. Bloquear tools fuera de scope segun la senal activa

    En E2 (paper trading): Tau simula la aprobacion humana
    para todas las acciones. No ejecuta ordenes reales sin
    confirmacion explicita del operador.
    """

    # Limite de posicion que requiere aprobacion (del paper: 5%)
    POSITION_CHANGE_THRESHOLD = 0.05

    def evaluate(
        self,
        sigma_decision: str,
        trading_signal: str,
        portfolio_value: float,
        proposed_allocation_pct: float,
        is_paper_trading: bool = True
    ) -> TauDecision:
        """
        Evalua si la accion propuesta puede ejecutarse o requiere bloqueo.

        En paper trading: aprueba todo pero registra lo que requeriria
        aprobacion humana en trading real.
        En trading real: bloquea hasta recibir confirmacion humana.
        """
        timestamp = datetime.now().isoformat()

        # Determinar si la accion es irreversible
        action_type = self._classify_action(
            sigma_decision, proposed_allocation_pct, portfolio_value
        )
        is_irreversible = action_type in IRREVERSIBLE_ACTIONS

        # Tools permitidas segun la senal
        allowed = list(ALLOWED_TOOLS_BY_SIGNAL.get(trading_signal, {"market_data"}))
        all_tools = set().union(*ALLOWED_TOOLS_BY_SIGNAL.values())
        blocked = list(all_tools - set(allowed))

        # Decision
        if sigma_decision == "HOLD" or trading_signal in ("CASH",):
            return TauDecision(
                approved=True,
                action="HOLD_NO_ACTION",
                reason="Senal CASH/HOLD: no hay accion que aprobar.",
                requires_human=False,
                blocked_tools=blocked,
                allowed_tools=allowed,
                timestamp=timestamp
            )

        if sigma_decision == "BACKTRACK":
            return TauDecision(
                approved=True,
                action="BACKTRACK",
                reason="Backtrack automatico aprobado: Rho gestiona la recuperacion.",
                requires_human=False,
                blocked_tools=blocked,
                allowed_tools=allowed,
                timestamp=timestamp
            )

        if is_irreversible and not is_paper_trading:
            # Trading real: BLOQUEAR hasta aprobacion humana
            logger.warning(
                f"Tau: accion irreversible bloqueada: {action_type}. "
                f"Requiere aprobacion humana."
            )
            return TauDecision(
                approved=False,
                action=action_type,
                reason=(
                    f"Accion irreversible ({action_type}) bloqueada. "
                    f"Del paper: ninguna orden > {self.POSITION_CHANGE_THRESHOLD*100:.0f}% "
                    f"sin aprobacion humana."
                ),
                requires_human=True,
                blocked_tools=blocked,
                allowed_tools=allowed,
                timestamp=timestamp
            )

        if is_irreversible and is_paper_trading:
            # Paper trading: aprobar pero registrar que requeriria humano
            logger.info(
                f"Tau: accion irreversible ({action_type}) aprobada "
                f"en paper trading. En real requeriria aprobacion humana."
            )
            return TauDecision(
                approved=True,
                action=action_type,
                reason=(
                    f"Paper trading: {action_type} aprobada automaticamente. "
                    f"En trading real requeriria aprobacion humana explicita."
                ),
                requires_human=True,  # registrar que en real requeriria humano
                blocked_tools=blocked,
                allowed_tools=allowed,
                timestamp=timestamp
            )

        return TauDecision(
            approved=True,
            action=action_type,
            reason=f"Accion no irreversible aprobada: {action_type}",
            requires_human=False,
            blocked_tools=blocked,
            allowed_tools=allowed,
            timestamp=timestamp
        )

    def _classify_action(
        self,
        sigma_decision: str,
        allocation_pct: float,
        portfolio_value: float
    ) -> str:
        """Clasifica el tipo de accion segun los governance rules del paper."""
        if sigma_decision == "EXECUTE":
            if allocation_pct > self.POSITION_CHANGE_THRESHOLD:
                return "POSITION_CHANGE_LARGE"
            return "MARKET_BUY"
        elif sigma_decision == "DEFENSIVE":
            return "MARKET_BUY"
        elif sigma_decision == "BACKTRACK":
            return "MARKET_SELL"
        return "NO_ACTION"
