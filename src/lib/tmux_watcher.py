"""Tmux watcher library."""

import json
import logging
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from threading import Event

logger = logging.getLogger(__name__)


@dataclass
class TmuxWatcher:
    """Tmux pane monitor that captures tmux pane commands and outputs.

    Attributes
    ----------
    enable: Enable the watcher or not
    panes: List of tmux panes to monitor
    output_file: Output file for command outputs
    capture_full_output: If True, capture full pane content instead of just last command
    pane_states: Dictionary to hold the state of each tmux pane
    """

    enable: bool = True
    panes: list[str] = field(default_factory=list)
    output_file: str = "changes.json"
    capture_full_output: bool = False
    pane_states: dict[str, dict[str, object]] = field(default_factory=dict)


def update_from_config(watcher: TmuxWatcher, config_path: str) -> None:
    """Read a config file and update `watcher`.

    Parameters
    ----------
    watcher : TmuxWatcher
        Watcher values to be updated
    config_path : str
        Path to the configuration file

    """
    from lib.cfg import convert_to_list, parse_config

    cfg = parse_config(config_path)

    watcher.enable = cfg.getboolean("tmux", "enable")
    watcher.panes = convert_to_list(cfg.get("tmux", "panes"))
    watcher.output_file = os.path.expanduser(cfg["tmux"]["output_file"])
    watcher.capture_full_output = cfg.getboolean("tmux", "capture_full_output")  # type: ignore


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
        get_command_from_content,
        get_tmux_pane_content,
        is_command_finished,
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
        timestamp = cmd["timestamp"]
        if not isinstance(timestamp, datetime):
            raise TypeError("`timestamp` is not `datetime`")

        output = cmd["output"]
        if not isinstance(output, str):
            raise TypeError("`output` is not `str`")

        timestamp_str = int(timestamp.timestamp())
        all_events.append(
            {
                "event_type": "command_completed",
                "timestamp": timestamp_str,
                "pane": cmd["pane"],
                "command": cmd["command"],
                # Split output into lines for easier processing later
                "output": output.splitlines(),
            }
        )

    output_dir = os.path.dirname(watcher.output_file)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    # Write updated JSON back to file
    with open(watcher.output_file, "w", encoding="utf-8") as f:
        json.dump(all_events, f, ensure_ascii=False, indent=2)

    logger.debug(f"Captured {len(completed_commands)} completed commands")
    for cmd in completed_commands:
        logger.debug(f"[{cmd['pane']}] {cmd['command']}")


def get_active_tmux_panes(watcher: TmuxWatcher, timeout: int):
    """Continuously monitor and update the list of all active tmux pane indices. Prints added and removed panes, including when all panes are closed.

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
        if result is None:
            current_panes = set()
        elif result.returncode == 0:
            current_panes = set(result.stdout.strip().splitlines())
        else:
            current_panes = set()
    except Exception as e:
        logger.error(f"Error getting active tmux panes: {e}")
        current_panes = set()
    added = current_panes - previous_panes
    removed = previous_panes - current_panes
    if added:
        logger.debug(f"New panes detected: {added}")
    if removed:
        logger.debug(f"Panes closed: {removed}")
    watcher.panes = list(current_panes)
    if len(watcher.panes) == 0:
        logger.warning("No active tmux panes detected.")
        result = None
        while result is None or result.returncode != 0:
            result = subprocess.run(
                ["tmux", "list-panes", "-a", "-F", "#S:#I.#P"],
                capture_output=True,
                text=True,
            )
            sleep(timeout)


def watch(watcher: TmuxWatcher, stop_event: Event, timeout: int = 1) -> None:
    """
    Start the main watching loop to monitor panes continuously.

    Parameters
    ----------
    watcher : TmuxWatcher
        The watcher instance to monitor.
    stop_event : Event
        Event sent to stop watching
    timeout : int, optional
        Timeout in seconds between checks (default is 1).
    """
    from time import sleep

    logger.info("Start watching...")
    initial_panes = watcher.panes.copy()
    if initial_panes:
        logger.debug(f"Watching tmux panes: {', '.join(initial_panes)}")
    else:
        logger.debug("No specified panes to watch. Will monitor all tmux panes")
    logger.debug(f"Output file: {watcher.output_file}")
    logger.debug(
        f"Capture mode: {'Full output' if watcher.capture_full_output else 'Last command only'}"
    )

    while not stop_event.is_set():
        if not initial_panes:
            get_active_tmux_panes(watcher, timeout)
        completed_commands = check_for_completed_commands(watcher)
        if completed_commands:
            write_commands_to_file(watcher, completed_commands)
        sleep(timeout)
