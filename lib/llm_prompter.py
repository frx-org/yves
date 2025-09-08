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

