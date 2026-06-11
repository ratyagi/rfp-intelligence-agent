"""Single Foundry model-call client used by every reasoning stage.

Design constraints:
- Plain REST against the Azure OpenAI-compatible chat completions API that
  Foundry resources expose — no preview-SDK version landmines.
- Rate-limit aware: free-trial subscriptions cap models at ~1,000 tokens/min,
  so the client keeps a token budget, spaces calls out, and honours 429
  Retry-After with exponential backoff instead of failing the pipeline.
- JSON-first: every agent consumes structured output, so chat_json() requests
  JSON mode and retries once with the parse error fed back to the model.
"""
import json
import logging
import os
import re
import time

import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

API_VERSION = os.getenv("FOUNDRY_API_VERSION", "2024-10-21")
MAX_RETRIES_429 = 6
REQUEST_TIMEOUT_SECONDS = 120

# Tokens-per-minute budget used to pace requests proactively (free trial cap).
# Set FOUNDRY_TPM_BUDGET=0 to disable pacing on an unthrottled subscription.
TPM_BUDGET = int(os.getenv("FOUNDRY_TPM_BUDGET", "1000"))

_last_call_ts = 0.0
_last_call_tokens = 0


def estimate_tokens(text: str) -> int:
    """Rough estimate (~4 chars/token) — used only for pacing, never billing."""
    return max(1, len(text) // 4)


def _base_url() -> str:
    endpoint = os.getenv("AZURE_FOUNDRY_ENDPOINT", "").rstrip("/")
    if not endpoint:
        raise EnvironmentError("AZURE_FOUNDRY_ENDPOINT must be set in .env")
    # Accept any of the endpoint shapes the Foundry portal shows: a bare
    # resource endpoint, or a project endpoint with an /api/projects/... path.
    endpoint = re.sub(r"/api/projects/.*$", "", endpoint)
    return endpoint


def _pace(prompt_tokens: int, max_tokens: int) -> None:
    """Sleep long enough that this call fits the tokens-per-minute budget."""
    global _last_call_ts, _last_call_tokens
    if TPM_BUDGET <= 0:
        return
    needed = prompt_tokens + max_tokens
    if needed > TPM_BUDGET:
        logger.warning(
            f"foundry_client: single call (~{needed} tokens) exceeds the "
            f"{TPM_BUDGET} TPM budget — sending anyway; expect throttling"
        )
    # Time the previous call's tokens need to "drain" from the budget window.
    drain_seconds = (_last_call_tokens / TPM_BUDGET) * 60.0
    wait = _last_call_ts + drain_seconds - time.time()
    if wait > 0:
        logger.info(f"foundry_client: pacing for {wait:.1f}s (TPM budget {TPM_BUDGET})")
        time.sleep(wait)
    _last_call_ts = time.time()
    _last_call_tokens = needed


def chat(system_prompt: str, user_message: str, *,
         max_tokens: int = 1000, temperature: float = 0.0,
         json_mode: bool = False) -> str:
    """One chat completion. Returns the assistant message content as text."""
    api_key = os.getenv("AZURE_FOUNDRY_API_KEY", "")
    deployment = os.getenv("FOUNDRY_MODEL_DEPLOYMENT", "gpt-4o-mini")
    if not api_key:
        raise EnvironmentError("AZURE_FOUNDRY_API_KEY must be set in .env")

    url = (
        f"{_base_url()}/openai/deployments/{deployment}"
        f"/chat/completions?api-version={API_VERSION}"
    )
    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    _pace(estimate_tokens(system_prompt + user_message), max_tokens)

    backoff = 2.0
    for attempt in range(MAX_RETRIES_429 + 1):
        response = requests.post(
            url,
            headers={"api-key": api_key, "Content-Type": "application/json"},
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"].strip()

        if response.status_code == 429 and attempt < MAX_RETRIES_429:
            retry_after = float(response.headers.get("Retry-After", backoff))
            logger.warning(
                f"foundry_client: throttled (429), retrying in {retry_after:.0f}s "
                f"(attempt {attempt + 1}/{MAX_RETRIES_429})"
            )
            time.sleep(retry_after)
            backoff = min(backoff * 2, 60)
            continue

        raise RuntimeError(
            f"Foundry call failed: {response.status_code} {response.text[:500]}"
        )

    raise RuntimeError("Foundry call failed: retries exhausted on 429 throttling")


def chat_json(system_prompt: str, user_message: str, *,
              max_tokens: int = 1000, temperature: float = 0.0) -> dict:
    """Chat completion that must return a JSON object.

    Retries once on invalid JSON, feeding the parse error back to the model.
    """
    raw = chat(system_prompt, user_message,
               max_tokens=max_tokens, temperature=temperature, json_mode=True)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as first_error:
        logger.warning(f"foundry_client: invalid JSON from model, retrying once: {first_error}")
        retry_message = (
            f"{user_message}\n\nYour previous reply was not valid JSON "
            f"(error: {first_error}). Reply again with ONLY a valid JSON object."
        )
        raw = chat(system_prompt, retry_message,
                   max_tokens=max_tokens, temperature=temperature, json_mode=True)
        return json.loads(raw)  # let a second failure propagate to the orchestrator
