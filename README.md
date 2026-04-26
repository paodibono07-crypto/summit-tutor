# Summit Tutor

**Project Goal:** Summit Math Camp has been serving students in Tegucigalpa, Honduras for 10 years, founded by my sister and now directed by me. As we both moved to the United States, I wanted to find a way for Summit to continue helping students even without us physically present. Parents at camp always asked for extra practice materials to use at home, and that question stuck with me. Summit Tutor is my answer: an AI math tutor that knows the actual Summit curriculum, speaks Spanish and English, and makes math practice feel like a game, so any Summit family can keep learning anywhere, anytime. This is also the first step toward a larger vision: an online Summit platform powered by 10 years of teaching materials, activities, and institutional knowledge from the camp.

Summit Tutor is an AI-powered math tutor for 1st and 2nd grade students at Summit Math Camp in Tegucigalpa, Honduras, built with the Claude API and Gradio. Students and parents can ask questions in English or Spanish and receive step-by-step explanations across arithmetic, fractions, subtraction with regrouping, multiplication, division, and telling time - with interactive games and adaptive worksheets powered by real Summit Math Camp curriculum materials.

---

## What it Does

Summit Tutor combines a conversational AI with a retrieval-augmented generation (RAG) pipeline to give 1st and 2nd grade students at Summit Math Camp in Tegucigalpa, Honduras accurate, curriculum-aligned answers. The app detects whether the student is writing in English or Spanish and responds in kind, and chain-of-thought prompting ensures the tutor always shows its work step by step. Before each response, the RAG pipeline retrieves relevant passages from uploaded course-note PDFs so answers stay grounded in the student's actual curriculum. Students can also photograph a handwritten math problem and upload it; Claude analyzes the image, identifies the topic, and explains the solution step by step. When a student wants extra practice, an inline HTML5 mountain-climbing game generates five topic-matched questions and advances a climber up the mountain with each correct answer. An adaptive worksheet generator presents eight problems one at a time, gives a hint on the first wrong attempt, reveals the correct answer with an explanation on the second, and shows a final score summary; answers are verified with Python arithmetic rather than Claude, eliminating hallucinated grading. Off-topic questions about politics, entertainment, food, and similar subjects are politely declined, while all math questions including simple arithmetic like "what is 2+5?" are allowed through. A per-user rolling window of 20 requests per 60 seconds prevents abuse, and every exchange is logged to `logs.jsonl` for later review. Three system-prompt variants (zero-shot, few-shot, and chain-of-thought) were tested and compared; see the Evaluation section for results.

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

The Gradio interface will open automatically. Check your terminal for the local URL. It will show something like `http://127.0.0.1:7860` or a nearby port number.

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
- **Few-shot** responses are the most concise, useful for quick arithmetic but potentially under-explaining harder problems.
- The production system prompt uses **chain-of-thought** style (explicitly instructs step-by-step reasoning with few-shot examples), trading latency for pedagogical quality.

**Qualitative analysis:**

Examining responses to the same question across prompt variants reveals meaningful pedagogical differences. The zero-shot response jumps directly to LaTeX-style formatting which may confuse young students. The few-shot response is concise but skips explaining why a common denominator is needed. The chain-of-thought response explicitly names the problem type, explains underlying concepts before computing, and shows work step by step, making it the most appropriate choice for a tutoring context where conceptual understanding matters more than speed.

---

## Individual Contributions

This project was completed individually by Paola Di Bono (Duke University, Computer Science).
