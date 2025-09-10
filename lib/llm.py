import json
import os


def load_prompt(prompt_name: str) -> str:
    """
    Load a system prompt from the prompts directory.

    Parameters
    ----------
    prompt_name : str
        Name of the prompt (e.g., "text" loads "prompts/text_system_prompt.txt").

    Returns
    -------
    str
        The content of the prompt file.

    """
    # Get the root directory of the project
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    prompt_file = os.path.join(root_dir, "prompts", f"{prompt_name}_system_prompt.txt")

    if not os.path.exists(prompt_file):
        raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

    with open(prompt_file, "r", encoding="utf-8") as f:
        return f.read().strip()


def merge_logs_by_timestamp(tmux_log_path: str, fs_log_path: str) -> str:
    """
    Read two JSON log files and concatenate their events in timestamp order.

    Parameters
    ----------
    tmux_log_path : str
        Path to the tmux log file.
    fs_log_path : str
        Path to the filesystem watcher log file.

    Returns
    -------
    str
        JSON string of all events from both logs, sorted by timestamp.
    """

    def read_json_log(path: str) -> list[dict]:
        """
        Read a JSON log file and return a list of events.

        Parameters
        ----------
        path : str
            Path to the JSON log file.

        Returns
        -------
        list of dict
            List of event dicts from the log file.
        """
        if not os.path.exists(path):
            return []

        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []

    tmux_events: list[dict] = read_json_log(tmux_log_path)
    fs_events: list[dict] = read_json_log(fs_log_path)
    all_events: list[dict] = tmux_events + fs_events
    all_events.sort(key=lambda event: event.get("timestamp", 0))
    merged_json_str = json.dumps(all_events, ensure_ascii=False, indent=0)
    return merged_json_str


def split_json_by_token_limit(json_str: str, token_limit: int) -> list[str]:
    """
    Split a JSON-formatted string (list of dicts) into sublists so that each sublist's token count does not exceed the limit.

    Parameters
    ----------
    json_str : str
        JSON string representing a list of dicts.
    token_limit : int
        Maximum number of tokens allowed per sublist.

    Returns
    -------
    list of str
        List of JSON strings, each representing a sublist within the token limit.
    """
    num_chars_per_token = 3.5
    try:
        items = json.loads(json_str)
    except json.JSONDecodeError:
        return []
    sublists = []
    current = []
    current_tokens = 0
    for item in items:
        item_str = json.dumps(item, ensure_ascii=False)
        item_tokens = len(item_str) // num_chars_per_token
        if current_tokens + item_tokens > token_limit:
            sublists.append(json.dumps(current, ensure_ascii=False))
            current = [item]
            current_tokens = item_tokens
        else:
            current.append(item)
            current_tokens += item_tokens
    if current:
        sublists.append(json.dumps(current, ensure_ascii=False))
    return sublists
