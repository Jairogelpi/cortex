"""
CAPA RHO - Fiabilidad y recuperacion
Cortex V2, Fase 7

Del paper (Seccion 2.2):
    Checkpoints cada 4 horas.
    Stop-loss absoluto 15%.
    Si el portfolio cae mas del 15%, el sistema se detiene
    y espera revision humana.
    Backtrack automatico al ultimo estado estable.

Escenario F7 prevenido:
    Sin limite de subagentes activos en Sigma.
    $1000+ en una sesion sin techo de presupuesto.
    Mitigacion: maximo N=5 subagentes, token budget por subagente.

Hipotesis H7 del paper:
    Tasa de exito >= 0.95 en 30 dias sin crash no gestionado.
    Falsificacion: crash no gestionado O loop > $50 en un evento.
"""
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
from loguru import logger

from cortex.config import config


CHECKPOINT_DIR = Path("data/checkpoints")


@dataclass
class SystemCheckpoint:
    """Estado completo del sistema en un momento dado."""
    checkpoint_id: str
    timestamp: str
    portfolio_value: float
    delta: float
    regime: str
    trading_signal: str
    open_positions: list
    session_id: str
    is_stable: bool      # True si delta >= DELTA_CONSOLIDATE

    def to_dict(self) -> dict:
        return {
            "checkpoint_id": self.checkpoint_id,
            "timestamp": self.timestamp,
            "portfolio_value": self.portfolio_value,
            "delta": self.delta,
            "regime": self.regime,
            "trading_signal": self.trading_signal,
            "open_positions": self.open_positions,
            "session_id": self.session_id,
            "is_stable": self.is_stable
        }


@dataclass
class RhoStatus:
    """Estado actual de fiabilidad del sistema."""
    stop_loss_triggered: bool = False
    last_checkpoint_id: Optional[str] = None
    last_stable_checkpoint_id: Optional[str] = None
    total_checkpoints: int = 0
    backtrack_count: int = 0
    current_drawdown_pct: float = 0.0
    system_healthy: bool = True
    alert_message: str = ""

    def summary(self) -> str:
        status = "HEALTHY" if self.system_healthy else "ALERT"
        lines = [
            f"Rho Status | {status}",
            f"  Stop-loss activado:    {self.stop_loss_triggered}",
            f"  Drawdown actual:       {self.current_drawdown_pct:.2f}%",
            f"  Checkpoints totales:   {self.total_checkpoints}",
            f"  Backtracks:            {self.backtrack_count}",
            f"  Ultimo checkpoint:     {self.last_checkpoint_id or 'ninguno'}",
            f"  Ultimo estable:        {self.last_stable_checkpoint_id or 'ninguno'}",
        ]
        if self.alert_message:
            lines.append(f"  ALERTA: {self.alert_message}")
        return "\n".join(lines)


class RhoLayer:
    """
    Capa Rho: fiabilidad y recuperacion.

    Tres responsabilidades del paper:
    1. Checkpoints cada 4 horas (persistencia del estado)
    2. Stop-loss absoluto 15% (limite de perdida)
    3. Backtrack al ultimo estado estable si delta < 0.65
    """

    STOP_LOSS_PCT       = config.STOP_LOSS_PCT       # 0.15
    CHECKPOINT_HOURS    = config.CHECKPOINT_HOURS    # 4
    INITIAL_VALUE       = 100_000.0

    def __init__(self):
        CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
        self.status = RhoStatus()
        self._load_latest_status()
        logger.info("Capa Rho inicializada")

    def check_stop_loss(self, portfolio_value: float) -> bool:
        """
        Verifica el stop-loss absoluto del 15% (del paper).

        Si el portfolio cae mas del 15% desde el valor inicial,
        el sistema se detiene y espera revision humana.
        H7: sin crash no gestionado en 30 dias.
        """
        drawdown = (portfolio_value - self.INITIAL_VALUE) / self.INITIAL_VALUE
        self.status.current_drawdown_pct = round(drawdown * 100, 2)

        if drawdown <= -self.STOP_LOSS_PCT:
            self.status.stop_loss_triggered = True
            self.status.system_healthy = False
            self.status.alert_message = (
                f"STOP-LOSS ACTIVADO: portfolio={portfolio_value:.2f} "
                f"drawdown={drawdown*100:.1f}% <= -{self.STOP_LOSS_PCT*100:.0f}%"
            )
            logger.critical(self.status.alert_message)
            return True

        return False

    def save_checkpoint(
        self,
        portfolio_value: float,
        delta: float,
        regime: str,
        trading_signal: str,
        open_positions: list,
        session_id: str
    ) -> SystemCheckpoint:
        """Guarda checkpoint del estado actual."""
        checkpoint_id = f"ckpt_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        is_stable = delta >= config.DELTA_CONSOLIDATE

        checkpoint = SystemCheckpoint(
            checkpoint_id=checkpoint_id,
            timestamp=datetime.now().isoformat(),
            portfolio_value=portfolio_value,
            delta=delta,
            regime=regime,
            trading_signal=trading_signal,
            open_positions=open_positions,
            session_id=session_id,
            is_stable=is_stable
        )

        # Persistir
        path = CHECKPOINT_DIR / f"{checkpoint_id}.json"
        with open(path, "w") as f:
            json.dump(checkpoint.to_dict(), f, indent=2)

        self.status.total_checkpoints += 1
        self.status.last_checkpoint_id = checkpoint_id
        if is_stable:
            self.status.last_stable_checkpoint_id = checkpoint_id

        logger.info(
            f"Rho: checkpoint guardado {checkpoint_id} "
            f"delta={delta:.4f} estable={is_stable}"
        )
        return checkpoint

    def get_last_stable_checkpoint(self) -> Optional[SystemCheckpoint]:
        """Recupera el ultimo checkpoint estable para backtrack."""
        if not self.status.last_stable_checkpoint_id:
            logger.warning("Rho: no hay checkpoint estable para backtrack")
            return None

        path = CHECKPOINT_DIR / f"{self.status.last_stable_checkpoint_id}.json"
        if not path.exists():
            return None

        with open(path) as f:
            data = json.load(f)
        return SystemCheckpoint(**data)

    def execute_backtrack(self) -> Optional[SystemCheckpoint]:
        """Ejecuta backtrack al ultimo estado estable (delta >= 0.75)."""
        checkpoint = self.get_last_stable_checkpoint()
        if checkpoint:
            self.status.backtrack_count += 1
            logger.warning(
                f"Rho: BACKTRACK a {checkpoint.checkpoint_id} "
                f"delta={checkpoint.delta:.4f} "
                f"portfolio={checkpoint.portfolio_value:.2f}"
            )
        return checkpoint

    def _load_latest_status(self):
        """Carga el ultimo estado de Rho desde disco."""
        checkpoints = sorted(CHECKPOINT_DIR.glob("ckpt_*.json"))
        if checkpoints:
            self.status.total_checkpoints = len(checkpoints)
            self.status.last_checkpoint_id = checkpoints[-1].stem
            stable = [
                c for c in checkpoints
                if self._is_stable_checkpoint(c)
            ]
            if stable:
                self.status.last_stable_checkpoint_id = stable[-1].stem

    def _is_stable_checkpoint(self, path: Path) -> bool:
        try:
            with open(path) as f:
                return json.load(f).get("is_stable", False)
        except Exception:
            return False
