"""
Token tracker global para Cortex V2.
Registra tokens reales de cada llamada LLM via OpenRouter.

Uso:
    from cortex.token_tracker import token_tracker
    # En cada capa, tras la llamada:
    token_tracker.add("phi", response.usage.prompt_tokens, response.usage.completion_tokens)
    # Al final del pipeline:
    summary = token_tracker.summary()
"""
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class LayerTokens:
    layer: str
    tokens_in: int = 0
    tokens_out: int = 0

    @property
    def total(self):
        return self.tokens_in + self.tokens_out


class TokenTracker:
    """Acumula tokens reales por capa en una sesion."""

    def __init__(self):
        self._layers: Dict[str, LayerTokens] = {}

    def reset(self):
        self._layers = {}

    def add(self, layer: str, tokens_in: int, tokens_out: int):
        if layer not in self._layers:
            self._layers[layer] = LayerTokens(layer)
        self._layers[layer].tokens_in  += tokens_in
        self._layers[layer].tokens_out += tokens_out

    def total(self) -> int:
        return sum(lt.total for lt in self._layers.values())

    def summary(self) -> dict:
        return {
            "total": self.total(),
            "by_layer": {
                layer: {"in": lt.tokens_in, "out": lt.tokens_out, "total": lt.total}
                for layer, lt in self._layers.items()
            }
        }


# Instancia global — se resetea al inicio de cada pipeline
token_tracker = TokenTracker()
