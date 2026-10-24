import os
import json
import pdfplumber
from PIL import Image
from pathlib import Path

COORDS_DIR = "datapipline/pastpaperspipline/coords"
CHUNKS_DIR = "datapipline/pastpaperspipline/chunks"

# (top, bottom) used for the middle/continuation pages of a multi-page chunk.
# QP pages are portrait (~842 tall), MS pages are landscape (~595 tall),
# so they need different bounds.
BOUNDS = {
  "qp": (50.0, 780.0),
  "ms": (68.0, 545.0),   # below the Question/Answer header row, above the footer
}


def normalize_mcq_coords(coords):
  for coord in coords:
    if coord['start_y'] == coord['end_y']:
      coord['end_y'] += 20
    coord['start_y'] -= 5
  return coords

def _noramlize_coordinates(coords):
  # question-paper only: the QP parser's coords need a small upward shift
  for coord in coords:
    coord['start_y'] -= 10
    if coord['end_y'] <= 55:
      coord["end_page"] -= 1
      coord['end_y'] = 780
  return coords

def _generate_file_name(pdf_name, coord):
  part = coord["part"].replace(")", "").replace("(", "").replace(",", "")
  part = part.replace(" ", "_")
  return f"{pdf_name}_q{coord['question']}_{part}"

def _save_coords(pdf_name, coords):
  file_name = pdf_name + ".json"
  storing_path = COORDS_DIR + f"/{file_name}"
  with open(storing_path, 'w') as f:
    json.dump(coords, f, indent=2)
  print(f"save_coords of file {pdf_name} to {file_name}")

def _create_segment_coords(coord, bounds=BOUNDS["qp"]):
  top, bottom = bounds
  segment_coords = [{'page': coord['start_page'], 'start_y': coord['start_y'], 'end_y': bottom}]
  for pg in range(coord['start_page'] + 1, coord['end_page'] + 1):
    if pg == coord['end_page']:
      segment_coords.append({'page': pg, 'start_y': top, 'end_y': coord['end_y']})
    else:
      segment_coords.append({'page': pg, 'start_y': top, 'end_y': bottom})
  return segment_coords   # (was indented inside the loop, so 3+ page chunks lost pages)

def _safe_bbox(page, start_y, end_y):
  """Clamp to the real page so pdfplumber never raises 'not within parent bbox'."""
  top = max(0.0, start_y)
  bottom = min(page.height, end_y)
  return (0, top, page.width, bottom)

def _crop_segments(pdf_path, segment_coords, storing_dir):
  cropped_images = []
  with pdfplumber.open(pdf_path) as pdf:
    for segment in segment_coords:
      page = pdf.pages[segment['page'] - 1]
      bbox = _safe_bbox(page, segment['start_y'], segment['end_y'])
      if bbox[3] - bbox[1] < 2:   # empty sliver, skip it
        continue
      cropped = page.crop(bbox).to_image(resolution=300).original
      cropped_images.append(cropped)
  total_width = max(img.width for img in cropped_images)
  total_height = sum(img.height for img in cropped_images)
  final_image = Image.new("RGB", (total_width, total_height), "white")
  current_y = 0
  for img in cropped_images:
    final_image.paste(img, (0, current_y))
    current_y += img.height
  final_image.save(storing_dir)

def _crop_questions(pdf_path, coord, storing_dir):
  with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[coord['start_page'] - 1]
    bbox = _safe_bbox(page, coord['start_y'], coord['end_y'])
    cropped = page.crop(bbox).to_image(resolution=300).original
  final_image = Image.new("RGB", (cropped.width, cropped.height), "white")
  final_image.paste(cropped, (0, 0))
  final_image.save(storing_dir)

def _crop_one(pdf_path, coord, out_path, bounds):
  """Crop one chunk (single or multi page) and return its segment coords."""
  if coord['start_page'] != coord['end_page']:
    segment_coords = _create_segment_coords(coord, bounds)
    _crop_segments(pdf_path, segment_coords, out_path)
    return segment_coords
  _crop_questions(pdf_path, coord, out_path)
  return [{'page': coord['start_page'], 'start_y': coord['start_y'], 'end_y': coord['end_y']}]

def create_chunks_from_scratch(pdf_path, coords, chunk_type="img", question_type="structured", doc_type="qp"):
  """
  doc_type: "qp" for question papers, "ms" for mark schemes.
  The MS parser already pads its coords, so they are not shifted again here.
  """
  pdf_path_path = Path(pdf_path)
  pdf_name = pdf_path_path.stem
  bounds = BOUNDS[doc_type]

  if question_type == 'mcq':
    normalized_coords = normalize_mcq_coords(coords)
  elif doc_type == "ms":
    normalized_coords = coords
  else:
    normalized_coords = _noramlize_coordinates(coords)

  _save_coords(pdf_name, normalized_coords)
  if chunk_type == "coords":
    return None

  storing_dir = CHUNKS_DIR + f"/{pdf_name}"
  os.makedirs(storing_dir, exist_ok=True)
  for coord in normalized_coords:
    out_path = storing_dir + f"/{_generate_file_name(pdf_name, coord)}.png"
    if question_type == 'mcq':
      _crop_questions(pdf_path, coord, out_path)
    else:
      _crop_one(pdf_path, coord, out_path, bounds)

def create_create_chunks_from_coords(pdf_path, coords, doc_type="qp"):
  chunks_created = []
  pdf_path_path = Path(pdf_path)
  pdf_name = pdf_path_path.stem
  storing_dir = CHUNKS_DIR + f"/{pdf_name}"
  os.makedirs(storing_dir, exist_ok=True)
  bounds = BOUNDS[doc_type]
  for coord in coords:
    out_path = storing_dir + f"/{_generate_file_name(pdf_name, coord)}.png"
    segment_coords = _crop_one(pdf_path, coord, out_path, bounds)
    chunks_created.append((segment_coords, out_path))   # was append(a, b): TypeError
  return chunks_created