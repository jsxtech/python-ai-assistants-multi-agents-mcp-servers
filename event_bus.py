from typing import Dict, List, Callable
import time

class EventBus:
    def __init__(self):
        self.subscribers = {}
        self.event_history = []
    
    def subscribe(self, event_type: str, handler: Callable):
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)
    
    def unsubscribe(self, event_type: str, handler: Callable):
        if event_type in self.subscribers:
            self.subscribers[event_type].remove(handler)
    
    def publish(self, event_type: str, data: Dict):
        event = {
            "type": event_type,
            "data": data,
            "timestamp": time.time()
        }
        self.event_history.append(event)
        
        if event_type in self.subscribers:
            for handler in self.subscribers[event_type]:
                handler(event)
    
    def get_events(self, event_type: str = None, since: float = None) -> List[Dict]:
        events = self.event_history
        if event_type:
            events = [e for e in events if e["type"] == event_type]
        if since:
            events = [e for e in events if e["timestamp"] > since]
        return events
