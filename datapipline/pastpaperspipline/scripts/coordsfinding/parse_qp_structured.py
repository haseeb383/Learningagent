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

# ─── Column X-ranges (from instructions.md & lines_qp.txt) ───
Q_NUM_X_MIN, Q_NUM_X_MAX = 48.0, 51.0       # Question number at x≈49.6
PART_LABEL_X_MIN, PART_LABEL_X_MAX = 71.0, 75.0  # Part labels (a)(b) at x≈72.3
SUBPART_LABEL_X_MIN, SUBPART_LABEL_X_MAX = 94.0, 98.0  # Sub-parts (i)(ii) at x≈95
STEM_X_MIN, STEM_X_MAX = 71.0, 75.0         # Stem text at x≈72.3
MARK_BOX_X_MIN, MARK_BOX_X_MAX = 530.0, 535.0  # Mark boxes [n] at x≈532.3
DOTTED_LINE_X_MIN, DOTTED_LINE_X_MAX = 94.0, 98.0  # Dotted lines at x≈95
CHOICE_A_X_MIN, CHOICE_A_X_MAX = 70.0, 75.0  # Choice labels A/B/C/D

HEADER_Y = 63.4
FOOTER_Y = 790.0
PAGE_NUM_X = 290.0  # Page numbers at x≈294

# Regex patterns
Q_NUM_RE = re.compile(r'^\d+$')
PART_LABEL_RE = re.compile(r'^\(([a-z])\)')
SUBPART_LABEL_RE = re.compile(r'^\(([ivx]+)\)$')
MARK_BOX_RE = re.compile(r'^\[\d+\]$')
DOTTED_LINE_RE = re.compile(r'^\.+$')
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
    if line.y0 < HEADER_Y and ('Cambridge' in line.text or 'UCLES' in line.text):
        return True
    if line.y0 > FOOTER_Y and ('Cambridge' in line.text or 'Page' in line.text or 'Trace' in line.text or 'PapaCambridge' in line.text):
        return True
    if 'DO NOT WRITE' in line.text:
        return True
    if 'BLANK PAGE' in line.text:
        return True
    return False

def is_page_number(line: Line) -> bool:
    """Page numbers at x≈294, y≈37-38."""
    return (abs(line.x0 - PAGE_NUM_X) < 10 and
            Q_NUM_RE.match(line.text) and
            line.y0 < 50)

def filter_content_lines(lines: List[Line]) -> List[Line]:
    """Remove headers, footers, page numbers, margin text."""
    out = []
    for ln in lines:
        if is_header_footer(ln) or is_page_number(ln):
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
    # Sort by page then y
    starts.sort(key=lambda q: (q.page, q.y))
    return starts

@dataclass
class PartLabel:
    part: str
    page: int
    y: float

def find_part_labels(lines: List[Line]) -> List[PartLabel]:
    """Find all part labels (a)(b)(c) at x≈72.3."""
    labels = []
    for ln in lines:
        if PART_LABEL_X_MIN <= ln.x0 <= PART_LABEL_X_MAX:
            m = PART_LABEL_RE.match(ln.text)
            if m:
                labels.append(PartLabel(m.group(1), ln.page, ln.y0))
    labels.sort(key=lambda p: (p.page, p.y))
    return labels

def find_dotted_line_y(lines: List[Line], after_y: float, page: int) -> Optional[float]:
    """Find first dotted line after given y on same page."""
    for ln in lines:
        if ln.page == page and ln.y0 > after_y:
            if (DOTTED_LINE_X_MIN <= ln.x0 <= DOTTED_LINE_X_MAX and
                DOTTED_LINE_RE.match(ln.text)):
                return ln.y0
    return None

def find_mark_box_y(lines: List[Line], after_y: float, page: int) -> Optional[float]:
    """Find mark box [n] after given y on same page."""
    for ln in lines:
        if ln.page == page and ln.y0 > after_y:
            if (MARK_BOX_X_MIN <= ln.x0 <= MARK_BOX_X_MAX and
                MARK_BOX_RE.match(ln.text)):
                return ln.y0
    return None

