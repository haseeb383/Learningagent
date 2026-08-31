import os
import numpy as np
from PIL import Image
from scipy import ndimage
from question_finder import run_pipeline

try:
    import fitz  # PyMuPDF
except ImportError as e:
    raise ImportError(
        "PyMuPDF is required for this script. Install it with:\n"
        "    pip install PyMuPDF --break-system-packages"
    ) from e


# --------------------------------------------------------------------------- #
# Low level helpers
# --------------------------------------------------------------------------- #

def _render_region(page, y0, y1, zoom):
    """Render the full page-width strip [y0, y1] (in PDF points) of `page`.

    Returns (pil_rgb_image, grayscale_numpy_array).
    At zoom=1, 1 pdf point == 1 pixel, so px = pt * zoom for every conversion.
    """
    y0 = max(0.0, min(y0, page.rect.height))
    y1 = max(0.0, min(y1, page.rect.height))
    if y1 <= y0:
        return None, None
    clip = fitz.Rect(page.rect.x0, y0, page.rect.x1, y1)
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, clip=clip, alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    gray = np.array(img.convert("L"), dtype=np.uint8)
    return img, gray


def _page_segments(doc, start_page, start_y, end_page, end_y):
    """Split a (possibly multi-page) search box into a list of
    (page_index, y0, y1) strips, one per page it touches, in point coords."""
    segments = []
    if start_page == end_page:
        segments.append((start_page, start_y, end_y))
    else:
        first_page = doc[start_page]
        segments.append((start_page, start_y, first_page.rect.height))
        for p in range(start_page + 1, end_page):
            pg = doc[p]
            segments.append((p, 0.0, pg.rect.height))
        segments.append((end_page, 0.0, end_y))
    return segments


def _compute_ink_mask(gray, ink_gray_threshold):
    """True where a pixel is dark enough to count as real ink.

    This single threshold is what filters out light-gray watermark text --
    lower it if watermark is still leaking through as "ink", raise it if
    faint real text/diagrams are being lost.
    """
    return gray < ink_gray_threshold


def _remove_dot_leaders(ink_mask, zoom, dot_max_width_pt, dot_max_height_pt,
                         min_dots_per_band):
    """Strip out connected components that look like leader dots/dashes
    ("....." used for "write your answer here" lines) from the ink mask.

    A component is *dot-shaped* if it's small in both width and height
    (<= dot_max_width_pt / dot_max_height_pt, converted to px via zoom).
    A dot-shaped component is only actually removed if there are at least
    `min_dots_per_band` other dot-shaped components at roughly the same
    vertical position -- a single small mark (e.g. the dot on an "i", a
    period, a bullet) is left alone; a *row* of many small marks in a line
    is what gets suppressed.
    """
    if not ink_mask.any():
        return ink_mask

    labeled, num = ndimage.label(ink_mask)
    if num == 0:
        return ink_mask

    objs = ndimage.find_objects(labeled)
    dot_max_w_px = max(1.0, dot_max_width_pt * zoom)
    dot_max_h_px = max(1.0, dot_max_height_pt * zoom)

    dot_ids = []
    for i, sl in enumerate(objs, start=1):
        if sl is None:
            continue
        h = sl[0].stop - sl[0].start
        w = sl[1].stop - sl[1].start
        if w <= dot_max_w_px and h <= dot_max_h_px:
            dot_ids.append(i)

    if not dot_ids:
        return ink_mask

    # Bucket dot-shaped components into coarse vertical bands so that dots
    # sitting on (roughly) the same text line get grouped together even if
    # their exact y differs by a pixel or two.
    band_height = max(1, int(round(dot_max_h_px * 2)))
    bands = {}
    for i in dot_ids:
        sl = objs[i - 1]
        yc = (sl[0].start + sl[0].stop) // 2
        band = yc // band_height
        bands.setdefault(band, []).append(i)

    suppress_ids = set()
    for band, ids in bands.items():
        if len(ids) >= min_dots_per_band:
            suppress_ids.update(ids)

    if not suppress_ids:
        return ink_mask

    mask = ink_mask.copy()
    for i in suppress_ids:
        sl = objs[i - 1]
        local = labeled[sl] == i
        mask[sl][local] = False
    return mask


def _row_has_ink(mask, min_ink_pixels_per_row):
    return mask.sum(axis=1) >= min_ink_pixels_per_row


def _crop_block(segments_data, start_global, end_global, padding_px, total_rows):
    """Crop out global row range [start_global-pad, end_global+pad] across
    however many page-segments it spans, and stitch the pieces vertically
    into a single image."""
    start_global = max(0, start_global - padding_px)
    end_global = min(total_rows, end_global + padding_px + 1)

    crops = []
    for seg in segments_data:
        seg_start = seg["global_start"]
        seg_end = seg_start + seg["height"]
        lo = max(start_global, seg_start)
        hi = min(end_global, seg_end)
        if lo < hi:
            local_lo = lo - seg_start
            local_hi = hi - seg_start
            crops.append(seg["img"].crop((0, local_lo, seg["img"].width, local_hi)))

    if not crops:
        return None
    if len(crops) == 1:
        return crops[0]

    width = max(c.width for c in crops)
    total_height = sum(c.height for c in crops)
    combined = Image.new("RGB", (width, total_height), "white")
    y_off = 0
    for c in crops:
        if c.width != width:
            # pad narrower crops (shouldn't normally happen, same page width)
            padded = Image.new("RGB", (width, c.height), "white")
            padded.paste(c, (0, 0))
            c = padded
        combined.paste(c, (0, y_off))
        y_off += c.height
    return combined


