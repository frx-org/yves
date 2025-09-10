from types import FrameType


def signal_handler(signal: int, frame: FrameType | None):
    """Handle signal. For now we suppose that we only catch SIGTERM and SIGINT to cleanly exit the program.
    This function is supposed to be called with `signal.signal(SIG, signal_handler)`

    Parameters
    ----------
    signal : int
        First argument needed by `signal.signal`
    frame : FrameType | None
        Second argument needed by `signal.signal`

    """
    from sys import exit

    exit(0)
