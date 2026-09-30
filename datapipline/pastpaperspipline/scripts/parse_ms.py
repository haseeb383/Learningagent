from  extract_lines import extract_lines
import re
import json
from dataclasses import dataclass
from typing import List, Optional

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

# ─── Column X-ranges (from lines_ms.txt analysis) ───
Q_COL_MIN, Q_COL_MAX = 70.0, 90.0      # Question column: part labels at ~82.5-83.3
MARKS_COL_MIN, MARKS_COL_MAX = 458.0, 468.0  # Marks column: total marks at ~462.8
MARK_CODE_MIN, MARK_CODE_MAX = 450.0, 458.0  # Mark codes (M1, A1, B1) at ~452-455

HEADER_Y = 55.7
FOOTER_Y = 550.0
FRONT_MATTER_MAX_PAGE = 8

PART_LABEL_RE = re.compile(r'^(\d+)\(([a-z])\)$')  # e.g., "1(a)", "2(b)"
TOTAL_MARKS_RE = re.compile(r'^\d+$')              # standalone integer: "1", "2", "3", "4", "5"

def parse_lines_ms(content: str) -> List[Line]:
    """Parse lines_ms string (same format as lines_ms.txt) into Line objects."""
    lines = []
    current_page = None
    for raw in content.splitlines():
        raw = raw.rstrip('\n')
        # Page header: "=== Page N ==="
        m = re.match(r'=== Page (\d+) ===', raw)
        if m:
            current_page = int(m.group(1))
            continue
        # Line format: "  y=XXX.X x=XXX.X: text"
        m = re.match(r'\s+y=([\d.]+)\s+x=([\d.]+):\s*(.*)', raw)
        if m and current_page is not None:
            y0 = float(m.group(1))
            x0 = float(m.group(2))
            text = m.group(3).strip()
            if text:  # skip empty
                lines.append(Line(current_page, text, x0, y0, x0 + 10, y0 + 8))
    return lines

def is_header_line(line: Line) -> bool:
    """Header row: 'Question' at x≈70.5, 'Answer' at x≈257, 'Marks' at x≈435, 'Guidance' at x≈603"""
    return (abs(line.y0 - HEADER_Y) < 2.0 and
            line.text in ('Question', 'Answer', 'Marks', 'Guidance'))

def is_footer_line(line: Line) -> bool:
    return line.y0 > FOOTER_Y and ('Cambridge' in line.text or 'Page' in line.text)

def is_front_matter(page: int) -> bool:
    return page <= FRONT_MATTER_MAX_PAGE

def filter_content_lines(lines: List[Line]) -> List[Line]:
    """Drop front matter pages, headers, footers, guidance column."""
    out = []
    for ln in lines:
        if is_front_matter(ln.page):
            continue
        if is_header_line(ln) or is_footer_line(ln):
            continue
        if ln.x0 > 470:  # Guidance column
            continue
        out.append(ln)
    return out

def extract_parts(lines: List[Line]) -> List[PartCoord]:
    """Main extraction: scan lines in page order, then y-order.
    For each part, collect ALL candidate end markers (standalone int at x≈462.8)
    and use the LAST one before the next part starts.
    """
    by_page = {}
    for ln in lines:
        by_page.setdefault(ln.page, []).append(ln)
    for pg in by_page:
        by_page[pg].sort(key=lambda l: l.y0)

    parts = []
    current_q = None
    current_part = None
    part_start = None  # (page, y)
    candidate_ends = []  # list of (page, y) for current part

    def close_current_part():
        nonlocal current_q, current_part, part_start, candidate_ends
        if current_part is not None and candidate_ends:
            # Use the LAST candidate end
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
            # Part start: label like "1(a)" in Question column
            if Q_COL_MIN <= ln.x0 <= Q_COL_MAX:
                m = PART_LABEL_RE.match(ln.text)
                if m:
                    # Close previous part before starting new one
                    close_current_part()
                    q_num, p_letter = m.groups()
                    current_q = q_num
                    current_part = p_letter
                    part_start = (pg, ln.y0)
                    continue

            # Candidate end: standalone integer in Marks column (total marks)
            if (current_part is not None and
                MARKS_COL_MIN <= ln.x0 <= MARKS_COL_MAX and
                TOTAL_MARKS_RE.match(ln.text)):
                candidate_ends.append((pg, ln.y0))
                continue

    # Close any remaining open part at end of document
    close_current_part()

    return parts

def main(ms_lines):
    lines = parse_lines_ms(ms_lines)
    content_lines = filter_content_lines(lines)
    parts = extract_parts(content_lines)

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
    with open('datapipline/pastpaperspipline/scripts/ms_coords.json', 'w') as f:
        json.dump(out, f, indent=2)
    print("\nSaved to ms_coords.json")

if __name__ == '__main__':
    pdf_path = "datapipline/pastpaperspipline/scripts/9709_w25_ms_55.pdf"
    lines = extract_lines(pdf_path)
    main(lines)
