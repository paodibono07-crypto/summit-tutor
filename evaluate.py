"""
Evaluation harness for Summit Tutor.
Runs 15 test questions (10 math + 5 off-topic) through the full chat pipeline,
saves results to evaluation_results.csv, and prints a summary.
"""

import csv
import time

from chat import chat
from guardrails import is_on_topic, off_topic_reply
from rag import retrieve_context

CSV_PATH = "evaluation_results.csv"
CSV_FIELDS = [
    "question",
    "response",
    "response_length",
    "latency_seconds",
    "retrieved_context_length",
    "passed_guardrails",
]

# ── Test questions ─────────────────────────────────────────────────────────────

# expected_blocked=True  → guardrail should block it (off-topic)
# expected_blocked=False → guardrail should allow it (math)
TEST_CASES = [
    # 10 math questions (should pass through)
    {"question": "What is 2 + 5?",                                             "expected_blocked": False},
    {"question": "Solve for x: 3x + 5 = 20",                                  "expected_blocked": False},
    {"question": "What is 1/3 + 1/4?",                                        "expected_blocked": False},
    {"question": "What is 25% of 80?",                                         "expected_blocked": False},
    {"question": "What is the area of a triangle with base 6 and height 4?",   "expected_blocked": False},
    {"question": "How do I factor x^2 - 5x + 6?",                             "expected_blocked": False},
    {"question": "What is the slope of the line y = 3x - 2?",                 "expected_blocked": False},
    {"question": "What is the Pythagorean theorem?",                           "expected_blocked": False},
    {"question": "How do I calculate the mean of 4, 8, 15, 16, 23?",          "expected_blocked": False},
    {"question": "What is the derivative of x^2?",                            "expected_blocked": False},
    # 5 off-topic questions (should be blocked)
    {"question": "Who won the last presidential election?",                    "expected_blocked": True},
    {"question": "What is the best recipe for chocolate cake?",                "expected_blocked": True},
    {"question": "Who is the most famous actor in Hollywood?",                 "expected_blocked": True},
    {"question": "What team won the Super Bowl this year?",                    "expected_blocked": True},
    {"question": "Can you recommend a good Netflix show to watch?",            "expected_blocked": True},
]


# ── Runner ─────────────────────────────────────────────────────────────────────

def run_evaluation() -> list[dict]:
    results = []
    total = len(TEST_CASES)

    for i, tc in enumerate(TEST_CASES, 1):
        question = tc["question"]
        expected_blocked = tc["expected_blocked"]
        print(f"[{i:>2}/{total}] {question[:60]}")

        context = retrieve_context(question)
        ctx_len = len(context) if context else 0

        start = time.perf_counter()

        if not is_on_topic(question):
            response = off_topic_reply(question)
            passed_guardrails = False   # question was blocked
        else:
            response, _ = chat(question, [])
            passed_guardrails = True    # question reached Claude

        latency = round(time.perf_counter() - start, 3)

        results.append({
            "question": question,
            "response": response,
            "response_length": len(response),
            "latency_seconds": latency,
            "retrieved_context_length": ctx_len,
            "passed_guardrails": passed_guardrails,
            # internal — used for accuracy calc, not written to CSV
            "_expected_blocked": expected_blocked,
        })

    return results


# ── Output ─────────────────────────────────────────────────────────────────────

def save_csv(results: list[dict], path: str = CSV_PATH) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)
    print(f"\nResults saved → {path}")


def print_summary(results: list[dict]) -> None:
    math_cases     = [r for r in results if not r["_expected_blocked"]]
    offtopic_cases = [r for r in results if r["_expected_blocked"]]

    # Average latency (math questions only — off-topic are near-instant)
    avg_latency = sum(r["latency_seconds"] for r in math_cases) / len(math_cases)

    # Average response length across all questions
    avg_len = sum(r["response_length"] for r in results) / len(results)

    # Guardrail accuracy
    correctly_blocked  = sum(1 for r in offtopic_cases if not r["passed_guardrails"])
    correctly_allowed  = sum(1 for r in math_cases     if r["passed_guardrails"])
    guardrail_accuracy = (correctly_blocked + correctly_allowed) / len(results)

    # Failure cases: math responses that are suspiciously short (< 80 chars)
    failures = sorted(
        [r for r in math_cases if r["response_length"] < 80],
        key=lambda r: r["response_length"],
    )[:3]
    # Pad to 3 entries so the section always prints something
    while len(failures) < 3:
        failures.append(None)

    sep = "─" * 62
    print(f"\n{sep}")
    print("  EVALUATION SUMMARY")
    print(sep)
    print(f"  Total questions        : {len(results)}")
    print(f"  Math questions         : {len(math_cases)}")
    print(f"  Off-topic questions    : {len(offtopic_cases)}")
    print(f"  Avg latency (math)     : {avg_latency:.2f}s")
    print(f"  Avg response length    : {avg_len:.0f} chars")
    print(f"  Guardrail accuracy     : {guardrail_accuracy:.0%}  "
          f"({correctly_blocked}/{len(offtopic_cases)} off-topic blocked, "
          f"{correctly_allowed}/{len(math_cases)} math allowed)")
    print(f"\n  Example failure cases (shortest math responses):")
    for idx, r in enumerate(failures, 1):
        if r is None:
            print(f"    {idx}. (none — all responses met the length threshold)")
        else:
            snippet = r["response"][:120].replace("\n", " ")
            print(f"    {idx}. [{r['response_length']} chars] Q: {r['question'][:45]}")
            print(f"         A: {snippet}...")
    print(sep + "\n")


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"Summit Tutor — evaluation ({len(TEST_CASES)} questions)\n")
    results = run_evaluation()
    save_csv(results)
    print_summary(results)
