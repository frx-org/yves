"""Sanity check library."""

import logging

from lib.llm_summarizer import LLMSummarizer

logger = logging.getLogger(__name__)


def command_exists(command: str) -> bool:
    """Check if a command exists.

    Parameters
    ----------
    command : str
        Command to check

    Returns
    -------
    bool
        `True` is the command exists, else `False`

    """
    from shutil import which

    return which(command) is not None


def check_file_system_config(config_path) -> bool:
    """Check file system watcher configuration.

    Parameters
    ----------
    config_path : str
        Path to the configuration file

    Returns
    -------
    bool
        Return `True` is configuration is valid else `False`

    """
    import os

    from lib.cfg import convert_to_list, parse_config

    is_valid = True
    cfg = parse_config(config_path)

    fs_watcher_dirs = [
        os.path.expanduser(p) for p in convert_to_list(cfg.get("filesystem", "dirs"))
    ]
    for fs_watcher_dir in fs_watcher_dirs:
        if os.path.exists(fs_watcher_dir):
            logger.debug(f"Directory {fs_watcher_dir} exist")
        else:
            logger.warning(f"Directory {fs_watcher_dir} does not exist")

    fs_min_lines_changed = cfg.getint("filesystem", "min_lines_changed")
    if fs_min_lines_changed >= 0:
        logger.debug(f"`min_lines_changed` is equal to {fs_min_lines_changed}")
    else:
        logger.error(
            f"`min_lines_changed` is negative (value is {fs_min_lines_changed})"
        )
        is_valid = False

    fs_similarity_threshold = cfg.getfloat("filesystem", "similarity_threshold")
    if 0 <= fs_similarity_threshold <= 1:
        logger.debug(f"`similarity_threshold` is equal to {fs_similarity_threshold}")
    else:
        logger.error(
            f"`similarity_threshold` is not in [0, 1] (value is {fs_similarity_threshold})"
        )
        is_valid = False

    return is_valid


def check_tmux_config(config_path) -> bool:
    """Check tmux watcher configuration.

    Parameters
    ----------
    config_path : str
        Path to the configuration file

    Returns
    -------
    bool
        Return `True` is configuration is valid else `False`

    """
    from lib.cfg import parse_config

    is_valid = True
    cfg = parse_config(config_path)

    tmux_enabled = cfg.getboolean("tmux", "enable")
    if tmux_enabled:
        logger.debug("Tmux watcher is enabled")
        if command_exists("tmux"):
            logger.debug("`tmux` command found")
        else:
            logger.error("Tmux watcher is enabled but `tmux` command is not found")
            is_valid = False

    return is_valid


def check_config(config_path: str) -> bool:
    """Check if configuration file has valid values.

    Parameters
    ----------
    config_path : str
        Path to the configuration file

    Returns
    -------
    bool
        Return `True` is configuration is valid else `False`

    """
    logger.info(f"Checking your configuration file {config_path}...")
    is_valid = check_file_system_config(config_path)
    is_valid = is_valid and check_tmux_config(config_path)

    return is_valid


def check_llm(summarizer: LLMSummarizer) -> bool:
    """Check if the LLM provider works as intended.

    Parameters
    ----------
    summarizer : LLMSummarizer
        Summarizer instance to be updated

    Returns
    -------
    bool
        Return `True` is configuration is valid else `False`

    """
    from importlib.resources import files
    from json import load

    from lib.llm_summarizer import multiply_prompt, summarize

    logger.info("Checking communication with your LLM...")
    logger.info(f"Checking {summarizer.model_name} from {summarizer.provider}...")

    prompt_file = files("yves.check") / "fs_prompt_example.json"
    with prompt_file.open("r", encoding="utf-8") as f:
        fs_log_data = load(f)

    multiple_fs_log_json, _, _ = multiply_prompt(
        fs_log_data, factor=1.5, token_limit=summarizer.token_limit
    )
    ret = summarize(summarizer, multiple_fs_log_json)

    return ret is not None


def check_all(config_path: str, summarizer: LLMSummarizer):
    """Check if Yves is configured properly.

    Parameters
    ----------
    config_path : str
        Path to the configuration file
    summarizer : LLMSummarizer
        Summarizer instance to be updated

    """
    logger.info(
        "We are going to check if your configuration is valid. If everything works as intended, you shouldn't see any error messages."
    )

    cfg_is_valid = check_config(config_path)
    llm_is_valid = check_llm(summarizer)

    if cfg_is_valid and llm_is_valid:
        logger.info("✅ Everything seems fine!")
    else:
        logger.error("🛑 Error(s) encountered... Please fix them before calling Yves.")
