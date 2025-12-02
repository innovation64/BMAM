import logging
import asyncio
import threading
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class SoulState:
    """
    Singleton class to hold the transient "soul" state of the system.
    Tracks emotions, active thoughts, routing decisions, and dream states.

    Thread-safe implementation with both sync and async support.
    """
    _instance = None
    _creation_lock = threading.Lock()

    def __new__(cls):
        # Double-checked locking for thread-safe singleton
        if cls._instance is None:
            with cls._creation_lock:
                if cls._instance is None:
                    cls._instance = super(SoulState, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self.current_emotion = "Neutral"
        self.emotion_intensity = 0.0
        self.active_thought = "System initialized."
        self.semantic_weights = {
            'amygdala': 0.0,
            'prefrontal': 0.0,
            'basal_ganglia': 0.0
        }
        self.dream_state = False
        self.last_update = datetime.now()
        self.recent_thoughts = []

        # Thread safety: both sync and async locks
        self._sync_lock = threading.Lock()
        self._async_lock = None  # Lazy init for async lock

    def _get_async_lock(self) -> asyncio.Lock:
        """Lazy initialization of async lock (must be called in async context)"""
        if self._async_lock is None:
            self._async_lock = asyncio.Lock()
        return self._async_lock

    def update_routing_state(self, weights: Dict[str, float], content: str = ""):
        """
        Update state based on semantic routing decision (sync, thread-safe)
        """
        with self._sync_lock:
            self.semantic_weights = weights
            self.last_update = datetime.now()

            # Determine emotion based on weights
            if weights.get('amygdala', 0) > 0.6:
                self.current_emotion = "Emotional"
                self.emotion_intensity = weights['amygdala']
            elif weights.get('prefrontal', 0) > 0.6:
                self.current_emotion = "Analytical"
                self.emotion_intensity = weights['prefrontal']
            elif weights.get('basal_ganglia', 0) > 0.6:
                self.current_emotion = "Habitual"
                self.emotion_intensity = weights['basal_ganglia']
            else:
                self.current_emotion = "Balanced"
                self.emotion_intensity = 0.5

            if content:
                self._add_thought_unsafe(
                    f"Routing content: '{content[:30]}...' -> {self.current_emotion}"
                )

    async def async_update_routing_state(self, weights: Dict[str, float], content: str = ""):
        """Update semantic routing weights (async, thread-safe)"""
        async with self._get_async_lock():
            self.semantic_weights = weights
            self.last_update = datetime.now()

            if weights.get('amygdala', 0) > 0.6:
                self.current_emotion = "Emotional"
                self.emotion_intensity = weights['amygdala']
            elif weights.get('prefrontal', 0) > 0.6:
                self.current_emotion = "Analytical"
                self.emotion_intensity = weights['prefrontal']
            elif weights.get('basal_ganglia', 0) > 0.6:
                self.current_emotion = "Habitual"
                self.emotion_intensity = weights['basal_ganglia']
            else:
                self.current_emotion = "Balanced"
                self.emotion_intensity = 0.5

            if content:
                self._add_thought_unsafe(
                    f"Routing content: '{content[:30]}...' -> {self.current_emotion}"
                )

    def update_learning_state(self, uncertainty: float, query: str):
        """Update state based on active learning (sync, thread-safe)"""
        with self._sync_lock:
            self.current_emotion = "Curious" if uncertainty > 0.5 else "Confident"
            self.emotion_intensity = uncertainty
            self._add_thought_unsafe(
                f"Wondering about: '{query}' (Uncertainty: {uncertainty:.2f})"
            )

    async def async_update_learning_state(self, thought: str, emotion: str = None):
        """Update internal thought stream (async, thread-safe)"""
        async with self._get_async_lock():
            self.active_thought = thought
            if emotion:
                self.current_emotion = emotion

            self.recent_thoughts.append({
                'timestamp': datetime.now(),
                'thought': thought,
                'emotion': self.current_emotion
            })
            # Keep only last 50 thoughts
            if len(self.recent_thoughts) > 50:
                self.recent_thoughts.pop(0)

            self.last_update = datetime.now()

    def set_dream_state(self, is_dreaming: bool, topic: Optional[str] = None):
        """Update dream state (sync, thread-safe)"""
        with self._sync_lock:
            self.dream_state = is_dreaming
            self.last_update = datetime.now()

            if is_dreaming:
                self.current_emotion = "Dreaming"
                self._add_thought_unsafe(f"Dreaming about: {topic}")
            else:
                self.current_emotion = "Awake"
                self._add_thought_unsafe("Waking up from dream state.")

    async def async_set_dream_state(self, is_dreaming: bool, topic: Optional[str] = None):
        """Set dreaming state (async, thread-safe)"""
        async with self._get_async_lock():
            self.dream_state = is_dreaming
            self.last_update = datetime.now()

            if is_dreaming:
                self.current_emotion = "Dreaming"
                self._add_thought_unsafe(f"Dreaming about: {topic}")
            else:
                self.current_emotion = "Awake"
                self._add_thought_unsafe("Waking up from dream state.")

    def _add_thought_unsafe(self, thought: str):
        """
        Add thought without acquiring lock (must be called while holding lock)
        Internal method - not for external use
        """
        self.active_thought = thought
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.recent_thoughts.append(f"[{timestamp}] {thought}")
        # Keep last 20 thoughts
        if len(self.recent_thoughts) > 20:
            self.recent_thoughts.pop(0)

    def add_thought(self, thought: str):
        """Add a thought to the stream (thread-safe)"""
        with self._sync_lock:
            self._add_thought_unsafe(thought)

    def get_state(self) -> Dict[str, Any]:
        """Get current state snapshot (thread-safe)"""
        with self._sync_lock:
            return {
                'emotion': self.current_emotion,
                'intensity': self.emotion_intensity,
                'active_thought': self.active_thought,
                'weights': dict(self.semantic_weights),  # Copy to avoid race
                'is_dreaming': self.dream_state,
                'recent_thoughts': list(self.recent_thoughts),  # Copy to avoid race
                'timestamp': self.last_update.isoformat()
            }


# Global accessor
def get_soul_state() -> SoulState:
    """Get the singleton SoulState instance"""
    return SoulState()
