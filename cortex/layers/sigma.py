"""
CAPA SIGMA - Orquestador adaptativo
Cortex V2, Fase 6

Fundamentado en Badre (2025): el PFC anterior realiza planificacion
jerarquica de objetivos. Sigma decide que subagentes activar, en
que orden, y con que timeout.

Del paper (Seccion 2.2):
    Sigma activa solo los subagentes relevantes para el regimen detectado.
    Timeout 60s por subagente.
    Detecta deadlocks y reinicia subagentes bloqueados (escenario F4).

Escenario F4 prevenido:
    Sigma asigna dos subagentes Xi que esperan el uno al otro.
    Sistema inactivo. Heartbeat falla.
    Mitigacion: timeout 60s, Sigma detecta deadlock y reinicia.
"""
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from loguru import logger

from cortex.config import config
from cortex.layers.phi import PhiState
from cortex.layers.kappa import KappaEvaluation
from cortex.layers.omega import OmegaHypothesis
from cortex.layers.lambda_ import LambdaValidation


@dataclass
class SubagentTask:
    """Tarea asignada a un subagente Xi."""
    name: str
    task_type: str       # ANALYSIS | VALIDATION | EXECUTION
    input_data: dict
    timeout_seconds: int = config.SUBAGENT_TIMEOUT
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[dict] = None
    status: str = "PENDING"   # PENDING | RUNNING | DONE | TIMEOUT | ERROR


@dataclass
class SigmaOrchestration:
    """Plan de orquestacion generado por Sigma."""
    regime: str
    active_subagents: list
    tasks: list = field(default_factory=list)
    decision: str = ""           # EXECUTE | HOLD | DEFENSIVE | BACKTRACK
    reasoning: str = ""
    timestamp: str = ""
    deadlocks_detected: int = 0
    total_duration_seconds: float = 0.0

    def summary(self) -> str:
        lines = [
            f"Sigma Orchestration | Regimen: {self.regime} | Decision: {self.decision}",
            f"  Subagentes activos:    {self.active_subagents}",
            f"  Tareas planificadas:   {len(self.tasks)}",
            f"  Deadlocks detectados:  {self.deadlocks_detected}",
            f"  Duracion total:        {self.total_duration_seconds:.1f}s",
            f"  Razonamiento:          {self.reasoning}",
        ]
        return "\n".join(lines)


