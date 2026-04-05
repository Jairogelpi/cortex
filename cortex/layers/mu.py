"""
CAPA MU - Memoria selectiva con isolacion
Cortex V2, Fase 5

Fundamentado en consolidacion hipocampal (sleep replay):
El hipocampo no consolida todo lo que ocurre durante el dia.
Solo consolida los episodios que superan un umbral de relevancia.
Los estados de baja calidad se descartan. Los de alta calidad
se transfieren a memoria a largo plazo durante el "replay".

Referencia del paper (Seccion 2.2):
    Mu replica el 'sleep replay' hipocampal: consolida solo estados
    con delta > 0.70 y cambios de regimen confirmados.
    Reduce tokens de consolidacion un 50%.

Condicion de consolidacion (Seccion 2.1, ajustado pre-OSF):
    Solo consolida si delta >= 0.70 (DELTA_CONSOLIDATE)
    Si delta < 0.70: el estado no se guarda en memoria.

    Justificacion del ajuste 0.75 -> 0.70:
    El techo natural del delta en condiciones neutras es 0.73.
    Con 0.75, Mu nunca consolida en condiciones normales de mercado
    y H5 no es testeable. Con 0.70, consolida cuando el sistema
    opera 3 puntos sobre el techo natural. Ver CHANGELOG_UMBRALES.md.

Riesgo principal (Seccion 2, tabla):
    Contaminacion de memoria entre sesiones (escenario F2).
    Mu consolida datos de sesion A que contaminan evaluacion sesion B.
    Resultado: Sharpe inflado artificialmente. Falso positivo H4.

Mitigacion F2 (Seccion 4):
    Isolation layers: cada sesion tiene su propio namespace.
    Test de correlacion entre sesiones (rho < 0.3).
    Solo consolida estados de alta delta.

Hipotesis H5 del paper:
    Sesiones futuras con delta_inicial >= 0.71 vs 0.65 sin Mu.
    Mu mejora el punto de partida de cada sesion nueva.

Condicion de confianza (Seccion 5):
    Mu con isolacion confirmada (no leakage).
    Senal de alarma: correlacion entre memorias de sesiones > 0.3.
    Accion: reset de Mu, reconstruccion desde checkpoints.
"""
import json
import numpy as np
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional
from loguru import logger

from cortex.config import config
from cortex.layers.phi import PhiState
from cortex.layers.kappa import KappaEvaluation
from cortex.layers.lambda_ import LambdaValidation


# Directorio de persistencia de memoria
MEMORY_DIR = Path("data/memory")


@dataclass
class MemoryEntry:
    """
    Una entrada consolidada en memoria.
    Solo se crea cuando delta >= DELTA_CONSOLIDATE (0.70).
    """
    session_id: str                  # ID unico de sesion (namespace isolation)
    timestamp: str                   # cuando se consolido
    delta: float                     # score delta en el momento de consolidacion
    regime: str                      # regimen de mercado confirmado
    z_vector: list                   # vector Z de Phi en ese momento
    trading_signal: str              # senal que se consolida
    isomorph: str                    # isomorfo detectado por Omega
    isomorph_similarity: float       # similitud con el isomorfo
    lambda_verdict: str              # veredicto de Lambda
    lambda_similarity: float         # similitud de validacion de Lambda
    market_snapshot: dict            # indicadores de mercado en ese momento
    consolidation_reason: str        # por que se consolido este estado

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "MemoryEntry":
        return cls(**d)


@dataclass
class MuState:
    """Estado completo de la memoria Mu para una sesion."""
    session_id: str
    entries: list = field(default_factory=list)
    total_consolidated: int = 0
    total_rejected: int = 0
    last_delta: float = 0.0
    session_start: str = ""

    def add_entry(self, entry: MemoryEntry):
        self.entries.append(entry)
        self.total_consolidated += 1
        self.last_delta = entry.delta

    def reject(self, delta: float):
        self.total_rejected += 1
        self.last_delta = delta

    @property
    def consolidation_rate(self) -> float:
        total = self.total_consolidated + self.total_rejected
        return self.total_consolidated / total if total > 0 else 0.0

    def summary(self) -> str:
        lines = [
            f"Mu State | Sesion: {self.session_id}",
            f"  Entradas consolidadas: {self.total_consolidated}",
            f"  Rechazadas (delta bajo): {self.total_rejected}",
            f"  Tasa de consolidacion:   {self.consolidation_rate:.1%}",
            f"  Ultimo delta visto:      {self.last_delta:.4f}",
        ]
        if self.entries:
            last = self.entries[-1]
            lines.append(f"  Ultima entrada consolidada:")
            lines.append(f"    Regimen: {last.regime}")
            lines.append(f"    Senal:   {last.trading_signal}")
            lines.append(f"    Delta:   {last.delta:.4f}")
            lines.append(f"    Z7(valencia): {last.z_vector[6]:+.3f}")
        return "\n".join(lines)


