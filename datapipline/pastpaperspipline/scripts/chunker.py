import fitz  # PyMuPDF
from PIL import Image
import os
from collections import defaultdict

# ============ CONFIG - edit these ============

PDF_PATH = "datapipline/pastpaperspipline/scripts/9709_w25_qp_55.pdf"
OUTPUT_DIR = "datapipline/pastpaperspipline/chunks"

PADDING_TOP = 10      # extra points added above start_y
PADDING_BOTTOM = 10   # extra points added below end_y
MIN_HEIGHT = 20       # if a crop ends up shorter than this (e.g. zero-height rows), pad up to this height
ZOOM = 3.0            # render resolution multiplier (2.0 ~144dpi, 3.0 ~216dpi)
GAP_BETWEEN_PARTS = 10  # white gap (px, at output resolution) between stitched part images

DATA = [
    {"question": "1", "part": "a", "start_page": 3, "start_y": 63.4, "end_page": 3, "end_y": 102.4},
    {"question": "2", "part": "a", "start_page": 4, "start_y": 63.4, "end_page": 4, "end_y": 172.6},
    {"question": "2", "part": "b", "start_page": 5, "start_y": 89.4, "end_page": 5, "end_y": 89.4},
    {"question": "3", "part": "a", "start_page": 6, "start_y": 63.4, "end_page": 6, "end_y": 792.9},
    {"question": "3", "part": "b", "start_page": 7, "start_y": 63.4, "end_page": 7, "end_y": 63.4},
    {"question": "3", "part": "c", "start_page": 7, "start_y": 362.4, "end_page": 7, "end_y": 375.4},
    {"question": "4", "part": "a", "start_page": 8, "start_y": 63.4, "end_page": 8, "end_y": 792.9},
    {"question": "4", "part": "b", "start_page": 9, "start_y": 63.4, "end_page": 9, "end_y": 63.4},
    {"question": "4", "part": "c", "start_page": 9, "start_y": 297.4, "end_page": 9, "end_y": 310.4},
    {"question": "4", "part": "d", "start_page": 9, "start_y": 592.2, "end_page": 9, "end_y": 605.2},
    {"question": "5", "part": "a", "start_page": 10, "start_y": 63.4, "end_page": 10, "end_y": 102.4},
    {"question": "5", "part": "b", "start_page": 11, "start_y": 102.4, "end_page": 11, "end_y": 115.4},
    {"question": "5", "part": "c", "start_page": 11, "start_y": 466.4, "end_page": 11, "end_y": 479.4},
    {"question": "6", "part": "a", "start_page": 12, "start_y": 63.4, "end_page": 12, "end_y": 141.4},
    {"question": "6", "part": "b", "start_page": 12, "start_y": 557.4, "end_page": 12, "end_y": 557.4},
    {"question": "6", "part": "c", "start_page": 13, "start_y": 89.4, "end_page": 13, "end_y": 102.4},
]

# ============ END CONFIG ============


def crop_part(doc, part):
    """Render one part's region (possibly spanning pages) as a single PIL image,
    stacking sub-page-crops vertically if start_page != end_page."""
    start_page = part["start_page"] - 1  # convert to 0-indexed
    end_page = part["end_page"] - 1
    start_y = part["start_y"] - PADDING_TOP
    end_y = part["end_y"] + PADDING_BOTTOM

    sub_images = []

    if start_page == end_page:
        page = doc[start_page]
        rect = page.rect
        y0 = max(0, start_y)
        y1 = min(rect.height, end_y)
        if y1 - y0 < MIN_HEIGHT:
            # expand symmetrically to hit MIN_HEIGHT, clamped to page bounds
            mid = (y0 + y1) / 2
            y0 = max(0, mid - MIN_HEIGHT / 2)
            y1 = min(rect.height, y0 + MIN_HEIGHT)
            y0 = max(0, y1 - MIN_HEIGHT)
        clip = fitz.Rect(0, y0, rect.width, y1)
        pix = page.get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM), clip=clip)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        sub_images.append(img)
    else:
        # spans multiple pages: first page from start_y to bottom,
        # middle pages full width/height, last page from top to end_y
        for pno in range(start_page, end_page + 1):
            page = doc[pno]
            rect = page.rect
            if pno == start_page:
                y0, y1 = max(0, start_y), rect.height
            elif pno == end_page:
                y0, y1 = 0, min(rect.height, end_y)
            else:
                y0, y1 = 0, rect.height
            clip = fitz.Rect(0, y0, rect.width, y1)
            pix = page.get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM), clip=clip)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            sub_images.append(img)

    if len(sub_images) == 1:
        return sub_images[0]

    # stitch sub-page images vertically
    width = max(im.width for im in sub_images)
    total_height = sum(im.height for im in sub_images)
    combined = Image.new("RGB", (width, total_height), "white")
    y_offset = 0
    for im in sub_images:
        combined.paste(im, (0, y_offset))
        y_offset += im.height
    return combined


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    doc = fitz.open(PDF_PATH)

    by_question = defaultdict(list)
    for part in DATA:
        by_question[part["question"]].append(part)

    saved_files = []
    for q, parts in sorted(by_question.items(), key=lambda kv: int(kv[0])):
        part_images = []
        for part in parts:
            img = crop_part(doc, part)
            part_images.append(img)

        width = max(im.width for im in part_images)
        total_height = sum(im.height for im in part_images) + GAP_BETWEEN_PARTS * (len(part_images) - 1)
        combined = Image.new("RGB", (width, total_height), "white")
        y_offset = 0
        for im in part_images:
            combined.paste(im, (0, y_offset))
            y_offset += im.height + GAP_BETWEEN_PARTS

        out_path = os.path.join(OUTPUT_DIR, f"question_{q}.png")
        combined.save(out_path)
        saved_files.append(out_path)
        print(f"Saved question {q}: {out_path} ({combined.width}x{combined.height})")

    doc.close()
    return saved_files


if __name__ == "__main__":
    main()