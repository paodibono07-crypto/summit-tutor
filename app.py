import difflib
import html as _html
import json as _json
import time
from collections import defaultdict

import gradio as gr

from chat import chat, chat_with_image, start_worksheet, worksheet_turn, _py_game_questions
from guardrails import is_on_topic, off_topic_reply
from logger import log_interaction
from resource_index import get_topic_name, find_resources

# Per-user rate limiting: maps user IP → list of request timestamps in last 60 s
_rate_limit_window = 60
_rate_limit_max    = 20
_request_log: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(user_ip: str) -> bool:
    now = time.time()
    _request_log[user_ip] = [t for t in _request_log[user_ip] if now - t < _rate_limit_window]
    if len(_request_log[user_ip]) >= _rate_limit_max:
        return False
    _request_log[user_ip].append(now)
    return True


TITLE = "Summit Tutor"

EXAMPLES = [
    "What is 35 - 27?",
    "How do I add fractions?",
    "What is 6 x 7?",
    "How do I regroup when subtracting?",
    "What is 1/2 + 1/4?",
    "¿Cuánto es 45 - 28?",
]

CSS = """
/* ── Blue palette variables ─────────────────────────────────── */
:root {
    --navy:       #0a1f44;
    --royal:      #1a56db;
    --sky:        #3b9edd;
    --light-blue: #dbeafe;
    --pale-blue:  #eff6ff;
}

/* ── Page background ────────────────────────────────────────── */
body, .gradio-container {
    background-color: var(--pale-blue) !important;
}

/* ── Primary button (Send) → royal blue ─────────────────────── */
button.primary, .btn-primary {
    background: var(--royal) !important;
    border-color: var(--royal) !important;
    color: white !important;
}
button.primary:hover {
    background: var(--navy) !important;
    border-color: var(--navy) !important;
}

/* ── Secondary button (Clear) → sky blue ───────────────────── */
button.secondary {
    background: var(--sky) !important;
    border-color: var(--sky) !important;
    color: white !important;
}
button.secondary:hover {
    background: #2a7db5 !important;
}

/* ── Squash any lingering orange from default theme ─────────── */
button[data-testid], .wrap button {
    --button-primary-background-fill: var(--royal) !important;
    --button-primary-background-fill-hover: var(--navy) !important;
}

/* ── Textbox focus ──────────────────────────────────────────── */
textarea:focus, input[type="text"]:focus {
    border-color: var(--sky) !important;
    box-shadow: 0 0 0 3px rgba(59, 158, 221, 0.25) !important;
}

/* ── Info boxes ─────────────────────────────────────────────── */
.welcome-box {
    background-color: #dbeafe;
    border-left: 5px solid #1a56db;
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 8px;
    color: #0a1f44;
    font-size: 0.97em;
    line-height: 1.6;
}
.parent-box {
    background-color: #bfdbfe;
    border-left: 5px solid #3b9edd;
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 14px;
    color: #0a1f44;
    font-size: 0.93em;
    line-height: 1.6;
}

/* ── Header text ────────────────────────────────────────────── */
.header-title {
    color: #0a1f44;
    font-size: 2.1em;
    font-weight: 800;
    margin: 0 0 4px 0;
    line-height: 1.15;
}
.header-tagline {
    color: #3b9edd;
    font-size: 1.1em;
    font-weight: 500;
    margin: 0;
}

/* ── Footer ─────────────────────────────────────────────────── */
.footer {
    text-align: center;
    color: #1a56db;
    font-size: 0.85em;
    margin-top: 16px;
    padding-top: 12px;
    border-top: 1px solid #bfdbfe;
    letter-spacing: 0.02em;
}
"""


# ── Fuzzy intent detection ────────────────────────────────────────────────────

_WORKSHEET_TRIGGERS = [
    # English (canonical + common typos)
    "worksheet", "work sheet", "workshet", "worsheet", "worksheat", "worksheets",
    "workheet", "worksheeet",
    # Spanish
    "hoja", "hoja de trabajo", "practica", "práctica",
    "hoja de practica", "hoja de práctica",
    "ejercicios", "ejercicio", "practicar",
]

_ACTIVITY_TRIGGERS = [
    # English (canonical + common typos)
    "activity", "activty", "activiti", "activites", "activities",
    "game", "play",
    # Spanish (canonical + accent variant + common typos)
    "actividad", "actívidad", "activdad", "actividades",
    "juego", "jugar", "juego de matematicas", "juego de matemáticas",
]


