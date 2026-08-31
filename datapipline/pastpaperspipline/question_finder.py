import re
import fitz

QUESTION_NUMBER_X0 = 49.6
X0_TOLERANCE = 2.0
NUMBER_PATTERN = re.compile(r"^(\d{1,2})\b")


def extract_lines(pdf_path: str) -> list[dict]:
  doc = fitz.open(pdf_path)
  pages_out = []

  for page_index in range(len(doc)):
    page = doc[page_index]
    raw = page.get_text("dict")

    lines_out = []
    for block in raw["blocks"]:
      if block.get("type") != 0:
        continue
      for line in block["lines"]:
          spans = line["spans"]
          if not spans:
            continue
          text = "".join(s["text"] for s in spans).strip()
          if not text:
            continue
          x0, y0, x1, y1 = line["bbox"]
          lines_out.append(
            {"text": text, "x0": round(x0, 1), "y0": round(y0, 1),
            "x1": round(x1, 1), "y1": round(y1, 1)}
          )

    lines_out.sort(key=lambda l: (l["y0"], l["x0"]))
    pages_out.append({"page_number": page_index + 1, "lines": lines_out})

  doc.close()
  return pages_out


def is_scanned_pdf(pdf_path: str, sample_pages: int = 3, min_chars_per_page: int = 30) -> bool:
  doc = fitz.open(pdf_path)
  pages_to_check = min(sample_pages, len(doc))
  total_chars = sum(len(doc[i].get_text("text").strip()) for i in range(pages_to_check))
  doc.close()
  if pages_to_check == 0:
    return False
  return (total_chars / pages_to_check) < min_chars_per_page


def find_question_starts(
  pages: list[dict],
  question_number_x0: float = QUESTION_NUMBER_X0,
  x0_tolerance: float = X0_TOLERANCE,
) -> list[dict]:
  results = []
  for page in pages:
    for line in page["lines"]:
      if abs(line["x0"] - question_number_x0) > x0_tolerance:
        continue
      match = NUMBER_PATTERN.match(line["text"])
      if not match:
        continue
      results.append({
        "question_number": match.group(1),
        "page_number": page["page_number"],
        "y0": line["y0"],
        }
      )
  return results


def run_pipeline(
  pdf_path: str,
  question_number_x0: float = QUESTION_NUMBER_X0,
  x0_tolerance: float = X0_TOLERANCE,
  y_padding: float = 10.0,
) -> list[dict]:
  if is_scanned_pdf(pdf_path):
    print(f"[{pdf_path}] This PDF appears to be scanned (no reliable "
          f"text layer). Skipping for now.")
    return []

  pages = extract_lines(pdf_path)
  matches = find_question_starts(pages, question_number_x0, x0_tolerance)
  matches.sort(key=lambda m: (m["page_number"], m["y0"]))

  if not matches:
    print(f"[{pdf_path}] No questions found. Check question_number_x0 "
      f"is correct for this paper.")
    return []
  expected = None
  for m in matches:
    num = int(m["question_number"])
    if expected is not None and num != expected:
      print(f"[{pdf_path}] Sequence warning: expected {expected}, "
        f"got {num} (page {m['page_number']}, y0={m['y0']}).")
    expected = num + 1

  total_pages = pages[-1]["page_number"]
  final = []
  for i, q in enumerate(matches):
    start_page = q["page_number"]
    start_y = max(q["y0"] - y_padding, 0)

    if i + 1 < len(matches):
      nxt = matches[i + 1]
      end_page, end_y = nxt["page_number"], max(nxt["y0"] - y_padding, 0)
    else:
      end_page, end_y = total_pages, None

    final.append({
      "question_number": q["question_number"],
      "start_page": start_page,
      "start_y": start_y,
      "end_page": end_page,
      "end_y": end_y,
      }
    )

  return final