"""Generates placeholder math PDF notes in the docs/ folder.
Run once before starting the app: python create_docs.py
"""
from pathlib import Path

from fpdf import FPDF

DOCS_DIR = Path(__file__).parent / "docs"
DOCS_DIR.mkdir(exist_ok=True)


FONT_PATH = Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf")
if not FONT_PATH.exists():
    # Fallback: DejaVu ships with many Linux/conda setups
    import shutil
    dv = shutil.which("fc-list")
    FONT_PATH = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")


def _register_unicode(pdf: FPDF) -> str:
    """Register a Unicode TTF font and return its family name."""
    if FONT_PATH.exists():
        pdf.add_font("UniFont", "", str(FONT_PATH))
        pdf.add_font("UniFont", "B", str(FONT_PATH))
        pdf.add_font("UniFont", "I", str(FONT_PATH))
        return "UniFont"
    return "Helvetica"  # ASCII-safe fallback


def _clean(text: str) -> str:
    """Replace characters that break Latin-1 encoding when no Unicode font is found."""
    return (
        text.replace("—", "-")   # em dash
            .replace("–", "-")   # en dash
            .replace("’", "'")   # right single quote
            .replace("‘", "'")   # left single quote
            .replace("“", '"')   # left double quote
            .replace("”", '"')   # right double quote
            .replace("π", "pi")  # pi symbol
            .replace("σ", "s")   # sigma
            .replace("²", "^2")  # superscript 2
            .replace("³", "^3")  # superscript 3
            .replace("√", "sqrt")
            .replace("≤", "<=")
            .replace("≥", ">=")
            .replace("≈", "~=")
            .replace("×", "x")   # multiplication sign
            .replace("÷", "/")   # division sign
            .replace("±", "+/-") # plus-minus
            .replace("≠", "!=")
    )


class NotesPDF(FPDF):
    def __init__(self, subject: str):
        super().__init__()
        self._subject = subject
        self._font = _register_unicode(self)

    def _f(self, style: str = "", size: int = 11) -> None:
        self.set_font(self._font, style, size)

    def header(self):
        self._f("", 9)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, _clean(f"Summit Tutor - {self._subject}"), align="R")
        self.ln(2)
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-14)
        self._f("", 9)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, f"Page {self.page_no()}", align="C")

    def doc_title(self, title: str) -> None:
        self._f("B", 18)
        self.ln(4)
        self.cell(0, 12, _clean(title), align="C")
        self.ln(10)

    def section(self, heading: str, body: str) -> None:
        self._f("B", 13)
        self.set_fill_color(230, 240, 255)
        self.cell(0, 8, _clean(f"  {heading}"), fill=True)
        self.ln(2)
        self._f("", 11)
        self.multi_cell(0, 6, _clean(body))
        self.ln(5)


def make_pdf(filename: str, title: str, subject: str, sections: list[tuple[str, str]]) -> None:
    pdf = NotesPDF(subject)
    pdf.add_page()
    pdf.doc_title(_clean(title))
    for heading, body in sections:
        pdf.section(_clean(heading), _clean(body))
    out_path = DOCS_DIR / filename
    pdf.output(str(out_path))
    print(f"  Created {out_path}")


print("Generating placeholder math PDFs...")

make_pdf(
    "algebra_notes.pdf",
    "Algebra Notes — Middle School",
    "Algebra",
    [
        (
            "1. Variables and Expressions",
            "A variable is a letter that stands for an unknown number.\n"
            "Example: In 3x + 7, the variable is x.\n\n"
            "An expression combines numbers, variables, and operations but has no equals sign.\n"
            "An equation has an equals sign: 3x + 7 = 19.",
        ),
        (
            "2. Solving One-Step and Two-Step Equations",
            "Goal: isolate the variable by doing the same operation to both sides.\n\n"
            "One-step:  x + 5 = 12  =>  x = 12 - 5 = 7\n\n"
            "Two-step:  2x + 3 = 11\n"
            "  Subtract 3 from both sides:  2x = 8\n"
            "  Divide both sides by 2:       x = 4\n\n"
            "Check: 2(4) + 3 = 11  ✓",
        ),
        (
            "3. The Quadratic Formula",
            "For ax² + bx + c = 0, the solutions are:\n\n"
            "  x = [ -b ± sqrt(b² - 4ac) ] / 2a\n\n"
            "The expression b² - 4ac is called the discriminant.\n"
            "  > 0  =>  two real solutions\n"
            "  = 0  =>  one real solution (double root)\n"
            "  < 0  =>  no real solutions\n\n"
            "Example: x² - 5x + 6 = 0  (a=1, b=-5, c=6)\n"
            "  x = [5 ± sqrt(25-24)] / 2 = [5 ± 1] / 2  =>  x = 3 or x = 2",
        ),
        (
            "4. Inequalities",
            "Solve like equations, but reverse the inequality when multiplying or\n"
            "dividing by a negative number.\n\n"
            "Example: -2x > 6  =>  x < -3\n\n"
            "Graph solutions on a number line:\n"
            "  Open circle  ( ) for strict inequality (< or >)\n"
            "  Closed circle [ ] for inclusive inequality (<= or >=)",
        ),
        (
            "5. Systems of Linear Equations",
            "Two methods: substitution and elimination.\n\n"
            "Substitution:\n"
            "  y = 2x + 1\n"
            "  3x + y = 16  =>  3x + (2x+1) = 16  =>  5x = 15  =>  x = 3, y = 7\n\n"
            "Elimination:\n"
            "  Add or subtract equations to cancel one variable.",
        ),
    ],
)

