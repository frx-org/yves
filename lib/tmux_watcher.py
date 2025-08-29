from dataclasses import dataclass, field
import logging
from types import FrameType
from datetime import datetime
import subprocess
import os
import json

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

<<<<<<< HEAD

def update_from_config(watcher: TmuxWatcher, config_path: str) -> None:
    """Read a config file and update `watcher`.

    Parameters
    ----------
    watcher : TmuxWatcher
        Watcher values to be updated
    config_path : str
        Path to the configuration file

    """
    from lib.cfg import parse_config

    cfg = parse_config(config_path)

    watcher.panes = cfg.getlist("tmux", "panes")  # type: ignore
    watcher.output_file = cfg["tmux"]["output_file"]
    watcher.capture_full_output = cfg.getbool("tmux", "capture_full_output")  # type: ignore


=======
>>>>>>> b4b64f6 (feat: add possibility to monitor realtime all tmux panes.)
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

    # Load existing JSON if the file exists
    if os.path.exists(watcher.output_file):
        with open(watcher.output_file, "r", encoding="utf-8") as f:
            try:
                all_events = json.load(f)
            except json.JSONDecodeError:
                all_events = []
    else:
        all_events = []

    # Append new completed commands
    for cmd in completed_commands:
        timestamp_str = int(cmd["timestamp"].timestamp())
        all_events.append(
            {
                "event_type": "command_completed",
                "timestamp": timestamp_str,
                "pane": cmd["pane"],
                "command": cmd["command"],
                # Split output into lines for easier processing later
                "output": cmd["output"].splitlines(),
            }
        )

    # Write updated JSON back to file
    with open(watcher.output_file, "w", encoding="utf-8") as f:
        json.dump(all_events, f, ensure_ascii=False, indent=2)

    # Log info
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
    Continuously monitor and update the list of all active tmux pane IDs.
    Prints added and removed panes, including when all panes are closed.

    Parameters
    ----------
    watcher : TmuxWatcher
        The watcher instance to update.
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
        print(f"Error getting active tmux panes: {e}")
        current_panes = set()
    added = current_panes - previous_panes
    removed = previous_panes - current_panes
    if added:
        print(f"New panes detected: {added}")
    if removed:
        print(f"Panes closed: {removed}")
    watcher.panes = list(current_panes)
    if len(watcher.panes)==0:
        print('[WARNING] No active tmux panes detected.')
        while result.returncode != 0:
            result = subprocess.run(
                ["tmux", "list-panes", "-a", "-F", "#S:#I.#P"],
                capture_output=True,
                text=True,
            )
            sleep(timeout)

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
