from dataclasses import dataclass, field
from types import FrameType
from datetime import datetime


@dataclass
class TmuxWatcher:
    """Tmux pane monitor that captures tmux pane commands and outputs.
    Attributes
    ----------
    panes: List of tmux panes to monitor
    output_file: Output file for command outputs
    file_patterns: Include patterns (e.g., ['*.py', '*.js'])
    capture_full_output: If True, capture full pane content instead of just last command
    pane_states: Dictionary to hold the state of each tmux pane
    """

    panes: list[str] = field(default_factory=list)
    output_file: str = "changes.txt"
    capture_full_output: bool = False
    pane_states: dict[str, dict[str, object]] = field(default_factory=dict)


def check_for_completed_commands(watcher: TmuxWatcher) -> list[dict[str, object]]:
    """Check all monitored panes for newly completed commands."""
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
    """Write completed commands and their outputs to the output file."""
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

    print(f"Captured {len(completed_commands)} completed commands")
    for cmd in completed_commands:
        print(f"  [{cmd['pane']}] {cmd['command']}")


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


def watch(watcher: TmuxWatcher, timeout: int = 1) -> None:
    """Start the main watching loop to monitor panes continuously.

    Parameters
    ----------
    watcher : TmuxWatcher
    timeout : int
        Timeout in seconds in the while loop

    """

    from signal import SIGINT, SIGTERM, signal
    from time import sleep

    print(f"Watching tmux panes: {', '.join(watcher.panes)}")
    print(f"Output file: {watcher.output_file}")
    print(
        f"Capture mode: {'Full output' if watcher.capture_full_output else 'Last command only'}"
    )
    print("Press Ctrl+C to stop watching...")
    print("-" * 50)

    signal(SIGTERM, signal_handler)
    signal(SIGINT, signal_handler)

    try:
        while True:
            completed_commands = check_for_completed_commands(watcher)
            if completed_commands:
                write_commands_to_file(watcher, completed_commands)
            sleep(timeout)
    except KeyboardInterrupt:
        print("\nStopped watching tmux panes")
