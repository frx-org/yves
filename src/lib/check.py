"""Check library."""

import logging

from lib.llm_summarizer import LLMSummarizer

logger = logging.getLogger(__name__)


def check_llm(summarizer: LLMSummarizer):
    """Check if the LLM provider works as intended.

    Parameters
    ----------
    summarizer : LLMSummarizer
        Summarizer instance to be updated

    """
    from importlib.resources import files
    from json import load

    from lib.llm_summarizer import multiply_prompt, summarize

    logger.info(
        "We are going to check if you can communicate with your LLM provider. If everything works as intended, you shouldn't see any error messages."
    )
    logger.info(f"Checking {summarizer.model_name} from {summarizer.provider}...")

    prompt_file = files("yves.check") / "fs_prompt_example.json"
    with prompt_file.open("r", encoding="utf-8") as f:
        fs_log_data = load(f)

    multiple_fs_log_json, _, _ = multiply_prompt(
        fs_log_data, factor=1.5, token_limit=summarizer.token_limit
    )
    ret = summarize(summarizer, multiple_fs_log_json)

    if ret:
        logger.info("✅ Everything seems fine!")
    else:
        logger.error("🛑 Error(s) encountered... Please fix them before calling Yves.")
