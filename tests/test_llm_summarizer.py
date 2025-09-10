def test_update_from_config(tmpdir):
    """Test `update_from_config` if it updates the current `LLMSummarizer` instance"""
    from configparser import ConfigParser
    from datetime import datetime
    from uuid import uuid4

    from lib.llm_summarizer import LLMSummarizer, update_from_config

    abs_path = tmpdir / f"{uuid4().hex}"
    default_summarizer = LLMSummarizer("", "", "", "", "")
    summarizer = LLMSummarizer("", "", "", "", "")

    config = ConfigParser()
    config["filesystem"] = {
        "output_file": "fs_output_file.txt",
    }
    config["tmux"] = {
        "output_file": "tmux_output_file.txt",
    }
    config["llm"] = {
        "api_key": "this-is-my-api-secret",
        "model_name": "gpt-4o-mini",
        "provider": "openai",
    }
    config["summarizer"] = {
        "output_file": "summarized.txt",
        "token_limit": "154546",
        "at": "15:49",
    }
    with open(abs_path, "w") as f:
        config.write(f)

    update_from_config(summarizer, abs_path)
    assert default_summarizer != summarizer
    assert summarizer == LLMSummarizer(
        "this-is-my-api-secret",
        "gpt-4o-mini",
        "openai",
        "tmux_output_file.txt",
        "fs_output_file.txt",
        "summarized.txt",
        154546,
        datetime.strptime("15:49", "%H:%M").time(),
    )
