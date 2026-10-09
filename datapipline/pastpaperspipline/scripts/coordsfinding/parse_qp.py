import re
import json
from dataclasses import dataclass
from typing import List, Tuple, Optional, Literal

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

# ─── Column X-ranges ───
Q_NUM_X_MIN, Q_NUM_X_MAX = 48.0, 51.0       # Question number at x≈49.6
PART_LABEL_X_MIN, PART_LABEL_X_MAX = 71.0, 75.0  # Part labels (a)(b) at x≈72.3
SUBPART_X_MIN, SUBPART_X_MAX = 88.0, 98.0      # Subpart labels (i)(ii) at x≈90-96
STEM_X_MIN, STEM_X_MAX = 71.0, 75.0         # Stem text at x≈72.3

HEADER_Y = 63.4
FOOTER_Y = 780.0
PAGE_NUM_X = 290.0
PART_GAP = 10.0
SUBPART_SCAN_LINES = 200              # number of lines to scan for subpart after part label
MCQ_EMPTY_PAGE_STOP = 2               # stop after N consecutive empty pages (no questions)

# Regex patterns
Q_NUM_RE = re.compile(r'^(\d+)')
PART_LABEL_RE = re.compile(r'^\(([a-z])\)')    # Matches (a), (a) Find..., (b) Calculate...
SUBPART_RE = re.compile(r'^\(([ivx]+)\)')      # Matches (i), (ii), (iii), (iv), (v)
DOTTED_LINE_RE = re.compile(r'^\.+$')
MARK_BOX_RE = re.compile(r'^\[\d+\]$')

# Noise detection
NOISE_EXACT = {
    'dfd',
    'do not write in this margin',
    'cambridge university press & assessment',
    'trace id:',
    're-uploading, mirroring or re-hosting this file on any other website or domain is unauthorised and t',
    'licensed for hosting on papacambridge.com only.',
    'papacambridge ?  papacambridge.com',
    'downloaded from papacambridge - https://papacambridge.com/',
}

NOISE_PATTERNS = [
    re.compile(r'^\* \d+ \*$'),                    # * 0000800000008 *
    re.compile(r'^\?+$'),                          # ??????????
    re.compile(r'^\.+$'),                          # ....................
    re.compile(r'^\[\d+\]$'),                      # [3], [1], etc.
    re.compile(r'^\d+/\d+/\w+/\d+$'),              # 9702/22/M/J/26
    re.compile(r'paper code \d+/\d+/\w+/\d+', re.I),
    re.compile(r'cambridge', re.I),
    re.compile(r'uccles', re.I),
    re.compile(r'papa', re.I),
    re.compile(r'trace id', re.I),
    re.compile(r're-uploading', re.I),
    re.compile(r'permission', re.I),
    re.compile(r'acknowledgement', re.I),
]

def is_noise(text: str) -> bool:
    """Check if text is noise (should not be treated as context)."""
    t = text.strip().lower()
    if t in NOISE_EXACT:
        return True
    for pat in NOISE_PATTERNS:
        if pat.search(t):
            return True
    return False

def parse_lines_qp(content: str) -> List[Line]:
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

def is_noise(text: str) -> bool:
    """Check if text is noise (should not be treated as context)."""
    t = text.strip().lower()
    if t in NOISE_EXACT:
        return True
    for pat in NOISE_PATTERNS:
        if pat.search(t):
            return True
    return False

def is_noise_line(line: Line) -> bool:
    """Full noise line filter for headers/footers/page numbers."""
    if line.y0 < HEADER_Y and ('Cambridge' in line.text or 'UCLES' in line.text):
        return True
    if line.y0 > FOOTER_Y and ('Cambridge' in line.text or 'UCLES' in line.text or 'Page' in line.text or 'Trace' in line.text or 'PapaCambridge' in line.text):
        return True
    if 'DO NOT WRITE' in line.text:
        return True
    if 'BLANK PAGE' in line.text:
        return True
    if abs(line.x0 - PAGE_NUM_X) < 10 and Q_NUM_RE.match(line.text) and line.y0 < 50:
        return True
    if is_noise(line.text):
        return True
    return False

def filter_content_lines(lines: List[Line]) -> List[Line]:
    return [ln for ln in lines if not is_noise_line(ln)]

def find_context_upward(lines: List[Line], start_idx: int, current_page: int) -> Tuple[Optional[float], bool]:
    """
    Scan upward from start_idx (exclusive) to find context text at x≈72.3.
    Returns (context_start_y, found_context).
    Stops at: noise line, page change, part label, or end of lines.
    context_start_y is the y of the FIRST line of the context block (furthest from part label).
    """
    context_start_y = None
    
    for i in range(start_idx - 1, -1, -1):
        ln = lines[i]
        if ln.page != current_page:
            break  # Don't cross page boundary upward
        
        # Stop if we hit a part label - context only between parts
        if PART_LABEL_X_MIN <= ln.x0 <= PART_LABEL_X_MAX and PART_LABEL_RE.match(ln.text):
            break
        
        if not (STEM_X_MIN <= ln.x0 <= STEM_X_MAX):
            continue  # Only consider text at x≈72.3
        
        if is_noise(ln.text):
            break  # Hit noise - stop looking
        
        # This line is valid context - record its y (will be the topmost as we scan up)
        if len(ln.text) > 0:
            context_start_y = ln.y0  # Keep updating - last one set is the topmost
    
    return context_start_y, context_start_y is not None
    
    return None, False