def _fuzzy(msg: str, triggers: list[str], cutoff: float = 0.80) -> bool:
    clean = msg.strip().lower()
    if clean in triggers:
        return True
    return bool(difflib.get_close_matches(clean, triggers, n=1, cutoff=cutoff))


_EXIT_TRIGGERS = [
    "exit", "quit", "stop", "leave", "end", "done",
    "salir", "parar", "terminar", "detener", "salgo",
]


def _is_activity(msg: str)  -> bool: return _fuzzy(msg, _ACTIVITY_TRIGGERS)
def _is_worksheet(msg: str) -> bool: return _fuzzy(msg, _WORKSHEET_TRIGGERS)
def _is_exit(msg: str)      -> bool: return _fuzzy(msg, _EXIT_TRIGGERS, cutoff=0.85)


_GAME_TEMPLATE = """\
<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',Arial,sans-serif;background:#eff6ff;padding:10px}}
.g{{max-width:460px;margin:0 auto}}
.hdr{{text-align:center;padding:6px 0 2px;color:#0a1f44;font-weight:800;font-size:1.05em}}
.tp{{font-size:.82em;color:#3b9edd;font-weight:600;margin-top:2px}}
.mtn{{background:linear-gradient(135deg,#dbeafe,#eff6ff);border-radius:12px;padding:12px 14px 8px;margin:8px 0}}
.cr{{display:flex;align-items:center;justify-content:space-between;margin-bottom:5px}}
.ce{{font-size:1.5em;line-height:1}}
.cl{{flex:1;height:4px;background:#d1d5db;border-radius:2px;margin:0 3px;transition:background .4s}}
.cl.lit{{background:#fbbf24}}
.wr{{display:flex;justify-content:space-between;padding:0 5px}}
.cs{{flex:1;text-align:center;font-size:1.2em;min-height:1.4em;line-height:1.4}}
.st{{display:flex;justify-content:space-between;align-items:center;margin:6px 0;font-weight:700;font-size:.92em;color:#0a1f44}}
.tm{{background:#1a56db;color:#fff;padding:3px 11px;border-radius:14px;font-size:.86em;min-width:60px;text-align:center}}
.tm.red{{background:#dc2626;animation:bl .75s ease-in-out infinite alternate}}
@keyframes bl{{from{{opacity:1}}to{{opacity:.5}}}}
.cl2{{font-size:.78em;color:#3b9edd;font-weight:600;text-align:center;margin:4px 0 5px}}
.qb{{background:#fff;border:2px solid #bfdbfe;border-radius:10px;padding:10px 14px;text-align:center;font-size:1.28em;font-weight:800;color:#0a1f44;margin-bottom:9px;min-height:2.4em;display:flex;align-items:center;justify-content:center}}
.ir{{display:flex;gap:7px;justify-content:center;margin-bottom:7px}}
input{{font-size:1.05em;padding:6px 11px;border:2px solid #1a56db;border-radius:8px;width:120px;text-align:center;color:#0a1f44;outline:none}}
input:focus{{border-color:#3b9edd;box-shadow:0 0 0 3px rgba(59,158,221,.22)}}
input:disabled{{background:#f3f4f6}}
.sb{{font-size:.95em;padding:6px 16px;background:#1a56db;color:#fff;border:none;border-radius:8px;cursor:pointer;font-weight:700}}
.sb:hover:not(:disabled){{background:#0a1f44}}
.sb:disabled{{background:#9ca3af;cursor:default}}
.fb{{text-align:center;font-weight:700;min-height:1.5em;font-size:.92em;padding:2px 0}}
.fb.ok{{color:#16a34a}}.fb.no{{color:#dc2626}}.fb.to{{color:#d97706}}
.end{{display:none;background:linear-gradient(135deg,#1a3a6c,#0a1f44);color:#fff;border-radius:12px;padding:20px 16px;text-align:center;margin-top:8px}}
.end h2{{font-size:1.35em;margin-bottom:7px}}
.end p{{margin:3px 0;font-size:.92em}}
.rb{{margin-top:12px;padding:7px 20px;background:#3b9edd;color:#fff;border:none;border-radius:8px;cursor:pointer;font-weight:700;font-size:.92em}}
.rb:hover{{background:#2a7db5}}
</style></head><body>
<div class="g">
<div class="hdr">🏔️ SUMMIT MATH CHALLENGE 🏔️<br><span class="tp">__TOPIC_NAME__</span></div>
<div class="mtn">
  <div class="cr">
    <span class="ce">⛺</span><span class="cl" id="l0"></span>
    <span class="ce">🌲</span><span class="cl" id="l1"></span>
    <span class="ce">🪨</span><span class="cl" id="l2"></span>
    <span class="ce">❄️</span><span class="cl" id="l3"></span>
    <span class="ce">🦅</span><span class="cl" id="l4"></span>
    <span class="ce">🏔️</span>
  </div>
  <div class="wr">
    <span class="cs" id="c0"></span><span class="cs" id="c1"></span>
    <span class="cs" id="c2"></span><span class="cs" id="c3"></span>
    <span class="cs" id="c4"></span><span class="cs" id="c5"></span>
  </div>
</div>
<div class="st"><span id="sc">⭐ 0 / 5</span><span id="tm" class="tm">⏱️ 30s</span></div>
<div id="qa">
  <div id="cpl" class="cl2"></div>
  <div id="qel" class="qb">Loading…</div>
  <div class="ir">
    <input type="text" id="ai" inputmode="decimal" placeholder="Answer…" autocomplete="off">
    <button class="sb" id="sb">Submit ➤</button>
  </div>
  <div id="fb" class="fb"></div>
</div>
<div class="end" id="end">
  <h2>🏔️ SUMMIT REACHED! 🏔️</h2>
  <p id="es"></p><p id="ev"></p>
  <button class="rb" id="rb">🔄 Play Again</button>
</div>
</div>
<script>
const QS=__QUESTIONS_JSON__;
const TOTAL=QS.length;
const CPN=['⛺ Base Camp','🌲 Forest Trail','🪨 Rocky Ridge','❄️ Snow Zone','🦅 Peak','🏔️ SUMMIT'];
let qi=0,sc=0,tl=30,th=null,done=false,wrg=0;
function pn(t){{t=(t+'').trim().replace(/,/g,'');if(t.includes('/')){{const[a,b]=t.split('/').map(Number);return isNaN(a)||isNaN(b)||!b?null:a/b;}}const n=parseFloat(t);return isNaN(n)?null:n;}}
function neq(a,b){{const na=pn(''+a),nb=pn(''+b);return na!==null&&nb!==null&&Math.abs(na-nb)<0.01;}}
function sfb(t,c){{const e=document.getElementById('fb');e.textContent=t;e.className='fb '+(c||'');}}
function updSc(){{document.getElementById('sc').textContent='⭐ '+sc+' / '+TOTAL;}}
function mv(p){{for(let i=0;i<6;i++)document.getElementById('c'+i).textContent=i===p?'🧗':'';for(let i=0;i<5;i++)document.getElementById('l'+i).classList.toggle('lit',i<p);}}
function tick(){{const e=document.getElementById('tm');e.textContent='⏱️ '+tl+'s';e.className='tm'+(tl<=8?' red':'');}}
function startT(){{clearInterval(th);tl=30;tick();th=setInterval(()=>{{tl--;tick();if(tl<=0){{clearInterval(th);tout();}}}},1000);}}
function tout(){{if(done)return;done=true;sfb('⏰ Time up! Answer: '+QS[qi].a,'to');lk();setTimeout(nxtQ,2200);}}
function lk(){{document.getElementById('ai').disabled=true;document.getElementById('sb').disabled=true;}}
function ulk(){{const i=document.getElementById('ai');i.value='';i.disabled=false;document.getElementById('sb').disabled=false;}}
function showQ(){{done=false;wrg=0;document.getElementById('cpl').textContent=CPN[qi]+' — Q'+(qi+1)+'/'+TOTAL;document.getElementById('qel').textContent=QS[qi].q;ulk();sfb('');startT();setTimeout(()=>document.getElementById('ai').focus(),60);}}
function nxtQ(){{qi++;if(qi>=TOTAL){{endG();return;}}showQ();}}
function sub(){{
  if(done)return;
  const raw=document.getElementById('ai').value.trim();if(!raw)return;
  if(neq(raw,QS[qi].a)){{clearInterval(th);done=true;sc++;updSc();mv(Math.min(qi+1,5));sfb('✅ Correct! '+QS[qi].a+' — Great job! 🌟','ok');lk();setTimeout(nxtQ,1900);}}
  else{{wrg++;document.getElementById('ai').value='';setTimeout(()=>document.getElementById('ai').focus(),30);
    if(wrg>=2){{done=true;clearInterval(th);sfb('❌ Answer: '+QS[qi].a+'. Keep going! 💪','no');lk();setTimeout(nxtQ,2200);}}
    else sfb('❌ Not quite — try again! 💪','no');}}
}}
function endG(){{
  clearInterval(th);document.getElementById('qa').style.display='none';
  const end=document.getElementById('end');end.style.display='block';
  document.getElementById('es').textContent='Score: '+sc+'/'+TOTAL+' '+('⭐'.repeat(sc));
  const vs=['🌱 Good try — keep practicing!','🌱 Nice start!','⛰️ Getting there!','🏔️ Great work!','🏔️ Excellent!','🏆 PERFECT!'];
  document.getElementById('ev').textContent=vs[Math.min(sc,5)];
}}
function rst(){{qi=0;sc=0;done=false;wrg=0;updSc();mv(0);document.getElementById('qa').style.display='block';document.getElementById('end').style.display='none';showQ();}}
document.getElementById('sb').addEventListener('click',sub);
document.getElementById('ai').addEventListener('keydown',e=>{{if(e.key==='Enter')sub();}});
document.getElementById('rb').addEventListener('click',rst);
mv(0);showQ();
</script></body></html>"""


