import re
from pathlib import Path
import json
from dataclasses import dataclass, field
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
    source_pdf: str = ''
    chunk_id: str = ''
    chunk_combination: List[str] = field(default_factory=list)
    question_type: str = ''


# ─── Structured MS Constants ───
Q_COL_MIN, Q_COL_MAX = 70.0, 90.0
TABLE_TOP_Y = 70.0      # below the Question/Answer/Marks header row (~56)
PAGE_BOTTOM_Y = 545.0   # above the footer (~550)
START_PAD = 6.0         # chunk starts a bit above the label (tune to your cropper)
END_PAD = 12.0          # chunk ends a bit below the last line
LABEL_TOL = 3.0         # a line this close above a label belongs to that label
HEADER_WORDS = {'Question', 'Answer', 'Marks'}

# "1", "1(a)", "1(b)(iv)"
LABEL_RE = re.compile(r'^(\d+)(?:\(([a-z])\))?(?:\(([ivx]+)\))?$')

# ─── MCQ MS Constants ───
MCQ_Q_COL_MIN, MCQ_Q_COL_MAX = 70.0, 85.0        # Question number at ~75-78
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
def first_answer_page(lines: List[Line]) -> int:
    """First page that has the Question/Answer header row."""
    rows = {}
    for ln in lines:
        if ln.text in HEADER_WORDS:
            rows.setdefault((ln.page, round(ln.y0)), set()).add(ln.text)
    pages = [pg for (pg, _), words in rows.items() if {'Question', 'Answer'} <= words]
    if not pages:
        raise ValueError("No Question/Answer header row found in mark scheme")
    return min(pages)


def filter_structured_lines(lines: List[Line]) -> List[Line]:
    start = first_answer_page(lines)
    return [ln for ln in lines
            if ln.page >= start and TABLE_TOP_Y <= ln.y0 <= PAGE_BOTTOM_Y]


def _part_name(letter, roman) -> str:
    return ')'.join(x for x in (letter, roman) if x)   # "b)i", "a", ""


def extract_structured_parts(lines: List[Line]) -> List[PartCoord]:
    lines = sorted(lines, key=lambda l: (l.page, l.y0))

    # pass 1: find every label line
    label_of = {}   # id(line) -> (question, part)
    labels = []
    for ln in lines:
        if Q_COL_MIN <= ln.x0 <= Q_COL_MAX:
            m = LABEL_RE.match(ln.text)
            if m:
                q, letter, roman = m.groups()
                label_of[id(ln)] = (q, _part_name(letter, roman))
                labels.append(ln)

    # pass 2: build spans
    spans = []
    cur = None
    li = 0   # number of labels seen so far -> labels[li] is the next label
    for ln in lines:
        key = label_of.get(id(ln))
        if key:
            li += 1
            if cur is None or cur['key'] != key:   # same key = continuation row on next page
                cur = {
                    'key': key,
                    'start_page': ln.page,
                    'start_y': max(ln.y0 - START_PAD, TABLE_TOP_Y),
                    'end_page': ln.page,
                    'end_y': ln.y0 + END_PAD,
                }
                spans.append(cur)
        else:
            # a line sitting just above the next label (same row, y slightly smaller)
            # belongs to that label, not to the part we are in
            nxt = labels[li] if li < len(labels) else None
            if (nxt is not None and nxt.page == ln.page
                    and 0 <= nxt.y0 - ln.y0 <= LABEL_TOL
                    and (cur is None or label_of[id(nxt)] != cur['key'])):
                continue
        if cur is not None:
            cur['end_page'] = ln.page
            cur['end_y'] = min(ln.y0 + END_PAD, PAGE_BOTTOM_Y)

    # safety net: never let a part end below the next part's start on the same page
    for a, b in zip(spans, spans[1:]):
        if a['end_page'] == b['start_page'] and a['end_y'] >= b['start_y']:
            a['end_y'] = b['start_y'] - 1.0

    return [
        PartCoord(
            question=s['key'][0], part=s['key'][1],
            start_page=s['start_page'], start_y=round(s['start_y'], 1),
            end_page=s['end_page'], end_y=round(s['end_y'], 1),
        )
        for s in spans
    ]


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
        q_lines = [ln for ln in page_lines
                   if MCQ_Q_COL_MIN <= ln.x0 <= MCQ_Q_COL_MAX and ln.text.isdigit()]
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
def parse_marchingscheme(content: str, question_type: QuestionType = "structured") -> List[PartCoord]:
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

def enrich(parts, pdf_name):
    by_question = {}
    for i, p in enumerate(parts, start=1):
        p.source_pdf = pdf_name
        part = p.part.replace(")", "").replace("(", "").replace(",", "")
        part = part.replace(" ", "_")
        chunk_structure = f"{pdf_name}_q{p.question}_{part}"
        p.chunk_id = f"{chunk_structure}_{i}"
        by_question.setdefault(p.question, []).append(p.chunk_id)

    for p in parts:
        p.chunk_combination = by_question[p.question]
    return parts


def parse_ms(pdf_path, ms_lines: str, question_type: QuestionType = "structured"):
    parts = parse_marchingscheme(ms_lines, question_type)
    pdf_path = Path(pdf_path)
    pdf_name = pdf_path.stem
    parts = enrich(parts, pdf_name)

    out = [
        {
            "question": p.question,
            "part": p.part,
            "start_page": p.start_page,
            "start_y": p.start_y,
            "end_page": p.end_page,
            "end_y": p.end_y,
            "source_pdf": p.source_pdf,
            "chunk_id": p.chunk_id,
            "chunk_combination": p.chunk_combination,
            "question_type": question_type
        }
        for p in parts
    ]

    with open('datapipline/pastpaperspipline/coords/ms_coords.json', 'w') as f:
        json.dump(out, f, indent=2)
    print("\nSaved to ms_coords.json")
    return parts


# with open(r"D:\chrome download\importantfiles\learningagent/lines_ms.txt", 'r') as file:
#     lines = file.read()
# parts = parse_ms(lines, "structured")
# for p in parts:
#     print(p.question, repr(p.part))