class MuLayer:
    """
    Capa Mu: memoria selectiva con isolacion entre sesiones.

    Replica el mecanismo de sleep replay hipocampal:
    - Solo consolida estados con delta >= DELTA_CONSOLIDATE (0.70)
    - Cada sesion tiene su propio namespace (isolation)
    - Test de correlacion entre sesiones para detectar leakage
    - Reduce tokens de consolidacion 50% vs consolidar todo

    Persistencia: archivos JSON en data/memory/
    Cada sesion = un archivo separado (isolation layer).
    """

    DELTA_CONSOLIDATE = config.DELTA_CONSOLIDATE   # 0.70 (ajustado pre-OSF)
    MAX_ENTRIES_PER_SESSION = 100
    LEAKAGE_THRESHOLD = 0.3                        # rho max entre sesiones (paper)

    def __init__(self, session_id: Optional[str] = None):
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)

        if session_id is None:
            session_id = datetime.now().strftime("session_%Y%m%d_%H%M%S")

        self.session_id = session_id
        self.state = self._load_or_create_session(session_id)
        logger.info(
            f"Capa Mu inicializada: sesion={session_id} "
            f"entradas_previas={self.state.total_consolidated}"
        )

    def should_consolidate(self, kappa: KappaEvaluation) -> bool:
        """
        Decide si el estado actual debe consolidarse en memoria.

        Condicion: delta >= DELTA_CONSOLIDATE (0.70)
        Por debajo: sleep replay descarta el estado.
        """
        if kappa.delta >= self.DELTA_CONSOLIDATE:
            logger.info(
                f"Mu: delta={kappa.delta:.4f} >= {self.DELTA_CONSOLIDATE} "
                f"-> CONSOLIDAR"
            )
            return True
        else:
            logger.info(
                f"Mu: delta={kappa.delta:.4f} < {self.DELTA_CONSOLIDATE} "
                f"-> RECHAZAR (sleep replay no consolida estados de baja calidad)"
            )
            self.state.reject(kappa.delta)
            self._save_session()
            return False

    def consolidate(
        self,
        phi_state: PhiState,
        kappa: KappaEvaluation,
        lambda_val: LambdaValidation,
        reason: str = "delta >= 0.70"
    ) -> MemoryEntry:
        """
        Consolida el estado actual en memoria permanente.
        Solo se llama cuando should_consolidate() devuelve True.
        """
        isomorph_name = self._infer_isomorph_name(lambda_val)

        entry = MemoryEntry(
            session_id=self.session_id,
            timestamp=datetime.now().isoformat(),
            delta=kappa.delta,
            regime=phi_state.regime,
            z_vector=phi_state.to_vector().tolist(),
            trading_signal=kappa.decision,
            isomorph=isomorph_name,
            isomorph_similarity=lambda_val.similarity,
            lambda_verdict=lambda_val.verdict,
            lambda_similarity=lambda_val.similarity,
            market_snapshot=phi_state.raw_indicators,
            consolidation_reason=reason
        )

        self.state.add_entry(entry)
        self._save_session()

        logger.info(
            f"Mu: consolidado estado "
            f"delta={kappa.delta:.4f} regimen={phi_state.regime} "
            f"isomorfo={isomorph_name} lambda={lambda_val.verdict}"
        )
        return entry

    def get_relevant_memories(self, phi_state: PhiState, top_k: int = 3) -> list:
        """
        Recupera las memorias mas relevantes para el estado actual.
        Usa similitud coseno entre Z_actual y Z de cada entrada.

        Mecanismo de recuperacion para H5:
        'Sesiones futuras con delta_inicial >= 0.71 vs 0.65 sin Mu'
        """
        if not self.state.entries:
            logger.info("Mu: memoria vacia, no hay entradas relevantes")
            return []

        z_current = phi_state.to_vector()
        scored = []
        for entry in self.state.entries:
            z_entry = np.array(entry.z_vector)
            sim = self._cosine_sim(z_current, z_entry)
            scored.append((sim, entry))

        scored.sort(key=lambda x: -x[0])
        top = scored[:top_k]

        logger.info(f"Mu: recuperadas {len(top)} memorias relevantes")
        return [(sim, entry) for sim, entry in top]

    def check_isolation(self, other_session_ids: list) -> dict:
        """
        Test de isolacion entre sesiones (condicion de confianza, Seccion 5).
        Si rho >= 0.3: posible contaminacion (escenario F2).
        """
        if not self.state.entries:
            return {"isolation_ok": True, "reason": "sesion sin entradas"}

        z_current_session = np.array([e.z_vector for e in self.state.entries])
        results = {}

        for other_id in other_session_ids:
            other_state = self._load_session(other_id)
            if not other_state or not other_state.entries:
                results[other_id] = {"rho": 0.0, "ok": True}
                continue

            z_other = np.array([e.z_vector for e in other_state.entries])
            if len(z_current_session) > 0 and len(z_other) > 0:
                mean_current = z_current_session.mean(axis=0)
                mean_other   = z_other.mean(axis=0)
                rho = float(self._cosine_sim(mean_current, mean_other))
                ok  = rho < self.LEAKAGE_THRESHOLD
                results[other_id] = {"rho": round(rho, 4), "ok": ok}
                if not ok:
                    logger.warning(
                        f"Mu: posible leakage con sesion {other_id}: "
                        f"rho={rho:.4f} >= {self.LEAKAGE_THRESHOLD}"
                    )

        all_ok = all(v["ok"] for v in results.values())
        return {
            "isolation_ok": all_ok,
            "sessions_checked": results,
            "leakage_threshold": self.LEAKAGE_THRESHOLD
        }

    def get_initial_delta_estimate(self) -> float:
        """
        Estima el delta inicial basado en memorias previas.

        H5: 'Sesiones futuras con delta_inicial >= 0.71 vs 0.65 sin Mu'
        Con memorias consolidadas, el sistema parte de un estado informado.
        """
        if not self.state.entries:
            return config.DELTA_BACKTRACK  # sin memoria: umbral minimo

        recent = self.state.entries[-5:]
        weights = np.array([1.0, 1.2, 1.5, 1.8, 2.0][-len(recent):])
        deltas  = np.array([e.delta for e in recent])
        delta_estimate = float(np.average(deltas, weights=weights))

        logger.info(
            f"Mu: delta inicial estimado = {delta_estimate:.4f} "
            f"(basado en {len(recent)} memorias previas)"
        )
        return round(delta_estimate, 4)

    # ─── Persistencia ─────────────────────────────────────────────────────────

    def _session_path(self, session_id: str) -> Path:
        return MEMORY_DIR / f"{session_id}.json"

    def _load_or_create_session(self, session_id: str) -> MuState:
        path = self._session_path(session_id)
        if path.exists():
            return self._load_session(session_id) or MuState(
                session_id=session_id,
                session_start=datetime.now().isoformat()
            )
        return MuState(
            session_id=session_id,
            session_start=datetime.now().isoformat()
        )

    def _load_session(self, session_id: str) -> Optional[MuState]:
        path = self._session_path(session_id)
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            state = MuState(
                session_id=data["session_id"],
                total_consolidated=data.get("total_consolidated", 0),
                total_rejected=data.get("total_rejected", 0),
                last_delta=data.get("last_delta", 0.0),
                session_start=data.get("session_start", "")
            )
            for entry_dict in data.get("entries", []):
                state.entries.append(MemoryEntry.from_dict(entry_dict))
            return state
        except Exception as e:
            logger.error(f"Mu: error cargando sesion {session_id}: {e}")
            return None

    def _save_session(self):
        path = self._session_path(self.session_id)
        data = {
            "session_id": self.state.session_id,
            "session_start": self.state.session_start,
            "total_consolidated": self.state.total_consolidated,
            "total_rejected": self.state.total_rejected,
            "last_delta": self.state.last_delta,
            "entries": [e.to_dict() for e in self.state.entries]
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    # ─── Utilidades ───────────────────────────────────────────────────────────

    def _cosine_sim(self, a: np.ndarray, b: np.ndarray) -> float:
        na, nb = np.linalg.norm(a), np.linalg.norm(b)
        if na == 0 or nb == 0:
            return 0.0
        return float(np.dot(a, b) / (na * nb))

    def _infer_isomorph_name(self, lambda_val: LambdaValidation) -> str:
        """Infiere el nombre del isomorfo desde el z_reference de Lambda."""
        from cortex.layers.omega import PHYSICAL_ISOMORPHS
        z_ref = np.array(lambda_val.z_reference)
        best, best_sim = "unknown", -1.0
        for name, iso in PHYSICAL_ISOMORPHS.items():
            sim = self._cosine_sim(z_ref, iso["Z"])
            if sim > best_sim:
                best_sim, best = sim, name
        return best


def test_mu():
    """Prueba la capa Mu con el pipeline completo."""
    from cortex.market_data import MarketData
    from cortex.layers.phi import PhiLayer
    from cortex.layers.kappa import KappaLayer
    from cortex.layers.omega import OmegaLayer
    from cortex.layers.lambda_ import LambdaLayer

    print("\n" + "="*55)
    print("  CORTEX V2 - Test Capa Mu (memoria selectiva)")
    print("="*55 + "\n")

    md         = MarketData()
    indicators = md.get_regime_indicators()
    account    = md.get_account()

    phi_layer  = PhiLayer()
    phi_state  = phi_layer.factorize(indicators)

    kappa_layer = KappaLayer()
    kappa_eval  = kappa_layer.evaluate(
        phi_state, account["portfolio_value"],
        initial_value=100_000.0,
        spy_benchmark_return=indicators.get("momentum_21d_pct", 0.0) / 3.0,
        open_positions=[]
    )

    omega_layer = OmegaLayer()
    hypothesis  = omega_layer.generate_hypothesis(phi_state)

    lambda_layer = LambdaLayer()
    lambda_val   = lambda_layer.validate(hypothesis, phi_state)

    print(f"Pipeline ejecutado:")
    print(f"  Phi:    regimen={phi_state.regime} confianza={phi_state.confidence:.2f}")
    print(f"  Kappa:  delta={kappa_eval.delta:.4f} decision={kappa_eval.decision}")
    print(f"  Omega:  isomorfo={hypothesis.best_isomorph} senal={hypothesis.trading_signal}")
    print(f"  Lambda: veredicto={lambda_val.verdict} sim={lambda_val.similarity:.4f}")

    print(f"\nInicializando Mu (memoria selectiva)...\n")
    mu = MuLayer()
    print(mu.state.summary())

    print(f"\nDecision de consolidacion:")
    print(f"  Delta actual          = {kappa_eval.delta:.4f}")
    print(f"  Umbral consolidacion  = {config.DELTA_CONSOLIDATE}  (ajustado 0.75->0.70 pre-OSF)")

    should = mu.should_consolidate(kappa_eval)

    if should:
        print(f"  -> CONSOLIDAR: delta >= {config.DELTA_CONSOLIDATE}")
        entry = mu.consolidate(phi_state, kappa_eval, lambda_val)
        print(f"     Timestamp: {entry.timestamp}")
        print(f"     Delta:     {entry.delta:.4f}")
        print(f"     Regimen:   {entry.regime}")
        print(f"     Isomorfo:  {entry.isomorph}")
        print(f"     Senal:     {entry.trading_signal}")
    else:
        print(
            f"  -> NO CONSOLIDAR: delta={kappa_eval.delta:.4f} < {config.DELTA_CONSOLIDATE}"
        )
        print(f"     (Sleep replay no guarda estados de baja calidad)")
        print(f"     (Con regimen INDETERMINATE y sin posiciones, correcto)")

    delta_est = mu.get_initial_delta_estimate()
    print(f"\nDelta inicial estimado proxima sesion: {delta_est:.4f}")

    relevant = mu.get_relevant_memories(phi_state, top_k=3)
    print(f"Memorias relevantes encontradas: {len(relevant)}")

    print(f"\nEstado final de Mu:")
    print(mu.state.summary())

    print("\n" + "="*55)
    print("  Mu OK -> Siguiente: capa Sigma (orquestador)")
    print("="*55 + "\n")
    return mu


if __name__ == "__main__":
    test_mu()
