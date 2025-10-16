"""Threading library."""

import logging
from collections.abc import Callable
from threading import Event

logger = logging.getLogger(__name__)


def make_runner(
    target: Callable[..., None],
    *args: object,
    stop_event: Event,
    exceptions: list[BaseException],
) -> Callable[[], None]:
    """Wrap a function to be used for threading.

    Parameters
    ----------
    target : Callable[..., None]
        Function to be called in a thread.
    *args : object
        Arguments to be passed in the function.
    stop_event : Event
        Event sent to stop watching.
    exceptions: list[BaseException]
        List containing all exceptions caught.

    Returns
    -------
    Callable[[], None]
        Wrapped function.

    """

    def runner():
        logger.debug(f"Thread {target.__name__} has started")
        try:
            target(*args, stop_event)
        except Exception as e:
            logger.exception(f"Thread {target.__name__} crashed")
            exceptions.append(e)
            stop_event.set()
        finally:
            logger.debug(f"Thread {target.__name__} stopped")

    return runner
