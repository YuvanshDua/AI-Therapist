import time
from collections import deque
from threading import Lock
from typing import Deque, Dict, List, Tuple


class ConversationStore:
    """
    Simple in-memory conversation store with TTL and bounded history per session.
    """

    def __init__(self, max_messages: int = 50, ttl_seconds: int = 3600):
        self.max_messages = max_messages
        self.ttl_seconds = ttl_seconds
        self._messages: Dict[str, Deque[Tuple[str, str, float]]] = {}
        self._lock = Lock()

    def _purge_expired(self):
        now = time.time()
        expired = [sid for sid, msgs in self._messages.items() if msgs and now - msgs[-1][2] > self.ttl_seconds]
        for sid in expired:
            del self._messages[sid]

    def add(self, session_id: str, role: str, content: str):
        with self._lock:
            self._purge_expired()
            if session_id not in self._messages:
                self._messages[session_id] = deque(maxlen=self.max_messages)
            self._messages[session_id].append((role, content, time.time()))

    def get(self, session_id: str) -> List[Dict[str, str]]:
        with self._lock:
            self._purge_expired()
            if session_id not in self._messages:
                return []
            return [{"role": role, "content": content} for role, content, _ in self._messages[session_id]]


conversation_store = ConversationStore()
