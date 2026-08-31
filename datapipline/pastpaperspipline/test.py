import fitz
import numpy as np
from PIL import Image
import json
import os
from question_finder import run_pipeline

DPI = 200
INK_DARKNESS_CUTOFF = 245
INK_ROW_THRESHOLD = 0.006
CROP_PADDING_PX = 8
MIN_ISLAND_GAP_PX = 18
SEPARATOR_HEIGHT_PX = 14
SEPARATOR_COLOR = (235, 235, 235)

def _render_region(page, y0, y1, dpi=DPI):
  zoom = dpi / 72
  mat = fitz.Matrix(zoom, zoom)
  y0 = max(0, y0)
  y1 = min(page.rect.y1, y1)
  if y1 <= y0:
    return None, zoom
  clip = fitz.Rect(page.rect.x0, y0, page.rect.x1, y1)
  pix = page.get_pixmap(matrix=mat, clip=clip)
  img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
  if img.shape[2] == 4:
    img = img[..., :3]
  return img, zoom

def _ink_rows_mask(img):
  gray = img.mean(axis=2)
  dark_fraction_per_row = (gray < INK_DARKNESS_CUTOFF).mean(axis=1)
  return dark_fraction_per_row > INK_ROW_THRESHOLD

def _content_bounds(img, trim_top=True, trim_bottom=True, pad=CROP_PADDING_PX):
  mask = _ink_rows_mask(img)
  rows = np.where(mask)[0]
  if len(rows) == 0:
    return 0, img.shape[0]
  top = rows[0] if trim_top else 0
  bottom = rows[-1] + 1 if trim_bottom else img.shape[0]
  top = max(0, top - pad)
  bottom = min(img.shape[0], bottom + pad)
  return top, bottom

def _find_islands(img, min_gap_px=MIN_ISLAND_GAP_PX):
  mask = _ink_rows_mask(img)
  rows = np.where(mask)[0]
  if len(rows) == 0:
    return []
  islands = []
  start = rows[0]
  prev = rows[0]
  for r in rows[1:]:
    if r - prev > min_gap_px:
      islands.append((int(start), int(prev + 1)))
      start = r
    prev = r
  islands.append((int(start), int(prev + 1)))
  return islands

def _crop_single_page_question(doc, start_page, start_y, end_y):
  page = doc[start_page]
  img, zoom = _render_region(page, start_y, end_y)
  if img is None:
    return None
  top, bottom = _content_bounds(img, trim_top=True, trim_bottom=True)
  cropped = img[top:bottom]
  return cropped


def _crop_multi_page_question(doc, start_page, start_y, end_page, end_y):
  slices = []
  for pno in range(start_page, end_page + 1):
    page = doc[pno]
    if pno == start_page:
      y0, y1 = start_y, page.rect.y1
      trim_top, trim_bottom = True, True
    elif pno == end_page:
      y0, y1 = 0, end_y
      trim_top, trim_bottom = True, True
    else:
      y0, y1 = 0, page.rect.y1
      trim_top, trim_bottom = True, True

    img, zoom = _render_region(page, y0, y1)
    if img is None:
      continue
    top, bottom = _content_bounds(img, trim_top=trim_top, trim_bottom=trim_bottom)
    piece = img[top:bottom]
    if piece.shape[0] > 0:
      slices.append(piece)

  if not slices:
    return None
  if len(slices) == 1:
    return slices[0]

  width = max(s.shape[1] for s in slices)
  total_height = sum(s.shape[0] for s in slices) + SEPARATOR_HEIGHT_PX * (len(slices) - 1)
  canvas = np.full((total_height, width, 3), 255, dtype=np.uint8)

  y_cursor = 0
  for i, s in enumerate(slices):
    h, w = s.shape[:2]
    canvas[y_cursor:y_cursor + h, 0:w] = s
    y_cursor += h
    if i != len(slices) - 1:
      canvas[y_cursor:y_cursor + SEPARATOR_HEIGHT_PX, :] = SEPARATOR_COLOR
      y_cursor += SEPARATOR_HEIGHT_PX

  return canvas


def crop_question(doc, q):
  start_page = q["start_page"] - 1 if q.get("_one_indexed_pages", True) else q["start_page"]
  end_page = q["end_page"] - 1 if q.get("_one_indexed_pages", True) else q["end_page"]

  if start_page == end_page:
    img = _crop_single_page_question(doc, start_page, q["start_y"], q["end_y"])
  else:
    img = _crop_multi_page_question(doc, start_page, q["start_y"], end_page, q["end_y"])
  return img

def chunk_questions(pdf_path, questions, output_dir, doc_id=None, page_numbers_are_1_indexed=True):
  os.makedirs(output_dir, exist_ok=True)
  if doc_id is None:
    doc_id = os.path.splitext(os.path.basename(pdf_path))[0]

  doc = fitz.open(pdf_path)
  results = []

  for q in questions:
    q = dict(q)  # don't mutate caller's dict
    q["_one_indexed_pages"] = page_numbers_are_1_indexed

    img = crop_question(doc, q)
    qnum = str(q["question_number"]).replace(" ", "_")

    if img is None or img.shape[0] == 0:
      print(f"[warn] question {qnum}: no content detected, skipping")
      continue

    islands = _find_islands(img)

    filename = f"{doc_id}_q{qnum}.png"
    out_path = os.path.join(output_dir, filename)
    Image.fromarray(img).save(out_path)

    results.append({
      "question_number": q["question_number"],
      "source_pdf": pdf_path,
      "image_path": out_path,
      "start_page": q["start_page"],
      "end_page": q["end_page"],
      "pixel_height": int(img.shape[0]),
      "pixel_width": int(img.shape[1]),
      "content_islands_px": islands,
    })

  meta_path = os.path.join(output_dir, f"{doc_id}_metadata.json")
  with open(meta_path, "w") as f:
    json.dump(results, f, indent=2)

  doc.close()
  return results

if __name__ == "__main__":
    pdf_path = "datapipline/pastpaperspipline/downlaods/9709_m26_qp_62.pdf"
    questions = run_pipeline(pdf_path=pdf_path)
    output_dir = "datapipline/pastpaperspipline/question_images"
    chunk_questions(pdf_path=pdf_path, questions=questions, output_dir=output_dir)