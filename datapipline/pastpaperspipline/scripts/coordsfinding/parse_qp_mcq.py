from extract_lines import extract_lines
import re
import json
from dataclasses import dataclass
from typing import List, Literal, Optional

QuestionType = Literal["structured", "mcq"]

@dataclass
class Line:
    page: int
    text: str
    x0: float
    y0: float
    x1: float
    y1: float

@dataclass
class PartCoord:
    question: str
    part: str
    start_page: int
    start_y: float
    end_page: int
    end_y: float

# ─── MCQ QP Column X-ranges ───
Q_NUM_X_MIN, Q_NUM_X_MAX = 48.0, 51.0       # Question number at x≈49.6
STEM_X_MIN, STEM_X_MAX = 70.0, 75.0         # Stem text at x≈70.8
CHOICE_LABEL_X_MIN, CHOICE_LABEL_X_MAX = 70.0, 75.0  # A/B/C/D labels at x≈70.9
CHOICE_TEXT_X_RANGES = [                    # Choice text columns
    (90.0, 100.0),    # A text at x≈92
    (165.0, 175.0),   # B text at x≈170
    (265.0, 275.0),   # C text at x≈269
    (365.0, 395.0),   # D text at x≈368-389
]

DATA_FORMULAE_Y_MAX = 500.0  # Page 2 data/formulae ends around here

# Regex patterns
Q_NUM_RE = re.compile(r'^\d+$')
CHOICE_LABEL_RE = re.compile(r'^[ABCD]$')

def parse_lines_qp(content: str) -> List[Line]:
    """Parse lines_qp.txt format into Line objects."""
    lines = []
    current_page = None
    for raw in content.splitlines():
        raw = raw.rstrip('\n')
        m = re.match(r'=== Page (\d+) ===', raw)
        if m:
            current_page = int(m.group(1))
            continue
        m = re.match(r'\s+y=([\d.]+)\s+x=([\d.]+):\s*(.*)', raw)
        if m and current_page is not None:
            y0 = float(m.group(1))
            x0 = float(m.group(2))
            text = m.group(3).strip()
            if text:
                lines.append(Line(current_page, text, x0, y0, x0 + 10, y0 + 8))
    return lines

def is_header_footer(line: Line) -> bool:
    """Skip page headers, footers, copyright, trace IDs."""
    if line.y0 < 50 and ('Cambridge' in line.text or 'UCLES' in line.text or 'Data' in line.text or 'Formulae' in line.text):
        return True
    if line.y0 > 790 and ('Cambridge' in line.text or 'Page' in line.text or 'Trace' in line.text or 'PapaCambridge' in line.text):
        return True
    if 'DO NOT WRITE' in line.text:
        return True
    if 'BLANK PAGE' in line.text:
        return True
    return False

def is_page_number(line: Line) -> bool:
    """Page numbers at x≈294."""
    return (abs(line.x0 - 294.0) < 10 and
            Q_NUM_RE.match(line.text) and
            line.y0 < 50)

def is_data_formulae_page(line: Line) -> bool:
    """Detect data/formulae page (page 2 for 9702)."""
    keywords = ['Data', 'Formulae', 'uniformly accelerated motion', 'hydrostatic pressure',
                'g = 9.81', 'speed of light', 'elementary charge', 'unified atomic mass',
                'rest mass of proton', 'rest mass of electron', 'Avogadro constant',
                'molar gas constant', 'Boltzmann constant', 'gravitational constant',
                'permittivity of free space', 'Planck constant', 'Stefan-Boltzmann']
    return any(kw in line.text for kw in keywords)

def filter_content_lines(lines: List[Line]) -> List[Line]:
    """Remove headers, footers, page numbers, data/formulae page."""
    out = []
    for ln in lines:
        if is_header_footer(ln) or is_page_number(ln):
            continue
        # Skip entire page 2 (data/formulae) - detect by content
        if ln.page == 2 and is_data_formulae_page(ln):
            continue
        out.append(ln)
    return out

@dataclass
class QuestionStart:
    number: str
    page: int
    y: float

