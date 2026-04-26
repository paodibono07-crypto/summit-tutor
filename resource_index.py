"""
Maps Summit Math Camp curriculum topics to their PDF documents.

Document types:
  teaching     – lesson slides, explanations, introductions
  activity     – games, worksheets, practice problems
  placeholder  – stub docs not from camp (excluded from suggestions and RAG)
"""

# ── Doc type lookup (used by rag.py to tag chunks) ─────────────────────────────

DOC_TYPES: dict[str, str] = {
    # Teaching docs
    "Teaching document - Google Docs.pdf":                                        "teaching",
    "Intro to fractions .ppt - Google Slides.pdf":                                "teaching",
    "Basic addition - Google Slides.pdf":                                         "teaching",
    "addition word problems - Google Slides.pdf":                                 "teaching",
    "equal Groups, Repeated Addition, Multiplication Sentence - Google Slides.pdf": "teaching",
    "division intro 2nd grade.pptx - Google Slides.pdf":                          "teaching",
    "telling time intro review 2nd grade.pptx - Google Slides.pdf":               "teaching",
    # Activity / worksheet docs
    "Subtraction with Regrouping game - Google Slides.pdf":                       "activity",
    "fraction worksheet .pptx - Google Slides.pdf":                               "activity",
    "Mac - Equivalent Fractions Game - Google Slides.pdf":                        "activity",
    "AdditionalPracticeProblems.pdf":                                             "activity",
    # Placeholder stubs — excluded from RAG and suggestions
    "algebra_notes.pdf":     "placeholder",
    "geometry_notes.pdf":    "placeholder",
    "statistics_intro.pdf":  "placeholder",
}

# ── Topic → document mapping ───────────────────────────────────────────────────

RESOURCE_INDEX: dict[str, dict] = {
    "subtraction_regrouping": {
        "topic": "Subtraction with Regrouping",
        "keywords": [
            "subtraction", "subtract", "regroup", "regrouping",
            "borrow", "borrowing", "take away", "minus",
            "resta", "restar",
        ],
        "teaching": None,
        "activity": "Subtraction with Regrouping game - Google Slides.pdf",
    },
    "fractions_intro": {
        "topic": "Introduction to Fractions",
        "keywords": [
            "fraction", "fractions", "numerator", "denominator",
            "half", "quarter", "third", "1/2", "1/3", "1/4", "1/8",
            "add fraction", "adding fraction",
            "fracción", "fracciones", "medio", "cuarto", "tercio",
        ],
        "teaching": "Intro to fractions .ppt - Google Slides.pdf",
        "activity": "fraction worksheet .pptx - Google Slides.pdf",
    },
    "equivalent_fractions": {
        "topic": "Equivalent Fractions",
        "keywords": [
            "equivalent fraction", "same fraction", "equal fraction",
            "equivalent", "fracciones equivalentes",
        ],
        "teaching": "Intro to fractions .ppt - Google Slides.pdf",
        "activity": "Mac - Equivalent Fractions Game - Google Slides.pdf",
    },
    "addition": {
        "topic": "Addition",
        "keywords": [
            "addition", "add", "adding", "sum", "plus", "total",
            "carry", "carrying", "adición", "suma", "sumar",
        ],
        "teaching": "Basic addition - Google Slides.pdf",
        "activity": "AdditionalPracticeProblems.pdf",
    },
    "addition_word_problems": {
        "topic": "Addition Word Problems",
        "keywords": [
            "word problem", "story problem", "how many in all",
            "how many total", "problema de palabras",
        ],
        "teaching": "addition word problems - Google Slides.pdf",
        "activity": "AdditionalPracticeProblems.pdf",
    },
    "multiplication": {
        "topic": "Multiplication & Equal Groups",
        "keywords": [
            "multiplication", "multiply", "times", "equal groups",
            "repeated addition", "multiplication sentence",
            "multiplicación", "multiplicar", "grupos iguales",
        ],
        "teaching": "equal Groups, Repeated Addition, Multiplication Sentence - Google Slides.pdf",
        "activity": "AdditionalPracticeProblems.pdf",
    },
    "division": {
        "topic": "Division",
        "keywords": [
            "division", "divide", "dividing", "quotient",
            "how many groups", "split into",
            "división", "dividir",
        ],
        "teaching": "division intro 2nd grade.pptx - Google Slides.pdf",
        "activity": "AdditionalPracticeProblems.pdf",
    },
    "telling_time": {
        "topic": "Telling Time",
        "keywords": [
            "time", "clock", "hour", "minute", "half past",
            "quarter past", "o'clock", "telling time",
            "hora", "reloj", "minuto",
        ],
        "teaching": "telling time intro review 2nd grade.pptx - Google Slides.pdf",
        "activity": None,
    },
}


# ── Helper functions ───────────────────────────────────────────────────────────

def find_resources(query: str) -> list[dict]:
    """Return all resource entries whose keywords appear in the query."""
    q = query.lower()
    return [
        entry for entry in RESOURCE_INDEX.values()
        if any(kw in q for kw in entry["keywords"])
    ]


def get_topic_name(query: str) -> str:
    """Return the best human-readable topic name for a query.

    Falls back to a trimmed excerpt of the question itself.
    """
    matches = find_resources(query)
    if matches:
        return matches[0]["topic"]
    return query.strip("?¿!¡.").strip()[:60]
