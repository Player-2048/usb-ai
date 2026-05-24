"""
Protocol translation: OpenAI format is the universal interface.

Inbound:  OpenAI Chat Completions format  →  translate to target provider format
Outbound: Target provider response        →  translate back to OpenAI format
"""


def openai_to_anthropic(messages: list[dict], model: str, **params) -> dict:
    """OpenAI messages → Anthropic Messages API format."""
    system_prompts = []
    conversation = []

    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if role == "system":
            system_prompts.append(content)
        elif role in ("user", "assistant"):
            conversation.append({"role": role, "content": content})

    body = {
        "model": model,
        "messages": conversation,
        "max_tokens": params.get("max_tokens", 4096),
    }

    if system_prompts:
        body["system"] = "\n\n".join(system_prompts)

    if params.get("temperature") is not None:
        body["temperature"] = params["temperature"]
    if params.get("top_p") is not None:
        body["top_p"] = params["top_p"]

    return body


def anthropic_to_openai(response: dict, model: str) -> dict:
    """Anthropic Messages response → OpenAI Chat Completions format."""
    content_list = response.get("content", [])
    text_parts = []
    for block in content_list:
        if block.get("type") == "text":
            text_parts.append(block.get("text", ""))

    return {
        "id": response.get("id", ""),
        "object": "chat.completion",
        "created": 0,
        "model": model,
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "\n".join(text_parts),
            },
            "finish_reason": response.get("stop_reason", "stop"),
        }],
        "usage": {
            "prompt_tokens": response.get("usage", {}).get("input_tokens", 0),
            "completion_tokens": response.get("usage", {}).get("output_tokens", 0),
            "total_tokens": (
                response.get("usage", {}).get("input_tokens", 0)
                + response.get("usage", {}).get("output_tokens", 0)
            ),
        },
    }


def openai_to_gemini(messages: list[dict], model: str, **params) -> dict:
    """OpenAI messages → Gemini API format."""
    system_parts = []
    contents = []

    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if role == "system":
            system_parts.append({"text": content})
        elif role == "user":
            contents.append({"role": "user", "parts": [{"text": content}]})
        elif role == "assistant":
            contents.append({"role": "model", "parts": [{"text": content}]})

    body = {
        "contents": contents,
        "generationConfig": {
            "maxOutputTokens": params.get("max_tokens", 4096),
        },
    }

    if system_parts:
        body["systemInstruction"] = {"parts": system_parts}

    if params.get("temperature") is not None:
        body["generationConfig"]["temperature"] = params["temperature"]
    if params.get("top_p") is not None:
        body["generationConfig"]["topP"] = params["top_p"]

    return body


def gemini_to_openai(response: dict, model: str) -> dict:
    """Gemini response → OpenAI Chat Completions format."""
    candidates = response.get("candidates", [])
    text = ""
    finish_reason = "stop"

    if candidates:
        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts)
        finish_reason = candidates[0].get("finishReason", "STOP").lower()

    usage = response.get("usageMetadata", {})

    return {
        "id": "",
        "object": "chat.completion",
        "created": 0,
        "model": model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": text},
            "finish_reason": finish_reason,
        }],
        "usage": {
            "prompt_tokens": usage.get("promptTokenCount", 0),
            "completion_tokens": usage.get("candidatesTokenCount", 0),
            "total_tokens": usage.get("totalTokenCount", 0),
        },
    }
