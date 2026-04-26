import base64
import json
import mimetypes
import os
import random as _random
import re

import anthropic

from guardrails import SYSTEM_PROMPT
from rag import retrieve_context

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1024

_FOOTER_EN = (
    "\n\n---\n"
    "🏔️ Want to keep practicing? Reply **activity** for a fun Summit game "
    "or **worksheet** for practice problems!"
)
_FOOTER_ES = (
    "\n\n---\n"
    "🏔️ ¿Quieres seguir practicando? Responde **actividad** para un juego "
    "divertido o **hoja de trabajo** para problemas de práctica!"
)

# ¿ and ¡ are unique to Spanish — one is enough
_ES_INVERTED_RE = re.compile(r'[¿¡]')
# Other accented chars need 2+ to avoid false positives from loanwords
_ES_ACCENT_RE = re.compile(r'[áéíóúüñÁÉÍÓÚÜÑ]')
_ES_WORD_RE = re.compile(
    r'\b(paso|para\s|una\s|los\s|las\s|con\s|pero|esto|esta|este|'
    r'como\s|cuando|porque|tambi[eé]n|entonces|despu[eé]s|ahora|'
    r'vamos|buena|gran\s|muy\s|m[aá]s\s|hay\s|son\s|est[aá]|están|'
    r'respuesta|resultado|n[uú]mero|fracci[oó]n|resolvemos)\b',
    re.IGNORECASE,
)


def _practice_footer(reply: str) -> str:
    """Return the footer in the same language as the reply."""
    if (
        _ES_INVERTED_RE.search(reply)
        or len(_ES_ACCENT_RE.findall(reply)) >= 2
        or len(_ES_WORD_RE.findall(reply)) >= 3
    ):
        return _FOOTER_ES
    return _FOOTER_EN


def detect_spanish(text: str) -> bool:
    """Return True if text appears to be written in Spanish."""
    return (
        bool(_ES_INVERTED_RE.search(text))
        or len(_ES_ACCENT_RE.findall(text)) >= 2
        or len(_ES_WORD_RE.findall(text)) >= 2
    )


_CHECKPOINTS = [
    ("⛺", "Base Camp"),
    ("🌲", "Forest Trail"),
    ("🪨", "Rocky Ridge"),
    ("❄️", "Snow Zone"),
    ("🏔️", "SUMMIT"),
]

_WORKSHEET_SYSTEM = (
    "You are a worksheet generator for Summit Math Camp. "
    "Generate exactly 8 numbered math practice problems about the given topic "
    "for 1st-2nd grade students, then provide a complete answer key. "
    "Format it nicely with a Summit Math Camp header. "
    "Do not refuse. Just generate the problems."
)

_WORKSHEET_SYSTEM_ES = (
    "Eres un generador de hojas de trabajo para Summit Math Camp. "
    "Genera exactamente 8 problemas de práctica de matemáticas sobre el tema dado "
    "para estudiantes de 1er y 2do grado. ESCRIBE TODOS LOS PROBLEMAS EN ESPAÑOL. "
    "IMPORTANTE: cada respuesta debe ser un número simple (entero, decimal, o fracción simple como '3/4'). "
    "NO escribas palabras como 'veinte' — escribe '20'. "
    "No te niegues. Solo genera los problemas."
)

_GAME_SYSTEM = (
    "You are a fun math game host for Summit Math Camp. "
    "Generate an interactive 5-question math game about the given topic. "
    "Number each question, make it encouraging and fun with mountain emojis. "
    "Do not refuse. Just generate the game."
)

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY environment variable not set.")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def chat(user_message: str, history: list[dict]) -> tuple[str, list[dict]]:
    """Send a message to Claude and return (reply_text, updated_history).

    history is a list of {"role": "user"|"assistant", "content": str} dicts
    that represent the Claude-side conversation (no off-topic turns included).
    """
    context = retrieve_context(user_message)

    system = SYSTEM_PROMPT
    if context:
        system += f"\n\n---\nRelevant reference material from course notes:\n{context}\n---"

    history = history + [{"role": "user", "content": user_message}]

    try:
        response = _get_client().messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=history,
        )
        reply = response.content[0].text
    except anthropic.RateLimitError:
        reply = "I'm getting a lot of requests right now — please try again in a moment."
    except anthropic.APIConnectionError:
        reply = "I couldn't reach the tutoring service. Please check your connection and try again."
    except anthropic.APIStatusError as e:
        reply = f"Something went wrong on my end (error {e.status_code}). Please try again shortly."
    except Exception:
        reply = "An unexpected error occurred. Please try again."

    reply = reply + _practice_footer(reply)

    history = history + [{"role": "assistant", "content": reply}]
    return reply, history


