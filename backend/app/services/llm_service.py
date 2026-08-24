import json
import logging

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI, RateLimitError
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.clinical import PostVisitLLMResult, PreVisitLLMResult

logger = logging.getLogger("llm_service")

PRE_VISIT_PROMPT = (
    "Analyse these symptoms and return:\n"
    "1. urgency level (Low / Medium / High)\n"
    "2. chief complaint\n"
    "3. three suggested questions for the doctor.\n\n"
    "This is decision-support only, NOT a diagnosis. Respond with ONLY a JSON object of the exact shape:\n"
    '{{"urgency_level": "Low|Medium|High", "chief_complaint": "...", '
    '"suggested_questions": ["...", "...", "..."]}}\n\n'
    "Symptoms:\n{symptoms}"
)

POST_VISIT_PROMPT = (
    "Convert these clinical notes into a patient-friendly summary with a medication schedule "
    "and follow-up steps. Use ONLY information present in the notes below — do not invent "
    "medications, diagnoses, or facts that are not present. Respond with ONLY a JSON object of "
    "the exact shape:\n"
    '{{"summary": "...", "medication_schedule": [{{"medicine": "...", "dose": "...", '
    '"frequency": "...", "duration": "..."}}], "follow_up_steps": ["...", "..."]}}\n\n'
    "Clinical notes:\n{notes}"
)


class LLMResult:
    def __init__(self, success: bool, data=None, error: str | None = None):
        self.success = success
        self.data = data
        self.error = error


def _client() -> OpenAI:
    return OpenAI(api_key=settings.OPENAI_API_KEY, timeout=settings.OPENAI_TIMEOUT_SECONDS)


def _call_openai_json(prompt: str) -> dict:
    client = _client()
    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    content = response.choices[0].message.content
    return json.loads(content)


def generate_pre_visit_summary(symptoms_text: str) -> LLMResult:
    """Never raises. Any failure mode (timeout, rate limit, bad key, network,
    malformed JSON, schema mismatch) is caught and returned as a failed
    LLMResult so the caller can store status=FAILED and keep booking flowing.
    """
    if not settings.OPENAI_API_KEY:
        return LLMResult(False, error="OpenAI API key is not configured")
    try:
        raw = _call_openai_json(PRE_VISIT_PROMPT.format(symptoms=symptoms_text))
        validated = PreVisitLLMResult.model_validate(raw)
        return LLMResult(True, data=validated)
    except APITimeoutError:
        logger.warning("LLM pre-visit summary timed out")
        return LLMResult(False, error="LLM request timed out")
    except RateLimitError:
        logger.warning("LLM pre-visit summary rate limited")
        return LLMResult(False, error="LLM rate limit exceeded")
    except APIConnectionError:
        logger.warning("LLM pre-visit summary: network/connection error")
        return LLMResult(False, error="LLM service unreachable")
    except APIStatusError as exc:
        logger.warning("LLM pre-visit summary API error: %s", exc.status_code)
        return LLMResult(False, error=f"LLM API error (status {exc.status_code})")
    except (json.JSONDecodeError, ValidationError) as exc:
        logger.warning("LLM pre-visit summary returned malformed output: %s", exc)
        return LLMResult(False, error="LLM returned an invalid response")
    except Exception as exc:  # noqa: BLE001 - last-resort guard, must never crash booking flow
        logger.exception("Unexpected LLM failure (pre-visit)")
        return LLMResult(False, error=f"Unexpected LLM error: {exc}")


def generate_post_visit_summary(clinical_notes: str) -> LLMResult:
    if not settings.OPENAI_API_KEY:
        return LLMResult(False, error="OpenAI API key is not configured")
    try:
        raw = _call_openai_json(POST_VISIT_PROMPT.format(notes=clinical_notes))
        validated = PostVisitLLMResult.model_validate(raw)
        return LLMResult(True, data=validated)
    except APITimeoutError:
        return LLMResult(False, error="LLM request timed out")
    except RateLimitError:
        return LLMResult(False, error="LLM rate limit exceeded")
    except APIConnectionError:
        return LLMResult(False, error="LLM service unreachable")
    except APIStatusError as exc:
        return LLMResult(False, error=f"LLM API error (status {exc.status_code})")
    except (json.JSONDecodeError, ValidationError) as exc:
        logger.warning("LLM post-visit summary returned malformed output: %s", exc)
        return LLMResult(False, error="LLM returned an invalid response")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected LLM failure (post-visit)")
        return LLMResult(False, error=f"Unexpected LLM error: {exc}")
