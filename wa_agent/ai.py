import subprocess, os, anthropic

CLAUDE_CLI = "/usr/local/bin/claude"
CLAUDE_TOKEN_FILE = os.environ.get("CLAUDE_TOKEN_FILE", "/home/deploy/wa-agent/.claude_token")


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


def _get_subscription_token() -> str:
    """Read the OAuth token from file or environment."""
    token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
    if token:
        return token
    try:
        with open(CLAUDE_TOKEN_FILE) as f:
            return f.read().strip()
    except OSError:
        raise RuntimeError(f"No OAuth token available (checked env + {CLAUDE_TOKEN_FILE})")


def generate_reply_cli(
    model: str,
    system_prompt: str,
    history: list,
) -> str:
    """Generate reply using Claude subscription OAuth token via SDK."""
    token = _get_subscription_token()
    client = anthropic.Anthropic(api_key=token)
    messages = build_messages(history)
    response = client.messages.create(
        model=model,
        max_tokens=512,
        system=system_prompt,
        messages=messages,
    )
    return response.content[0].text.strip()