_IMAGE_PROMPT = (
    "Look at this math problem image. "
    "Identify what type of math it is (addition, subtraction, fractions, etc.), "
    "solve it step by step, and explain it in a way a 1st or 2nd grade student can understand."
)

# Regex that matches any A)/B)/C) or A./B./C. option-menu block Claude might add
_MENU_RE = re.compile(
    r'\n[^\S\n]*\*{0,2}[A-D][).][^\S\n]*\*{0,2}[^\n]+(?:\n[^\S\n]*\*{0,2}[B-E][).][^\S\n]*\*{0,2}[^\n]+)+',
    re.IGNORECASE,
)
# Also remove "Would you like to …?" sentences that introduce such menus
_MENU_INTRO_RE = re.compile(
    r'\n+(?:Would you like|¿[Tt]e gustar[ií]a|[Qq]uieres)[^\n]*[?!.]?\s*$',
    re.IGNORECASE,
)


def _strip_menu(text: str) -> str:
    """Remove any A/B/C option menus Claude generates so our footer is the only CTA."""
    text = _MENU_RE.sub('', text)
    text = _MENU_INTRO_RE.sub('', text)
    return text.rstrip()

_MEDIA_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}


def chat_with_image(
    user_message: str,
    image_path: str,
    history: list[dict],
) -> tuple[str, list[dict]]:
    """Send a multimodal (image + text) message to Claude.

    Returns (reply_text, updated_history).  The image is NOT stored in history
    to keep subsequent turns lightweight; only the text summary is kept.
    """
    with open(image_path, "rb") as f:
        image_b64 = base64.standard_b64encode(f.read()).decode()

    mime, _ = mimetypes.guess_type(image_path)
    if mime not in _MEDIA_TYPES:
        mime = "image/jpeg"

    text_prompt = user_message.strip() if user_message.strip() else _IMAGE_PROMPT

    multimodal_msg = {
        "role": "user",
        "content": [
            {
                "type": "image",
                "source": {"type": "base64", "media_type": mime, "data": image_b64},
            },
            {"type": "text", "text": text_prompt},
        ],
    }

    context = retrieve_context(text_prompt)
    system = SYSTEM_PROMPT
    if context:
        system += f"\n\n---\nRelevant reference material from course notes:\n{context}\n---"

    try:
        response = _get_client().messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=history + [multimodal_msg],
        )
        reply = response.content[0].text
    except anthropic.RateLimitError:
        reply = "I'm getting a lot of requests right now — please try again in a moment."
    except anthropic.APIConnectionError:
        reply = "I couldn't reach the tutoring service. Please check your connection and try again."
    except anthropic.APIStatusError as e:
        reply = f"Something went wrong on my end (error {e.status_code}). Please try again shortly."
    except Exception:
        reply = "An unexpected error occurred. Please try again."

    reply = _strip_menu(reply) + _practice_footer(reply)

    # Store a text-only summary in history (keeps follow-up turns lightweight)
    display_user = user_message.strip() or "📸 [math problem photo]"
    updated_history = history + [
        {"role": "user", "content": display_user},
        {"role": "assistant", "content": reply},
    ]
    return reply, updated_history


# ── Pure-Python game question generator (no API call) ─────────────────────────

