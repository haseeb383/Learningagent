import re
import json
from dataclasses import dataclass
from typing import List

Q_NUM_X_MIN, Q_NUM_X_MAX = 48.0, 51.0
PART_LABEL_X_MIN, PART_LABEL_X_MAX = 71.0, 75.0
SUBPART_X_MIN, SUBPART_X_MAX = 88.0, 98.0
CONTENT_TOP_Y = 60.0

Q_NUM_RE = re.compile(r'^(\d+)')
PART_LABEL_RE = re.compile(r'^\(([a-z])\)(?![ivx])')
SUBPART_RE = re.compile(r'^\(([ivx]+)\)')
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

NOISE_EXACT = {
  ',\x01\x01\x01\x01\t\x01\x01\x01\x01\x01\x01\x01\x04,',
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

def _find_part(line):
  matches = None
  if _find_subpart(line) is not None:
    return None
  matches = PART_LABEL_RE.search(line.text)
  if matches:
    return matches.group(1)
  return None

def _find_subpart(line):
  matches = None
  matches = SUBPART_RE.search(line.text)
  if matches:
    return matches.group(1)
  return None

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

# this function if the parser comes accross a question number
def _state_coords_end_of_question(cq, cp, csp, start_line_question, start_line_part, start_line_subpart, end_line, lines):
  if cq:
    # if there is a question going on and there is no sup part or part and the parser comes accross question number closing a question
    if not cp and not csp:
      start_y = start_line_question.y0
      end_y = end_line.y0 - 10
      start_page = start_line_question.page
      end_page = end_line.page
      question = cq
      part = ''
      coordinates = PartCoord(question, part, start_page, start_y, end_page, end_y)
      return coordinates
    # if there is part going on but no subpart going on and the parser comes accross a question number closing a part
    elif cp and not csp:
      start_y = _find_start_y(lines, start_line_part)
      end_y = end_line.y0 - 10
      start_page = start_line_part.page
      end_page = end_line.page
      question = cq
      part = cp
      coordinates = PartCoord(question, part, start_page, start_y, end_page, end_y)
      return coordinates
    # if there is a subpart going on inside a part and the parser comes accross a question number closing a subpart
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

# this function if a parser comes accross a part label
def _state_coords_end_of_part(cq, cp, csp, start_line_part, start_line_subpart, end_line, lines):
  if cq and cp:
    # if there is a part going on but no sub part and the parser finds a part lable closing a part
    if cp and not csp:
      start_y = _find_start_y(lines, start_line_part)
      end_y = _find_end_y(lines, end_line)
      start_page  = start_line_part.page
      end_page = end_line.page
      question = cq
      part = cp
      coordinates = PartCoord(question, part, start_page, start_y, end_page, end_y)
      return coordinates
    # if there is a subpart going on and the parser finds a part label close a subpart
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

# this function if the parser comes accross subpart label
def _state_coords_end_of_subpart(cq, cp, csp, start_line_part, start_line_subpart, end_line, lines):
  # if there is no subpart and the parser comes accross a subapart
  if csp:
    if cq and cp and csp != 'i':
      # if there is subpart going on and the parser finds a sub part closing a subpart
      # print(f"there is subpart going on and now it is closing this is where it started {start_line_subpart}")
      start_y = start_line_subpart.y0
      end_y = end_line.y0 - 10
      start_page  = start_line_subpart.page
      end_page = end_line.page
      question = cq
      part = cp + ')' + csp
      coordinates = PartCoord(question, part, start_page, start_y, end_page, end_y)
      return coordinates
    elif cq and cp and csp == 'i':
      # if there is subpart going on and the parser finds a sub part closing a subpart
      # print(f"there is a part going on and this is the first subpart of the part {csp}")
      start_y = _find_start_y(lines, start_line_part)
      end_y = end_line.y0 - 10
      start_page  = start_line_part.page
      end_page = end_line.page
      question = cq
      part = cp + ')' + csp
      coordinates = PartCoord(question, part, start_page, start_y, end_page, end_y)
      return coordinates   
  return None


def parse_question_paper(lines):
  empty_page_counter = 0
  current_page = lines[0].page
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
      # print(f"question found {current_question} at line {current_question_start_line}")

    part_found = _find_part(line) or current_part
    if part_found != current_part:
      coordinates = _state_coords_end_of_part(current_question, current_part, current_subpart, current_part_start_line, current_subpart_start_line, line, lines)
      if coordinates:
        parts.append(coordinates)
      current_part = _find_part(line)
      current_part_start_line = line
      current_subpart = None
      # print(f"part found {current_part} at line {current_part_start_line}")

    subpart_found = _find_subpart(line) or current_subpart
    if subpart_found != current_subpart:
      # print(f"creating another coordinate set here is the start line {current_subpart_start_line}")
      coordinates = _state_coords_end_of_subpart(current_question, current_part, current_subpart, current_part_start_line, current_subpart_start_line, line, lines)
      if coordinates:
        parts.append(coordinates)
      current_subpart = _find_subpart(line)
      current_subpart_start_line = line
      # print(f"sub part found {current_subpart} at line {current_subpart_start_line}")

    # if counter > 130:
    #   break
    # counter += 1

    if line.page != current_page:
      current_page = line.page
      if len(parts) == 0:
        empty_page_counter += 1
      else:
        empty_page_counter = 0
      if empty_page_counter > 2:
        break
  return parts

def parse_qp(lines):
  lines = get_data_from_lines(lines)
  parts = parse_question_paper(lines)
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

# with open(r'D:\chrome download\importantfiles\learningagent/lines_qp_structured.txt', 'r') as file:
#   lines = file.read()
# lines = get_data_from_lines(lines)
# print(lines[123])
# print(parse_question_paper(lines[122:]))
# print(_find_subpart(Line(page=5, text='(i) State the feature of the graph that represents the distance travelled by the car between', x0=96.0, y0=63.8, x1=106.0, y1=71.8)))
# print(_find_part(Line(page=5, text='(i) State the feature of the graph that represents the distance travelled by the car between', x0=96.0, y0=63.8, x1=106.0, y1=71.8)))