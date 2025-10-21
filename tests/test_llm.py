"""Test lib/llm.py."""


def test_merge_logs_by_timestamp(tmp_path):
    """Test `merge_logs_by_timestamp`."""
    from json import load, dump, dumps

    from lib.llm import merge_logs_by_timestamp
    from importlib.resources import files

    fs_log_path = tmp_path / "fs_log_path.json"
    fs_prompt_file = files("yves.check") / "fs_prompt_example.json"
    with fs_prompt_file.open("r", encoding="utf-8") as f:
        fs_log_data = load(f)

    with fs_log_path.open("w") as f:
        dump(fs_log_data, f)

    tmux_log_path = tmp_path / "tmux_log_path.json"
    tmux_prompt_file = "./samples/tmux_prompt_example.json"
    with open(tmux_prompt_file, "r", encoding="utf-8") as f:
        tmux_log_data = load(f)

    with tmux_log_path.open("w") as f:
        dump(tmux_log_data, f)

    merged_prompt_file = "./samples/merged_prompt_example.json"
    with open(merged_prompt_file, "r", encoding="utf-8") as f:
        expected_merged = load(f)

    merged_str = merge_logs_by_timestamp(tmux_log_path, fs_log_path)

    assert merged_str == dumps(expected_merged, ensure_ascii=False, indent=0)


def test_split_json_by_token_limit():
    """Test `split_json_by_token_limit`."""
    from json import dumps, load
    from importlib.resources import files
    from lib.llm import split_json_by_token_limit

    prompt_file = files("yves.check") / "fs_prompt_example.json"
    with prompt_file.open("r", encoding="utf-8") as f:
        fs_log_data = load(f)
    fs_log_json = dumps(fs_log_data)

    num_chars_per_token = 3.5
    json_token_length = len(fs_log_json) / num_chars_per_token
    token_limit = json_token_length
    multiple_fs_log_json = dumps(fs_log_data * 2)

    splits = split_json_by_token_limit(multiple_fs_log_json, int(token_limit))
    assert len(splits) == 2
    assert (
        "[" + splits[0].replace(" ", "") + "]"
        == "[" + splits[1].replace(" ", "") + "]"
        == fs_log_json.replace(" ", "")
    )