def find_subpart_on_line(text: str) -> Optional[str]:
    """Check if part label text contains subpart indicator like '(b) (i)'."""
    # Match patterns like "(b) (i)" or "(b)(i)" or "(b) (i) ..."
    m = re.search(r'\([a-z]\)\s*\(([ivx]+)\)', text)
    if m:
        return m.group(1)
    return None

def find_subpart_downward(lines: List[Line], start_idx: int, max_lines: int) -> Optional[Tuple[str, float]]:
    """Scan downward from part label to find first subpart (i) label.
    Stops at next part label, question number, or max_lines.
    Returns (subpart_letter, y) or None.
    """
    for i in range(start_idx + 1, min(start_idx + max_lines, len(lines))):
        ln = lines[i]
        # Stop at next part label or question number
        if (PART_LABEL_X_MIN <= ln.x0 <= PART_LABEL_X_MAX and PART_LABEL_RE.match(ln.text)) or \
           (Q_NUM_X_MIN <= ln.x0 <= Q_NUM_X_MAX and Q_NUM_RE.match(ln.text)):
            break
        if SUBPART_X_MIN <= ln.x0 <= SUBPART_X_MAX:
            m = SUBPART_RE.match(ln.text)
            if m and m.group(1) == 'i':
                return m.group(1), ln.y0
    return None

def find_last_content_on_page(lines: List[Line], page: int) -> float:
    """Find last non-noise content y on a page (for page boundary)."""
    page_lines = [ln for ln in lines if ln.page == page]
    last_y = 0.0
    for ln in page_lines:
        if (STEM_X_MIN <= ln.x0 <= STEM_X_MAX and len(ln.text) > 5 and not is_noise(ln.text)):
            last_y = max(last_y, ln.y0)
    return last_y if last_y > 0 else FOOTER_Y

def find_question_content_end(lines: List[Line], start_page: int) -> Tuple[int, float]:
    """Find the last page and y with question content for EOF handling."""
    max_page = max(ln.page for ln in lines)
    end_page = start_page
    end_y = 0.0
    for pg in range(start_page, max_page + 1):
        page_lines = [ln for ln in lines if ln.page == pg]
        has_q_content = any(
            (PART_LABEL_X_MIN <= ln.x0 <= PART_LABEL_X_MAX and PART_LABEL_RE.match(ln.text)) or
            (Q_NUM_X_MIN <= ln.x0 <= Q_NUM_X_MAX and Q_NUM_RE.match(ln.text)) or
            (STEM_X_MIN <= ln.x0 <= STEM_X_MAX and len(ln.text) > 5 and not is_noise(ln.text))
            for ln in page_lines
        )
        if has_q_content:
            end_page = pg
            end_y = find_last_content_on_page(lines, pg)
        else:
            break
    return end_page, end_y if end_y > 0 else FOOTER_Y

