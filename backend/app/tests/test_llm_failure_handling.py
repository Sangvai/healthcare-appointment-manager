from unittest.mock import patch

import httpx

from app.services import llm_service

_DUMMY_REQUEST = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")


def test_missing_api_key_fails_gracefully_without_raising():
    with patch.object(llm_service.settings, "OPENAI_API_KEY", ""):
        result = llm_service.generate_pre_visit_summary("fever, cough for 3 days")
    assert result.success is False
    assert "not configured" in result.error


def test_timeout_is_caught_and_returns_failed_result():
    with patch.object(llm_service.settings, "OPENAI_API_KEY", "sk-fake"):
        with patch.object(llm_service, "_call_openai_json", side_effect=llm_service.APITimeoutError(request=_DUMMY_REQUEST)):
            result = llm_service.generate_pre_visit_summary("fever, cough")
    assert result.success is False
    assert "timed out" in result.error


def test_malformed_json_is_caught_and_returns_failed_result():
    with patch.object(llm_service.settings, "OPENAI_API_KEY", "sk-fake"):
        with patch.object(llm_service, "_call_openai_json", return_value={"unexpected": "shape"}):
            result = llm_service.generate_pre_visit_summary("fever, cough")
    assert result.success is False
    assert result.error is not None


def test_unexpected_exception_never_propagates():
    with patch.object(llm_service.settings, "OPENAI_API_KEY", "sk-fake"):
        with patch.object(llm_service, "_call_openai_json", side_effect=RuntimeError("boom")):
            result = llm_service.generate_pre_visit_summary("fever, cough")
    assert result.success is False
