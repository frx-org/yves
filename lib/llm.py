import json


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
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return []


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
    try:
        items: list[dict] = json.loads(json_str)
        breakpoint()
    except Exception:
        return []
    sublists: list[str] = []
    current: list[dict] = []
    current_tokens: int = 0
    for item in items:
        item_str: str = json.dumps(item, ensure_ascii=False)
        item_tokens: int = len(item_str.split())
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


if __name__ == "__main__":
    # Test the merge_logs_by_timestamp function with your provided paths
    tmux_log_path: str = "/home/kfrem/temp/recapify/test_file_monitor.txt"
    fs_log_path: str = "/home/kfrem/temp/recapify/changes.txt"
    merged_json_str: list[dict] = merge_logs_by_timestamp(tmux_log_path, fs_log_path)
    print("Merged events (sorted by timestamp):")
    print(merged_json_str)
    print(f"Total events: {len(merged_json_str)}")

    # Test the split_json_by_token_limit function
    token_limit: int = 4000  # Example token limit
    split_jsons: list[str] = split_json_by_token_limit(merged_json_str, token_limit)
    print(f"\nSplit into {len(split_jsons)} sublists (token limit: {token_limit}):")
    breakpoint()
    for i, sublist_json in enumerate(split_jsons):
        print(f"--- Sublist {i+1} ---")
        print(sublist_json)