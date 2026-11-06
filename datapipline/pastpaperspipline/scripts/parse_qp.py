import re
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List

Q_NUM_X_MIN, Q_NUM_X_MAX = 48.0, 51.0
PART_LABEL_X_MIN, PART_LABEL_X_MAX = 71.0, 75.0
SUBPART_X_MIN, SUBPART_X_MAX = 88.0, 98.0
CONTENT_TOP_Y = 60.0
BOTTOM_Y = 780.0

BLANK_MARKERS = ('blank page',)
HEADING_MARKERS = ('additional page',)
IGNORABLE_RE = re.compile(r'^\[?\s*turn over', re.I)

Q_NUM_RE = re.compile(r'^(\d+)')
PART_LABEL_RE = re.compile(r'^\(([a-z])\)(?![ivx])')
SUBPART_RE = re.compile(r'^(?:\([a-z]\)\s*)?\(([ivx]+)\)')  # "(i)" or "(b) (i)"
PURE_SUBPART_RE = re.compile(r'^\(([ivx]+)\)')
DOTTED_LINE_RE = re.compile(r'^\.+$')
MARK_BOX_RE = re.compile(r'^\[\d+\]$')

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
  re.compile(r'\.{4,}'),
  re.compile(r'\[\d+\]\s*$'),
  re.compile(r'^\[(total:|turn over)', re.I),
  re.compile(r'do not write in this margin', re.I),
  re.compile(r',\x01+\t\x01+[\x00-\x1f],'),
  re.compile(r'^\* \d+ \*$'),
  re.compile(r'^\?+$'),
  re.compile(r'^\.+$'),
  re.compile(r'^\[\d+\]$'),
  re.compile(r'^\d+/\d+/\w+/\d+$'),
  re.compile(r'paper code \d+/\d+/\w+/\d+', re.I),
  re.compile(r'cambridge', re.I),
  re.compile(r'uccles', re.I),
  re.compile(r'papa', re.I),
  re.compile(r'trace id', re.I),
  re.compile(r're-uploading', re.I),
  re.compile(r'permission', re.I),
  re.compile(r'acknowledgement', re.I),
]

def get_data_from_lines(content: str) -> List[Line]:
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

def _is_noise(text):
  t = text.strip().lower()
  if t in NOISE_EXACT:
    return True
  for pat in NOISE_PATTERNS:
    if pat.search(t):
      return True
  return False

def _check_context_upward(lines, line):
  index = lines.index(line)
  context_start_y = None
  found_noise = False
  counter = 1
  while not found_noise:
    previous_line = lines[index - counter]
    if _is_noise(previous_line.text):
      context_start_y = lines[index - counter + 1].y0
    if context_start_y:
      found_noise = True
    counter += 1
  return context_start_y

def _norm(text):
  return ' '.join(text.lower().split())

def _looks_blank(real):
  if not real:
    return True
  # no question number, part label, subpart label, or long text on the page
  has_structure = any(
    _check_for_question_number(l) or _find_part(l) or _find_subpart(l) or len(l.text) > 25
    for l in real
  )
  return not has_structure

def _blank_pages(lines):
  by_page = {}
  for l in lines:
    by_page.setdefault(l.page, []).append(l)

  blank = set()
  for p, ls in by_page.items():
    texts = [_norm(l.text) for l in ls]

    # 1) the page announces itself
    if any(m in t for t in texts for m in BLANK_MARKERS) or \
       any(t.startswith(m) for t in texts for m in HEADING_MARKERS):
      blank.add(p)
      continue

    # 2) fallback: nothing real on the page
    real = [
      l for l in ls
      if CONTENT_TOP_Y <= l.y0 <= BOTTOM_Y
      and not _is_noise(l.text)
      and not re.fullmatch(r'\d+', l.text.strip())
      and not IGNORABLE_RE.match(l.text.strip())
    ]
    if _looks_blank(real):
      blank.add(p)
  return blank

def _trim_end(p, blank):
  # part ends "above the first line of the next page" -> really ended on the previous page
  if p.end_page > p.start_page and p.end_y <= CONTENT_TOP_Y + 5:
    p.end_page -= 1
    p.end_y = BOTTOM_Y
    while p.end_page in blank and p.end_page > p.start_page:
      p.end_page -= 1
  return p

def _find_subpart(line):
  m = SUBPART_RE.search(line.text)
  return m.group(1) if m else None

def _find_part(line):
  if PURE_SUBPART_RE.search(line.text):   # line starts with (i)/(ii)... -> not a part
    return None
  m = PART_LABEL_RE.search(line.text)
  return m.group(1) if m else None

def _check_for_question_number(line):
  matches = None
  if line.x0 >= Q_NUM_X_MIN and line.x0 <= Q_NUM_X_MAX:
    matches = Q_NUM_RE.search(line.text)
  if matches:
    return matches.group(0)
  return None

def _find_start_y(lines, start_line):
  start_y = _check_context_upward(lines, start_line) or start_line.y0
  return max(start_y, CONTENT_TOP_Y)

def _find_end_y(lines, end_line):
  y = _check_context_upward(lines, end_line)
  y = (y if y is not None else end_line.y0) - 10
  return max(y, CONTENT_TOP_Y)

