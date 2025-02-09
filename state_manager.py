from typing import Dict, Any, Optional
from threading import Lock


class StateManager:
    _instance = None
    _lock = Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(StateManager, cls).__new__(cls)
                cls._instance._state = {}
                cls._instance._order_states = {}
            return cls._instance

    def set_state(self, order_id: str, state: Dict[str, Any]) -> None:
        with self._lock:
            self._order_states[order_id] = state

    def get_state(self, order_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._order_states.get(order_id)

    def update_state(self, order_id: str, updates: Dict[str, Any]) -> None:
        with self._lock:
            current_state = self._order_states.get(order_id, {})
            current_state.update(updates)
            self._order_states[order_id] = current_state

    def clear_state(self, order_id: str) -> None:
        with self._lock:
            if order_id in self._order_states:
                del self._order_states[order_id]


# Global instance
state_manager = StateManager()