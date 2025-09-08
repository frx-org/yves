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
    from lib.llm import merge_logs_by_timestamp

    text = merge_logs_by_timestamp(summarizer.tmux_log_path, summarizer.fs_log_path)
    try:
        response = litellm.completion(
            api_key=summarizer.api_key,
            model=summarizer.model_name,
            messages=[
                {"role": "system", "content": summarizer.system_prompt},
                {"role": "user", "content": text},
            ],
            provider=summarizer.provider,
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        logger.error(f"LLM summarization failed: {e}")
        return None

