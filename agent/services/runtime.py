"""Per-run progress, cancellation and deadline propagation."""
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Callable
import time

class RunCancelled(Exception):
    pass

@dataclass
class RunContext:
    emit: Callable = lambda **event: None
    cancelled: Callable = lambda: False
    deadline: float = field(default_factory=lambda: time.monotonic() + 240)
    checkpoint: Callable = lambda state: None
    cache: object = None
    cache_lease: str = ""
    refresh: bool = False

context = ContextVar("research_context", default=None)

def remaining(limit=25):
    ctx = context.get()
    if ctx and ctx.cancelled():
        raise RunCancelled()
    seconds = min(limit, ctx.deadline - time.monotonic()) if ctx else limit
    if seconds <= 0:
        raise TimeoutError("Research time budget exhausted")
    return max(0.01, seconds)

def emit(event_type="progress", **event):
    ctx = context.get()
    if ctx:
        ctx.emit(event_type=event_type, **event)
