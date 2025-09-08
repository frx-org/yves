from dataclasses import dataclass
import logging
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
    output_file : str
        Path to the output file for the summary.
    """

    api_key: str
    model_name: str
    provider: str
    tmux_log_path: str
    fs_log_path: str
    output_file: str = "summary_output.txt"
    token_limit: int = 1000000


def summarize_one(summarizer: LLMSummarizer, text: str, prompt: str) -> str:
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


def summarize_many(summarizer: LLMSummarizer, list_text: list[str]) -> str:
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
    summary = ""
    summary = summarize_one(summarizer, list_text[0], prompt="single")
    for idx, text in enumerate(list_text[1:]):
        logger.info(f"Summarizing chunk {idx + 1}/{len(list_text)}")
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
    if len(list_text) < 2:
        if len(list_text) == 0:
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
    if not summarizer.api_key:
        logger.error(
            "API key is required. Either set it using CLI argument or LLM_API_KEY environment variable."
        )
        return
    logger.info(
        f"Generating summary using {summarizer.model_name} from {summarizer.provider}..."
    )
    logger.info(f"Reading logs: {summarizer.tmux_log_path}, {summarizer.fs_log_path}")
    logger.info(f"Output will be saved to: {summarizer.output_file}")
    summary = summarize(summarizer)
    if summary is None:
        logger.error("No summary generated to save.")
        return
    try:
        with open(summarizer.output_file, "w", encoding="utf-8") as f:
            f.write(summary)
        logger.info(f"Summary saved to {summarizer.output_file}")
    except Exception as e:
        logger.error(f"Failed to save summary: {e}")
