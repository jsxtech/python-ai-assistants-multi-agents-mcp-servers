from typing import Dict, List, Callable
from collections import deque
import logging
import time

logger = logging.getLogger(__name__)


class EventBus:
    MAX_HISTORY = 5000

    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}
        self.event_history = deque(maxlen=self.MAX_HISTORY)

    def subscribe(self, event_type: str, handler: Callable):
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Callable):
        if event_type in self.subscribers:
            try:
                self.subscribers[event_type].remove(handler)
            except ValueError:
                pass  # Handler was not subscribed — no-op

    def publish(self, event_type: str, data: Dict):
        event = {
            "type": event_type,
            "data": data,
            "timestamp": time.time()
        }
        self.event_history.append(event)

        if event_type in self.subscribers:
            # Iterate over a snapshot to prevent mutation during iteration
            # (a handler could call subscribe/unsubscribe)
            handlers = self.subscribers[event_type][:]
            for handler in handlers:
                try:
                    handler(event)
                except Exception as e:
                    # Log but don't let one bad handler block others
                    logger.error(
                        f"Handler {handler!r} failed for event '{event_type}': {e}"
                    )

    def get_events(self, event_type: str = None, since: float = None) -> List[Dict]:
        events = list(self.event_history)
        if event_type:
            events = [e for e in events if e["type"] == event_type]
        if since:
            events = [e for e in events if e["timestamp"] > since]
        return events
