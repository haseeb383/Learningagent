import re
from dataclasses import dataclass
from typing import List

Q_NUM_X_MIN, Q_NUM_X_MAX = 48.0, 51.0
PART_LABEL_X_MIN, PART_LABEL_X_MAX = 71.0, 75.0
SUBPART_X_MIN, SUBPART_X_MAX = 88.0, 98.0

Q_NUM_RE = re.compile(r'^(\d+)')
PART_LABEL_RE = re.compile(r'^\(([a-z])\)')
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

with open(r"D:\chrome download\importantfiles\learningagent/lines_qp.txt", 'r') as file:
  lines = file.read()

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

def _is_noise(text: str) -> bool:
  t = text.strip().lower()
  if t in NOISE_EXACT:
    return True
  for pat in NOISE_PATTERNS:
    if pat.search(t):
      return True
  return False

def _check_context_upward(lines: List[Line], line: Line):
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
  return start_y

def _state_coords_end_of_part(cq, cp, csp, start_line, end_line, lines):
  if csp:
    pass
  elif not cp:
    return None
  else:
    start_y = _find_start_y(lines, start_line)
    end_y = end_line.y0 - 10
    start_page  = start_line.page
    end_page = end_line.page
    question = cq
    part = cp
    coordinates = PartCoord(question, part, start_page, start_y, end_page, end_y)
    return coordinates

def _state_coords_end_of_question():
  pass


def parse_qp(lines):
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
      current_question = _check_for_question_number(line)
      current_part = None
      current_subpart = None
      current_question_start_line = line

    part_found = _find_part(line) or current_part
    if part_found != current_part:
      coordinates = _state_coords_end_of_part(current_question, current_part, current_subpart, current_part_start_line, line, lines)
      if coordinates:
        parts.append(coordinates)
      current_part = _find_part(line)
      current_part_start_line = line
      current_subpart = None

    subpart_found = _find_subpart(line) or current_subpart
    if subpart_found != current_subpart:
      current_subpart = _find_subpart(line)
      current_subpart_start_line = line

    if counter > 300:
      break
    counter += 1
  return parts


lines = get_data_from_lines(lines)
# print(lines[16])
# print(lines[287])
# for index, line in enumerate(lines):
#   if line.page == 9 and line.x0 == 72.3 and line.y0 == 297.4:
#     print(f"the line for the label of part c of question 4 is found it is line number {index}")
# print(check_context_upward(lines, lines[287]))
# print(_find_part(lines[19]))
print(parse_qp(lines))
# print(_state_coords_end_of_part(1, 'a', None, lines[19], lines[33], lines))
# print(_check_context_upward(lines, lines[16]))
# lines = filter_content_lines(lines)