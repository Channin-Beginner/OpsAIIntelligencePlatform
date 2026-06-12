"""DeepSeek Chat Completions 客户端（OpenAI 兼容）。"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx

from app.config import get_settings

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)


def _extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("{"):
        return json.loads(stripped)
    match = _JSON_BLOCK_RE.search(text)
    if match:
        return json.loads(match.group(1).strip())
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        return json.loads(stripped[start : end + 1])
    raise ValueError("LLM 响应中未找到 JSON 对象")


def chat_json(
    *,
    system_prompt: str,
    user_prompt: str,
    timeout: float | None = None,
) -> tuple[dict[str, Any], str]:
    """
    调用 DeepSeek，要求返回单个 JSON 对象。

    :returns: (parsed_json, model_name)
    """
    settings = get_settings()
    if not settings.llm_api_key.strip():
        raise ValueError("未配置 LLM_API_KEY，无法调用 DeepSeek")

    url = f"{settings.llm_api_base.rstrip('/')}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    client_timeout = timeout or float(settings.llm_timeout)

    with httpx.Client(timeout=client_timeout) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        body = response.json()

    choices = body.get("choices") or []
    if not choices:
        raise ValueError("DeepSeek 返回空 choices")
    content = choices[0].get("message", {}).get("content", "")
    if not content:
        raise ValueError("DeepSeek 返回空 content")

    parsed = _extract_json_object(content)
    model = body.get("model") or settings.llm_model
    return parsed, model
