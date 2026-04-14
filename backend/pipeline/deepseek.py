"""Thin wrapper around the DeepSeek OpenAI-compatible API."""

import json
import logging
import urllib.request

logger = logging.getLogger(__name__)

BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-reasoner"
FAST_MODEL = "deepseek-chat"


def chat_completion(
    messages: list[dict],
    api_key: str,
    base_url: str,
    model: str,
    temperature: float,
) -> str:
    """POSTs to the OpenAI-compatible chat completions endpoint.

    Returns:
        The message content string from the API response.
    """
    url = base_url.rstrip("/") + "/chat/completions"
    payload = json.dumps(
        {
            "model": model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": temperature,
        }
    ).encode()

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    logger.info("Calling DeepSeek API (model=%s)", model)
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
    logger.info("Received response from DeepSeek API")

    return data["choices"][0]["message"]["content"]
