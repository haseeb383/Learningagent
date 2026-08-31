import fitz  # PyMuPDF
import numpy as np
from PIL import Image
import json
import os
from question_finder import run_pipeline

# ---------------------------------------------------------------------------
# Tunables
# ---------------------------------------------------------------------------

DPI = 200                      # render resolution; higher = sharper but slower/bigger
INK_DARKNESS_CUTOFF = 100      # pixel value below this (0-255) counts as "ink"
INK_ROW_THRESHOLD = 0.006      # fraction of dark pixels in a row to count as "content"
CROP_PADDING_PX = 8            # padding kept around detected content, in output pixels

# Gap threshold used to decide "this is a real part boundary, cut here" vs
# "this is just normal spacing within a part, keep together". This is in
# OUTPUT PIXELS at the DPI above. At DPI=200, one typical text line + its
# line-gap is roughly 30-40px, so e.g. PART_GAP_THRESHOLD_PX=120 means
# "cut after roughly 3-4 blank lines". This will need tuning per paper
# format (different subjects/boards have different answer-space heights) -
# treat this as the main knob to experiment with.
PART_GAP_THRESHOLD_PX = 20


# ---------------------------------------------------------------------------
# Core ink-projection helpers
# ---------------------------------------------------------------------------

def _render_region(page, y0, y1, dpi=DPI):
    """Render a horizontal band [y0, y1] of a PDF page to a numpy image array."""
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)
    y0 = max(0, y0)
    y1 = min(page.rect.y1, y1)
    if y1 <= y0:
        return None, zoom
    clip = fitz.Rect(page.rect.x0, y0, page.rect.x1, y1)
    pix = page.get_pixmap(matrix=mat, clip=clip)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    if img.shape[2] == 4:  # drop alpha if present
        img = img[..., :3]
    return img, zoom


def _ink_rows_mask(img):
    """Boolean array: for each row, is there enough dark ink to count as content?"""
    gray = img.mean(axis=2)
    dark_fraction_per_row = (gray < INK_DARKNESS_CUTOFF).mean(axis=1)
    return dark_fraction_per_row > INK_ROW_THRESHOLD


def _content_bounds(img, trim_top=True, trim_bottom=True, pad=CROP_PADDING_PX):
    """
    Find [top, bottom) pixel rows containing real content in img.
    If trim_top/trim_bottom is False, that edge is left at the image border
    (used e.g. on the start page where the bottom is a genuine continuation
    onto the next page, not a natural end-of-content edge... though in
    practice trimming trailing blank rows there is still safe & desired).
    """
    mask = _ink_rows_mask(img)
    rows = np.where(mask)[0]
    if len(rows) == 0:
        # no ink detected at all (e.g. blank region) -> keep as-is
        return 0, img.shape[0]
    top = rows[0] if trim_top else 0
    bottom = rows[-1] + 1 if trim_bottom else img.shape[0]
    top = max(0, top - pad)
    bottom = min(img.shape[0], bottom + pad)
    return top, bottom


def _find_islands(img, min_gap_px):
    """Return list of (top, bottom) pixel ranges for contiguous ink blocks,
    separated by gaps of at least min_gap_px blank rows."""
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


# ---------------------------------------------------------------------------
# Composite building (spans all pages of a question, no stitching seams)
# ---------------------------------------------------------------------------

def _build_composite(doc, start_page, start_y, end_page, end_y):
    """
    Render every page in [start_page, end_page] for this question's window
    and stack them into ONE continuous image, top to bottom, in reading
    order. No separators - a page break with no real content gap should
    look exactly like it wasn't there, and a page break WITH a real content
    gap will simply show up as blank rows, same as any other gap.
    """
    imgs = []
    for pno in range(start_page, end_page + 1):
        page = doc[pno]
        if pno == start_page:
            y0 = start_y
        else:
            y0 = 0
        if pno == end_page:
            y1 = end_y
        else:
            y1 = page.rect.y1

        img, zoom = _render_region(page, y0, y1)
        if img is not None and img.shape[0] > 0:
            imgs.append(img)

    if not imgs:
        return None

    # pages should normally be the same width, but pad defensively just in case
    max_w = max(im.shape[1] for im in imgs)
    padded = []
    for im in imgs:
        if im.shape[1] < max_w:
            pad = np.full((im.shape[0], max_w - im.shape[1], 3), 255, dtype=np.uint8)
            im = np.hstack([im, pad])
        padded.append(im)

    return np.vstack(padded)


