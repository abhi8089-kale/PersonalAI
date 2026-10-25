"""
LLM Service for PersonalAI.
Provides OpenAI-compatible API connectivity, provider auto-detection,
connection testing & health verification, and secure error sanitization.
"""

import os
import time
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv, find_dotenv

# Connection state cache
_connection_state: Dict[str, Any] = {
    "status": "untested",  # "verified", "error", "untested"
    "verified": False,
    "last_error": None,
    "last_tested": None,
    "latency_ms": None,
}


class LLMServiceError(Exception):
    """Custom exception for LLM API errors with sanitized messages."""
    pass


def reload_environment():
    """
    Safely ensures .env variables are loaded without overriding any
    explicitly set os.environ variables (including empty string overrides).
    """
    env_file = find_dotenv() or os.path.join(os.getcwd(), ".env")
    if os.path.exists(env_file):
        load_dotenv(env_file, override=False)


def get_config_value(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Retrieves configuration with strict environment precedence:
    1. If `key` is present in os.environ (even if empty string ""), os.environ takes precedence.
       An empty or whitespace-only value explicitly evaluates to None.
    2. If `key` is NOT in os.environ, reads from the .env file if available.
    3. Falls back to default.
    """
    if key in os.environ:
        raw = os.environ[key]
        cleaned = raw.strip() if raw is not None else ""
        return cleaned if cleaned else None

    # Not explicitly in os.environ; inspect .env file safely
    env_file = find_dotenv() or os.path.join(os.getcwd(), ".env")
    if os.path.exists(env_file):
        from dotenv import dotenv_values
        file_values = dotenv_values(env_file)
        if key in file_values:
            raw = file_values[key]
            cleaned = raw.strip() if raw is not None else ""
            return cleaned if cleaned else None

    return default


def infer_provider(base_url: Optional[str]) -> str:
    """Detects provider brand based on endpoint URL for user clarity."""
    if not base_url:
        return "OpenAI"
    url_lower = base_url.lower()
    if "groq.com" in url_lower:
        return "Groq"
    if "generativelanguage.googleapis.com" in url_lower or "googleapis" in url_lower:
        return "Google Gemini (OpenAI Endpoint)"
    if "openrouter.ai" in url_lower:
        return "OpenRouter"
    if "localhost:11434" in url_lower or "ollama" in url_lower:
        return "Ollama (Local)"
    if "deepseek" in url_lower:
        return "DeepSeek"
    if "api.openai.com" in url_lower:
        return "OpenAI"
    return "Custom OpenAI-Compatible Provider"


def get_default_model_for_provider(provider: str) -> str:
    """Returns a sensible default model compatible with the detected provider."""
    defaults = {
        "OpenAI": "gpt-4o-mini",
        "Groq": "llama-3.3-70b-versatile",
        "Google Gemini (OpenAI Endpoint)": "gemini-2.5-flash",
        "OpenRouter": "openai/gpt-4o-mini",
        "Ollama (Local)": "llama3.1",
        "DeepSeek": "deepseek-chat",
    }
    return defaults.get(provider, "gpt-4o-mini")


def get_llm_config() -> Dict[str, Any]:
    """
    Retrieves current LLM configuration with strict environment precedence.
    An explicitly set environment variable, including empty string, takes precedence over .env.
    """
    base_url = get_config_value("OPENAI_BASE_URL")
    provider = infer_provider(base_url)
    model = get_config_value("OPENAI_MODEL") or get_default_model_for_provider(provider)
    api_key = get_config_value("OPENAI_API_KEY")

    return {
        "api_key": api_key,
        "model": model,
        "base_url": base_url,
        "provider": provider,
    }


def is_api_key_configured() -> bool:
    """Returns True if a valid API key (or local endpoint configuration) is present."""
    # If OPENAI_API_KEY is explicitly in os.environ with an empty value, it is missing
    if "OPENAI_API_KEY" in os.environ and not os.environ["OPENAI_API_KEY"].strip():
        return False

    config = get_llm_config()
    api_key = config.get("api_key")
    if not api_key:
        # Check if local Ollama without key is intentionally configured
        base_url = config.get("base_url")
        if base_url and ("localhost:11434" in base_url or "ollama" in base_url):
            return True
        return False
    return True


def is_llm_available() -> bool:
    """
    Returns True if an API key is configured and available.
    Used by orchestrators to determine whether to attempt online ReAct agent execution.
    """
    return is_api_key_configured()


def mask_api_key(key: Optional[str]) -> str:
    """Safely masks an API key so it is never exposed in UI or logs."""
    if not key:
        return "Not Configured"
    cleaned = key.strip()
    if len(cleaned) <= 8:
        return "••••••••"
    return f"{cleaned[:4]}••••••••{cleaned[-4:]}"


def sanitize_error_message(err: Exception, api_key: Optional[str] = None) -> str:
    """Removes sensitive key tokens and produces clear, actionable explanations."""
    msg = str(err)
    if api_key and api_key in msg:
        msg = msg.replace(api_key, "[REDACTED_API_KEY]")

    msg_lower = msg.lower()

    if "authentication" in msg_lower or "invalid api key" in msg_lower or "401" in msg_lower:
        return "Authentication Error (401): The provided API key is invalid, revoked, or lacks required permissions. Please verify your API key in Settings."
    if "rate limit" in msg_lower or "quota" in msg_lower or "429" in msg_lower:
        return "Quota / Rate Limit Error (429): You have exceeded your API quota or request rate limit. Check your provider billing or try again later."
    if "model" in msg_lower and ("not found" in msg_lower or "404" in msg_lower or "does not exist" in msg_lower):
        return f"Model Error (404): The specified model was not found on this provider endpoint. Please verify OPENAI_MODEL in Settings."
    if "connection" in msg_lower or "failed to resolve" in msg_lower or "connect" in msg_lower:
        return "Connection Error: Failed to reach the AI endpoint. Check your internet connection or OPENAI_BASE_URL."

    return f"AI Provider Error: {msg}"


def get_openai_client(
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
):
    """Initializes and returns an OpenAI client instance."""
    config = get_llm_config()
    effective_key = api_key or config["api_key"]
    effective_base_url = base_url if base_url is not None else config["base_url"]

    # For local Ollama without explicit key, provide a dummy token
    if not effective_key and effective_base_url and "localhost:11434" in effective_base_url:
        effective_key = "ollama"

    if not effective_key:
        raise LLMServiceError(
            "No OPENAI_API_KEY configured. Please add your API key in .env or Settings."
        )

    try:
        from openai import OpenAI
        client_kwargs: Dict[str, Any] = {"api_key": effective_key}
        if effective_base_url:
            client_kwargs["base_url"] = effective_base_url
        return OpenAI(**client_kwargs)
    except Exception as e:
        raise LLMServiceError(f"Failed to initialize LLM client: {sanitize_error_message(e, effective_key)}")


def test_connection(
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Performs a genuine, lightweight test call against the configured AI provider.
    Updates the connection status cache and returns diagnostic results.
    """
    config = get_llm_config()
    target_key = api_key or config["api_key"]
    target_base_url = base_url if base_url is not None else config["base_url"]
    provider = infer_provider(target_base_url)
    target_model = model or config["model"] or get_default_model_for_provider(provider)

    if not target_key and not (target_base_url and "localhost:11434" in target_base_url):
        _connection_state["status"] = "untested"
        _connection_state["verified"] = False
        _connection_state["last_error"] = "API Key is not configured."
        return {
            "success": False,
            "error": "API Key is missing. Please provide a valid API key to enable Online AI Mode.",
            "provider": provider,
            "model": target_model,
        }

    start_time = time.time()
    try:
        client = get_openai_client(api_key=target_key, base_url=target_base_url)
        response = client.chat.completions.create(
            model=target_model,
            messages=[{"role": "user", "content": "Respond with 'PersonalAI Online Verified'."}],
            max_tokens=10,
            temperature=0.0,
        )
        latency = round((time.time() - start_time) * 1000)
        reply = response.choices[0].message.content or ""

        # Update cache
        _connection_state["status"] = "verified"
        _connection_state["verified"] = True
        _connection_state["last_error"] = None
        _connection_state["last_tested"] = time.strftime("%Y-%m-%d %H:%M:%S")
        _connection_state["latency_ms"] = latency

        return {
            "success": True,
            "message": f"Connection verified in {latency}ms! Model responded: '{reply.strip()}'",
            "provider": provider,
            "model": target_model,
            "latency_ms": latency,
            "response": reply.strip(),
        }

    except Exception as e:
        err_msg = sanitize_error_message(e, target_key)
        _connection_state["status"] = "error"
        _connection_state["verified"] = False
        _connection_state["last_error"] = err_msg
        _connection_state["last_tested"] = time.strftime("%Y-%m-%d %H:%M:%S")
        _connection_state["latency_ms"] = None

        return {
            "success": False,
            "error": err_msg,
            "provider": provider,
            "model": target_model,
        }


def get_connection_status() -> Dict[str, Any]:
    """
    Returns the current AI connection status summary for UI badges and diagnostics.
    """
    config = get_llm_config()
    has_key = is_api_key_configured()

    if not has_key:
        return {
            "mode": "Offline Mode",
            "badge_color": "offline",
            "badge_label": "🟠 Offline Mode Active",
            "configured": False,
            "verified": False,
            "provider": config["provider"],
            "model": config["model"],
            "base_url": config["base_url"],
            "masked_key": mask_api_key(config["api_key"]),
            "error": None,
        }

    if _connection_state["verified"]:
        return {
            "mode": "Online AI Mode",
            "badge_color": "online",
            "badge_label": f"🟢 Online AI Active ({config['provider']})",
            "configured": True,
            "verified": True,
            "provider": config["provider"],
            "model": config["model"],
            "base_url": config["base_url"],
            "masked_key": mask_api_key(config["api_key"]),
            "latency_ms": _connection_state.get("latency_ms"),
            "error": None,
        }

    if _connection_state["status"] == "error":
        return {
            "mode": "Online AI Error",
            "badge_color": "error",
            "badge_label": "🔴 AI Connection Error",
            "configured": True,
            "verified": False,
            "provider": config["provider"],
            "model": config["model"],
            "base_url": config["base_url"],
            "masked_key": mask_api_key(config["api_key"]),
            "error": _connection_state["last_error"],
        }

    # Configured but untested
    return {
        "mode": "Online AI Configured",
        "badge_color": "configured",
        "badge_label": f"🟡 AI Configured ({config['provider']})",
        "configured": True,
        "verified": False,
        "provider": config["provider"],
        "model": config["model"],
        "base_url": config["base_url"],
        "masked_key": mask_api_key(config["api_key"]),
        "error": None,
    }


def chat_completion(
    messages: List[Dict[str, Any]],
    tools: Optional[List[Dict[str, Any]]] = None,
    temperature: float = 0.2,
) -> Dict[str, Any]:
    """
    Executes a chat completion call with optional function/tool declarations.
    Returns a unified response structure:
    {
        "content": str,
        "tool_calls": List[{"id": ..., "function": {"name": ..., "arguments": ...}}],
        "model": str,
        "finish_reason": str
    }
    """
    if not is_api_key_configured():
        raise LLMServiceError(
            "AI Agent API Key is not set. Please enter an OpenAI-compatible API Key in Settings to enable Online AI Mode."
        )

    config = get_llm_config()
    client = get_openai_client()

    kwargs: Dict[str, Any] = {
        "model": config["model"],
        "messages": messages,
        "temperature": temperature,
    }

    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    try:
        response = client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        message = choice.message

        formatted_tool_calls = []
        if message.tool_calls:
            for tc in message.tool_calls:
                formatted_tool_calls.append({
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    }
                })

        # Mark connection as verified on successful call
        _connection_state["status"] = "verified"
        _connection_state["verified"] = True
        _connection_state["last_error"] = None

        return {
            "content": message.content or "",
            "tool_calls": formatted_tool_calls,
            "model": response.model or config["model"],
            "finish_reason": choice.finish_reason,
        }

    except Exception as e:
        err_msg = sanitize_error_message(e, config["api_key"])
        _connection_state["status"] = "error"
        _connection_state["verified"] = False
        _connection_state["last_error"] = err_msg
        raise LLMServiceError(err_msg)
