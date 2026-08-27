from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from collections import defaultdict, deque

@dataclass(frozen=True)
class Event:
    topic: str
    payload: dict[str, Any] = field(default_factory=dict)

class EventBus:
    def __init__(self) -> None:
        self._queues: dict[str, deque[Event]] = defaultdict(deque)

    def publish(self, event: Event) -> None:
        self._queues[event.topic].append(event)

    def take(self, topic: str) -> Event | None:
        queue = self._queues.get(topic)
        if not queue:
            return None
        return queue.popleft()

    def pending(self, topic: str) -> int:
        return len(self._queues.get(topic, ()))
