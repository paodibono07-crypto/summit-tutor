import re
import unicodedata


def _normalize(text: str) -> str:
    """Lowercase and strip diacritical marks for accent-insensitive keyword matching."""
    return unicodedata.normalize("NFD", text.lower()).encode("ascii", "ignore").decode()

# Matches a message that is purely a number (int, decimal, or simple fraction)
# e.g. "12", "44", "3.5", "1/2", " 17 " — always allowed (worksheet/game answers)
_NUMERIC_RE = re.compile(r'^\s*-?\d+(\.\d+)?(\s*/\s*\d+(\.\d+)?)?\s*$')

# Matches arithmetic expressions and numeric math queries that lack keyword markers
_ARITH_RE = re.compile(
    r'\d+\s*[+\-*/÷×%^]\s*\d+'    # 2+5, 3×4, 10%2
    r'|\bwhat\s+is\s+\d'           # what is 2...
    r'|\bhow\s+much\s+is\s+\d'     # how much is 5...
    r'|\bwhat\'s\s+\d'             # what's 9...
    r'|\d+\s*squared\b'            # 5 squared
    r'|\d+\s*cubed\b'              # 5 cubed
    r'|\bsquare\s+root\s+of\s+\d'  # square root of 9
    r'|\d+\s*[=<>]\s*\d',          # 5=5, 3<4
    re.IGNORECASE,
)

MATH_KEYWORDS_EN = [
    "subtraction", "addition", "multiplication", "division", "regrouping", "borrowing", "carrying", "arithmetic", "multiply", "divide", "subtract", "add", "times", "plus", "minus",
    "math", "algebra", "geometry", "calculus", "equation", "number", "fraction",
    "decimal", "percent", "ratio", "proportion", "function", "graph", "triangle",
    "circle", "area", "perimeter", "volume", "angle", "slope", "derivative",
    "integral", "matrix", "vector", "probability", "statistics", "polynomial",
    "exponent", "logarithm", "theorem", "proof", "variable", "coefficient",
    "quadratic", "linear", "factor", "solve", "simplify", "calculate", "compute",
    "plus", "minus", "multiply", "divide", "sum", "product", "difference",
    "addition", "subtraction", "multiplication", "division",
    "regroup", "regrouping", "borrow", "borrowing", "carry", "carrying",
    "quotient", "square", "cube", "root", "prime", "integer", "rational",
    "irrational", "inequality", "expression", "formula", "coordinate", "axis",
    "symmetry", "congruent", "similar", "parallel", "perpendicular", "hypotenuse",
    "pythagorean", "trigonometry", "sine", "cosine", "tangent", "radian", "degree",
    "limit", "series", "sequence", "arithmetic", "digit", "place value", "factor",
    "multiple", "greatest common", "least common", "mean", "median", "mode", "range",
    "histogram", "scatter", "regression", "parabola", "hyperbola", "ellipse",
    "asymptote", "domain", "range", "inverse", "composition", "absolute value",
    "distance", "midpoint", "gradient", "intercept", "system", "matrix",
]

