import anthropic


def build_messages(history: list, my_jid_prefix: str = None) -> list:
    """Convert bridge message history to Anthropic messages format."""
    result = []
    for msg in history:
        role = "assistant" if msg.get("is_from_me") else "user"
        content = msg.get("content") or f"[{msg.get('media_type', 'media')}]"
        if not content.strip():
            continue
        # Merge consecutive same-role messages
        if result and result[-1]["role"] == role:
            result[-1]["content"] += "\n" + content
        else:
            result.append({"role": role, "content": content})
    # Anthropic requires starting with user
    while result and result[0]["role"] == "assistant":
        result.pop(0)
    return result or [{"role": "user", "content": "Hello"}]


def generate_reply(
    api_key: str,
    model: str,
    system_prompt: str,
    history: list,
) -> str:
    client = anthropic.Anthropic(api_key=api_key)
    messages = build_messages(history)
    response = client.messages.create(
        model=model,
        max_tokens=512,
        system=system_prompt,
        messages=messages,
    )
    return response.content[0].text.strip()