def trim_dotted_lines(parts: List[PartCoord], lines: List[Line]) -> List[PartCoord]:
    """Post-process: crop part end_y to before dotted lines if present."""
    trimmed = []
    for p in parts:
        end_y = p.end_y
        # Look for dotted line between start_y and end_y on same page
        dotted_y = find_dotted_line_y(lines, p.start_y, p.start_page)
        if dotted_y and dotted_y < end_y:
            # Also check for mark box before dotted line
            mark_y = find_mark_box_y(lines, p.start_y, p.start_page)
            if mark_y and mark_y < dotted_y:
                end_y = mark_y
            else:
                end_y = dotted_y - 2.0
        trimmed.append(PartCoord(p.question, p.part, p.start_page, p.start_y, p.end_page, end_y))
    return trimmed

def parse_structured_qp(content: str, question_type: QuestionType = "structured") -> List[PartCoord]:
    """Main entry: parse structured question paper lines -> part coordinates."""
    if question_type != "structured":
        raise ValueError(f"Expected 'structured', got '{question_type}'")

    lines = parse_lines_qp(content)
    lines = filter_content_lines(lines)

    # Pass 1: Find question boundaries
    q_starts = find_question_starts(lines)
    if not q_starts:
        return []

    # Validate sequential question numbers
    q_nums = [int(q.number) for q in q_starts]
    if q_nums != list(range(1, len(q_nums) + 1)):
        print(f"WARNING: Question numbers not sequential: {q_nums}")

    parts = []

    for i, q_start in enumerate(q_starts):
        q_num = q_start.number
        q_page = q_start.page
        q_y = q_start.y

        # Question end: next question start or page end
        if i + 1 < len(q_starts):
            next_q = q_starts[i + 1]
            q_end_page = next_q.page
            q_end_y = next_q.y - 2.0
        else:
            # Last question: use footer or last content line
            q_end_page = q_page
            page_lines = [ln for ln in lines if ln.page == q_page]
            if page_lines:
                q_end_y = max(ln.y0 for ln in page_lines)
            else:
                q_end_y = FOOTER_Y

        # Collect lines within this question window
        q_lines = [
            ln for ln in lines
            if (ln.page > q_page or (ln.page == q_page and ln.y0 >= q_y)) and
               (ln.page < q_end_page or (ln.page == q_end_page and ln.y0 <= q_end_y))
        ]

        # Pass 2: Find part labels within question
        part_labels = find_part_labels(q_lines)

        if not part_labels:
            # Single-part question (no (a) label)
            parts.append(PartCoord(
                question=q_num,
                part="",
                start_page=q_page,
                start_y=q_y,
                end_page=q_end_page,
                end_y=q_end_y
            ))
            continue

        # Create part windows
        for j, part_label in enumerate(part_labels):
            part_letter = part_label.part

            if j == 0:
                # First part (a): start at question number (includes stem)
                start_page = q_page
                start_y = q_y
            else:
                start_page = part_label.page
                start_y = part_label.y

            # Part end: next part label or question end
            if j + 1 < len(part_labels):
                next_part = part_labels[j + 1]
                end_page = next_part.page
                end_y = next_part.y - 2.0
            else:
                end_page = q_end_page
                end_y = q_end_y

            parts.append(PartCoord(
                question=q_num,
                part=part_letter,
                start_page=start_page,
                start_y=round(start_y, 1),
                end_page=end_page,
                end_y=round(end_y, 1)
            ))

    # Optional: trim dotted lines
    parts = trim_dotted_lines(parts, lines)

    return parts

def main(qp_lines: str, question_type: QuestionType = "structured"):
    parts = parse_structured_qp(qp_lines, question_type)
    print(f"Extracted {len(parts)} parts (type={question_type})")

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
    print(json.dumps(out, indent=2))

    with open('datapipline/pastpaperspipline/scripts/qp_structured_coords.json', 'w') as f:
        json.dump(out, f, indent=2)
    print("\nSaved to qp_structured_coords.json")

if __name__ == '__main__':
    pdf_path = "datapipline/pastpaperspipline/downlaods/9709_w25_qp_55.pdf"
    lines = extract_lines(pdf_path)
    main(lines)