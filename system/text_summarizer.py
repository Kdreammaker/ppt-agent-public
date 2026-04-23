from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any


def llm_summary_enabled() -> bool:
    return os.getenv("PPTX_ENABLE_LLM_SUMMARY") == "1"


def mock_summary_for_slot(slot_name: str) -> tuple[str | None, str | None]:
    mock_json = os.getenv("PPTX_LLM_SUMMARY_MOCK_JSON")
    if mock_json:
        try:
            payload = json.loads(mock_json)
        except json.JSONDecodeError:
            return None, "invalid_mock_json"
        value = payload.get(slot_name, payload.get("*"))
        return (None, "mock_missing") if value is None else (str(value), None)

    mock_text = os.getenv("PPTX_LLM_SUMMARY_MOCK_TEXT")
    if mock_text is not None:
        return mock_text, None

    return None, "no_provider_configured"


def parse_response_text(payload: dict[str, Any]) -> str | None:
    output_text = payload.get("output_text")
    if isinstance(output_text, str):
        return output_text
    parts: list[str] = []
    for item in payload.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if isinstance(content, dict) and content.get("type") in {"output_text", "text"}:
                text = content.get("text")
                if isinstance(text, str):
                    parts.append(text)
    return "\n".join(parts).strip() or None


def openai_summary_for_slot(*, text: str, budget: int, slot_name: str, slide_context: dict[str, Any]) -> tuple[str | None, str | None, str]:
    model = os.getenv("PPTX_LLM_SUMMARY_MODEL", "gpt-5-mini")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None, "missing_openai_api_key", model

    timeout_ms = int(os.getenv("PPTX_LLM_SUMMARY_TIMEOUT_MS", "3000"))
    endpoint = os.getenv("PPTX_OPENAI_RESPONSES_URL", "https://api.openai.com/v1/responses")
    prompt = (
        f"Summarize the following PowerPoint slot text for slot '{slot_name}'. "
        f"Return only the replacement text. Keep it within {budget} characters. "
        "Preserve names, dates, numbers, product terms, and the original business meaning.\n\n"
        f"Slide context: {json.dumps(slide_context, ensure_ascii=False)}\n\n"
        f"Text: {text}"
    )
    body = {
        "model": model,
        "instructions": "You write concise, presentation-ready text that fits strict character budgets.",
        "input": prompt,
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_ms / 1000) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return None, f"openai_http_{exc.code}", model
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return None, f"openai_error_{exc.__class__.__name__}", model
    return parse_response_text(payload), None, model


def provider_summary_for_slot(
    *,
    text: str,
    budget: int,
    slot_name: str,
    slide_context: dict[str, Any],
) -> tuple[str | None, str | None, str]:
    provider = os.getenv("PPTX_LLM_SUMMARY_PROVIDER", "mock").lower()
    if provider in {"", "mock"}:
        summary, error = mock_summary_for_slot(slot_name)
        return summary, error, os.getenv("PPTX_LLM_SUMMARY_MODEL", "mock")
    if provider == "openai":
        return openai_summary_for_slot(
            text=text,
            budget=budget,
            slot_name=slot_name,
            slide_context=slide_context,
        )
    return None, f"unsupported_provider_{provider}", provider


def protected_tokens_preserved(original: str, summary: str, protected_tokens: list[str]) -> bool:
    for token in protected_tokens:
        if token and token in original and token not in summary:
            return False
    return True


def validate_summary(
    *,
    original: str,
    summary: str | None,
    budget: int,
    protected_tokens: list[str],
    allow_line_breaks: bool,
) -> str | None:
    if summary is None:
        return "empty_response"
    cleaned = summary.strip()
    if not cleaned:
        return "empty_response"
    if len(cleaned) > budget:
        return "over_budget_response"
    if not allow_line_breaks and "\n" in cleaned:
        return "line_break_response"
    if not protected_tokens_preserved(original, cleaned, protected_tokens):
        return "protected_token_missing"
    return None


def summarize_to_budget(
    *,
    text: str,
    budget: int,
    slot_name: str,
    slide_context: dict[str, Any] | None = None,
    protected_tokens: list[str] | None = None,
    allow_line_breaks: bool = False,
) -> tuple[str | None, dict[str, Any]]:
    start = time.perf_counter()
    protected_tokens = protected_tokens or []
    slide_context = slide_context or {}
    summary, provider_error, model = provider_summary_for_slot(
        text=text,
        budget=budget,
        slot_name=slot_name,
        slide_context=slide_context,
    )
    latency_ms = int((time.perf_counter() - start) * 1000)
    metadata = {
        "llm_attempted": True,
        "llm_used": False,
        "llm_model": model,
        "llm_latency_ms": latency_ms,
        "slide_context": slide_context,
    }
    if provider_error:
        metadata["fallback_reason"] = provider_error
        return None, metadata

    failure = validate_summary(
        original=text,
        summary=summary,
        budget=budget,
        protected_tokens=protected_tokens,
        allow_line_breaks=allow_line_breaks,
    )
    if failure:
        metadata["fallback_reason"] = failure
        return None, metadata

    metadata["llm_used"] = True
    metadata["fallback_reason"] = None
    return summary.strip(), metadata