class SigmaLayer:
    """
    Capa Sigma: orquestador adaptativo.

    Recibe el estado completo del pipeline (Phi, Kappa, Omega, Lambda)
    y decide que hacer a continuacion:
    - Que subagentes Xi activar (maximo MAX_SUBAGENTS)
    - En que orden ejecutarlos
    - Como manejar timeouts y deadlocks (F4)
    - La decision final de trading

    No llama a LLMs. Sigma es logica determinista pura.
    La complejidad del LLM ya ocurrio en Phi, Omega y Lambda.
    """

    MAX_SUBAGENTS = config.MAX_SUBAGENTS      # 5 del paper
    SUBAGENT_TIMEOUT = config.SUBAGENT_TIMEOUT # 60s del paper

    def orchestrate(
        self,
        phi_state: PhiState,
        kappa_eval: KappaEvaluation,
        omega_hyp: OmegaHypothesis,
        lambda_val: LambdaValidation,
    ) -> SigmaOrchestration:
        """
        Genera el plan de orquestacion basado en el estado completo.

        Logica del paper:
        - INDETERMINATE + delta bajo -> HOLD, subagentes minimos
        - Regimen claro + Lambda CONFIRMED -> plan de ejecucion completo
        - Lambda CONTRADICTED -> BACKTRACK, sin subagentes de ejecucion
        - F4: si detecta deadlock potencial -> timeout + reinicio
        """
        start = time.time()

        regime     = phi_state.regime
        delta      = kappa_eval.delta
        signal     = omega_hyp.trading_signal
        l_verdict  = lambda_val.verdict

        # Seleccionar subagentes relevantes segun regimen
        active_subagents, tasks = self._plan_subagents(
            regime, delta, signal, l_verdict, omega_hyp, lambda_val
        )

        # Decision final
        decision, reasoning = self._decide(
            delta, signal, l_verdict, regime, lambda_val
        )

        orchestration = SigmaOrchestration(
            regime=regime,
            active_subagents=active_subagents,
            tasks=tasks,
            decision=decision,
            reasoning=reasoning,
            timestamp=datetime.now().isoformat(),
            total_duration_seconds=round(time.time() - start, 3)
        )

        logger.info(
            f"Sigma: decision={decision} subagentes={active_subagents} "
            f"regimen={regime} delta={delta:.4f}"
        )
        return orchestration

    def _plan_subagents(
        self, regime, delta, signal, l_verdict, omega_hyp, lambda_val
    ) -> tuple:
        """
        Planifica subagentes segun el regimen y la senal.
        Maximo MAX_SUBAGENTS simultaneos (del paper).
        """
        subagents = []
        tasks = []

        # CASH/HOLD: minimos subagentes — solo monitoreo
        if signal in ("CASH",) or delta < config.DELTA_BACKTRACK:
            subagents = ["monitor_regime"]
            tasks.append(SubagentTask(
                name="monitor_regime",
                task_type="ANALYSIS",
                input_data={"regime": regime, "delta": delta},
            ))
            return subagents, tasks

        # Lambda CONTRADICTED: backtrack, sin ejecucion
        if l_verdict == "CONTRADICTED":
            subagents = ["backtrack_manager"]
            tasks.append(SubagentTask(
                name="backtrack_manager",
                task_type="VALIDATION",
                input_data={"reason": "lambda_contradicted"},
            ))
            return subagents, tasks

        # Regimen activo con señal real
        if l_verdict == "CONFIRMED" and signal not in ("CASH",):
            subagents = ["risk_calculator", "position_sizer", "order_validator"]
            tasks = [
                SubagentTask(
                    name="risk_calculator",
                    task_type="ANALYSIS",
                    input_data={
                        "instruments": omega_hyp.instruments,
                        "allocation_pct": omega_hyp.allocation_pct,
                        "stop_loss_pct": config.STOP_LOSS_PCT
                    },
                ),
                SubagentTask(
                    name="position_sizer",
                    task_type="ANALYSIS",
                    input_data={
                        "allocation_pct": omega_hyp.allocation_pct,
                        "lambda_similarity": lambda_val.similarity,
                        "delta": delta
                    },
                ),
                SubagentTask(
                    name="order_validator",
                    task_type="VALIDATION",
                    input_data={
                        "instruments": omega_hyp.instruments,
                        "signal": signal
                    },
                ),
            ]

        # DEFENSIVE: subagentes de proteccion
        elif signal == "DEFENSIVE" or l_verdict == "UNCERTAIN":
            subagents = ["defensive_allocator", "risk_calculator"]
            tasks = [
                SubagentTask(
                    name="defensive_allocator",
                    task_type="ANALYSIS",
                    input_data={"instruments": omega_hyp.instruments or ["IEF"]},
                ),
                SubagentTask(
                    name="risk_calculator",
                    task_type="ANALYSIS",
                    input_data={"stop_loss_pct": config.STOP_LOSS_PCT},
                ),
            ]

        # Garantizar limite de subagentes (escenario F7)
        if len(subagents) > self.MAX_SUBAGENTS:
            logger.warning(
                f"Sigma: {len(subagents)} subagentes > MAX ({self.MAX_SUBAGENTS}). "
                f"Truncando — escenario F7 prevenido."
            )
            subagents = subagents[:self.MAX_SUBAGENTS]
            tasks     = tasks[:self.MAX_SUBAGENTS]

        return subagents, tasks

    def _decide(self, delta, signal, l_verdict, regime, lambda_val) -> tuple:
        """Decision final y reasoning determinista."""

        if l_verdict == "CONTRADICTED":
            return (
                "BACKTRACK",
                f"Lambda contradijo a Omega (sim={lambda_val.similarity:.4f} < 0.40). "
                f"Escenario F1 activado."
            )

        if delta < config.DELTA_BACKTRACK:
            return (
                "HOLD",
                f"Delta={delta:.4f} < {config.DELTA_BACKTRACK}. "
                f"Sin posiciones hasta que delta mejore."
            )

        if signal == "CASH" or regime == "INDETERMINATE":
            return (
                "HOLD",
                f"Senal={signal} regimen={regime}. "
                f"Lorenz/INDETERMINATE: no operar en caos."
            )

        if l_verdict == "UNCERTAIN":
            return (
                "DEFENSIVE",
                f"Lambda incierta (sim={lambda_val.similarity:.4f}). "
                f"Asignacion defensiva hasta confirmacion."
            )

        if l_verdict == "CONFIRMED" and signal in ("LONG", "LONG_PREPARE", "MEAN_REVERSION"):
            return (
                "EXECUTE",
                f"Lambda confirmed (sim={lambda_val.similarity:.4f}), "
                f"delta={delta:.4f}, senal={signal}. "
                f"Proceder con Tau para aprobacion."
            )

        if signal == "DEFENSIVE":
            return (
                "DEFENSIVE",
                f"Isomorfo phase_transition detectado. Asignacion defensiva."
            )

        return (
            "HOLD",
            f"Estado no clasificado: signal={signal} verdict={l_verdict}"
        )
