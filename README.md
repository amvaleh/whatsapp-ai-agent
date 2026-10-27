# WA Agent — WhatsApp AI Auto-Reply Agent

An AI-powered WhatsApp auto-reply system built on the [whatsapp-mcp](https://github.com/lharries/whatsapp-mcp) bridge. Configure it once, and it answers your WhatsApp messages using Claude AI — acting as a sales agent, support bot, or personal assistant.

## Features

- **Per-chat auto-reply toggle** — enable AI for specific contacts, not all at once
- **Custom prompts per chat** — VIP client? Different tone? Set it per-conversation
- **Human-like delay** — configurable random delay before sending (feels natural)
- **Admin web panel** — clean dashboard to manage chats, settings, and view logs
- **Any use case** — configure via system prompt: sales, support, bookings, lead gen
- **Commercially deployable** — sell it as a SaaS or white-label it

## Requirements

- Python 3.9+
- [whatsapp-mcp bridge](https://github.com/lharries/whatsapp-mcp) running (Go binary)
- Anthropic API key

## Quick Start

```bash
# 1. Clone
git clone https://github.com/yourname/wa-agent
cd wa-agent

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure
cp .env.example .env
# Edit .env with your database paths

# 4. Start the bridge (separate terminal)
# Follow whatsapp-mcp setup to scan QR code

# 5. Run
python run.py

# 6. Open admin panel
open http://localhost:3000
# → Go to Settings, add your Anthropic API key
# → Go to Chats, toggle auto-reply for the contacts you want
```

## Admin Panel

| Page | Description |
|------|-------------|
| **Chats** | All WhatsApp chats with enable/disable toggle per chat |
| **Logs** | Every AI reply sent, with timestamps |
| **Settings** | API key, model, system prompt, delays, bridge URL |

## Configuration

All settings are managed via the admin panel (stored in `wa_agent.db`):

| Setting | Default | Description |
|---------|---------|-------------|
| `anthropic_api_key` | — | Your Anthropic API key |
| `model` | `claude-haiku-4-5` | AI model to use |
| `business_name` | `My Business` | Used in the default system prompt |
| `system_prompt` | See panel | The AI's personality and instructions |
| `reply_delay_min` | `3` | Min seconds before replying |
| `reply_delay_max` | `8` | Max seconds before replying |
| `poll_interval` | `5` | How often to check for new messages (seconds) |
| `auto_reply_all` | `off` | Reply to ALL chats (override per-chat toggle) |

## Per-Chat Settings

For each chat you can set:
- **Auto-reply on/off** toggle
- **Custom prompt override** — extra instructions for this specific chat
- **Max auto turns** — stop auto-replying after N turns (0 = unlimited)
- **Internal notes** — for your reference

## Architecture

```
WhatsApp ←→ whatsapp-bridge (Go) ←→ messages.db
                                          ↑
                          wa_agent/poller.py (polls every 5s)
                                          ↓
                          wa_agent/ai.py → Anthropic Claude API
                                          ↓
                          wa_agent/bridge.py → bridge HTTP /api/send
```

## License

MIT
