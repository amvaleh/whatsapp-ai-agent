import json, sqlite3, os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from . import db, bridge, poller

PORT = int(os.environ.get("WA_AGENT_PORT", "3000"))
BASE_PATH = os.environ.get("WA_AGENT_BASE_PATH", "").rstrip("/")

# ─── HTML Shell ───────────────────────────────────────────────────────────────

STYLE = """
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh}
nav{background:#1e293b;padding:14px 24px;display:flex;align-items:center;gap:24px;border-bottom:1px solid #334155;position:sticky;top:0;z-index:10}
nav .logo{font-size:17px;font-weight:700;color:#38bdf8;text-decoration:none}
nav a{color:#94a3b8;text-decoration:none;font-size:14px}nav a:hover,nav a.active{color:#e2e8f0}
.badge{background:#22c55e;color:#fff;font-size:10px;padding:2px 6px;border-radius:999px;margin-left:6px}
.badge.off{background:#64748b}
.container{max-width:1100px;margin:0 auto;padding:28px 20px}
h1{font-size:22px;font-weight:700;margin-bottom:20px}
h2{font-size:16px;font-weight:600;margin-bottom:14px;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em}
.card{background:#1e293b;border-radius:12px;padding:20px;margin-bottom:20px;border:1px solid #334155}
table{width:100%;border-collapse:collapse;font-size:14px}
th{text-align:left;padding:10px 12px;border-bottom:2px solid #334155;color:#64748b;font-weight:600;font-size:12px;text-transform:uppercase}
td{padding:10px 12px;border-bottom:1px solid #1e293b;vertical-align:middle}
tr:hover td{background:#0f172a33}
.toggle{position:relative;display:inline-block;width:42px;height:22px;cursor:pointer}
.toggle input{opacity:0;width:0;height:0}
.slider{position:absolute;inset:0;background:#334155;border-radius:999px;transition:.2s}
.toggle input:checked + .slider{background:#22c55e}
.slider:before{content:'';position:absolute;height:16px;width:16px;left:3px;top:3px;background:#fff;border-radius:50%;transition:.2s}
.toggle input:checked + .slider:before{transform:translateX(20px)}
.btn{display:inline-flex;align-items:center;gap:6px;padding:8px 16px;border-radius:8px;border:none;cursor:pointer;font-size:14px;font-weight:500;transition:.15s}
.btn-primary{background:#3b82f6;color:#fff}.btn-primary:hover{background:#2563eb}
.btn-sm{padding:5px 10px;font-size:12px}
.btn-ghost{background:transparent;border:1px solid #334155;color:#94a3b8}.btn-ghost:hover{border-color:#64748b;color:#e2e8f0}
.btn-danger{background:#ef4444;color:#fff}.btn-danger:hover{background:#dc2626}
input,textarea,select{width:100%;padding:9px 12px;background:#0f172a;border:1px solid #334155;border-radius:8px;color:#e2e8f0;font-size:14px;outline:none;transition:.15s}
input:focus,textarea:focus,select:focus{border-color:#3b82f6}
textarea{resize:vertical;font-family:inherit}
.form-group{margin-bottom:16px}
label{display:block;font-size:13px;color:#94a3b8;margin-bottom:5px;font-weight:500}
.grid-2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.chip{display:inline-block;padding:3px 8px;border-radius:999px;font-size:11px;font-weight:600}
.chip-on{background:#15803d22;color:#4ade80;border:1px solid #15803d55}
.chip-off{background:#1e293b;color:#64748b;border:1px solid #334155}
.log-row td:first-child{font-size:11px;color:#64748b;white-space:nowrap}
.log-me{color:#38bdf8}.log-user{color:#e2e8f0}.log-error{color:#f87171}
.stat{text-align:center;padding:16px}
.stat-val{font-size:28px;font-weight:700;color:#38bdf8}
.stat-label{font-size:12px;color:#64748b;margin-top:4px}
.grid-4{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
.alert{padding:12px 16px;border-radius:8px;margin-bottom:16px;font-size:14px}
.alert-warn{background:#78350f22;border:1px solid #d9770655;color:#fbbf24}
.modal-bg{display:none;position:fixed;inset:0;background:#0008;z-index:50;align-items:center;justify-content:center}
.modal-bg.show{display:flex}
.modal{background:#1e293b;border-radius:14px;padding:24px;width:500px;max-width:95vw;border:1px solid #334155}
.modal h3{font-size:16px;font-weight:700;margin-bottom:16px}
::-webkit-scrollbar{width:5px}::-webkit-scrollbar-track{background:transparent}::-webkit-scrollbar-thumb{background:#334155;border-radius:3px}
</style>
"""

