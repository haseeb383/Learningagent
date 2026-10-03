import re
import json
from dataclasses import dataclass
from typing import List, Tuple, Optional

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
STEM_X_MIN, STEM_X_MAX = 71.0, 75.0         # Stem text at x≈72.3

HEADER_Y = 63.4
FOOTER_Y = 780.0
PAGE_NUM_X = 290.0
PART_GAP = 10.0

# Regex patterns
Q_NUM_RE = re.compile(r'^\d+$')
PART_LABEL_RE = re.compile(r'^\(([a-z])\)')    # Matches (a), (a) Find..., (b) Calculate...
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

def parse_structured_qp(content: str) -> List[PartCoord]:
    """Single-pass parser with context-aware boundary detection."""
    lines = parse_lines_qp(content)
    lines = filter_content_lines(lines)
    lines.sort(key=lambda ln: (ln.page, ln.y0))

    parts = []
    current_q = None
    q_start_page = 0
    q_start_y = 0.0
    current_part = None
    part_start_page = 0
    part_start_y = 0.0
    pending_part_end = None  # (page, y) where previous part should end

    def close_part(end_page: int, end_y: float):
        nonlocal current_part, part_start_page, part_start_y
        if current_part is not None:
            # Multi-page fix: if part ends on different page than it started,
            # end it at FOOTER_Y (780) on the START page
            if end_page != part_start_page:
                end_page = part_start_page
                end_y = FOOTER_Y
            parts.append(PartCoord(
                question=current_q,
                part=current_part,
                start_page=part_start_page,
                start_y=round(part_start_y, 1),
                end_page=end_page,
                end_y=round(end_y, 1)
            ))
        current_part = None

    i = 0
    while i < len(lines):
        ln = lines[i]
        
        # Question number at x≈49.6
        if Q_NUM_X_MIN <= ln.x0 <= Q_NUM_X_MAX and Q_NUM_RE.match(ln.text):
            # Close previous part at question start (or pending)
            if pending_part_end:
                close_part(pending_part_end[0], pending_part_end[1])
                pending_part_end = None
            else:
                close_part(ln.page, ln.y0 - PART_GAP)
            
            current_q = ln.text
            q_start_page = ln.page
            q_start_y = ln.y0
            current_part = None
            i += 1
            continue
        
        # Part label at x≈72.3
        if PART_LABEL_X_MIN <= ln.x0 <= PART_LABEL_X_MAX:
            m = PART_LABEL_RE.match(ln.text)
            if m:
                part_letter = m.group(1)
                
                # Look upward for context text
                context_y, has_context = find_context_upward(lines, i, ln.page)
                
                if current_part is None:
                    # FIRST PART of question: always starts at question start
                    part_start_page = q_start_page
                    part_start_y = q_start_y
                else:
                    # SUBSEQUENT PART: previous part ends at this part's boundary
                    if has_context:
                        # Previous part ends where this part's context starts
                        close_part(ln.page, context_y - PART_GAP)
                        part_start_page = ln.page
                        part_start_y = context_y
                    else:
                        # No context - previous part ends at part label
                        close_part(ln.page, ln.y0 - PART_GAP)
                        part_start_page = ln.page
                        part_start_y = ln.y0
                
                current_part = part_letter
                i += 1
                continue
        
        i += 1
    
    # Handle pending part end if question ended without next part
    if pending_part_end:
        close_part(pending_part_end[0], pending_part_end[1])
    
    # Close any remaining open part at EOF
    if current_part is not None and current_q is not None:
        end_page, end_y = find_question_content_end(lines, q_start_page)
        # For last part of last question: extend to FOOTER_Y to include answer space
        end_y = FOOTER_Y
        if end_y <= part_start_y:
            end_y = part_start_y + 50.0
        close_part(end_page, end_y)
    
    return parts

def find_structured_qp_coords(qp_lines: str):
    parts = parse_structured_qp(qp_lines)

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

    with open('datapipline/pastpaperspipline/coords/qp_structured_coords.json', 'w') as f:
        json.dump(out, f, indent=2)
    print("\nSaved to qp_structured_coords.json")