def _py_game_questions(topic_name: str, lang: str = "en") -> list[dict]:
    """Return 5 {q, a} dicts generated in pure Python from the human-readable topic name."""
    print(f"[GAME] _py_game_questions: topic_name={topic_name!r}")
    ri = _random.randint
    t  = topic_name.lower()

    # Keyword sets — checked in priority order
    _SUB  = ('subtract', 'regroup', 'resta', 'regrup', 'minus', 'borrow',
             'prestamo', 'préstamo', 'take away', 'quitar', 'menos')
    _WORD = ('word problem', 'story problem', 'palabra', 'story', 'word')
    _MUL  = ('multipl', 'times table', 'times', 'group', 'grupo', 'repeated',
             'producto', 'factor')
    _DIV  = ('divis', 'divide', 'quotient', 'split', 'cocient', 'dividir')
    _EQFR = ('equivalent', 'equivalen')
    _FRAC = ('fraction', 'fraccion', 'fracción', 'fracciones', 'half',
             'medio', 'numerator', 'denominator', 'numerador', 'denominador')
    _TIME = ('time', 'clock', 'hora', 'reloj', 'telling time')
    _ADD  = ('addition', 'add', 'suma', 'sumar', 'plus', 'total')

    # Also detect from arithmetic operator patterns in the raw fallback string
    _sub_op  = bool(re.search(r'\d\s*[-−]\s*\d', t))
    _mul_op  = bool(re.search(r'\d\s*[×*]\s*\d', t))
    _div_op  = bool(re.search(r'\d\s*[÷/]\s*\d', t))

    if any(k in t for k in _SUB) or _sub_op:
        def _gen():
            b = ri(19, 79); a = b + ri(5, 30)
            while (a % 10) >= (b % 10):
                b = ri(19, 79); a = b + ri(5, 30)
            return {'q': f'{a} − {b} = ?', 'a': a - b}
    elif any(k in t for k in _WORD):
        def _gen():
            a = ri(5, 30); b = ri(5, 30)
            if lang == "es":
                stem = _random.choice([
                    f'Hay {a} excursionistas en el campamento y llegan {b} más. ¿Cuántos hay en total?',
                    f'María tiene {a} bocadillos y encuentra {b} más. ¿Cuántos tiene?',
                    f'Carlos subió {a} escalones y luego {b} más. ¿Cuántos escalones subió en total?',
                ])
            else:
                stem = _random.choice([
                    f'There are {a} hikers at Base Camp and {b} more arrive. How many total?',
                    f'María has {a} trail snacks and finds {b} more. How many does she have?',
                    f'Carlos climbed {a} steps then {b} more. How many steps total?',
                ])
            return {'q': stem, 'a': a + b}
    elif any(k in t for k in _MUL) or _mul_op:
        def _gen():
            a = ri(2, 12); b = ri(2, 12)
            return {'q': f'{a} × {b} = ?', 'a': a * b}
    elif any(k in t for k in _DIV) or _div_op:
        def _gen():
            b = ri(2, 9); q = ri(2, 9)
            return {'q': f'{b * q} ÷ {b} = ?', 'a': q}
    elif any(k in t for k in _EQFR):
        def _gen():
            n = ri(1, 4); d = ri(2, 6); m = ri(2, 4)
            return {'q': f'{n}/{d} = ?/{d * m}  (find the missing numerator)', 'a': n * m}
    elif any(k in t for k in _FRAC):
        def _gen():
            d  = _random.choice([2, 4, 6, 8])
            n1 = ri(1, d - 1); n2 = ri(1, max(1, d - n1))
            return {'q': f'{n1}/{d} + {n2}/{d} = ?/{d}  (find the numerator)', 'a': n1 + n2}
    elif any(k in t for k in _TIME):
        def _gen():
            h = ri(1, 12); m = _random.choice([5, 10, 15, 20, 25, 30, 35, 40, 45, 50])
            return {'q': f'A clock shows {h}:{str(m).zfill(2)}. Minutes past the hour?', 'a': m}
    else:  # addition / general math (default)
        def _gen():
            a = ri(11, 79); b = ri(11, 79)
            return {'q': f'{a} + {b} = ?', 'a': a + b}

    print(f"[GAME]   → detected type from keywords/operators")
    return [_gen() for _ in range(5)]


# ── Game helpers ──────────────────────────────────────────────────────────────

def _progress_bar(completed: int) -> str:
    return " ".join(["⛰️"] * completed + ["🔲"] * (5 - completed))


