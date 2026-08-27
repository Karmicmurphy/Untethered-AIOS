from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field

@dataclass
class FakeModel:
    """Deterministic stand-in for a model runtime.

    The kernel must be testable without Ollama, OpenAI, network access, or model weights.
    """
    responses: list[str]
    calls: list[str] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        self._index = 0

    def infer(self, prompt: str) -> str:
        self.calls.append(prompt)
        if not self.responses:
            return ""
        response = self.responses[min(self._index, len(self.responses) - 1)]
        self._index += 1
        return response
