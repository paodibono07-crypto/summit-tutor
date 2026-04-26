# Summit Tutor

An AI-powered math tutor for 1st and 2nd grade students at Summit Math Camp in Tegucigalpa, Honduras, built with the Claude API and Gradio. Students can ask questions in **English or Spanish** and receive step-by-step explanations across arithmetic, fractions, basic algebra, and geometry.

---

## What it Does

Summit Tutor combines a conversational AI with a retrieval-augmented generation (RAG) pipeline to give 1st and 2nd grade students at Summit Math Camp in Tegucigalpa, Honduras accurate, curriculum-aligned answers:

- **Bilingual support** — detects English or Spanish and responds in kind
- **Step-by-step reasoning** — chain-of-thought prompting ensures the tutor always shows its work
- **RAG pipeline** — retrieves relevant passages from uploaded course notes (PDF) before answering, so responses stay grounded in the student's actual curriculum
- **Interactive math game** — an inline HTML5 mountain-climbing game generates 5 topic-matched questions; the climber advances up the mountain with each correct answer
- **Adaptive worksheet generator** — presents 8 problems one at a time, gives a hint on the first wrong attempt, reveals the answer with explanation on the second, and shows a final score summary; answers are verified with Python arithmetic (not Claude), eliminating hallucinated grading
- **Image upload** — students can photograph a handwritten math problem; Claude analyzes the image, identifies the topic, and explains the solution step by step
- **Guardrails** — off-topic questions (politics, entertainment, food, etc.) are politely declined; all math questions, including simple arithmetic like "what is 2+5?", are allowed through
- **Rate limiting** — per-user rolling window (20 requests / 60 s) prevents abuse
- **Interaction logging** — every exchange is logged to `logs.jsonl` for later review
- **Prompt experiments** — three system-prompt variants (zero-shot, few-shot, chain-of-thought) were tested and compared; see the Evaluation section

---

## Quick Start

```bash
# 1. Clone and enter the project
git clone https://github.com/paodibono07-crypto/summit-tutor
cd summit-tutor

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set your API key
export ANTHROPIC_API_KEY=sk-ant-...

# 5. (Optional) add course-note PDFs for the RAG pipeline
cp your-notes.pdf docs/

# 6. Launch the app
python app.py
```

The Gradio interface will open automatically. Check your terminal for the local URL — it will show something like `http://127.0.0.1:7860` or a nearby port number.

For full setup details, see [SETUP.md](SETUP.md).

---

## Video Links

> **Demo video:** _[link to be added]_
> **Presentation / walkthrough:** _[link to be added]_

---

## Evaluation

### Guardrail & response quality

| Metric | Result |
|---|---|
| Guardrail accuracy | **93%** |
| Average latency (math questions) | **5.42 s** |
| Average response length | **585 chars** |

The guardrail correctly blocked 5/5 off-topic questions and allowed 9/10 math questions through (one borderline question was over-filtered), giving a 93% overall accuracy across 15 test cases.

### Prompt variant comparison

Three system-prompt strategies were tested against 5 math questions each using `prompt_experiments.py`. Results saved to `prompt_comparison.csv`.

| Prompt Type | Avg Response Length | Avg Latency |
|---|---|---|
| Zero-shot | 485 chars | 4.28 s |
| Few-shot | 280 chars | 2.82 s |
| Chain-of-thought | 965 chars | 6.42 s |

**Takeaways:**
- The **chain-of-thought** prompt produces the most thorough explanations but costs the most in latency.
- **Few-shot** responses are the most concise — useful for quick arithmetic but may under-explain harder problems.
- The production system prompt uses **chain-of-thought** style (explicitly instructs step-by-step reasoning with few-shot examples), trading latency for pedagogical quality.

**Qualitative analysis:**

Examining responses to the same question across prompt variants reveals meaningful pedagogical differences. The zero-shot response jumps directly to LaTeX-style formatting which may confuse young students. The few-shot response is concise but skips explaining why a common denominator is needed. The chain-of-thought response explicitly names the problem type, explains underlying concepts before computing, and shows work step by step — making it most appropriate for a tutoring context where conceptual understanding matters more than speed.

---

## Individual Contributions

This project was completed individually by Paola Di Bono (Duke University, Computer Science).
