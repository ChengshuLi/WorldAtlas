"""Share progress output and cancellation with a stage's worker threads."""

import threading
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import TextIO

_current: ContextVar[tuple[threading.Event, TextIO | None, threading.Lock] | None] = (
    ContextVar('map_build_stage', default=None)
)


@contextmanager
def stage(
    cancelled: threading.Event | None = None, log: TextIO | None = None
) -> Iterator[threading.Event]:
    """Give the current stage a cancellation event and progress stream.

    Args:
        cancelled: Event to use. Inherit the active event or create one when
            omitted.
        log: Stream for progress output, if provided.

    Yields:
        Event that workers can check to see whether to stop.
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


def emit(message: str, *, flush: bool = False) -> None:
    """Print progress, keeping messages from stage workers separate.

    Args:
        message: Progress message to print.
        flush: Write the message to the output stream immediately.
    """
    active = _current.get()
    if active is None:
        print(message, flush=flush)
        return
    _, log, lock = active
    with lock:
        print(message, file=log, flush=flush)


def check_cancelled() -> None:
    """Stop the current calculation when the stage has been cancelled.

    Raises:
        InterruptedError: A cancellation was requested.
    """
    active = _current.get()
    if active is not None and active[0].is_set():
        raise InterruptedError('pipeline cancelled')
