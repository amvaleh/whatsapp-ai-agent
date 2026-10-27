import time, random, threading, logging
from datetime import datetime, timezone

from . import db, bridge, ai

logger = logging.getLogger("wa_agent.poller")

_stop_event = threading.Event()
_thread = None
_rate_limit_backoff_until = 0.0


def _process_new_messages(last_ts: str) -> str:
    settings = db.get_all_settings()
    provider = settings.get("provider", "anthropic_api")
    api_key = settings.get("anthropic_api_key", "")
    model = settings.get("model", "claude-haiku-4-5-20251001")
    system_prompt_tpl = settings.get("system_prompt", "You are a helpful assistant.")
    business_name = settings.get("business_name", "our company")
    bridge_url = settings.get("bridge_url", "http://localhost:8080/api")
    auto_all = settings.get("auto_reply_all", "0") == "1"
    max_history = int(settings.get("max_history_messages", "20"))
    delay_min = float(settings.get("reply_delay_min", "3"))
    delay_max = float(settings.get("reply_delay_max", "8"))

    system_prompt = system_prompt_tpl.replace("{business_name}", business_name)

    if provider == "anthropic_api" and not api_key:
        return last_ts

    new_msgs = bridge.get_new_messages(last_ts)
    if not new_msgs:
        return last_ts

    names, lid_map = bridge.get_contact_name_map()

    # Group by chat, process each chat once (latest message triggers reply)
    seen_chats = {}
    for msg in new_msgs:
        seen_chats[msg["chat_jid"]] = msg

    def _norm(ts):
        return ts.replace("T", " ").split(".")[0] if ts else ""

    new_last_ts = last_ts
    for chat_jid, trigger_msg in seen_chats.items():
        msg_ts = trigger_msg.get("timestamp", "")
        if _norm(msg_ts) > _norm(new_last_ts):
            new_last_ts = msg_ts

        # Decide if we should reply
        rule = db.get_chat_rule(chat_jid)
        should_reply = False
        custom_prompt_extra = ""

        if rule:
            should_reply = bool(rule["enabled"])
            custom_prompt_extra = rule.get("custom_prompt") or ""
        elif auto_all:
            should_reply = True

        if not should_reply:
            continue

        chat_name = resolve_chat_name(chat_jid, names, lid_map, rule)

        full_system = system_prompt
        if custom_prompt_extra:
            full_system += "\n\n" + custom_prompt_extra

        try:
            history = bridge.get_chat_history(chat_jid, max_history)
            if provider == "claude_cli":
                reply = ai.generate_reply_cli(model, full_system, history)
            else:
                reply = ai.generate_reply(api_key, model, full_system, history)

            # Human-like delay
            delay = random.uniform(delay_min, delay_max)
            logger.info(f"Replying to {chat_name} ({chat_jid}) in {delay:.1f}s")
            time.sleep(delay)

            bridge.send_message(bridge_url, chat_jid, reply)
            db.add_log(chat_jid, chat_name, "assistant", reply)
            logger.info(f"Sent reply to {chat_name}: {reply[:80]}")

        except Exception as e:
            err_str = str(e)
            logger.error(f"Error processing {chat_jid}: {e}")
            db.add_log(chat_jid, chat_name, "error", err_str[:500], status="error")
            if "429" in err_str or "rate_limit" in err_str.lower():
                global _rate_limit_backoff_until
                _rate_limit_backoff_until = time.time() + 60
                logger.warning("Rate limited — backing off for 60s")
                break

    return new_last_ts


def resolve_chat_name(jid, names, lid_map, rule=None):
    if rule and rule.get("name"):
        return rule["name"]
    return bridge.resolve_name(jid, names, lid_map)


def poll_loop():
    last_ts = db.get_setting("_last_processed_ts") or datetime.now(timezone.utc).isoformat()
    logger.info(f"Poller started, watching from {last_ts}")

    while not _stop_event.is_set():
        try:
            interval = float(db.get_setting("poll_interval") or "5")
            if time.time() < _rate_limit_backoff_until:
                _stop_event.wait(timeout=5)
                continue
            new_ts = _process_new_messages(last_ts)
            if new_ts != last_ts:
                last_ts = new_ts
                db.set_setting("_last_processed_ts", last_ts)
        except Exception as e:
            logger.error(f"Poller error: {e}")
        _stop_event.wait(timeout=interval)

    logger.info("Poller stopped.")


def start():
    global _thread
    _stop_event.clear()
    _thread = threading.Thread(target=poll_loop, daemon=True, name="wa-poller")
    _thread.start()
    logger.info("Poller thread started.")


def stop():
    _stop_event.set()
    if _thread:
        _thread.join(timeout=10)