def page(title, content, active):
    status = "ON" if poller._thread and poller._thread.is_alive() else "OFF"
    badge_cls = "badge" if status == "ON" else "badge off"
    return f"""<!DOCTYPE html><html lang=en><head><meta charset=UTF-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>{title} — WA Agent</title>{STYLE}</head><body>
<nav>
  <a class=logo href="{BASE_PATH}/">⚡ WA Agent</a>
  <a href="{BASE_PATH}/" {"class=active" if active=="chats" else ""}>Chats</a>
  <a href="{BASE_PATH}/logs" {"class=active" if active=="logs" else ""}>Logs</a>
  <a href="{BASE_PATH}/settings" {"class=active" if active=="settings" else ""}>Settings</a>
  <span style="margin-left:auto;font-size:13px;color:#64748b">
    Agent <span class="{badge_cls}">{status}</span>
  </span>
</nav>
<div class=container>{content}</div>
<script>
function api(url,method,body){{return fetch(url,{{method:method||'GET',headers:{{'Content-Type':'application/json'}},body:body?JSON.stringify(body):undefined}}).then(r=>r.json())}}
</script>
</body></html>"""


# ─── Views ────────────────────────────────────────────────────────────────────

def _edit_btn(jid, name, rule):
    q = lambda s: (s or "").replace('"', "&quot;")
    return (
        f'<button class="btn btn-ghost btn-sm" onclick="openEdit(this)"'
        f' data-jid="{jid}"'
        f' data-name="{q(name)}"'
        f' data-prompt="{q(rule.get("custom_prompt"))}"'
        f' data-turns="{rule.get("max_auto_turns", 0)}"'
        f' data-notes="{q(rule.get("notes"))}">Edit</button>'
    )