def _build_inline_game(topic_name: str) -> str:
    """Return a gr.HTML value: a self-contained iframe embedding the full game."""
    questions = _py_game_questions(topic_name)
    game_html = (
        _GAME_TEMPLATE
        .replace("__TOPIC_NAME__", topic_name)
        .replace("__QUESTIONS_JSON__", _json.dumps(questions))
    )
    escaped = _html.escape(game_html, quote=True)
    return (
        f'<iframe srcdoc="{escaped}" '
        f'style="width:100%;height:490px;border:none;border-radius:12px;'
        f'box-shadow:0 4px 20px rgba(0,0,0,0.15);display:block;margin:6px 0">'
        f'</iframe>'
    )


def respond(
    message: str,
    image_path: str | None,
    history: list[list[str | None]],
    claude_history: list[dict],
    last_topic: str,
    worksheet_state: dict,
    game_active: bool,
    request: gr.Request,
):
    has_image = image_path is not None
    session_active = game_active or worksheet_state.get("is_active", False)

    if not message.strip() and not has_image:
        return (history, claude_history, "", last_topic, worksheet_state,
                gr.update(), None, game_active, gr.update(visible=session_active))

    user_ip = request.client.host if request and request.client else "unknown"
    if not _check_rate_limit(user_ip):
        reply = (
            "You've sent a lot of questions in the last minute — please wait a moment "
            "and try again. I'll be right here when you're ready!"
        )
        new_history = history + [{"role": "user", "content": message}, {"role": "assistant", "content": reply}]
        return (new_history, claude_history, "", last_topic, worksheet_state,
                gr.update(), None, game_active, gr.update(visible=session_active))

    t_start = time.perf_counter()
    claude_history_out = claude_history
    panel_update = gr.update()
    new_game_active = game_active

    # ── Exit command: typed during an active game or worksheet ───────────────────
    if session_active and _is_exit(message):
        reply = (
            "👋 No problem! You can start a new question anytime. "
            "What math topic would you like to explore? 🏔️"
        )
        worksheet_state = {}
        new_game_active = False
        panel_update = gr.update(value="")
        log_interaction(message, reply, 0)
        new_history = history + [{"role": "user", "content": message}, {"role": "assistant", "content": reply}]
        return (new_history, claude_history_out, "", last_topic, worksheet_state,
                panel_update, None, new_game_active, gr.update(visible=False))

    if has_image:
        # Multimodal path — image takes priority over all other routing
        reply, claude_history_out = chat_with_image(message, image_path, claude_history)
        last_topic = get_topic_name(reply)
    elif worksheet_state.get("is_active"):
        reply, worksheet_state = worksheet_turn(message, worksheet_state)
    elif _is_activity(message):
        topic = last_topic or "general math"
        print(f"[GAME] Activity triggered — last_topic_state={last_topic!r}, using topic={topic!r}")
        reply = (
            f"🏔️ **Summit Mountain Climber** — Topic: **{topic}**\n\n"
            f"The game is loading below! Answer 5 questions to reach the summit! ⛰️\n\n"
            f"💡 Tip: Type **exit** or **salir** at any time to stop and ask a new math question!"
        )
        panel_update = gr.update(value=_build_inline_game(topic))
        new_game_active = True
    elif _is_worksheet(message):
        topic = last_topic or "general math"
        reply, worksheet_state = start_worksheet(topic)
    elif not is_on_topic(message):
        reply = off_topic_reply(message)
    else:
        reply, claude_history_out = chat(message, claude_history)
        # Prefer a keyword match from the message; if none, try the reply
        # (Claude's reply is richer and more likely to name the topic explicitly)
        if find_resources(message):
            last_topic = get_topic_name(message)
        elif find_resources(reply):
            last_topic = get_topic_name(reply)
        else:
            last_topic = get_topic_name(message)  # raw fallback
        print(f"[TOPIC] message={message[:50]!r} → last_topic={last_topic!r}")

    latency = time.perf_counter() - t_start
    log_interaction(message, reply, latency)

    display_msg = message if message.strip() else "📸 [math problem photo]"
    new_history = history + [{"role": "user", "content": display_msg}, {"role": "assistant", "content": reply}]
    new_session_active = new_game_active or worksheet_state.get("is_active", False)
    return (new_history, claude_history_out, "", last_topic, worksheet_state,
            panel_update, None, new_game_active, gr.update(visible=new_session_active))


