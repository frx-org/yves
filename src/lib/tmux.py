import re
import subprocess


def get_tmux_pane_content(pane: str) -> str:
    """
    Capture and return the content of a specific tmux pane.

    Parameters
    ----------
    pane : str
        The target tmux pane identifier (e.g., 'session:window.pane').

    Returns
    -------
    str or None
        The content of the pane, or None if capture fails.
    """
    try:
        result = subprocess.run(
            ["tmux", "capture-pane", "-t", pane, "-S", "-1000", "-p"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout

        result = subprocess.run(
            ["tmux", "capture-pane", "-t", pane, "-p"],
            capture_output=True,
            text=True,
        )
        return result.stdout
    except subprocess.CalledProcessError:
        return None


def get_command_from_content(pane_content: str) -> str:
    """
    Extract the most recently executed command from pane content.

    Parameters
    ----------
    pane_content : str
        The full text content of a tmux pane.

    Returns
    -------
    str
        The extracted command, or an empty string if no command is found.
    """

    if not is_command_finished(pane_content):
        return ""

    lines = pane_content.strip().split("\n")
    if len(lines) < 2:
        return ""

    for i in range(len(lines) - 2, -1, -1):
        line = lines[i].strip()
        if not line:
            continue

        bash_match = re.match(r"^[^$]*\$\s*(.+)$", line)
        if bash_match:
            cmd = bash_match.group(1).strip()
            if is_valid_command(cmd):
                return cmd

        for char in ["❯", "➜", "→", "»", "⟩"]:
            if char in line:
                parts = line.split(char, 1)
                if len(parts) > 1 and parts[1].strip():
                    cmd = parts[1].strip()
                    if is_valid_command(cmd):
                        return cmd

        if line.startswith(">>> ") and len(line) > 4:
            cmd = line[4:].strip()
            if is_valid_command(cmd):
                return cmd

    return ""


def extract_last_command_output(pane_content: str) -> str:
    """
    Extract only the output from the last executed command.

    Parameters
    ----------
    pane_content : str
        The text content of the tmux pane.

    Returns
    -------
    str
        The output of the last command.
    """
    lines = pane_content.strip().split("\n")
    if not lines:
        return ""

    command_line_idx = -1
    for i in range(len(lines) - 1, -1, -1):
        line = lines[i].strip()

        command_patterns = [
            r"^[^$]*\$\s*.+$",
            r"^.*[❯➜→»⟩]\s*.+$",
            r"^>>>\s*.+$",
        ]

        for pattern in command_patterns:
            if re.match(pattern, line):
                command_line_idx = i
                break

        if command_line_idx != -1:
            break

    if command_line_idx == -1:
        return ""

    next_prompt_idx = len(lines)
    for i in range(command_line_idx + 1, len(lines)):
        line = lines[i].strip()

        prompt_patterns = [
            r"^[^$]*\$$",
            r"^.*[❯➜→»⟩]$",
            r"^>>>$",
        ]

        for pattern in prompt_patterns:
            if re.match(pattern, line):
                next_prompt_idx = i
                break

        if next_prompt_idx < len(lines):
            break

    result_lines = lines[command_line_idx:next_prompt_idx]
    return "\n".join(result_lines)


def is_valid_command(cmd: str) -> bool:
    """
    Filter out basic/uninteresting commands to reduce noise.

    Parameters
    ----------
    cmd : str
        The command string to validate.

    Returns
    -------
    bool
        True if the command is considered valid, False otherwise.
    """
    if not cmd:
        return False

    if len(cmd.split()) > 10:
        return False

    basic_commands = ["ls", "cd", "pwd", "echo", "cat", "clear", "history"]
    base_cmd = cmd.split()[0]

    return base_cmd not in basic_commands


def is_command_finished(pane_content: str) -> bool:
    """
    Check if the last line indicates a command has finished and shell is ready.

    Parameters
    ----------
    pane_content : str
        The text content of the tmux pane.

    Returns
    -------
    bool
        True if the command is finished, False otherwise.
    """
    lines = pane_content.strip().split("\n")
    if not lines:
        return False

    last_line = lines[-1].strip()

    prompt_indicators = [
        "$",
        "%",
        ">",
        ">>",
        ">>>",
        "❯",
        "➜",
        "✗",
        "✓",
        "→",
        "»",
        "⟩",
        "#",
    ]

    for indicator in prompt_indicators:
        if last_line.endswith(indicator) or last_line.endswith(indicator + " "):
            return True

    prompt_patterns = [
        r".*[@:].*[$%>❯➜#]\s*$",
        r"^[^@]*@[^:]*:[^$%>❯➜#]*[$%>❯➜#]\s*$",
        r"^\([^)]+\)\s*[$%>❯➜#]\s*$",
        r"^\[[^\]]+\]\s*[$%>❯➜#]\s*$",
        r"^.*\s+[$%>❯➜#]\s*$",
        r"^\w+\s*[$%>❯➜#]\s*$",
        r"^[$%>❯➜#]+\s*$",
    ]

    for pattern in prompt_patterns:
        if re.match(pattern, last_line):
            return True

    if re.match(r".*~[>$]\s*$", last_line):
        return True

    return False
