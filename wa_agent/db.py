import sqlite3, os

DB_PATH = os.environ.get("WA_AGENT_DB", "wa_agent.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS chat_rules (
    jid            TEXT PRIMARY KEY,
    name           TEXT,
    phone          TEXT,
    enabled        INTEGER DEFAULT 0,
    custom_prompt  TEXT,
    max_auto_turns INTEGER DEFAULT 0,
    notes          TEXT,
    updated_at     TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agent_logs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_jid   TEXT,
    chat_name  TEXT,
    role       TEXT,
    content    TEXT,
    timestamp  TEXT DEFAULT (datetime('now')),
    status     TEXT DEFAULT 'ok'
);
"""

DEFAULT_SETTINGS = {
    "provider": "anthropic_api",
    "anthropic_api_key": "",
    "model": "claude-haiku-4-5-20251001",
    "business_name": "ShootEmpire",
    "system_prompt": (
        "You are a helpful sales and support assistant for {business_name}. "
        "You help customers with bookings, pricing, packages, and general inquiries. "
        "Be friendly, professional, and concise. Keep responses short (1-3 sentences). "
        "If you cannot help, say you will connect them with a team member shortly."
    ),
    "reply_delay_min": "3",
    "reply_delay_max": "8",
    "poll_interval": "5",
    "bridge_url": "http://localhost:8080/api",
    "auto_reply_all": "1",
    "max_history_messages": "20",
}


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.executescript(SCHEMA)
    for k, v in DEFAULT_SETTINGS.items():
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
    conn.commit()
    conn.close()


def get_setting(key: str, default=None):
    conn = get_conn()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key: str, value: str):
    conn = get_conn()
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()


def get_all_settings():
    conn = get_conn()
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}


def get_chat_rules():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM chat_rules ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_chat_rule(jid: str):
    conn = get_conn()
    row = conn.execute("SELECT * FROM chat_rules WHERE jid = ?", (jid,)).fetchone()
    conn.close()
    return dict(row) if row else None


def upsert_chat_rule(jid, name=None, phone=None, enabled=None, custom_prompt=None,
                     max_auto_turns=None, notes=None):
    conn = get_conn()
    existing = conn.execute("SELECT * FROM chat_rules WHERE jid = ?", (jid,)).fetchone()
    if existing:
        fields, vals = [], []
        if name is not None: fields.append("name = ?"); vals.append(name)
        if phone is not None: fields.append("phone = ?"); vals.append(phone)
        if enabled is not None: fields.append("enabled = ?"); vals.append(int(enabled))
        if custom_prompt is not None: fields.append("custom_prompt = ?"); vals.append(custom_prompt)
        if max_auto_turns is not None: fields.append("max_auto_turns = ?"); vals.append(max_auto_turns)
        if notes is not None: fields.append("notes = ?"); vals.append(notes)
        fields.append("updated_at = datetime('now')")
        if fields:
            conn.execute(f"UPDATE chat_rules SET {', '.join(fields)} WHERE jid = ?", vals + [jid])
    else:
        conn.execute(
            "INSERT INTO chat_rules (jid, name, phone, enabled, custom_prompt, max_auto_turns, notes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (jid, name, phone, int(enabled or 0), custom_prompt, max_auto_turns or 0, notes)
        )
    conn.commit()
    conn.close()


def add_log(chat_jid, chat_name, role, content, status="ok"):
    conn = get_conn()
    conn.execute(
        "INSERT INTO agent_logs (chat_jid, chat_name, role, content, status) VALUES (?, ?, ?, ?, ?)",
        (chat_jid, chat_name, role, content[:2000], status)
    )
    conn.commit()
    conn.close()


def get_logs(limit=100, chat_jid=None):
    conn = get_conn()
    if chat_jid:
        rows = conn.execute(
            "SELECT * FROM agent_logs WHERE chat_jid = ? ORDER BY id DESC LIMIT ?",
            (chat_jid, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM agent_logs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