def find_question_starts(lines: List[Line]) -> List[QuestionStart]:
    """Find all question numbers at x≈49.6."""
    starts = []
    for ln in lines:
        if Q_NUM_X_MIN <= ln.x0 <= Q_NUM_X_MAX and Q_NUM_RE.match(ln.text):
            starts.append(QuestionStart(ln.text, ln.page, ln.y0))
    starts.sort(key=lambda q: (q.page, q.y))
    return starts

@dataclass
class ChoiceDLine:
    question_num: str
    page: int
    y: float

def find_choice_d_lines(lines: List[Line], q_starts: List[QuestionStart]) -> List[ChoiceDLine]:
    """Find D choice lines for each question (marks end of MCQ question)."""
    d_lines = []
    for ln in lines:
        if (CHOICE_LABEL_X_MIN <= ln.x0 <= CHOICE_LABEL_X_MAX and
            CHOICE_LABEL_RE.match(ln.text) and ln.text == 'D'):
            # Find which question this D belongs to
            for i, q in enumerate(q_starts):
                next_q_y = q_starts[i + 1].y if i + 1 < len(q_starts) else float('inf')
                next_q_page = q_starts[i + 1].page if i + 1 < len(q_starts) else float('inf')
                if (ln.page == q.page and ln.y0 > q.y and
                    (ln.page < next_q_page or (ln.page == next_q_page and ln.y0 < next_q_y))):
                    d_lines.append(ChoiceDLine(q.number, ln.page, ln.y0))
                    break
    return d_lines

def parse_mcq_qp(content: str, question_type: QuestionType = "mcq") -> List[PartCoord]:
    """Main entry: parse MCQ question paper lines -> question coordinates (part='')."""
    if question_type != "mcq":
        raise ValueError(f"Expected 'mcq', got '{question_type}'")

    lines = parse_lines_qp(content)
    lines = filter_content_lines(lines)

    # Find question starts
    q_starts = find_question_starts(lines)
    if not q_starts:
        return []

    # Validate sequential question numbers (MCQ has 40 questions)
    q_nums = [int(q.number) for q in q_starts]
    expected = list(range(1, len(q_nums) + 1))
    if q_nums != expected:
        print(f"WARNING: Question numbers not sequential: {q_nums}")

    # Find D choice lines (end of each question)
    d_lines = find_choice_d_lines(lines, q_starts)

    # Build mapping: question_num -> (end_page, end_y)
    q_ends = {d.question_num: (d.page, d.y) for d in d_lines}

    parts = []
    for i, q_start in enumerate(q_starts):
        q_num = q_start.number
        start_page = q_start.page
        start_y = q_start.y

        # End at D choice line if found, else next question start
        if q_num in q_ends:
            end_page, end_y = q_ends[q_num]
        elif i + 1 < len(q_starts):
            next_q = q_starts[i + 1]
            end_page = next_q.page
            end_y = next_q.y - 2.0
        else:
            # Last question (Q40)
            end_page = start_page
            page_lines = [ln for ln in lines if ln.page == start_page]
            if page_lines:
                end_y = max(ln.y0 for ln in page_lines)
            else:
                end_y = 800.0

        parts.append(PartCoord(
            question=q_num,
            part="",
            start_page=start_page,
            start_y=round(start_y, 1),
            end_page=end_page,
            end_y=round(end_y, 1)
        ))

    return parts

def main(qp_lines: str, question_type: QuestionType = "mcq"):
    parts = parse_mcq_qp(qp_lines, question_type)

    out = [
        {
            "question": p.question,
            "part": p.part,
            "start_page": p.start_page,
            "start_y": p.start_y,
            "end_page": p.end_page,
            "end_y": p.end_y
        }
        for p in parts
    ]

    with open('datapipline/pastpaperspipline/scripts/qp_mcq_coords.json', 'w') as f:
        json.dump(out, f, indent=2)
    print("\nSaved to qp_mcq_coords.json")

if __name__ == '__main__':
    pdf_path = "datapipline/pastpaperspipline/downlaods/9702_m26_qp_12.pdf"
    lines = extract_lines(pdf_path)
    main(lines)