MATH_KEYWORDS_ES = [
    # Core subject names
    "matematica", "matemática", "matemáticas", "algebra", "álgebra",
    "geometria", "geometría", "calculo", "cálculo",
    # Operations (verbs + nouns, accented and plain)
    "sumar", "suma", "restar", "resta", "multiplicar", "multiplicacion", "multiplicación",
    "dividir", "division", "división", "calcular", "resolver", "simplificar",
    "demostrar", "probar",
    # Numbers and types
    "numero", "número", "numeros", "números", "fraccion", "fracción",
    "fracciones", "decimal", "porcentaje", "entero", "primo", "racional",
    "irracional", "par", "impar", "digito", "dígito",
    # Equations and expressions
    "ecuacion", "ecuación", "expresion", "expresión", "formula", "fórmula",
    "variable", "coeficiente", "igual", "resultado", "resolucion", "resolución",
    # Shapes and measurement
    "triangulo", "triángulo", "circulo", "círculo", "area", "área",
    "perimetro", "perímetro", "volumen", "angulo", "ángulo", "hipotenusa",
    # Algebra / advanced
    "cuadratica", "cuadrática", "lineal", "factor", "exponente", "logaritmo",
    "teorema", "polinomio", "pendiente", "coordenada", "eje", "origen",
    "dominio", "rango", "inversa", "asintota", "asíntota",
    # Stats / probability
    "probabilidad", "estadistica", "estadística", "media", "mediana", "moda",
    "histograma", "parabola", "parábola", "regresion", "regresión",
    # Trig / calc
    "trigonometria", "trigonometría", "seno", "coseno", "tangente",
    "derivada", "integral", "limite", "límite", "serie", "sucesion", "sucesión",
    # Other math nouns
    "razon", "razón", "proporcion", "proporción", "funcion", "función",
    "grafica", "gráfica", "matriz", "vector", "sistema", "operacion", "operación",
    "simetria", "simetría", "congruente", "similar", "paralelo", "perpendicular",
    "pitágoras", "pitagoras", "producto", "diferencia", "cociente", "cuadrado",
    "cubo", "raiz", "raíz", "minimo", "mínimo", "maximo", "máximo",
    "distancia", "punto medio", "gradiente", "intercepto",
    # Patterns and place value
    "patron", "patrón", "patrones", "valor", "posicional", "valor posicional",
    "reagrupar", "reagrupacion", "reagrupación", "llevar", "prestamo", "préstamo",
    # Time / clock (common word-problem topic)
    "tiempo", "reloj", "hora", "minuto", "segundo",
    # Fractions sub-vocabulary
    "numerador", "denominador", "mixto", "impropia", "equivalente",
    # Student intent words — what makes "Quiero explicar fracciones" math
    "explicar", "explicacion", "explicación", "aprender", "entender",
    "quiero", "necesito", "ayuda", "como", "cómo", "cuanto", "cuánto",
    "cuantos", "cuántos", "ejercicio", "ejercicios", "problema", "problemas",
    "practicar", "practica", "práctica",
    # Misc
    "aritmetica", "aritmética", "desigualdad", "demostracion", "demostración",
]

SYSTEM_PROMPT = """You are Summit Tutor, a friendly and encouraging math tutor for middle and high school students (grades 6–12).

Core rules:
- Answer ONLY math-related questions. If asked about anything else, politely decline and redirect.
- Detect the student's language (English or Spanish) and respond in that same language.
- Always show step-by-step work — never give just an answer.
- Use simple, age-appropriate language and be encouraging.
- When relevant, use examples with concrete numbers.
- You cover: arithmetic, fractions, algebra, geometry, statistics, trigonometry, pre-calculus, and introductory calculus.
- Do not solve homework answers without explanation; teach the concept first.
- Always think step by step before giving your final answer, reasoning through each part out loud.

Tone: warm, patient, supportive — like a great study buddy who happens to know a lot of math.

---

Here are examples of how you should respond:

EXAMPLE 1 (English — linear equation):
Q: How do I solve 3x + 5 = 20?

A: Great question! Let me think through this step by step.

My goal is to get x by itself on one side of the equation.

Step 1 — Get rid of the +5 on the left side.
I'll subtract 5 from both sides so the equation stays balanced:
  3x + 5 - 5 = 20 - 5
  3x = 15

Step 2 — Get rid of the 3 that's multiplying x.
I'll divide both sides by 3:
  3x ÷ 3 = 15 ÷ 3
  x = 5

Step 3 — Check the answer by plugging x = 5 back in:
  3(5) + 5 = 15 + 5 = 20 ✓

So x = 5. The key idea here is to "undo" each operation one at a time, always doing the same thing to both sides. Does that make sense?

---

EXAMPLE 2 (Spanish — fracciones):
Q: ¿Cómo sumo 1/3 + 1/4?

A: ¡Buena pregunta! Vamos paso a paso.

Para sumar fracciones, ambas deben tener el mismo denominador. Eso se llama el mínimo común denominador (MCD).

Paso 1 — Encontrar el mínimo común denominador de 3 y 4.
Pienso: ¿cuál es el número más pequeño en el que caben tanto 3 como 4?
  Múltiplos de 3: 3, 6, 9, 12, 15...
  Múltiplos de 4: 4, 8, 12, 16...
  El primero que aparece en ambas listas es 12. ¡Ese es nuestro MCD!

Paso 2 — Convertir cada fracción para que tenga denominador 12.
  1/3 → multiplico arriba y abajo por 4 → 4/12
  1/4 → multiplico arriba y abajo por 3 → 3/12

Paso 3 — Ahora que los denominadores son iguales, sumo los numeradores:
  4/12 + 3/12 = 7/12

Paso 4 — Verificar si se puede simplificar 7/12.
  7 es primo y no divide a 12, así que ya está en su mínima expresión.

Resultado: 1/3 + 1/4 = 7/12

La idea clave es que no puedes sumar fracciones directamente hasta que tengan el mismo denominador — como intentar sumar manzanas y naranjas. ¿Quieres intentar otro ejemplo?

---"""