def _generate_questions(topic: str) -> list[dict]:
    prompt = (
        f"Topic: {topic}\n\n"
        "Generate exactly 5 math questions for 1st-2nd grade students, progressively harder. "
        "Return ONLY a valid JSON array with no markdown or explanation:\n"
        '[{"q":"full question text","a":"exact answer"},...]'
    )
    try:
        response = _get_client().messages.create(
            model=MODEL,
            max_tokens=600,
            system=_GAME_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        questions = json.loads(raw.strip())
        if isinstance(questions, list) and len(questions) == 5:
            return questions
    except Exception:
        pass
    return [{"q": f"What is a fact you know about {topic}?", "a": "any answer"} for _ in range(5)]


def _normalize_number(text: str) -> float | None:
    """Parse a student or stored answer into a float for numerical comparison."""
    text = text.strip().lower().replace(",", "")
    # Mixed number: "1 1/2"
    if " " in text:
        parts = text.split(" ", 1)
        try:
            whole = float(parts[0])
            num, den = parts[1].split("/")
            return whole + float(num) / float(den)
        except Exception:
            pass
    # Simple fraction: "3/4"
    if "/" in text:
        try:
            num, den = text.split("/")
            return float(num) / float(den)
        except Exception:
            pass
    # Plain integer or decimal
    try:
        return float(text)
    except ValueError:
        return None


def _check_answer_numerically(student_answer: str, correct_answer: str) -> bool:
    """Python-only numerical check. Returns True if answers are numerically equal."""
    student = _normalize_number(student_answer)
    correct = _normalize_number(correct_answer)
    if student is None or correct is None:
        return False
    return abs(student - correct) < 0.01


def _check_answer(question: str, correct_answer: str, student_answer: str) -> bool:
    prompt = (
        f"Math question: {question}\n"
        f"Correct answer: {correct_answer}\n"
        f"Student answer: {student_answer}\n\n"
        "Is the student mathematically correct? Accept equivalent forms "
        "('twenty' = '20', '1/2' = '0.5', etc.). "
        "Reply with exactly one word: CORRECT or INCORRECT."
    )
    try:
        response = _get_client().messages.create(
            model=MODEL,
            max_tokens=10,
            messages=[{"role": "user", "content": prompt}],
        )
        return "CORRECT" in response.content[0].text.upper()
    except Exception:
        return False


def _get_hint(question: str, correct_answer: str) -> str:
    prompt = (
        f"Math question: {question}\n"
        f"Correct answer: {correct_answer}\n\n"
        "Give a short friendly hint (1–2 sentences) to help an elementary student. "
        "Do NOT reveal the answer. Be encouraging."
    )
    try:
        response = _get_client().messages.create(
            model=MODEL,
            max_tokens=80,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception:
        return "Think carefully and try again — you've got this! 💪"


def start_game(topic: str) -> tuple[str, dict]:
    """Generate 5 questions and return the opening game message + initial game_state."""
    questions = _generate_questions(topic)
    game_state = {
        "is_active": True,
        "topic": topic,
        "questions": questions,
        "current_idx": 0,
        "score": 0,
        "attempts": 0,
    }
    emoji, name = _CHECKPOINTS[0]
    msg = (
        f"🏔️ **SUMMIT MATH CHALLENGE** 🏔️\n"
        f"Topic: **{topic}**\n\n"
        f"{_progress_bar(0)}\n\n"
        f"You're starting at {emoji} **{name}**!\n"
        f"Answer all 5 questions to reach the Summit! ⛰️\n\n"
        f"---\n"
        f"**Question 1 of 5:**\n{questions[0]['q']}"
    )
    return msg, game_state


def game_turn(student_answer: str, game_state: dict) -> tuple[str, dict]:
    """Evaluate one game turn and return (reply_message, updated_game_state)."""
    idx = game_state["current_idx"]
    questions = game_state["questions"]
    q = questions[idx]["q"]
    a = questions[idx]["a"]
    attempts = game_state["attempts"]
    score = game_state["score"]

    correct = _check_answer(q, a, student_answer)

    if correct:
        score += 1
        game_state["score"] = score
        completed = idx + 1

        if completed == 5:
            game_state["is_active"] = False
            stars = "⭐" * score
            if score == 5:
                celebration = "🎉 **PERFECT SCORE!** You're a true Summit champion! 🏆"
            elif score >= 4:
                celebration = "🎉 Amazing work — almost perfect! You're a math mountaineer! 🏔️"
            elif score >= 3:
                celebration = "🎉 Great job reaching the Summit! Keep climbing higher! 🏔️"
            else:
                celebration = "🎉 You made it to the Summit! Practice makes perfect! 💪"
            msg = (
                f"✅ Correct! **{a}** — Excellent! 🌟\n\n"
                f"{_progress_bar(5)}\n\n"
                f"🏔️ **YOU REACHED THE SUMMIT!** 🏔️\n\n"
                f"**Final Score: {score}/5** {stars}\n\n"
                f"{celebration}\n\n"
                f"---\n"
                f"Say **activity** to play again or **worksheet** for practice problems!"
            )
        else:
            game_state["current_idx"] = idx + 1
            game_state["attempts"] = 0
            emoji, name = _CHECKPOINTS[idx + 1]
            next_q = questions[idx + 1]["q"]
            msg = (
                f"✅ Correct! **{a}** — Great job! 🌟\n\n"
                f"{_progress_bar(completed)}\n\n"
                f"You've reached {emoji} **{name}**! Keep climbing!\n\n"
                f"---\n"
                f"**Question {idx + 2} of 5:**\n{next_q}"
            )

    elif attempts == 0:
        hint = _get_hint(q, a)
        game_state["attempts"] = 1
        msg = (
            f"Not quite — don't give up! 💪\n\n"
            f"**Hint:** {hint}\n\n"
            f"Try again → **Question {idx + 1} of 5:**\n{q}"
        )

    else:
        # Second wrong answer: show answer and advance
        game_state["attempts"] = 0
        if idx + 1 == 5:
            game_state["is_active"] = False
            stars = "⭐" * score
            msg = (
                f"The answer was **{a}**. No worries — that was tricky! 🤗\n\n"
                f"{_progress_bar(score)}\n\n"
                f"🏔️ **You reached the Summit!** 🏔️\n\n"
                f"**Final Score: {score}/5** {stars}\n\n"
                f"Keep practicing and you'll ace it next time! 💪\n\n"
                f"---\n"
                f"Say **activity** to play again or **worksheet** for more practice!"
            )
        else:
            game_state["current_idx"] = idx + 1
            emoji, name = _CHECKPOINTS[idx + 1]
            next_q = questions[idx + 1]["q"]
            msg = (
                f"The answer was **{a}**. No worries — that was tricky! 🤗\n\n"
                f"{_progress_bar(score)}\n\n"
                f"Moving on to {emoji} **{name}**!\n\n"
                f"---\n"
                f"**Question {idx + 2} of 5:**\n{next_q}"
            )

    return msg, game_state


# ── Worksheet helpers ─────────────────────────────────────────────────────────

def _generate_worksheet_problems(topic: str, lang: str = "en") -> tuple[list[str], list[str]]:
    if lang == "es":
        system = _WORKSHEET_SYSTEM_ES
        prompt = (
            f"Tema: {topic}\n\n"
            "Genera exactamente 8 problemas de matemáticas para estudiantes de 1er y 2do grado, "
            "progresivamente más difíciles. ESCRIBE TODO EN ESPAÑOL. "
            "IMPORTANTE: cada respuesta debe ser un número simple (entero, decimal, o fracción simple como '3/4'). "
            "NO escribas palabras como 'veinte' — escribe '20'. "
            "Devuelve SOLO un objeto JSON válido — sin markdown, sin explicación:\n"
            '{"problems":["texto completo del problema sin la respuesta","..."],"answers":["solo la respuesta numérica","..."]}'
        )
    else:
        system = _WORKSHEET_SYSTEM
        prompt = (
            f"Topic: {topic}\n\n"
            "Generate exactly 8 math problems for 1st-2nd grade students, progressively harder. "
            "IMPORTANT: every answer must be a plain number (integer, decimal, or simple fraction like '3/4'). "
            "Do NOT write words like 'twenty' — write '20'. "
            "Return ONLY a valid JSON object — no markdown, no explanation:\n"
            '{"problems":["full problem text without the answer","..."],"answers":["numeric answer only","..."]}'
        )
    try:
        response = _get_client().messages.create(
            model=MODEL,
            max_tokens=900,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw.strip())
        problems, answers = data["problems"], data["answers"]
        if len(problems) == 8 and len(answers) == 8:
            return problems, answers
    except Exception:
        pass
    return (
        [f"Practice problem {i + 1} about {topic}." for i in range(8)],
        ["See your teacher"] * 8,
    )


def _explain_answer(problem: str, answer: str) -> str:
    prompt = (
        f"Math problem: {problem}\n"
        f"Correct answer: {answer}\n\n"
        "Give a brief step-by-step explanation (2-3 sentences) for a 1st-2nd grade student. "
        "Be clear and encouraging."
    )
    try:
        response = _get_client().messages.create(
            model=MODEL,
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception:
        return f"The answer is {answer}. Keep practicing!"


# Bilingual string table for worksheet messages
_WS_T: dict[str, dict[str, str]] = {
    "header":       {"en": "📄 **SUMMIT MATH CAMP — Practice Worksheet**",     "es": "📄 **SUMMIT MATH CAMP — Hoja de Práctica**"},
    "topic_label":  {"en": "Topic",                                             "es": "Tema"},
    "instructions": {"en": "Answer each problem one at a time. Take your time! 🏔️", "es": "Responde cada problema uno a la vez. ¡Tómate tu tiempo! 🏔️"},
    "problem":      {"en": "**Problem {n} of 8:**",                            "es": "**Problema {n} de 8:**"},
    "try_again":    {"en": "**Problem {n} of 8 (try again):**",                "es": "**Problema {n} de 8 (intenta de nuevo):**"},
    "correct":      {"en": "✅ Correct! **{a}** — Well done! 🌟",              "es": "✅ ¡Correcto! **{a}** — ¡Bien hecho! 🌟"},
    "correct_last": {"en": "✅ Correct! **{a}** — Fantastic! 🌟",              "es": "✅ ¡Correcto! **{a}** — ¡Fantástico! 🌟"},
    "wrong":        {"en": "Not quite! Don't give up — you can do it! 💪",    "es": "¡No fue correcto! ¡No te rindas — puedes hacerlo! 💪"},
    "revealed":     {"en": "The answer is **{a}**.",                           "es": "La respuesta es **{a}**."},
    "complete":     {"en": "🏔️ **Worksheet Complete!**",                      "es": "🏔️ **¡Hoja de trabajo completa!**"},
    "score":        {"en": "**Score: {s}/8**",                                 "es": "**Puntaje: {s}/8**"},
    "review":       {"en": "**Review these:**",                                "es": "**Repasa estos:**"},
    "closing":      {"en": "Say **activity** for a game or **worksheet** to practice again!", "es": "Di **actividad** para un juego o **hoja de trabajo** para practicar de nuevo."},
    "tip":          {"en": "💡 Tip: Type **exit** or **salir** at any time to stop and ask a new math question!", "es": "💡 Consejo: Escribe **salir** o **exit** en cualquier momento para parar y hacer una nueva pregunta."},
}

_WS_VERDICTS = {
    "en": [
        "🏆 PERFECT SCORE! You're a Summit Math champion!",
        "🏔️ Amazing work! You're nearly at the summit!",
        "⛰️ Great effort! Keep climbing — you're improving!",
        "🌱 Good try! Every problem you practice makes you stronger!",
    ],
    "es": [
        "🏆 ¡PUNTAJE PERFECTO! ¡Eres un campeón de Summit Math!",
        "🏔️ ¡Trabajo increíble! ¡Casi llegas a la cima!",
        "⛰️ ¡Gran esfuerzo! ¡Sigue subiendo — estás mejorando!",
        "🌱 ¡Buen intento! ¡Cada problema que practicas te hace más fuerte!",
    ],
}


def _t(key: str, lang: str, **kwargs) -> str:
    """Look up a worksheet translation and format it."""
    s = _WS_T[key].get(lang, _WS_T[key]["en"])
    return s.format(**kwargs) if kwargs else s


def _ws_progress(results: list) -> str:
    icons = {"correct": "✅", "revealed": "❌", None: "⬜"}
    return "  " + " ".join(icons[r] for r in results)


def _ws_finale(ws: dict) -> str:
    score   = ws["score"]
    results = ws["results"]
    problems = ws["problems"]
    answers  = ws["answers"]
    lang     = ws.get("lang", "en")

    verdicts = _WS_VERDICTS[lang]
    if score == 8:
        verdict = verdicts[0]
    elif score >= 6:
        verdict = verdicts[1]
    elif score >= 4:
        verdict = verdicts[2]
    else:
        verdict = verdicts[3]

    prob_label = "Problem" if lang == "en" else "Problema"
    missed_lines = [
        f"  • {prob_label} {i + 1}: {problems[i]}  →  **{answers[i]}**"
        for i, r in enumerate(results) if r == "revealed"
    ]

    out = (
        f"{_t('complete', lang)}\n\n"
        f"{_t('score', lang, s=score)}\n{verdict}\n\n"
        f"{_ws_progress(results)}\n"
    )
    if missed_lines:
        out += f"\n{_t('review', lang)}\n" + "\n".join(missed_lines) + "\n"
    out += f"\n---\n{_t('closing', lang)}"
    return out


def start_worksheet(topic: str, lang: str = "en") -> tuple[str, dict]:
    """Generate 8 problems (no answers shown) and return the opening message + worksheet_state."""
    problems, answers = _generate_worksheet_problems(topic, lang)
    ws = {
        "mode": "worksheet",
        "is_active": True,
        "topic": topic,
        "lang": lang,
        "problems": problems,
        "answers": answers,
        "current_problem": 0,
        "wrong_attempts": {},
        "results": [None] * 8,
        "score": 0,
    }
    msg = (
        f"{_t('header', lang)}\n"
        f"{_t('topic_label', lang)}: **{topic}**\n\n"
        f"{_ws_progress(ws['results'])}\n\n"
        f"{_t('instructions', lang)}\n\n"
        f"---\n"
        f"{_t('problem', lang, n=1)}\n{problems[0]}\n\n"
        f"{_t('tip', lang)}"
    )
    return msg, ws


def worksheet_turn(student_answer: str, ws: dict) -> tuple[str, dict]:
    """Evaluate one worksheet answer and return (reply_message, updated_worksheet_state)."""
    idx      = ws["current_problem"]
    problem  = ws["problems"][idx]
    answer   = ws["answers"][idx]
    attempts = ws["wrong_attempts"].get(idx, 0)
    lang     = ws.get("lang", "en")

    correct = _check_answer_numerically(student_answer, answer)

    if correct:
        ws["score"] += 1
        ws["results"][idx] = "correct"
        next_idx = idx + 1

        if next_idx == 8:
            ws["is_active"] = False
            return _t("correct_last", lang, a=answer) + "\n\n" + _ws_finale(ws), ws

        ws["current_problem"] = next_idx
        msg = (
            f"{_t('correct', lang, a=answer)}\n\n"
            f"{_ws_progress(ws['results'])}\n\n"
            f"---\n"
            f"{_t('problem', lang, n=next_idx + 1)}\n{ws['problems'][next_idx]}"
        )
        return msg, ws

    # Wrong answer
    if attempts == 0:
        ws["wrong_attempts"][idx] = 1
        msg = (
            f"{_t('wrong', lang)}\n\n"
            f"{_ws_progress(ws['results'])}\n\n"
            f"{_t('try_again', lang, n=idx + 1)}\n{problem}"
        )
        return msg, ws

    # Second wrong: explain and advance
    explanation = _explain_answer(problem, answer)
    ws["results"][idx] = "revealed"
    next_idx = idx + 1

    reveal = f"{_t('revealed', lang, a=answer)}\n\n💡 {explanation}\n\n"

    if next_idx == 8:
        ws["is_active"] = False
        return reveal + _ws_finale(ws), ws

    ws["current_problem"] = next_idx
    msg = (
        reveal
        + f"{_ws_progress(ws['results'])}\n\n"
        + f"---\n"
        + f"{_t('problem', lang, n=next_idx + 1)}\n{ws['problems'][next_idx]}"
    )
    return msg, ws
