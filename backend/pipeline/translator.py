"""Translation + summarization using Groq (free tier). One API call per item."""

import asyncio
import logging
from openai import AsyncOpenAI, APIStatusError, APITimeoutError

from config import get_settings

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds, doubles each retry


async def translate_and_summarize(
    title: str,
    text: str = "",
) -> tuple[str, str]:
    """
    Single Groq call: translate title to Polish + generate Polish summary.
    Returns (title_pl, summary_pl).

    Fallback chain:
      1. Groq API call with retry on rate limits
      2. If Groq unavailable → return original (EN) text
      3. If output unparseable → return original + truncated text
      4. If summary too short → return truncated original text
    """
    settings = get_settings()

    if not settings.summarization_enabled:
        logger.debug("Summarization disabled — using original text")
        return _fallback(title, text)

    if not settings.groq_api_key:
        logger.warning("GROQ_API_KEY not set — translations will be in English")
        return _fallback(title, text)

    client = AsyncOpenAI(
        base_url=settings.summarization_endpoint,
        api_key=settings.groq_api_key,
        timeout=30.0,  # Groq is fast but network can hang
    )

    body = text[:1500] if text else title
    prompt = (
        f"Przetłumacz tytuł na polski i napisz 1-2 zdaniowe podsumowanie po polsku.\n"
        f"Tytuł: {title}\n"
        f"Treść: {body}\n\n"
        f"Odpowiedz DOKŁADNIE w formacie:\n"
        f"TYTUŁ: <przetłumaczony tytuł>\n"
        f"PODSUMOWANIE: <1-2 zdania po polsku>"
    )

    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            response = await client.chat.completions.create(
                model=settings.summarization_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=250,
                temperature=0.3,
            )
            output = response.choices[0].message.content
            if not output:
                logger.warning("Groq returned empty response for: %s", title[:80])
                return _fallback(title, text)

            title_pl, summary_pl = _parse_output(output.strip(), title, text)
            return _validate(title_pl, summary_pl, title, text)

        except APIStatusError as e:
            if e.status_code == 429:
                delay = RETRY_DELAY * (2 ** attempt)
                logger.warning(
                    "Groq rate limited (attempt %d/%d), retrying in %ds",
                    attempt + 1, MAX_RETRIES, delay,
                )
                await asyncio.sleep(delay)
                last_error = e
                continue
            else:
                logger.error("Groq API error %d: %s", e.status_code, e)
                return _fallback(title, text)

        except APITimeoutError:
            logger.warning("Groq timeout (attempt %d/%d)", attempt + 1, MAX_RETRIES)
            last_error = "timeout"
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY)
                continue
            return _fallback(title, text)

        except Exception as e:
            logger.error("Groq unexpected error: %s", e)
            return _fallback(title, text)

    logger.error("Groq failed after %d retries: %s", MAX_RETRIES, last_error)
    return _fallback(title, text)


def _parse_output(output: str, original_title: str, original_text: str) -> tuple[str, str]:
    """Parse Groq's TYTUŁ:/PODSUMOWANIE: structured output."""
    title_pl = original_title
    summary_pl = ""

    for line in output.split("\n"):
        line = line.strip()
        upper = line.upper()
        if upper.startswith("TYTUŁ:"):
            parsed = line.split(":", 1)[1].strip()
            if parsed:
                title_pl = parsed
        elif upper.startswith("PODSUMOWANIE:"):
            parsed = line.split(":", 1)[1].strip()
            if parsed:
                summary_pl = parsed

    if not summary_pl and original_text:
        summary_pl = original_text[:300]

    return title_pl, summary_pl


def _validate(
    title_pl: str, summary_pl: str, original_title: str, original_text: str
) -> tuple[str, str]:
    """Validate output — reject garbage, too-short, or copy-pasted English."""
    # Reject summaries that are just protocol markers or too short
    garbage = {"", ".", "..", "...", "-", "—", "tytuł:", "podsumowanie:"}
    if summary_pl.strip().lower() in garbage or len(summary_pl.strip()) < 10:
        logger.debug("Summary too short/garbage — using truncated original")
        summary_pl = original_text[:300] if original_text else original_title

    # Reject title that looks unparsed (contains raw markers)
    if "TYTUŁ:" in title_pl.upper() or "PODSUMOWANIE:" in title_pl.upper():
        logger.debug("Title contains unparsed markers — using original")
        title_pl = original_title

    return title_pl, summary_pl


def _fallback(title: str, text: str) -> tuple[str, str]:
    """Return original text as fallback when Groq is unavailable."""
    summary = (text[:300] + "..." if len(text) > 300 else text) if text else title
    return title, summary