def view_chats():
    names, lid_map = bridge.get_contact_name_map()
    rules_map = {r["jid"]: r for r in db.get_chat_rules()}

    # Load chats from messages DB
    conn = sqlite3.connect(bridge.MESSAGES_DB)
    conn.row_factory = sqlite3.Row
    chats = conn.execute(
        "SELECT c.jid, c.name, c.last_message_time, m.content as last_msg "
        "FROM chats c LEFT JOIN messages m ON m.chat_jid=c.jid AND m.timestamp=c.last_message_time "
        "ORDER BY c.last_message_time DESC LIMIT 300"
    ).fetchall()
    conn.close()

    rows_html = ""
    for c in chats:
        jid = c["jid"]
        jid_num = jid.split("@")[0]
        contact_name = names.get(jid_num)
        pn = lid_map.get(jid_num)
        display_name = contact_name or (("+" + pn) if pn else c["name"] or jid_num)
        phone_html = f'<br><small style="color:#64748b;font-size:11px">{("+" + pn) if pn and contact_name else ""}</small>'

        rule = rules_map.get(jid, {})
        enabled = bool(rule.get("enabled", 0))
        chip = f'<span class="chip {"chip-on" if enabled else "chip-off"}">{"AUTO" if enabled else "OFF"}</span>'

        rows_html += f"""
        <tr>
          <td><strong>{display_name}</strong>{phone_html}</td>
          <td style="color:#64748b;max-width:240px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{c['last_msg'] or ''}</td>
          <td style="text-align:center">{chip}</td>
          <td style="text-align:center">
            <label class=toggle title="Toggle auto-reply">
              <input type=checkbox {"checked" if enabled else ""} onchange="toggleChat('{jid}',this.checked,'{display_name}')">
              <span class=slider></span>
            </label>
          </td>
          <td>{_edit_btn(jid, display_name, rule)}</td>
        </tr>"""

    global_prompt = db.get_setting("system_prompt", "")
    warn = ""
    if db.get_setting("provider", "anthropic_api") == "anthropic_api" and not db.get_setting("anthropic_api_key"):
        warn = f'<div class="alert alert-warn">⚠ No Anthropic API key set. Go to <a href="{BASE_PATH}/settings" style="color:#fbbf24">Settings</a> to add it.</div>'

    content = f"""
{warn}
<h1>Chats</h1>
<div class=card>
<table>
<thead><tr><th>Contact</th><th>Last message</th><th>Status</th><th>Auto-reply</th><th></th></tr></thead>
<tbody id=chat-tbody>{rows_html}</tbody>
</table>
</div>

<div class="modal-bg" id=edit-modal>
<div class=modal>
  <h3 id=edit-title>Edit chat rule</h3>
  <input type=hidden id=edit-jid>
  <div class=form-group>
    <label>Custom prompt override (leave blank to use global)</label>
    <textarea id=edit-prompt rows=4 placeholder="E.g. This is a VIP client, be extra attentive..."></textarea>
  </div>
  <div class=form-group>
    <label>Max auto turns (0 = unlimited)</label>
    <input type=number id=edit-turns min=0 value=0>
  </div>
  <div class=form-group>
    <label>Notes (internal)</label>
    <input type=text id=edit-notes placeholder="e.g. Wedding client, don't mention pricing">
  </div>
  <div style="display:flex;gap:10px;margin-top:4px">
    <button class="btn btn-primary" onclick="saveEdit()">Save</button>
    <button class="btn btn-ghost" onclick="closeEdit()">Cancel</button>
  </div>
</div>
</div>

<script>
async function toggleChat(jid, enabled, name) {{
  await api('/api/chat-rule', 'POST', {{jid, enabled, name}});
  location.reload();
}}
function openEdit(btn) {{
  const d = btn.dataset;
  document.getElementById('edit-jid').value = d.jid;
  document.getElementById('edit-title').textContent = 'Edit: ' + d.name;
  document.getElementById('edit-prompt').value = d.prompt;
  document.getElementById('edit-turns').value = d.turns || 0;
  document.getElementById('edit-notes').value = d.notes;
  document.getElementById('edit-modal').classList.add('show');
}}
function closeEdit() {{ document.getElementById('edit-modal').classList.remove('show'); }}
async function saveEdit() {{
  const jid = document.getElementById('edit-jid').value;
  const custom_prompt = document.getElementById('edit-prompt').value;
  const max_auto_turns = parseInt(document.getElementById('edit-turns').value) || 0;
  const notes = document.getElementById('edit-notes').value;
  await api('/api/chat-rule', 'POST', {{jid, custom_prompt, max_auto_turns, notes}});
  closeEdit(); location.reload();
}}
</script>"""
    return page("Chats", content, "chats")


def view_logs():
    logs = db.get_logs(200)
    rows_html = ""
    for l in logs:
        role_cls = {"assistant": "log-me", "user": "log-user", "error": "log-error"}.get(l["role"], "")
        role_icon = {"assistant": "🤖", "user": "👤", "error": "❌"}.get(l["role"], "")
        rows_html += f"""<tr class=log-row>
          <td>{l['timestamp']}</td>
          <td>{l['chat_name'] or l['chat_jid']}</td>
          <td><span class="{role_cls}">{role_icon} {l['role']}</span></td>
          <td style="max-width:400px;word-break:break-word">{l['content']}</td>
        </tr>"""
    content = f"""<h1>Agent Logs</h1>
<div class=card>
<table>
<thead><tr><th>Time</th><th>Chat</th><th>Role</th><th>Content</th></tr></thead>
<tbody>{rows_html or "<tr><td colspan=4 style='color:#64748b;padding:20px;text-align:center'>No logs yet</td></tr>"}</tbody>
</table>
</div>"""
    return page("Logs", content, "logs")


