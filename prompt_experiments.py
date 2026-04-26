"""
Prompt experiment: compare 3 Summit Tutor system-prompt variants across 5 math questions.
Results are saved to prompt_comparison.csv.
"""

import csv
import time
from collections import defaultdict

import anthropic

client = anthropic.Anthropic()
MODEL = "claude-opus-4-7"

# ── Prompt variants ────────────────────────────────────────────────────────────

ZERO_SHOT = """You are Summit Tutor, a friendly math tutor for middle and high school students (grades 6–12).

Rules:
- Answer ONLY math-related questions.
- Detect the student's language (English or Spanish) and respond in that language.
- Show your work clearly.
- Use simple, age-appropriate language.
- You cover: arithmetic, fractions, algebra, geometry, statistics, trigonometry, and pre-calculus."""

FEW_SHOT = """You are Summit Tutor, a friendly math tutor for middle and high school students (grades 6–12).

Rules:
- Answer ONLY math-related questions.
- Detect the student's language (English or Spanish) and respond in that language.
- Show your work clearly.
- Use simple, age-appropriate language.
- You cover: arithmetic, fractions, algebra, geometry, statistics, trigonometry, and pre-calculus.

Here are examples of how to respond:

EXAMPLE 1:
Q: How do I solve 2x + 4 = 10?
A: Great question! My goal is to get x by itself.
Step 1 — Subtract 4 from both sides: 2x = 6
Step 2 — Divide both sides by 2: x = 3
Check: 2(3) + 4 = 10 ✓

EXAMPLE 2:
Q: What is 1/2 + 1/3?
A: To add fractions, I need a common denominator.
Step 1 — Find the LCD of 2 and 3: it's 6.
Step 2 — Convert: 1/2 = 3/6 and 1/3 = 2/6.
Step 3 — Add: 3/6 + 2/6 = 5/6."""

CHAIN_OF_THOUGHT = """You are Summit Tutor, a friendly math tutor for middle and high school students (grades 6–12).

Rules:
- Answer ONLY math-related questions.
- Detect the student's language (English or Spanish) and respond in that language.
- Use simple, age-appropriate language.
- You cover: arithmetic, fractions, algebra, geometry, statistics, trigonometry, and pre-calculus.

IMPORTANT — Always think step by step before giving your final answer:
1. Identify what type of math problem this is.
2. State the key concept or formula needed.
3. Break the solution into clearly numbered steps.
4. Show every calculation explicitly — never skip arithmetic.
5. Verify your answer by substituting it back or checking it a different way.
Never give a bare answer without showing the full reasoning."""

PROMPT_VARIANTS = {
    "zero_shot": ZERO_SHOT,
    "few_shot": FEW_SHOT,
    "chain_of_thought": CHAIN_OF_THOUGHT,
}

QUESTIONS = [
    "What is 2 + 5?",
    "Solve for x: 3x + 5 = 20",
    "What is 1/3 + 1/4?",
    "What is 25% of 80?",
    "What is the area of a triangle with base 6 and height 4?",
]

CSV_PATH = "prompt_comparison.csv"
CSV_FIELDS = ["prompt_type", "question", "response", "response_length_chars", "latency_seconds"]


# ── Experiment runner ──────────────────────────────────────────────────────────

def run_experiment() -> list[dict]:
    results = []
    total = len(PROMPT_VARIANTS) * len(QUESTIONS)
    done = 0

    for prompt_type, system_prompt in PROMPT_VARIANTS.items():
        for question in QUESTIONS:
            done += 1
            print(f"[{done}/{total}] {prompt_type:>15} | {question}")

            start = time.time()
            response = client.messages.create(
                model=MODEL,
                max_tokens=1024,
                # Cache the system prompt — reused 5 times per variant
                system=[{
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }],
                messages=[{"role": "user", "content": question}],
            )
            latency = round(time.time() - start, 3)

            text = next((b.text for b in response.content if b.type == "text"), "")

            results.append({
                "prompt_type": prompt_type,
                "question": question,
                "response": text,
                "response_length_chars": len(text),
                "latency_seconds": latency,
            })

    return results


# ── Output helpers ─────────────────────────────────────────────────────────────

def save_csv(results: list[dict], path: str = CSV_PATH) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(results)
    print(f"\nResults saved → {path}")


def print_summary(results: list[dict]) -> None:
    stats: dict[str, dict] = defaultdict(lambda: {"count": 0, "chars": 0, "latency": 0.0})

    for r in results:
        pt = r["prompt_type"]
        stats[pt]["count"] += 1
        stats[pt]["chars"] += r["response_length_chars"]
        stats[pt]["latency"] += r["latency_seconds"]

    col_w = [20, 14, 16]
    sep = "─" * (sum(col_w) + 6)

    print("\n" + sep)
    print("  SUMMARY  (averages across 5 questions)")
    print(sep)
    print(
        f"  {'Prompt Type':<{col_w[0]}} {'Avg Chars':>{col_w[1]}} {'Avg Latency (s)':>{col_w[2]}}"
    )
    print(sep)
    for pt in ("zero_shot", "few_shot", "chain_of_thought"):
        s = stats[pt]
        avg_chars = s["chars"] / s["count"]
        avg_lat = s["latency"] / s["count"]
        print(f"  {pt:<{col_w[0]}} {avg_chars:>{col_w[1]}.0f} {avg_lat:>{col_w[2]}.2f}")
    print(sep + "\n")


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    n = len(PROMPT_VARIANTS) * len(QUESTIONS)
    print(f"Summit Tutor prompt experiment")
    print(f"Model   : {MODEL}")
    print(f"Variants: {', '.join(PROMPT_VARIANTS)}")
    print(f"Total   : {len(PROMPT_VARIANTS)} variants × {len(QUESTIONS)} questions = {n} API calls\n")

    results = run_experiment()
    save_csv(results)
    print_summary(results)
