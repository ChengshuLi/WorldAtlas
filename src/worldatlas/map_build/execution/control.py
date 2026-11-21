"""Share progress output and cancellation with a stage's worker threads."""

from contextlib import contextmanager
from contextvars import ContextVar
import threading

_current = ContextVar('map_build_stage', default=None)


@contextmanager
def stage(cancelled=None, log=None):
    """Expose the cancellation event to code in the current stage.

    Args:
        cancelled: Optional event. Reuse the active stage when omitted.
        log: Optional stream for progress messages.

    Yields:
        The event used to request cancellation.
    """
    active = _current.get()
    if cancelled is None and log is None and active is not None:
        yield active[0]
        return
    if cancelled is None:
        cancelled = active[0] if active is not None else threading.Event()
    token = _current.set((cancelled, log, threading.Lock()))
    try:
        yield cancelled
    finally:
        _current.reset(token)


def emit(*values, **options):
    active = _current.get()
    if active is None:
        print(*values, **options)
        return
    _, log, lock = active
    if log is not None:
        options.setdefault('file', log)
    with lock:
        print(*values, **options)


def check_cancelled():
    active = _current.get()
    if active is not None and active[0].is_set():
        raise InterruptedError('pipeline cancelled')
