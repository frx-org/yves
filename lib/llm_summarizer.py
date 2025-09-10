import logging
import os
from dataclasses import dataclass
from datetime import datetime

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

    api_key: str
    model_name: str
    provider: str
    tmux_log_path: str
    fs_log_path: str
    output_dir: str = os.path.expanduser("~/.local/state/recapify")
    token_limit: int = 1000000
    run_hour: time = datetime.strptime("19:00", "%H:%M").time()
    last_run_day: date = datetime.strptime("0001-01-01", "%Y-%m-%d").date()


def update_from_config(summarizer: LLMSummarizer, config_path: str) -> None:
    """Read a config file and update `summarizer`.

    Parameters
    ----------
    watcher : LLMSummarizer
        Summarizer instance to be updated
    config_path : str
        Path to the configuration file

    """
    from lib.cfg import parse_config

    cfg = parse_config(config_path)

    summarizer.api_key = cfg["llm"]["api_key"]
    summarizer.model_name = cfg["llm"]["model_name"]
    summarizer.provider = cfg["llm"]["provider"]
    summarizer.fs_log_path = cfg["filesystem"]["output_file"]
    summarizer.tmux_log_path = cfg["tmux"]["output_file"]
    summarizer.output_dir = os.path.expanduser(cfg["summarizer"]["output_dir"])
    summarizer.token_limit = cfg.getint("summarizer", "token_limit")
    summarizer.run_hour = cfg.gettime("summarizer", "at")  # type: ignore


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
        )
        return response["choices"][0]["message"]["content"]
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
        summary = summarize_one(summarizer, summary + "\n\n" + text, prompt="many")
        if summary is None:
            logger.error("Failed to summarize one of the chunks.")
            return None
    return summary


def summarize(summarizer: LLMSummarizer):
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
    from lib.llm import merge_logs_by_timestamp, split_json_by_token_limit

    text = merge_logs_by_timestamp(summarizer.tmux_log_path, summarizer.fs_log_path)
    list_text = split_json_by_token_limit(text, summarizer.token_limit)
    num_chunks = len(list_text)
    if num_chunks < 2:
        if num_chunks == 0:
            logger.warning("No text to summarize.")
            return None
        return summarize_one(summarizer, list_text[0], prompt="single")
    return summarize_many(summarizer, list_text)


def generate_summary(summarizer: LLMSummarizer) -> None:
    """
    Save the generated summary to the specified output file.

    Parameters
    ----------
    summarizer : LLMSummarizer
        The summarizer instance.
    """
    from datetime import date

    if not summarizer.api_key:
        logger.error(
            "API key is required. Either set it using CLI argument or LLM_API_KEY environment variable."
        )
        return

    today = date.today().strftime("%Y-%m-%d")
    while True:
        now = datetime.now()
        if now.time() >= summarizer.run_hour and now.date() > summarizer.last_run_day:
            logger.debug(
                f"Generating summary using {summarizer.model_name} from {summarizer.provider}..."
            )
            logger.debug(
                f"Reading logs: {summarizer.tmux_log_path}, {summarizer.fs_log_path}"
            )

            output_file = os.path.join(summarizer.output_dir, f"{today}.md")

            logger.debug(f"Output will be saved to: {output_file}")
            summary = summarize(summarizer)
            if summary is None:
                logger.error("No summary generated to save.")
                return
            try:
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(summary)
                logger.debug(f"Summary saved to {output_file}")
            except Exception as e:
                logger.error(f"Failed to save summary: {e}")

            summarizer.last_run_day = now.date()
            break
