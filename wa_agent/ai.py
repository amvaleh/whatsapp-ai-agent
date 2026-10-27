import subprocess, anthropic

CLAUDE_CLI = "/usr/local/bin/claude"


def build_messages(history: list) -> list:
    """Convert bridge message history to Anthropic messages format."""
    result = []
    for msg in history:
        role = "assistant" if msg.get("is_from_me") else "user"
        content = msg.get("content") or f"[{msg.get('media_type', 'media')}]"
        if not content.strip():
            continue
        if result and result[-1]["role"] == role:
            result[-1]["content"] += "\n" + content
        else:
            result.append({"role": role, "content": content})
    while result and result[0]["role"] == "assistant":
        result.pop(0)
    return result or [{"role": "user", "content": "Hello"}]


def _format_history_for_cli(history: list) -> str:
    """Format conversation history as readable text for the CLI."""
    lines = []
    for msg in history:
        content = msg.get("content") or f"[{msg.get('media_type', 'media')}]"
        if not content.strip():
            continue
        speaker = "Agent" if msg.get("is_from_me") else "Customer"
        lines.append(f"{speaker}: {content}")
    return "\n".join(lines)


def generate_reply(
    api_key: str,
    model: str,
    system_prompt: str,
    history: list,
) -> str:
    """Generate reply using Anthropic API key."""
    client = anthropic.Anthropic(api_key=api_key)
    messages = build_messages(history)
    response = client.messages.create(
        model=model,
        max_tokens=512,
        system=system_prompt,
        messages=messages,
    )
    return response.content[0].text.strip()


def generate_reply_cli(
    model: str,
    system_prompt: str,
    history: list,
) -> str:
    """Generate reply using the local claude CLI (subscription-based)."""
    history_text = _format_history_for_cli(history)
    prompt = (
        f"{history_text}\n\n"
        "Now write only the Agent's next reply. "
        "Reply directly as the agent, no labels or prefixes."
    )
    cmd = [CLAUDE_CLI, "--print", "--model", model, "--system-prompt", system_prompt, "-p", prompt]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(f"claude CLI error: {result.stderr.strip()}")
    return result.stdout.strip()