def _state_coords_end_of_question(cq, cp, csp, start_line_question, start_line_part, start_line_subpart, end_line, lines):
  if cq:
    if not cp and not csp:
      start_y = start_line_question.y0
      end_y = end_line.y0 - 10
      start_page = start_line_question.page
      end_page = end_line.page
      question = cq
      part = ''
      coordinates = PartCoord(question, part, start_page, start_y, end_page, end_y)
      return coordinates

    elif cp and not csp:
      start_y = _find_start_y(lines, start_line_part)
      end_y = end_line.y0 - 10
      start_page = start_line_part.page
      end_page = end_line.page
      question = cq
      part = cp
      coordinates = PartCoord(question, part, start_page, start_y, end_page, end_y)
      return coordinates

    elif csp:
      start_y = _find_start_y(lines, start_line_subpart)
      end_y = end_line.y0 - 10
      start_page = start_line_subpart.page
      end_page = end_line.page
      question = cq
      part = cp + ')' + csp
      coordinates = PartCoord(question, part, start_page, start_y, end_page, end_y)
      return coordinates
  return None

def _state_coords_end_of_part(cq, cp, csp, start_line_part, start_line_subpart, end_line, lines):
  if cq and cp:
    if cp and not csp:
      start_y = _find_start_y(lines, start_line_part)
      end_y = _find_end_y(lines, end_line)
      start_page  = start_line_part.page
      end_page = end_line.page
      question = cq
      part = cp
      coordinates = PartCoord(question, part, start_page, start_y, end_page, end_y)
      return coordinates
    
    elif csp:
      start_y = _find_start_y(lines, start_line_subpart)
      end_y = end_line.y0 - 10
      start_page  = start_line_subpart.page
      end_page = end_line.page
      question = cq
      part = cp + ')' + csp
      coordinates = PartCoord(question, part, start_page, start_y, end_page, end_y)
      return coordinates
  return None

def _state_coords_end_of_subpart(cq, cp, csp, start_line_part, start_line_subpart, end_line, lines):
  if csp:
    if cq and cp and csp != 'i':
      start_y = start_line_subpart.y0
      end_y = end_line.y0 - 10
      start_page  = start_line_subpart.page
      end_page = end_line.page
      question = cq
      part = cp + ')' + csp
      coordinates = PartCoord(question, part, start_page, start_y, end_page, end_y)
      return coordinates
    
    elif cq and cp and csp == 'i':
      start_y = _find_start_y(lines, start_line_part)
      end_y = end_line.y0 - 10
      start_page  = start_line_part.page
      end_page = end_line.page
      question = cq
      part = cp + ')' + csp
      coordinates = PartCoord(question, part, start_page, start_y, end_page, end_y)
      return coordinates   
  return None

def _state_coords_last_part(cq, cp, csp, start_line_part, start_line_subpart, start_line_question, lines):
  if cq and not cp and not csp:
    start_y = start_line_question.y0
    end_y = 780
    start_page  = start_line_question.page
    end_page = start_line_question.page
    question = cq
    part = ''
    coordinates = PartCoord(question, part, start_page, start_y, end_page, end_y)
    return coordinates
  
  elif cq and cp and not csp:
    start_y = _find_start_y(lines, start_line_part)
    end_y = 780
    start_page  = start_line_part.page
    end_page = start_line_part.page
    question = cq
    part = cp
    coordinates = PartCoord(question, part, start_page, start_y, end_page, end_y)
    return coordinates
  
  elif cq and cp and csp:
    start_y = start_line_subpart.y0
    end_y = 780
    start_page  = start_line_question.page
    end_page = start_line_question.page
    question = cq
    part = cp + ')' + csp
    coordinates = PartCoord(question, part, start_page, start_y, end_page, end_y)
    return coordinates

def parse_question_paper(lines, coord_type="all"):
  lines = get_data_from_lines(lines)
  blank = _blank_pages(lines)
  lines = [l for l in lines if l.page not in blank]
  current_question = None
  current_part = None
  current_subpart = None
  current_question_start_line = None
  current_part_start_line = None
  current_subpart_start_line = None
  parts = []
  counter = 1
  for line in lines:
    question_number_found = _check_for_question_number(line) or current_question
    if question_number_found != current_question:
      coordinates = _state_coords_end_of_question(current_question, current_part, current_subpart, current_question_start_line, current_part_start_line, current_subpart_start_line, line, lines)
      if coordinates:
        parts.append(coordinates)
      current_question = _check_for_question_number(line)
      current_part = None
      current_subpart = None
      current_question_start_line = line

    if coord_type == "all":
      part_found = _find_part(line) or current_part
      if part_found != current_part:
        coordinates = _state_coords_end_of_part(current_question, current_part, current_subpart, current_part_start_line, current_subpart_start_line, line, lines)
        if coordinates:
          parts.append(coordinates)
        current_part = _find_part(line)
        current_part_start_line = line
        current_subpart = None

      subpart_found = _find_subpart(line) or current_subpart
      if subpart_found != current_subpart:
        coordinates = _state_coords_end_of_subpart(current_question, current_part, current_subpart, current_part_start_line, current_subpart_start_line, line, lines)
        if coordinates:
          parts.append(coordinates)
        current_subpart = _find_subpart(line)
        current_subpart_start_line = line

    # if counter > 500:
    #   break
    # counter += 1

  coords = _state_coords_last_part(current_question, current_part, current_subpart, current_part_start_line, current_subpart_start_line, current_question_start_line, lines)
  if coords:
    parts.append(coords)

  # return parts
  return [_trim_end(p, blank) for p in parts]

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

def parse_qp(lines, pdf_path, question_type, coord_type="all"):
  pdf_path = Path(pdf_path)
  pdf_name = pdf_path.stem
  parts = parse_question_paper(lines, coord_type)
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
  with open('datapipline/pastpaperspipline/coords/qp_coords.json', 'w') as f:
      json.dump(out, f, indent=2)
  print("\nSaved to qp_coords.json")
