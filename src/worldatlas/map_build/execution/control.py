"""Share progress output and cancellation with a stage's worker threads."""

import signal
import threading
from collections.abc import Callable, Generator
from contextlib import contextmanager
from contextvars import ContextVar
from types import FrameType
from typing import TextIO

_current: ContextVar[tuple[threading.Event, TextIO | None, threading.Lock] | None] = (
    ContextVar('map_build_stage', default=None)
)


def install_build_stop_handlers(request_cancel: Callable[[], None]) -> None:
    """Install the build command's Ctrl+C and SIGTERM handlers.

    Call from the main thread of the command-line process.

    Args:
        request_cancel: Callback that tells the workers to stop at their next check.
    """

    def stop(signum: int, frame: FrameType | None) -> None:
        """Ask workers to stop and interrupt the command's main thread.

        Args:
            signum: Signal number received by the command.
            frame: Python frame supplied by the signal handler.

        Raises:
            KeyboardInterrupt: Exit the command through its cleanup code.
        """
        request_cancel()
        raise KeyboardInterrupt(f'interrupted by signal {signum}')

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)


@contextmanager
def stage(
    cancelled: threading.Event | None = None, log: TextIO | None = None
) -> Generator[threading.Event]:
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
