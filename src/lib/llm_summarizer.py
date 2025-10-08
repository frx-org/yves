"""Summarizer library using LLM."""

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from threading import Event

import litellm

logger = logging.getLogger(__name__)


@dataclass
class LLMSummarizer:
    """
    LLM-based summarizer for generating structured summaries from text.

    Attributes
    ----------
    api_key : str
        API key for authenticating with the LLM provider.
    model_name : str
        Name of the model to use (e.g., 'gpt-4', 'claude-3').
    provider : str
        Name of the LLM provider (e.g., 'openai', 'anthropic').
    tmux_log_path : str
        Path to the tmux log file.
    fs_log_path : str
        Path to the filesystem watcher log file.
    output_dir : str
        Path to the output directory for the summary.
    run_hour: time
        Hour to give the summary of the day
    last_run_day: time
        Last time we gave a summary
    """

    from datetime import date, time

    api_key: str = ""
    model_name: str = ""
    provider: str = ""
    tmux_log_path: str = ""
    fs_log_path: str = ""
    output_dir: str = os.path.expanduser("~/.local/state/yves")
    token_limit: int = 1000000
    run_hour: time = datetime.strptime("19:00", "%H:%M").time()
    last_run_day: date = datetime.strptime("0001-01-01", "%Y-%m-%d").date()


def update_from_config(summarizer: LLMSummarizer, config_path: str) -> None:
    """Read a config file and update `summarizer`.

    Parameters
    ----------
    summarizer : LLMSummarizer
        Summarizer instance to be updated
    config_path : str
        Path to the configuration file

    """
    from lib.cfg import parse_config

    cfg = parse_config(config_path)

    summarizer.api_key = cfg["llm"]["api_key"]
    if not summarizer.api_key:
        logger.warning("No API key provided or empty string")

    summarizer.model_name = cfg["llm"]["model_name"]
    summarizer.provider = cfg["llm"]["provider"]
    summarizer.fs_log_path = os.path.expanduser(cfg["filesystem"]["output_file"])
    summarizer.tmux_log_path = os.path.expanduser(cfg["tmux"]["output_file"])
    summarizer.output_dir = os.path.expanduser(cfg["summarizer"]["output_dir"])
    summarizer.token_limit = cfg.getint("summarizer", "token_limit")
    summarizer.run_hour = cfg.gettime("summarizer", "at")  # type: ignore


def get_extra_headers(provider: str) -> dict:
    """Return `extra_headers` value for litellm `completion` function.

    Parameters
    ----------
    provider : str
        Provider name used for LLM

    Returns
    -------
    dict
        Dictionary to be passed as argument to litellm `completion` function

    """
    if provider == "github_copilot":
        return {
            "editor-version": "vscode/1.85.1",
            "Copilot-Integration-Id": "vscode-chat",
        }
    else:
        return {}


def summarize_one(summarizer: LLMSummarizer, text: str, prompt: str) -> str | None:
    """
    Generate a summary for a single text chunk using the configured LLM via litellm.

    Parameters
    ----------
    summarizer : LLMSummarizer
        The summarizer instance with API key, model, etc.
    text : str
        The input text chunk to summarize.
    prompt : str
        The name of the prompt to load from the prompts directory.

    Returns
    -------
    str or None
        The generated summary, or None if the API call fails.
    """
    from litellm.files.main import ModelResponse

    from lib.llm import load_prompt

    system_prompt = load_prompt(prompt)

    try:
        response = litellm.completion(
            api_key=summarizer.api_key,
            model=f"{summarizer.provider}/{summarizer.model_name}",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            extra_headers=get_extra_headers(summarizer.provider),
        )
        if isinstance(response, ModelResponse):
            return response["choices"][0]["message"]["content"]
        else:
            logger.error("LLM response is not of type `ModelResponse`")
            return ""
    except Exception as e:
        logger.error(f"LLM summarization failed: {e}")
        return None


