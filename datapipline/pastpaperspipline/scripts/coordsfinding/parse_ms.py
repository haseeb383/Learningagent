import re
import json
from dataclasses import dataclass
from typing import List, Literal

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

# ─── Structured MS Constants ───
Q_COL_MIN, Q_COL_MAX = 70.0, 90.0
MARKS_COL_MIN, MARKS_COL_MAX = 458.0, 468.0
MARK_CODE_MIN, MARK_CODE_MAX = 450.0, 458.0
HEADER_Y = 55.7
FOOTER_Y = 550.0
FRONT_MATTER_MAX_PAGE = 8
PART_LABEL_RE = re.compile(r'^(\d+)\(([a-z])\)$')
TOTAL_MARKS_RE = re.compile(r'^\d+$')

# ─── MCQ MS Constants ───
MCQ_Q_COL_MIN, MCQ_Q_COL_MAX = 70.0, 85.0      # Question number at ~75-78
MCQ_ANS_COL_MIN, MCQ_ANS_COL_MAX = 110.0, 130.0  # Answer letter at ~118.8
MCQ_MARKS_COL_MIN, MCQ_MARKS_COL_MAX = 525.0, 540.0  # Marks at ~534.2
MCQ_HEADER_Y = 68.8
MCQ_FOOTER_Y = 790.0

def parse_lines_ms(content: str) -> List[Line]:
    """Parse lines_ms string (same format as lines_ms.txt) into Line objects."""
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

# ─── Structured MS Parser ───
def is_structured_header(line: Line) -> bool:
    return (abs(line.y0 - HEADER_Y) < 2.0 and
            line.text in ('Question', 'Answer', 'Marks', 'Guidance'))

def is_structured_footer(line: Line) -> bool:
    return line.y0 > FOOTER_Y and ('Cambridge' in line.text or 'Page' in line.text)

def is_front_matter(page: int) -> bool:
    return page <= FRONT_MATTER_MAX_PAGE

def filter_structured_lines(lines: List[Line]) -> List[Line]:
    out = []
    for ln in lines:
        if is_front_matter(ln.page):
            continue
        if is_structured_header(ln) or is_structured_footer(ln):
            continue
        if ln.x0 > 470:  # Guidance column
            continue
        out.append(ln)
    return out

def extract_structured_parts(lines: List[Line]) -> List[PartCoord]:
    by_page = {}
    for ln in lines:
        by_page.setdefault(ln.page, []).append(ln)
    for pg in by_page:
        by_page[pg].sort(key=lambda l: l.y0)

    parts = []
    current_q = None
    current_part = None
    part_start = None
    candidate_ends = []

    def close_current_part():
        nonlocal current_q, current_part, part_start, candidate_ends
        if current_part is not None and candidate_ends:
            end_pg, end_y = candidate_ends[-1]
            parts.append(PartCoord(
                question=current_q,
                part=current_part,
                start_page=part_start[0],
                start_y=round(part_start[1], 1),
                end_page=end_pg,
                end_y=round(end_y, 1)
            ))
        current_q = None
        current_part = None
        part_start = None
        candidate_ends = []

    for pg in sorted(by_page.keys()):
        for ln in by_page[pg]:
            if Q_COL_MIN <= ln.x0 <= Q_COL_MAX:
                m = PART_LABEL_RE.match(ln.text)
                if m:
                    close_current_part()
                    q_num, p_letter = m.groups()
                    current_q = q_num
                    current_part = p_letter
                    part_start = (pg, ln.y0)
                    continue

            if (current_part is not None and
                MARKS_COL_MIN <= ln.x0 <= MARKS_COL_MAX and
                TOTAL_MARKS_RE.match(ln.text)):
                candidate_ends.append((pg, ln.y0))
                continue

    close_current_part()
    return parts

# ─── MCQ MS Parser ───
def is_mcq_header(line: Line) -> bool:
    return (abs(line.y0 - MCQ_HEADER_Y) < 2.0 and
            line.text in ('Question', 'Answer', 'Marks'))

def is_mcq_footer(line: Line) -> bool:
    return line.y0 > MCQ_FOOTER_Y and ('Cambridge' in line.text or 'Page' in line.text)

def filter_mcq_lines(lines: List[Line]) -> List[Line]:
    out = []
    for ln in lines:
        if is_mcq_header(ln) or is_mcq_footer(ln):
            continue
        out.append(ln)
    return out

def extract_mcq_parts(lines: List[Line]) -> List[PartCoord]:
    """MCQ MS: each row = one question. No parts. Output part=''."""
    by_page = {}
    for ln in lines:
        by_page.setdefault(ln.page, []).append(ln)
    for pg in by_page:
        by_page[pg].sort(key=lambda l: l.y0)

    parts = []
    for pg in sorted(by_page.keys()):
        page_lines = by_page[pg]
        # Group by question number (Question column)
        q_lines = [ln for ln in page_lines if MCQ_Q_COL_MIN <= ln.x0 <= MCQ_Q_COL_MAX and ln.text.isdigit()]
        q_lines.sort(key=lambda l: l.y0)

        for i, q_line in enumerate(q_lines):
            q_num = q_line.text
            start_y = q_line.y0
            # End y: next question's start_y - small gap, or page end
            if i + 1 < len(q_lines):
                end_y = q_lines[i + 1].y0 - 2.0
            else:
                # Last question on page: use footer y or marks column y
                marks_lines = [ln for ln in page_lines
                               if MCQ_MARKS_COL_MIN <= ln.x0 <= MCQ_MARKS_COL_MAX]
                if marks_lines:
                    end_y = max(ln.y0 for ln in marks_lines)
                else:
                    end_y = start_y + 20.0  # fallback

            parts.append(PartCoord(
                question=q_num,
                part="",
                start_page=pg,
                start_y=round(start_y, 1),
                end_page=pg,
                end_y=round(end_y, 1)
            ))
    return parts

# ─── Unified Entry Point ───
def parse_ms(content: str, question_type: QuestionType = "structured") -> List[PartCoord]:
    """Parse mark scheme lines and return part coordinates."""
    lines = parse_lines_ms(content)

    if question_type == "structured":
        content_lines = filter_structured_lines(lines)
        return extract_structured_parts(content_lines)
    elif question_type == "mcq":
        content_lines = filter_mcq_lines(lines)
        return extract_mcq_parts(content_lines)
    else:
        raise ValueError(f"Unknown question_type: {question_type}")

# ─── CLI ───
# find_ms_coords
def find_ms_coords(ms_lines: str, question_type: QuestionType = "structured"):
    parts = parse_ms(ms_lines, question_type)

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

    with open('datapipline/pastpaperspipline/coords/ms_coords.json', 'w') as f:
        json.dump(out, f, indent=2)
    print("\nSaved to ms_coords.json")