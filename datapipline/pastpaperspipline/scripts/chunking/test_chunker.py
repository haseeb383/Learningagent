import os
import json
import pdfplumber 
from PIL import Image
from pathlib import Path

COORDS_DIR = "datapipline/pastpaperspipline/coords"
CHUNKS_DIR = "datapipline/pastpaperspipline/chunks"

def _noramlize_coordinates(coords):
  for coord in coords:
    if coord['end_y'] >= 50 and coord['end_y'] <=55:
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

def _create_segment_coords(coord):
  segment_coords = []
  segment_coords.append({'page': coord['start_page'], 'start_y': coord['start_y'], 'end_y': 780})
  for x in range(coord['start_page'] + 1, coord['end_page'] + 1):
    if x == coord['end_page']:
      segment_coords.append({'page': coord['end_page'], 'start_y': 50, 'end_y': coord['end_y']})
    else:
      segment_coords.append({'page': x, 'start_y': 50, 'end_y': 780})
    return segment_coords

def _crop_segments(pdf_path, segment_coords, storing_dir):
  cropped_images = []
  with pdfplumber.open(pdf_path) as pdf:
    for segment in segment_coords:
      page = pdf.pages[segment['page'] - 1]
      bbox = (0, segment['start_y'], page.width, segment['end_y'])
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
    bbox = (0, coord['start_y'], page.width, coord['end_y'])
    cropped = page.crop(bbox).to_image(resolution=300).original
  total_width = cropped.width
  total_height = cropped.height
  final_image = Image.new("RGB", (total_width, total_height), "white")
  final_image.paste(cropped, (0, 0))
  final_image.save(storing_dir)

def create_chunks(pdf_path, coords):
  normalized_coords = _noramlize_coordinates(coords)
  pdf_path_path = Path(pdf_path)
  pdf_name = pdf_path_path.stem
  _save_coords(pdf_name, normalized_coords)
  storing_dir = CHUNKS_DIR + f"/{pdf_name}"
  os.makedirs(storing_dir, exist_ok=True)
  for coord in normalized_coords:
    if coord['start_page'] != coord['end_page']:
      segment_coords = _create_segment_coords(coord)
      _crop_segments(pdf_path, segment_coords, storing_dir + f"/{_generate_file_name(pdf_name, coord)}.png")
    else:
      _crop_questions(pdf_path, coord, storing_dir + f"/{_generate_file_name(pdf_name, coord)}.png")