def do_exit(history: list, claude_history: list, last_topic: str):
    """Exit handler for the Exit Game button."""
    reply = (
        "👋 No problem! You can start a new question anytime. "
        "What math topic would you like to explore? 🏔️"
    )
    new_history = history + [{"role": "assistant", "content": reply}]
    return (new_history, claude_history, "", last_topic, {},
            gr.update(value=""), None, False, gr.update(visible=False))


def clear_session():
    return ([], [], "", "", {}, gr.update(value=""), None, False, gr.update(visible=False))


with gr.Blocks(title=TITLE, theme=gr.themes.Soft(primary_hue="blue"), css=CSS) as demo:

    # ── Header: logo + title ─────────────────────────────────────
    with gr.Row(equal_height=True):
        with gr.Column(scale=1, min_width=170):
            gr.Image(
                value="logo.png",
                width=150,
                show_label=False,
                container=False,
            )
        with gr.Column(scale=5):
            gr.HTML("""
                <p class="header-title">SUMMIT Math Camp</p>
                <p class="header-tagline">Ain't No Mountain High Enough! 🏔️</p>
            """)

    # ── Info boxes ───────────────────────────────────────────────
    gr.HTML("""
        <div class="welcome-box">
            🎓 <strong>Welcome!</strong> I am your AI math tutor. Ask me any math question
            in <strong>English or Spanish</strong> and I will find activities from your
            Summit Math Camp materials and explain step by step.<br>
            <em>¡Bienvenido! Soy tu tutor de matemáticas. Pregunta en inglés o español y
            te explicaré paso a paso con materiales de Summit Math Camp.</em>
        </div>
        <div class="parent-box">
            🎒 <strong>For Parents:</strong> Use this after camp to keep practicing with
            your child! Ask about the same topics from Summit Math Camp.
        </div>
    """)

    claude_state     = gr.State([])
    last_topic_state = gr.State("")
    worksheet_state  = gr.State({})
    game_active_state = gr.State(False)

    chatbot = gr.Chatbot(value=[], label="Summit Tutor", height=600)

    with gr.Row(equal_height=True):
        img_upload = gr.Image(
            type="filepath",
            label="📸 Upload a math problem photo (optional)",
            show_label=True,
            height=120,
            width=300,
            sources=["upload", "clipboard"],
            scale=2,
        )
        msg_box = gr.Textbox(
            placeholder="Escribe tu pregunta · Type your question...",
            show_label=False,
            scale=6,
            autofocus=True,
        )
        send_btn = gr.Button("Send ➤", scale=1, variant="primary")

    with gr.Row():
        clear_btn = gr.Button("Clear chat", size="sm", variant="secondary")
        exit_btn  = gr.Button("🚪 Exit Game / Worksheet", size="sm", variant="stop", visible=False)

    game_panel = gr.HTML(value="")

    gr.Examples(examples=EXAMPLES, inputs=msg_box, label="Try an example")

    # ── Footer ───────────────────────────────────────────────────
    gr.HTML("""
        <div class="footer">
            Summit¹⁰ Math Camp &nbsp;·&nbsp; Tegucigalpa, Honduras 🇭🇳
            &nbsp;·&nbsp; Ain't No Mountain High Enough
        </div>
    """)

    _respond_inputs  = [msg_box, img_upload, chatbot, claude_state, last_topic_state, worksheet_state, game_active_state]
    _respond_outputs = [chatbot, claude_state, msg_box, last_topic_state, worksheet_state, game_panel, img_upload, game_active_state, exit_btn]

    send_btn.click(respond, inputs=_respond_inputs, outputs=_respond_outputs)
    msg_box.submit(respond, inputs=_respond_inputs, outputs=_respond_outputs)

    clear_btn.click(
        clear_session,
        outputs=_respond_outputs,
    )
    exit_btn.click(
        do_exit,
        inputs=[chatbot, claude_state, last_topic_state],
        outputs=_respond_outputs,
    )

if __name__ == "__main__":
    demo.launch()
