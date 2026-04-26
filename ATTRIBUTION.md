# Attribution — Use of Claude Code and the Claude API

This document describes how Anthropic's tools were used during the development of Summit Tutor.

---

## Claude Code (CLI)

[Claude Code](https://claude.ai/code) was used as the primary development assistant throughout the project. Specific uses included:

**Code generation**
- Initial scaffolding of `app.py`, `chat.py`, `guardrails.py`, `rag.py`, and `logger.py`
- Writing `prompt_experiments.py` to run and compare three system-prompt strategies
- Writing `evaluate.py` to benchmark guardrail accuracy, latency, and response quality
- Implementing per-user rate limiting in `app.py` using a rolling in-memory timestamp window
- Adding structured error handling (`try/except`) in `chat.py` for API failure scenarios

**Iterative refinement**
- Updating `guardrails.py` to flip from a keyword allowlist to a blocklist + regex approach, so simple arithmetic like "what is 2+5?" is correctly allowed through
- Extending the `SYSTEM_PROMPT` in `guardrails.py` with chain-of-thought few-shot examples in both English and Spanish

**Debugging and review**
- Identifying that the original guardrail implementation would block bare arithmetic expressions, and designing the fix
- Catching a bug in the original rate-limiting code where all users shared a single bucket instead of being tracked individually

**Documentation**
- Drafting `README.md`, `SETUP.md`, and this file

All generated code was reviewed, tested, and modified by Paola Di Bono before being incorporated into the project.

---

## Claude API (claude-sonnet-4-6)

The Claude API powers Summit Tutor's tutoring responses at runtime. It is called in `chat.py` via the official `anthropic` Python SDK.

**How it is used**
- **Model:** `claude-sonnet-4-6` — chosen for its balance of response quality and latency
- **System prompt:** A chain-of-thought prompt (defined in `guardrails.py`) instructs the model to identify the problem type, state the relevant concept, show numbered steps, and verify its answer
- **Few-shot examples:** Two worked examples (one English linear-equation solution, one Spanish fractions solution) are embedded in the system prompt to demonstrate the expected reasoning style
- **RAG augmentation:** Retrieved passages from course-note PDFs are appended to the system prompt before each API call, grounding the model's answers in the student's actual curriculum
- **Multi-turn context:** The full conversation history is passed on every call (stateless API, stateful client), enabling coherent multi-turn tutoring sessions
- **Prompt caching:** `cache_control: {type: "ephemeral"}` is applied to the system prompt in `prompt_experiments.py` to reduce cost across repeated calls during experimentation

**Prompt variants tested**
Three system-prompt strategies were evaluated using `prompt_experiments.py`:
1. **Zero-shot** — basic role and rules, no examples
2. **Few-shot** — two worked examples demonstrating desired format
3. **Chain-of-thought** — explicit step-by-step instruction with reasoning verification

The chain-of-thought variant was selected for production because it produced the most thorough and pedagogically useful explanations (avg 965 chars vs 485 for zero-shot and 280 for few-shot), at an acceptable latency cost.

---

## Third-party models (non-Anthropic)

The RAG pipeline uses a locally-run sentence embedding model (`sentence-transformers`) from Hugging Face to convert student questions and course-note passages into vectors for similarity search. This model runs entirely on the local machine and is not part of the Claude API.

---

## Summary

| Component | Tool used |
|---|---|
| Code generation & debugging | Claude Code (CLI) |
| Tutoring responses at runtime | Claude API (`claude-sonnet-4-6`) |
| Document embeddings for RAG | `sentence-transformers` (Hugging Face, local) |
| Vector similarity search | FAISS (`faiss-cpu`, local) |
