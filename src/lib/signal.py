"""System signal library."""

from signal import SIGINT, SIGTERM, signal
from threading import Event
from types import FrameType


def setup_signal_handler(stop_event: Event):
    """Signal handlers to catch specific events.

    Parameters
    ----------
    stop_event : Event
        Event to quit threads loop

    """

    def signal_handler(signal: int, frame: FrameType | None):
        """Handle signal.

        For now we suppose that we only catch SIGTERM and SIGINT to cleanly exit the program.
        This function is supposed to be called with `signal.signal(SIG, signal_handler)`

        Parameters
        ----------
        signal : int
            First argument needed by `signal.signal`
        frame : FrameType | None
            Second argument needed by `signal.signal`

        """
        stop_event.set()

    signal(SIGTERM, signal_handler)
    signal(SIGINT, signal_handler)