def _check_cli_status():
    """Return (ok: bool, message: str) — lightweight token-file check only."""
    import os
    token_file = os.environ.get("CLAUDE_TOKEN_FILE", "/home/deploy/wa-agent/.claude_token")
    if os.path.exists(token_file):
        return True, "SDK ready"
    return False, "No OAuth token found"


def view_settings():
    s = db.get_all_settings()
    models = [
        ("claude-haiku-4-5-20251001", "Claude Haiku 4.5 (fast, cheap)"),
        ("claude-sonnet-4-6", "Claude Sonnet 4.6 (balanced)"),
        ("claude-opus-4-7", "Claude Opus 4.7 (most capable)"),
    ]
    model_opts = "".join(
        f'<option value="{m}" {"selected" if s.get("model")==m else ""}>{label}</option>'
        for m, label in models
    )
    cur_provider = s.get("provider", "anthropic_api")
    cli_ok, cli_msg = _check_cli_status()
    cli_color = "#4ade80" if cli_ok else "#f87171"
    cli_icon = "✓" if cli_ok else "✗"
    content = f"""<h1>Settings</h1>
<form id=settings-form>
<div class=card>
  <h2>AI Configuration</h2>
  <div class=form-group>
    <label>AI Provider</label>
    <select id=provider onchange="toggleApiKey(this.value)">
      <option value="anthropic_api" {"selected" if cur_provider=="anthropic_api" else ""}>Anthropic API Key</option>
      <option value="claude_cli" {"selected" if cur_provider=="claude_cli" else ""}>Claude CLI (claude.ai subscription)</option>
    </select>
  </div>
  <div class=form-group id=api-key-group style="{"display:none" if cur_provider=="claude_cli" else ""}">
    <label>Anthropic API Key</label>
    <input type=password id=anthropic_api_key value="{s.get('anthropic_api_key','')}" placeholder="sk-ant-...">
    <small style="color:#64748b;font-size:12px;margin-top:4px;display:block">Get yours at console.anthropic.com</small>
  </div>

  <div id=cli-status-card style="{"" if cur_provider=="claude_cli" else "display:none"}">
    <div style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:14px 16px;margin-bottom:12px;display:flex;align-items:center;gap:10px">
      <span style="font-size:18px;color:{cli_color}">{cli_icon}</span>
      <div>
        <div style="font-size:14px;font-weight:600;color:{cli_color}">Claude CLI: {cli_msg}</div>
        <div style="font-size:12px;color:#64748b;margin-top:2px">Status checked on page load</div>
      </div>
      <button type=button class="btn btn-ghost btn-sm" style="margin-left:auto" onclick="testCli()">Re-check</button>
    </div>
    <div style="background:#0f172a;border:1px solid #1e40af44;border-radius:8px;padding:14px 16px;font-size:13px;color:#94a3b8;line-height:1.7">
      <strong style="color:#e2e8f0">How to authenticate on your server:</strong><br>
      1. Install Claude CLI: <code style="background:#1e293b;padding:1px 5px;border-radius:4px">npm install -g @anthropic-ai/claude-code</code><br>
      2. Login: <code style="background:#1e293b;padding:1px 5px;border-radius:4px">claude login</code> — opens browser OAuth for claude.ai<br>
      3. Credentials are saved in <code style="background:#1e293b;padding:1px 5px;border-radius:4px">~/.claude/</code> and reused automatically<br>
      4. Return here and click <strong>Re-check</strong> to confirm
    </div>
  </div>
  <div class=form-group>
    <label>Model</label>
    <select id=model>{model_opts}</select>
  </div>
  <div class=form-group>
    <label>Business Name</label>
    <input type=text id=business_name value="{s.get('business_name','')}">
  </div>
  <div class=form-group>
    <label>Default System Prompt (use {{{{business_name}}}} as placeholder)</label>
    <textarea id=system_prompt rows=6>{s.get('system_prompt','')}</textarea>
  </div>
</div>
<div class=card>
  <h2>Behaviour</h2>
  <div class=grid-2>
    <div class=form-group>
      <label>Reply delay min (seconds)</label>
      <input type=number id=reply_delay_min value="{s.get('reply_delay_min','3')}" min=0 step=0.5>
    </div>
    <div class=form-group>
      <label>Reply delay max (seconds)</label>
      <input type=number id=reply_delay_max value="{s.get('reply_delay_max','8')}" min=0 step=0.5>
    </div>
    <div class=form-group>
      <label>Poll interval (seconds)</label>
      <input type=number id=poll_interval value="{s.get('poll_interval','5')}" min=1>
    </div>
    <div class=form-group>
      <label>Max history messages</label>
      <input type=number id=max_history_messages value="{s.get('max_history_messages','20')}" min=5 max=100>
    </div>
  </div>
  <div class=form-group>
    <label style="display:flex;align-items:center;gap:10px;cursor:pointer">
      <label class=toggle>
        <input type=checkbox id=auto_reply_all {"checked" if s.get('auto_reply_all')=='1' else ""}>
        <span class=slider></span>
      </label>
      Auto-reply to new/unknown contacts (doesn't affect per-chat toggle)
    </label>
  </div>
</div>
<div class=card>
  <h2>Bridge</h2>
  <div class=form-group>
    <label>Bridge API URL</label>
    <input type=text id=bridge_url value="{s.get('bridge_url','http://localhost:8080/api')}">
  </div>
</div>
<button type=button class="btn btn-primary" onclick="saveSettings()">Save Settings</button>
<span id=save-msg style="margin-left:12px;color:#4ade80;display:none">✓ Saved</span>
</form>
<script>
function toggleApiKey(val) {{
  document.getElementById('api-key-group').style.display = val === 'claude_cli' ? 'none' : '';
  document.getElementById('cli-status-card').style.display = val === 'claude_cli' ? '' : 'none';
}}
async function testCli() {{
  // /api/cli-status endpoint removed; status is now shown server-side only
}}
async function saveSettings() {{
  const keys = ['provider','anthropic_api_key','model','business_name','system_prompt',
    'reply_delay_min','reply_delay_max','poll_interval','max_history_messages','bridge_url'];
  const data = {{}};
  keys.forEach(k => data[k] = document.getElementById(k).value);
  data['auto_reply_all'] = document.getElementById('auto_reply_all').checked ? '1' : '0';
  const r = await api('/api/settings', 'POST', data);
  const m = document.getElementById('save-msg');
  m.style.display = 'inline'; setTimeout(()=>m.style.display='none', 2500);
}}
</script>"""
    return page("Settings", content, "settings")


