from __future__ import annotations
from dataclasses import dataclass

@dataclass
class FakeModel:
    """Deterministic stand-in for a model runtime.

    The kernel must be testable without Ollama, OpenAI, network access, or model weights.
    """
    responses: list[str]

    def __post_init__(self) -> None:
        self._index = 0

    def infer(self, prompt: str) -> str:
        if not self.responses:
            return ""
        response = self.responses[min(self._index, len(self.responses) - 1)]
        self._index += 1
        return response