def summarize_many(summarizer: LLMSummarizer, list_text: list[str]) -> str | None:
    """
    Generate a summary for multiple text chunks by summarizing each and then combining.

    Parameters
    ----------
    summarizer : LLMSummarizer
        The summarizer instance with API key, model, etc.
    list_text : list of str
        List of input text chunks to summarize.

    Returns
    -------
    str or None
        The combined summary, or None if any API call fails.
    """
    summary = summarize_one(summarizer, list_text[0], prompt="single")
    num_chunks = len(list_text)
    for idx, text in enumerate(list_text[1:]):
        logger.debug(f"Summarizing chunk {idx + 1}/{num_chunks}")
        if summary is None:
            logger.error("Failed to summarize one of the chunks.")
            return None

        summary = summarize_one(summarizer, summary + "\n\n" + text, prompt="many")
    return summary


def summarize(summarizer: LLMSummarizer, text: str):
    """
    Generate a summary for the given text using the configured LLM via litellm.

    Parameters
    ----------
    summarizer : LLMSummarizer
        The summarizer instance with API key, model, etc.
    text : str
        The input text to summarize.

    Returns
    -------
    str or None
        The generated summary, or None if the API call fails.

    """
    from lib.llm import split_json_by_token_limit

    list_text = split_json_by_token_limit(text, summarizer.token_limit)
    num_chunks = len(list_text)
    if num_chunks < 2:
        if num_chunks == 0:
            logger.warning("No text to summarize.")
            return None
        return summarize_one(summarizer, list_text[0], prompt="single")
    return summarize_many(summarizer, list_text)


def generate_summary(
    summarizer: LLMSummarizer,
    stop_event: Event,
    timeout: int = 1,
    wait_to_summarize: bool = True,
) -> None:
    """
    Save the generated summary to the specified output file.

    Parameters
    ----------
    summarizer : LLMSummarizer
        The summarizer instance.
    stop_event : Event
        Event sent to stop watching
    timeout : int
        Timeout in seconds in the while loop
    wait_to_summarize : bool
        If `True` we wait for the `stop_event` to be set to summarize.
        Else we summarize directly.
    """
    from datetime import date
    from time import sleep

    from lib.llm import merge_logs_by_timestamp

    today = date.today().strftime("%Y-%m-%d")
    if not os.path.exists(summarizer.output_dir):
        os.makedirs(summarizer.output_dir, exist_ok=True)

    while not stop_event.is_set() or not wait_to_summarize:
        now = datetime.now()
        if not wait_to_summarize or (
            now.time() >= summarizer.run_hour and now.date() > summarizer.last_run_day
        ):
            logger.debug(
                f"Generating summary using {summarizer.model_name} from {summarizer.provider}..."
            )
            logger.debug(
                f"Reading logs: {summarizer.tmux_log_path}, {summarizer.fs_log_path}"
            )

            output_file = os.path.join(summarizer.output_dir, f"{today}.md")

            logger.debug(
                f"Merge {summarizer.tmux_log_path} and {summarizer.fs_log_path}"
            )
            text = merge_logs_by_timestamp(
                summarizer.tmux_log_path, summarizer.fs_log_path
            )

            logger.debug(f"Output will be saved to: {output_file}")
            summary = summarize(summarizer, text)

            if summary is None:
                logger.error("No summary generated to save.")
                return
            try:
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(summary)
                logger.info(f"Summary saved to {output_file}")
            except Exception as e:
                logger.error(f"Failed to save summary: {e}")

            summarizer.last_run_day = now.date()

            with open(summarizer.fs_log_path, "w") as f:
                logger.debug(f"Emptying {summarizer.fs_log_path}")
            with open(summarizer.tmux_log_path, "w") as f:
                logger.debug(f"Emptying {summarizer.tmux_log_path}")

            break

        sleep(timeout)


def check(summarizer: LLMSummarizer):
    """Check if the LLM provider works as intended.

    Parameters
    ----------
    summarizer : LLMSummarizer
        Summarizer instance to be updated

    """
    from json import dumps

    from lib.llm import load_prompt

    logger.info(
        "We are going to check if you can communicate with your LLM provider. If everything works as intended, you shouldn't see any error messages."
    )
    logger.info(f"Checking {summarizer.model_name} from {summarizer.provider}...")

    long_json = dumps("\n".join([load_prompt("single") for _ in range(1000)]))
    ret = summarize(summarizer, long_json)

    if ret:
        logger.info("✅ Everything seems fine!")
    else:
        logger.error("🛑 Error(s) encountered... Please fix them before calling Yves.")