# ─── HTTP Handler ─────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def send_html(self, html):
        b = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def send_json(self, data, status=200):
        b = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length)) if length else {}

    def _strip_base(self, raw_path):
        path = urlparse(raw_path).path
        if BASE_PATH and path.startswith(BASE_PATH):
            path = path[len(BASE_PATH):] or "/"
        return path

    def do_GET(self):
        path = self._strip_base(self.path)
        if path in ("/", "/chats"):
            self.send_html(view_chats())
        elif path == "/logs":
            self.send_html(view_logs())
        elif path == "/settings":
            self.send_html(view_settings())
        else:
            self.send_response(404); self.end_headers()

    def do_POST(self):
        path = self._strip_base(self.path)
        body = self.read_body()

        if path == "/api/settings":
            for k, v in body.items():
                db.set_setting(k, str(v))
            self.send_json({"ok": True})

        elif path == "/api/chat-rule":
            jid = body.get("jid")
            if not jid:
                self.send_json({"error": "jid required"}, 400); return
            db.upsert_chat_rule(
                jid=jid,
                name=body.get("name"),
                enabled=body.get("enabled"),
                custom_prompt=body.get("custom_prompt"),
                max_auto_turns=body.get("max_auto_turns"),
                notes=body.get("notes"),
            )
            self.send_json({"ok": True})

        else:
            self.send_response(404); self.end_headers()


def run(host="0.0.0.0", port=PORT):
    server = HTTPServer((host, port), Handler)
    print(f"WA Agent admin UI → http://localhost:{port}")
    server.serve_forever()