# ---------------------------------------------------------------------------
# Per-question part-splitting
# ---------------------------------------------------------------------------

def chunk_question_into_parts(doc, q, gap_threshold_px=PART_GAP_THRESHOLD_PX, pad=CROP_PADDING_PX):
    """
    q is one dict: {question_number, start_page, start_y, end_page, end_y}.

    Returns a list of numpy image arrays, one per detected "part" of the
    question - i.e. one per contiguous block of ink separated by a real
    gap of at least gap_threshold_px blank rows. A single-part question
    (most MCQs, most short-answer questions) returns a list of length 1.
    """
    start_page = q["start_page"] - 1 if q.get("_one_indexed_pages", True) else q["start_page"]
    end_page = q["end_page"] - 1 if q.get("_one_indexed_pages", True) else q["end_page"]

    composite = _build_composite(doc, start_page, q["start_y"], end_page, q["end_y"])
    if composite is None:
        return []

    # trim the loose outer whitespace from the raw coordinates first
    top, bottom = _content_bounds(composite, trim_top=True, trim_bottom=True, pad=0)
    trimmed = composite[top:bottom]
    if trimmed.shape[0] == 0:
        return []

    islands = _find_islands(trimmed, min_gap_px=gap_threshold_px)

    parts = []
    for (isl_top, isl_bottom) in islands:
        t = max(0, isl_top - pad)
        b = min(trimmed.shape[0], isl_bottom + pad)
        piece = trimmed[t:b]
        if piece.shape[0] > 0:
            parts.append(piece)

    return parts


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def chunk_questions(pdf_path, questions, output_dir, doc_id=None,
                     page_numbers_are_1_indexed=True,
                     gap_threshold_px=PART_GAP_THRESHOLD_PX):
    """
    pdf_path:          path to the source PDF (QP or MS)
    questions:         list of dicts like
                        {'question_number': '1', 'start_page': 3, 'start_y': 61.4,
                         'end_page': 3, 'end_y': 127.4}
                        start_page/end_page are assumed 1-indexed unless
                        page_numbers_are_1_indexed=False
    output_dir:        directory to save cropped part-images into
                        (created if it doesn't exist)
    doc_id:             filename prefix; defaults to the PDF's filename stem
    gap_threshold_px:   blank-row run length (in output pixels, at DPI above)
                        needed to cut a new part. This is the main thing to
                        experiment with per paper format.

    No metadata is written yet (deliberately left for later) - this just
    saves images, named <doc_id>_q<question_number>_part<N>.png, one per
    detected part of each question. Returns a dict:
        {question_number: [list of saved image paths, in order]}
    """
    os.makedirs(output_dir, exist_ok=True)
    if doc_id is None:
        doc_id = os.path.splitext(os.path.basename(pdf_path))[0]

    doc = fitz.open(pdf_path)
    saved = {}

    for q in questions:
        q = dict(q)  # don't mutate caller's dict
        q["_one_indexed_pages"] = page_numbers_are_1_indexed
        qnum = str(q["question_number"]).replace(" ", "_")

        parts = chunk_question_into_parts(doc, q, gap_threshold_px=gap_threshold_px)

        if not parts:
            print(f"[warn] question {qnum}: no content detected, skipping")
            continue

        paths = []
        for i, part_img in enumerate(parts, start=1):
            filename = f"{doc_id}_q{qnum}_part{i}.png"
            out_path = os.path.join(output_dir, filename)
            Image.fromarray(part_img).save(out_path)
            paths.append(out_path)

        saved[q["question_number"]] = paths
        print(f"question {qnum}: {len(parts)} part(s) saved")

    doc.close()
    total = sum(len(v) for v in saved.values())
    print(f"Saved {total} part-images across {len(saved)} questions to {output_dir}")
    return saved


# ---------------------------------------------------------------------------
# Example / manual test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pdf_path = "datapipline/pastpaperspipline/downlaods/9709_m26_qp_62.pdf"
    questions = run_pipeline(pdf_path=pdf_path)
    output_dir = "datapipline/pastpaperspipline/question_images"
    chunk_questions(pdf_path=pdf_path, questions=questions, output_dir=output_dir, )