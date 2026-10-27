import sqlite3, os, requests
from datetime import datetime, timezone

MESSAGES_DB = os.environ.get(
    "WA_MESSAGES_DB",
    "/home/deploy/whatsapp-mcp/whatsapp-bridge/store/messages.db"
)
WA_DB = os.environ.get(
    "WA_STORE_DB",
    "/home/deploy/whatsapp-mcp/whatsapp-bridge/store/whatsapp.db"
)


def _msg_conn():
    conn = sqlite3.connect(MESSAGES_DB)
    conn.row_factory = sqlite3.Row
    return conn


def get_new_messages(since_timestamp: str):
    """Return incoming messages received after since_timestamp (ISO string)."""
    # Normalize to SQLite-compatible format (space separator, no sub-second)
    normalized = since_timestamp.replace("T", " ").split(".")[0]
    if "+" not in normalized and normalized[-1] != "Z":
        normalized += "+00:00"
    conn = _msg_conn()
    rows = conn.execute(
        "SELECT * FROM messages WHERE is_from_me = 0 AND datetime(timestamp) > datetime(?) ORDER BY timestamp ASC",
        (normalized,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_chat_history(chat_jid: str, limit: int = 20):
    """Return last N messages in a chat (both directions), oldest first."""
    conn = _msg_conn()
    rows = conn.execute(
        "SELECT * FROM messages WHERE chat_jid = ? ORDER BY timestamp DESC LIMIT ?",
        (chat_jid, limit)
    ).fetchall()
    conn.close()
    return list(reversed([dict(r) for r in rows]))


def get_contact_name_map():
    """Build jid_num → name map from whatsapp.db."""
    names = {}
    lid_map = {}
    try:
        conn = sqlite3.connect(WA_DB)
        conn.row_factory = sqlite3.Row
        for r in conn.execute("SELECT lid, pn FROM whatsmeow_lid_map").fetchall():
            lid_map[r["lid"]] = r["pn"]
        for r in conn.execute(
            "SELECT their_jid, push_name FROM whatsmeow_contacts WHERE push_name IS NOT NULL"
        ).fetchall():
            jid_num = r["their_jid"].split("@")[0]
            names[jid_num] = r["push_name"]
        conn.close()
    except Exception:
        pass
    return names, lid_map


def resolve_name(jid: str, names: dict, lid_map: dict):
    jid_num = jid.split("@")[0]
    name = names.get(jid_num)
    if name:
        return name
    pn = lid_map.get(jid_num)
    if pn:
        return "+" + pn
    return jid_num


def send_message(bridge_url: str, recipient_jid: str, message: str):
    """Send a message via the WhatsApp bridge HTTP API."""
    url = f"{bridge_url.rstrip('/')}/send"
    payload = {"recipient": recipient_jid, "message": message}
    resp = requests.post(url, json=payload, timeout=15)
    resp.raise_for_status()
    return resp.json()


def now_iso():
    return datetime.now(timezone.utc).isoformat()