make_pdf(
    "geometry_notes.pdf",
    "Geometry Notes — Middle & High School",
    "Geometry",
    [
        (
            "1. Basic Shapes — Area and Perimeter",
            "Rectangle:  Area = l × w,  Perimeter = 2(l + w)\n"
            "Triangle:   Area = (b × h) / 2\n"
            "Trapezoid:  Area = (b1 + b2) / 2 × h\n"
            "Circle:     Area = π r²,  Circumference = 2π r  (π ≈ 3.14159)",
        ),
        (
            "2. The Pythagorean Theorem",
            "In any right triangle:  a² + b² = c²\n"
            "where c is the hypotenuse (side opposite the right angle).\n\n"
            "Example: legs a = 3, b = 4\n"
            "  c = sqrt(9 + 16) = sqrt(25) = 5\n\n"
            "Common Pythagorean triples: (3,4,5)  (5,12,13)  (8,15,17)",
        ),
        (
            "3. Angles",
            "Acute: 0° < angle < 90°\n"
            "Right: angle = 90°\n"
            "Obtuse: 90° < angle < 180°\n"
            "Straight: angle = 180°\n\n"
            "Sum of interior angles:\n"
            "  Triangle:   180°\n"
            "  Quadrilateral: 360°\n"
            "  n-gon:  (n - 2) × 180°\n\n"
            "Vertical angles are equal; supplementary angles add to 180°.",
        ),
        (
            "4. Similarity and Congruence",
            "Congruent figures: same shape AND same size (all sides and angles equal).\n"
            "Similar figures: same shape, sides proportional, angles equal.\n\n"
            "If triangles ABC ~ DEF, then:\n"
            "  AB/DE = BC/EF = AC/DF  (scale factor)",
        ),
        (
            "5. Volume of 3-D Shapes",
            "Rectangular prism: V = l × w × h\n"
            "Cylinder: V = π r² h\n"
            "Cone:     V = (1/3) π r² h\n"
            "Sphere:   V = (4/3) π r³\n"
            "Pyramid:  V = (1/3) × base area × height",
        ),
    ],
)

make_pdf(
    "statistics_intro.pdf",
    "Introduction to Statistics & Probability",
    "Statistics",
    [
        (
            "1. Measures of Central Tendency",
            "Mean (average): sum of all values / count of values\n"
            "Median: middle value when data is sorted\n"
            "Mode: value that appears most often\n\n"
            "Example dataset: {2, 4, 4, 6, 8, 10}\n"
            "  Mean   = (2+4+4+6+8+10)/6 = 34/6 ≈ 5.67\n"
            "  Median = (4+6)/2 = 5  (even count → average the two middle values)\n"
            "  Mode   = 4",
        ),
        (
            "2. Measures of Spread",
            "Range = max - min\n\n"
            "Variance: average of squared deviations from the mean.\n"
            "Standard deviation (σ) = sqrt(variance)\n\n"
            "Interquartile range (IQR) = Q3 - Q1\n"
            "  Used in box-and-whisker plots.\n"
            "  Outlier rule: values below Q1 - 1.5×IQR or above Q3 + 1.5×IQR.",
        ),
        (
            "3. Probability Basics",
            "P(event) = (favorable outcomes) / (total equally likely outcomes)\n"
            "0 ≤ P(event) ≤ 1;  P(impossible) = 0;  P(certain) = 1\n\n"
            "P(A or B) = P(A) + P(B) - P(A and B)   [Addition Rule]\n"
            "P(A and B) = P(A) × P(B)                [if A, B independent]\n\n"
            "Example: rolling a fair die\n"
            "  P(rolling a 3) = 1/6 ≈ 0.167",
        ),
        (
            "4. Reading Data Displays",
            "Bar chart: compare counts or amounts across categories.\n"
            "Line graph: show change over time (trend).\n"
            "Pie/circle chart: show parts of a whole (each slice = % of total).\n"
            "Histogram: like a bar chart but for continuous data; bars touch.\n"
            "Scatter plot: shows relationship between two numeric variables.\n"
            "  Positive correlation: both variables increase together.\n"
            "  Negative correlation: one increases as the other decreases.",
        ),
        (
            "5. Counting Principles",
            "Fundamental Counting Principle: if one event has m outcomes and\n"
            "another has n outcomes, together they have m × n outcomes.\n\n"
            "Permutations (order matters):  P(n,r) = n! / (n-r)!\n"
            "Combinations (order doesn't matter): C(n,r) = n! / [r!(n-r)!]\n\n"
            "Example: How many ways to choose 2 from 5 students?\n"
            "  C(5,2) = 5!/(2!×3!) = 10",
        ),
    ],
)

print("Done! All PDFs written to docs/")