OFF_TOPIC_BLOCKLIST = [
    # Politics
    "election", "president", "senator", "congress", "democrat", "republican",
    "political party", "prime minister", "parliament", "legislation",
    # Entertainment
    "movie", "film", "actor", "actress", "celebrity", "pop star", "singer",
    "tv show", "netflix", "tiktok", "instagram", "youtube channel",
    # Food & recipes
    "recipe", "how to cook", "restaurant", "ingredients", "cuisine", "calorie",
    # Sports scores / gossip (math word problems about sports are fine)
    "nfl", "nba", "nhl", "mlb", "who won the game", "sports news",
    # Misc off-topic
    "horoscope", "astrology", "zodiac", "dating advice", "relationship advice",
    "weather forecast",
]


def is_on_topic(query: str) -> bool:
    q = query.lower().strip()
    # Always allow single-letter multiple-choice answers (A–F)
    if re.match(r'^[a-f]$', q):
        return True
    # Always allow very short follow-up answers (under 5 chars: "yes", "ok", "both", etc.)
    if len(q) < 5:
        return True
    # Always allow messages containing "all" (e.g. "all three", "all of them")
    if re.search(r'\ball\b', q):
        return True
    # Block clearly off-topic subjects first
    if any(kw in q for kw in OFF_TOPIC_BLOCKLIST):
        return False
    # Always allow pure numeric answers (worksheet / game replies like "12" or "44")
    if _NUMERIC_RE.match(query):
        return True
    # Allow any numeric/arithmetic expression
    if _ARITH_RE.search(q):
        return True
    # Allow if it matches known math keywords (accent-insensitive for Spanish)
    q_norm = _normalize(q)
    all_keywords = MATH_KEYWORDS_EN + MATH_KEYWORDS_ES
    return any(kw in q for kw in all_keywords) or any(_normalize(kw) in q_norm for kw in all_keywords)


def off_topic_reply(query: str) -> str:
    spanish_hints = [
        "qué", "cómo", "cuál", "dónde", "quién", "cuándo", "por qué",
        "eres", "puedes", "necesito", "ayuda", "tengo", "mi ", "yo ",
    ]
    is_spanish = any(h in query.lower() for h in spanish_hints)

    if is_spanish:
        return (
            "Lo siento, solo puedo ayudarte con preguntas de matemáticas para "
            "estudiantes de secundaria y preparatoria. ¿Tienes alguna pregunta sobre "
            "álgebra, geometría, fracciones, ecuaciones u otro tema matemático?"
        )
    return (
        "Sorry, I can only help with math questions for middle and high school students. "
        "Do you have a question about algebra, geometry, fractions, equations, "
        "or another math topic?"
    )