# --------------------------------------------------------------------------- #
# Main entry point
# --------------------------------------------------------------------------- #

def extract_question_chunks(
    pdf_path,
    questions,
    output_dir,
    *,
    zoom=3.0,                    # render resolution: px per pdf-point (3.0 ~= 216 dpi)
    page_index_base=1,           # set to 0 if your coordinates are already 0-indexed
    ink_gray_threshold=100,      # 0-255, lower = stricter/darker-only = filters more watermark
    dot_max_width_pt=3.0,        # leader-dot component size cap, in pdf points
    dot_max_height_pt=3.0,
    min_dots_per_band=4,         # how many small marks in a row before it's called a dot-line
    min_ink_pixels_per_row=3,    # noise floor: row needs >= this many ink px to count as content
    blank_gap_pt=60.0,           # vertical blank run (pdf points) big enough to force a cut
    padding_pt=4.0,              # padding kept around each cropped block
    min_block_height_pt=6.0,     # discard ink blocks shorter than this (stray specks)
    image_format="png",
):
    """
    Parameters
    ----------
    pdf_path : str
        Path to the source question-paper PDF.
    questions : list[dict]
        Each dict needs: question_number, start_page, start_y, end_page, end_y.
    output_dir : str
        Directory the cropped images are written into.

    Returns
    -------
    list[dict]
        [{"question_number": ..., "parts": ["/path/q1.png", ...]}, ...]
    """
    os.makedirs(output_dir, exist_ok=True)
    doc = fitz.open(pdf_path)

    blank_gap_px = max(1, int(round(blank_gap_pt * zoom)))
    padding_px = int(round(padding_pt * zoom))
    min_block_height_px = int(round(min_block_height_pt * zoom))

    results = []

    for q in questions:
        qnum = q["question_number"]
        start_page = q["start_page"] - page_index_base
        end_page = q["end_page"] - page_index_base
        start_y = q["start_y"]
        end_y = q["end_y"]

        segs_raw = _page_segments(doc, start_page, start_y, end_page, end_y)

        segments_data = []
        ink_row_chunks = []
        global_offset = 0

        for (p_idx, y0, y1) in segs_raw:
            page = doc[p_idx]
            img, gray = _render_region(page, y0, y1, zoom)
            if img is None:
                continue
            ink_mask = _compute_ink_mask(gray, ink_gray_threshold)
            ink_mask = _remove_dot_leaders(
                ink_mask, zoom, dot_max_width_pt, dot_max_height_pt, min_dots_per_band
            )
            has_ink_row = _row_has_ink(ink_mask, min_ink_pixels_per_row)

            segments_data.append(
                {"img": img, "height": img.height, "global_start": global_offset}
            )
            ink_row_chunks.append(has_ink_row)
            global_offset += img.height

        if not segments_data:
            results.append({"question_number": qnum, "parts": []})
            continue

        global_ink_rows = np.concatenate(ink_row_chunks)
        total_rows = len(global_ink_rows)

        # --- walk the row-ink array, cutting on long blank runs ---
        blocks = []
        pos = 0
        while pos < total_rows:
            # skip leading blank rows
            while pos < total_rows and not global_ink_rows[pos]:
                pos += 1
            if pos >= total_rows:
                break

            block_start = pos
            last_ink = pos
            gap_run = 0
            pos += 1
            while pos < total_rows:
                if global_ink_rows[pos]:
                    last_ink = pos
                    gap_run = 0
                else:
                    gap_run += 1
                    if gap_run >= blank_gap_px:
                        break
                pos += 1
            block_end = last_ink

            if (block_end - block_start) >= min_block_height_px:
                blocks.append((block_start, block_end))

            # `pos` is now just past the blank gap (or == total_rows).
            # If nothing but blank remains in the original box, stop searching;
            # otherwise loop back around and keep looking for more content.
            if pos < total_rows and not global_ink_rows[pos:].any():
                break

        # --- crop + save each block ---
        part_paths = []
        multi = len(blocks) > 1
        for i, (s, e) in enumerate(blocks, start=1):
            crop = _crop_block(segments_data, s, e, padding_px, total_rows)
            if crop is None:
                continue
            suffix = f"_part{i}" if multi else ""
            fname = f"q{qnum}{suffix}.{image_format}"
            fpath = os.path.join(output_dir, fname)
            crop.save(fpath)
            part_paths.append(fpath)

        results.append({"question_number": qnum, "parts": part_paths})

    doc.close()
    return results


# --------------------------------------------------------------------------- #
# Example manual usage (edit and run this file directly to test, or just
# import extract_question_chunks(...) into the rest of your pipeline)
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    pdf_path = "datapipline/pastpaperspipline/downlaods/9709_m26_qp_62.pdf"
    output_dir = "datapipline/pastpaperspipline/question_images"
    questions = run_pipeline(pdf_path=pdf_path)

    results = extract_question_chunks(
        pdf_path,
        questions,
        output_dir,
        zoom=3.0,
        page_index_base=1,
        ink_gray_threshold=140,
        dot_max_width_pt=3.0,
        dot_max_height_pt=1.0,
        min_dots_per_band=4,
        min_ink_pixels_per_row=3,
        blank_gap_pt=30.0,
        padding_pt=4.0,
        min_block_height_pt=6.0,
    )

    for r in results:
        print(f"Q{r['question_number']}: {len(r['parts'])} image(s) -> {r['parts']}")