def parse_qp(content: str, mode: Literal["structured", "mcq"] = "structured") -> List[PartCoord]:
    """Single-pass parser with context-aware boundary detection and subpart support.
    Supports both structured (parts a,b,c) and MCQ (single questions) modes.
    """
    lines = parse_lines_qp(content)
    lines = filter_content_lines(lines)
    lines.sort(key=lambda ln: (ln.page, ln.y0))

    parts = []
    current_q = None
    q_start_page = 0
    q_start_y = 0.0
    current_part = None
    current_subpart = None
    part_start_page = 0
    part_start_y = 0.0
    subpart_start_page = 0
    subpart_start_y = 0.0
    pending_part_end = None  # (page, y) where previous part should end

    # MCQ-specific state
    questions_found = 0
    consecutive_empty_pages = 0
    last_question_page = 0
    questions_on_current_page = 0
    current_page = 0

    def close_part(end_page: int, end_y: float):
        nonlocal current_part, part_start_page, part_start_y
        if current_part is not None:
            parts.append(PartCoord(
                question=current_q,
                part=current_part,
                start_page=part_start_page,
                start_y=round(part_start_y, 1),
                end_page=end_page,
                end_y=round(end_y, 1)
            ))
        current_part = None

    def close_subpart(end_page: int, end_y: float):
        nonlocal current_subpart, subpart_start_page, subpart_start_y
        if current_subpart is not None:
            parts.append(PartCoord(
                question=current_q,
                part=f"{current_part}){current_subpart})",  # e.g., "b)i)"
                start_page=subpart_start_page,
                start_y=round(subpart_start_y, 1),
                end_page=end_page,
                end_y=round(end_y, 1)
            ))
        current_subpart = None

    i = 0
    while i < len(lines):
        ln = lines[i]
        
        # Track page changes for MCQ empty page detection
        if ln.page != current_page:
            # Check if current page had questions (MCQ mode)
            if mode == "mcq":
                if questions_on_current_page > 0:
                    consecutive_empty_pages = 0
                else:
                    if questions_found > 0:
                        consecutive_empty_pages += 1
                        if consecutive_empty_pages >= MCQ_EMPTY_PAGE_STOP:
                            # Stop at last found question's page, y=780
                            close_part(last_question_page, FOOTER_Y)
                            break
                questions_on_current_page = 0
            current_page = ln.page
        
        # Question number at x≈49.6
        if Q_NUM_X_MIN <= ln.x0 <= Q_NUM_X_MAX and Q_NUM_RE.match(ln.text):
            # Close any open subpart first
            if current_subpart is not None:
                close_subpart(ln.page, ln.y0 - PART_GAP)
            elif current_part is not None:
                close_part(ln.page, ln.y0 - PART_GAP)
            elif pending_part_end:
                close_part(pending_part_end[0], pending_part_end[1])
            
            # Extract question number from capture group
            q_match = Q_NUM_RE.match(ln.text)
            current_q = q_match.group(1) if q_match else ln.text
            q_start_page = ln.page
            q_start_y = ln.y0
            current_part = None
            current_subpart = None
            
            # MCQ: track question found
            if mode == "mcq":
                questions_found += 1
                questions_on_current_page += 1
                last_question_page = ln.page
                # For MCQ, the question itself is the "part" (empty string in output)
                current_part = ""  # MCQ questions have empty part
                # Start the question at the question number
                part_start_page = q_start_page
                part_start_y = q_start_y
            
            i += 1
            continue
        
        # Part label at x≈72.3 (structured mode only)
        if mode == "structured" and PART_LABEL_X_MIN <= ln.x0 <= PART_LABEL_X_MAX:
            m = PART_LABEL_RE.match(ln.text)
            if m:
                part_letter = m.group(1)
                
                # Check for subpart (i) on same line
                subpart_on_line = find_subpart_on_line(ln.text)
                
                # If not on same line, scan downward a bit
                if not subpart_on_line:
                    subpart_result = find_subpart_downward(lines, i, SUBPART_SCAN_LINES)
                    if subpart_result:
                        subpart_on_line, _ = subpart_result
                
                # Close any open subpart first
                if current_subpart is not None:
                    close_subpart(ln.page, ln.y0 - PART_GAP)
                elif current_part is not None:
                    close_part(ln.page, ln.y0 - PART_GAP)
                
                # Start new part
                current_part = part_letter
                current_subpart = None
                
                if part_letter == 'a':
                    # First part of question starts at question start
                    part_start_page = q_start_page
                    part_start_y = q_start_y
                else:
                    part_start_page = ln.page
                    part_start_y = ln.y0
                
                # Enter subpart mode if subpart found
                if subpart_on_line:
                    current_subpart = subpart_on_line
                    # First subpart starts at part's start
                    subpart_start_page = part_start_page
                    subpart_start_y = part_start_y
                
                i += 1
                continue
        
        # Subpart label at x≈90-96 (structured mode only)
        if current_subpart is not None and SUBPART_X_MIN <= ln.x0 <= SUBPART_X_MAX:
            m = SUBPART_RE.match(ln.text)
            if m:
                subpart_letter = m.group(1)
                
                # Only create new subpart if the letter CHANGES (e.g., i -> ii)
                # If it's the same letter, it's just the label for the current subpart
                if subpart_letter != current_subpart:
                    # Close previous subpart
                    close_subpart(ln.page, ln.y0 - PART_GAP)
                    
                    # Start new subpart
                    current_subpart = subpart_letter
                    subpart_start_page = ln.page
                    subpart_start_y = ln.y0
                i += 1
                continue
        
        # MCQ: Track questions on current page
        if mode == "mcq" and Q_NUM_X_MIN <= ln.x0 <= Q_NUM_X_MAX and Q_NUM_RE.match(ln.text):
            questions_on_current_page += 1
        
        i += 1
    
    # Handle any remaining open subpart/part at EOF
    if current_subpart is not None and current_q is not None:
        end_page, end_y = find_question_content_end(lines, q_start_page)
        end_y = FOOTER_Y
        if end_y <= subpart_start_y:
            end_y = subpart_start_y + 50.0
        close_subpart(end_page, end_y)
    elif current_part is not None and current_q is not None:
        end_page, end_y = find_question_content_end(lines, q_start_page)
        end_y = FOOTER_Y
        if end_y <= part_start_y:
            end_y = part_start_y + 50.0
        close_part(end_page, end_y)
    elif pending_part_end:
        close_part(pending_part_end[0], pending_part_end[1])
    
    return parts

def find_structured_qp_coords(qp_lines: str, mode="structured"):
    parts = parse_qp(qp_lines, mode)

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

    with open('datapipline/pastpaperspipline/coords/qp_coords.json', 'w') as f:
        json.dump(out, f, indent=2)
    print("\nSaved to qp_coords.json")