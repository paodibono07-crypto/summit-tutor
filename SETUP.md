# Setup Instructions

## Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.10 or higher |
| pip | bundled with Python 3.10+ |
| Anthropic API key | [Get one at console.anthropic.com](https://console.anthropic.com) |

---

## Step 1 — Clone the repository

```bash
git clone https://github.com/paodibono07-crypto/summit-tutor.git
cd summit-tutor
```

---

## Step 2 — Create a virtual environment

```bash
python -m venv .venv
```

Activate it:

```bash
# macOS / Linux
source .venv/bin/activate

# Windows (Command Prompt)
.venv\Scripts\activate.bat

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

You should see `(.venv)` prepended to your shell prompt.

---

## Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `anthropic` — Claude API client
- `gradio` — web UI framework
- `langchain`, `langchain-community`, `langchain-huggingface` — RAG pipeline
- `faiss-cpu` — vector similarity search
- `sentence-transformers` — embedding model (downloads ~90 MB on first run)
- `pypdf` — PDF text extraction
- `fpdf2` — PDF generation utilities

> **Note:** `sentence-transformers` downloads the embedding model from Hugging Face on first run. This requires an internet connection and takes 1–2 minutes. Subsequent runs use the cached model.

---

## Step 4 — Set your Anthropic API key

```bash
# macOS / Linux
export ANTHROPIC_API_KEY=sk-ant-...

# Windows (Command Prompt)
set ANTHROPIC_API_KEY=sk-ant-...

# Windows (PowerShell)
$env:ANTHROPIC_API_KEY="sk-ant-..."
```

To avoid setting this every session, add it to a `.env` file:

```
ANTHROPIC_API_KEY=sk-ant-...
```

Then load it before running:

```bash
export $(cat .env | xargs)   # macOS / Linux
```

---

## Step 5 — (Optional) Add course-note PDFs for the RAG pipeline

Place PDF files in the `docs/` directory. Summit Tutor will automatically index them on startup and use them to ground answers in your curriculum.

```bash
cp algebra_notes.pdf docs/
cp geometry_notes.pdf docs/
```

The `docs/` directory already contains sample notes. You can add, remove, or replace any PDFs — the index rebuilds automatically.

---

## Step 6 — Launch the app

```bash
python app.py
```

Check your terminal for the local URL — it will show something like `http://127.0.0.1:7860` or a nearby port. Open that URL in your browser.

---

## Optional: Run the prompt experiments

```bash
python prompt_experiments.py
```

This makes 15 Claude API calls (3 prompt variants × 5 questions) and saves results to `prompt_comparison.csv`. Expect ~2–3 minutes of runtime.

---

## Optional: Run the evaluation harness

```bash
python evaluate.py
```

This runs 15 test questions through the full pipeline and saves results to `evaluation_results.csv`.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `EnvironmentError: ANTHROPIC_API_KEY not set` | Re-run Step 4 and ensure the key is exported in the same shell session |
| `ModuleNotFoundError` | Make sure the virtual environment is activated (`source .venv/bin/activate`) and dependencies are installed (`pip install -r requirements.txt`) |
| Embedding model download hangs | Check your internet connection; the model (~90 MB) is downloaded from Hugging Face on first use |
| `faiss-cpu` install fails on Apple Silicon | Run `pip install faiss-cpu --no-binary faiss-cpu` |
| Port 7860 already in use | Pass a different port: `python app.py` then set `demo.launch(server_port=7861)` in `app.py` |
