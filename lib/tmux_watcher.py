from dataclasses import dataclass, field
import logging
from types import FrameType
from datetime import datetime
import subprocess

logger = logging.getLogger(__name__)


@dataclass
class TmuxWatcher:
    """Tmux pane monitor that captures tmux pane commands and outputs.
    Attributes
    ----------
    panes: List of tmux panes to monitor
    output_file: Output file for command outputs
    capture_full_output: If True, capture full pane content instead of just last command
    pane_states: Dictionary to hold the state of each tmux pane
    """

    panes: list[str] = field(default_factory=list)
    output_file: str = "changes.txt"
    capture_full_output: bool = False
    pane_states: dict[str, dict[str, object]] = field(default_factory=dict)


def check_for_completed_commands(watcher: TmuxWatcher) -> list[dict[str, object]]:
    """
    Check all monitored panes for newly completed commands.

    Parameters
    ----------
    watcher : TmuxWatcher
        The watcher instance containing pane states and configuration.

    Returns
    -------
    list of dict
        List of completed commands with pane, command, output, and timestamp.
    """
    from lib.tmux import (
        extract_last_command_output,
        is_command_finished,
        get_command_from_content,
        get_tmux_pane_content,
    )

    completed_commands = []

    for pane in watcher.panes:
        current_content = get_tmux_pane_content(pane)
        if current_content is None:
            continue

        if pane not in watcher.pane_states:
            watcher.pane_states[pane] = {
                "last_command": "",
                "waiting_for_completion": False,
            }

        pane_state = watcher.pane_states[pane]

        if is_command_finished(current_content):
            command = get_command_from_content(current_content)

            if command and command != pane_state["last_command"]:
                if watcher.capture_full_output:
                    output = current_content
                else:
                    output = extract_last_command_output(current_content)

                if output and output.strip():
                    completed_commands.append(
                        {
                            "pane": pane,
                            "command": command,
                            "output": output,
                            "timestamp": datetime.now(),
                        }
                    )

                pane_state["last_command"] = command
                pane_state["waiting_for_completion"] = False

    return completed_commands


def write_commands_to_file(
    watcher: TmuxWatcher, completed_commands: list[dict[str, object]]
) -> None:
    """
    Write completed commands and their outputs to the output file.

    Parameters
    ----------
    watcher : TmuxWatcher
        The watcher instance with the output file path.
    completed_commands : list of dict
        List of completed command objects to write.
    """
    if not completed_commands:
        return

    with open(watcher.output_file, "a", encoding="utf-8") as f:
        for cmd in completed_commands:
            timestamp = cmd["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"\n{'=' * 80}\n")
            f.write(f"COMMAND COMPLETED AT: {timestamp} | PANE: {cmd['pane']}\n")
            f.write(f"COMMAND: {cmd['command']}\n")
            f.write(f"{'=' * 80}\n")
            f.write(cmd["output"])
            f.write(f"\n{'=' * 80}\n")

    logger.info(f"Captured {len(completed_commands)} completed commands")
    for cmd in completed_commands:
        logger.info(f"  [{cmd['pane']}] {cmd['command']}")


def signal_handler(signal: int, frame: FrameType | None):
    """
    Handle signal for clean exit (SIGTERM, SIGINT).

    Parameters
    ----------
    signal : int
        Signal number (from signal.signal).
    frame : FrameType or None
        Current stack frame (from signal.signal).
    """
    from sys import exit

    exit(0)


def get_active_tmux_panes(watcher: TmuxWatcher, timeout: int):
    """
    Continuously monitor and update the list of all active tmux pane indices.
    Prints added and removed panes, including when all panes are closed.

    Parameters
    ----------
    watcher : TmuxWatcher
        The watcher instance to update.
    timeout : int
        The timeout duration for checking active panes.
    """
    from time import sleep

    previous_panes = set(watcher.panes)
    try:
        result = subprocess.run(
            ["tmux", "list-panes", "-a", "-F", "#S:#I.#P"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            current_panes = set(result.stdout.strip().splitlines())
        else:
            current_panes = set()
    except Exception as e:
        logger.error(f"Error getting active tmux panes: {e}")
        current_panes = set()
    added = current_panes - previous_panes
    removed = previous_panes - current_panes
    if added:
        logger.info(f"New panes detected: {added}")
    if removed:
        logger.info(f"Panes closed: {removed}")
    watcher.panes = list(current_panes)
    if len(watcher.panes) == 0:
        logger.warning("No active tmux panes detected.")
        while result.returncode != 0:
            result = subprocess.run(
                ["tmux", "list-panes", "-a", "-F", "#S:#I.#P"],
                capture_output=True,
                text=True,
            )
            sleep(timeout)


def watch(watcher: TmuxWatcher, timeout: int = 1) -> None:
    """
    Start the main watching loop to monitor panes continuously.

    Parameters
    ----------
    watcher : TmuxWatcher
        The watcher instance to monitor.
    timeout : int, optional
        Timeout in seconds between checks (default is 1).
    """

    from signal import SIGINT, SIGTERM, signal
    from time import sleep

    initial_panes = watcher.panes.copy()
    if initial_panes:
        logger.info(f"Watching tmux panes: {', '.join(initial_panes)}")
    else:
        logger.info("No specified panes to watch. Will monitor all tmux panes")
    logger.info(f"Output file: {watcher.output_file}")
    logger.info(
        f"Capture mode: {'Full output' if watcher.capture_full_output else 'Last command only'}"
    )
    logger.info("Press Ctrl+C to stop watching...")
    logger.info("-" * 50)

    signal(SIGTERM, signal_handler)
    signal(SIGINT, signal_handler)

    while True:
        if not initial_panes:
            get_active_tmux_panes(watcher, timeout)
        completed_commands = check_for_completed_commands(watcher)
        if completed_commands:
            write_commands_to_file(watcher, completed_commands)
        sleep(timeout)
