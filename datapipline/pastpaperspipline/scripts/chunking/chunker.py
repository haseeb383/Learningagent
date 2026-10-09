import pymupdf  # PyMuPDF
from PIL import Image
import json
import io
from pathlib import Path
from typing import List, Dict, Literal, Optional
from dataclasses import dataclass, asdict

# ─── Constants ───
CHUNK_DIR = Path("datapipline/pastpaperspipline/chunks")
COORDS_DIR = Path("datapipline/pastpaperspipline/coords")
FOOTER_Y = 780.0
PAGE_START_Y = 50.0
END_Y_THRESHOLD_MIN = 50.0
END_Y_THRESHOLD_MAX = 55.0
DEFAULT_DPI = 200
IMAGE_FORMAT = "PNG"

CHUNK_DIR.mkdir(exist_ok=True)
COORDS_DIR.mkdir(exist_ok=True)

@dataclass
class Coord:
    question: str
    part: str
    start_page: int
    start_y: float
    end_page: int
    end_y: float

@dataclass
class ChunkMetadata:
    chunk_file: str
    pdf_source: str
    question: str
    part: str
    coordinates: Dict
    page_range: List[int]
    chunk_type: str

def normalize_coord(coord: Dict) -> Dict:
    """
    Adjust coordinates for edge cases.
    Rule: end_y between 50-55 → previous page, y=780
    """
    coord = coord.copy()
    if END_Y_THRESHOLD_MIN <= coord["end_y"] <= END_Y_THRESHOLD_MAX:
        coord["end_page"] = coord["end_page"] - 1
        coord["end_y"] = FOOTER_Y
    return coord

def segment_multipage(coord: Dict) -> List[Dict]:
    """
    Split multi-page coordinate into single-page segments.
    Rules:
    - First page: start_y → 780
    - Middle pages: 50 → 780
    - Last page: 50 → end_y (normalized)
    """
    if coord["start_page"] == coord["end_page"]:
        return [coord]
    
    segments = []
    
    # First page
    segments.append({
        **coord,
        "end_page": coord["start_page"],
        "end_y": FOOTER_Y
    })
    
    # Middle pages
    for pg in range(coord["start_page"] + 1, coord["end_page"]):
        segments.append({
            **coord,
            "start_page": pg,
            "start_y": PAGE_START_Y,
            "end_page": pg,
            "end_y": FOOTER_Y
        })
    
    # Last page
    segments.append({
        **coord,
        "start_page": coord["end_page"],
        "start_y": PAGE_START_Y
    })
    
    return segments

def crop_page(doc: pymupdf.Document, page_num: int, start_y: float, end_y: float, dpi: int = DEFAULT_DPI) -> Optional[Image]:
    """Crop a single page segment and return as PIL Image. Returns None if page out of bounds."""
    if page_num < 1 or page_num > len(doc):
        return None
    page = doc[page_num - 1]  # 0-indexed
    rect = pymupdf.Rect(0, start_y, page.rect.width, end_y)
    pix = page.get_pixmap(clip=rect, dpi=dpi)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return img

def merge_vertical(images: List[Image]) -> Image:
    """Merge images vertically."""
    if not images:
        return Image.new("RGB", (100, 100), "white")
    
    total_height = sum(img.height for img in images)
    max_width = max(img.width for img in images)
    
    merged = Image.new("RGB", (max_width, total_height), "white")
    y_offset = 0
    for img in images:
        merged.paste(img, (0, y_offset))
        y_offset += img.height
    
    return img

def generate_filename(pdf_name: str, coord: Dict) -> str:
    """Generate chunk filename from pdf name and coordinate."""
    # Remove .pdf extension if present
    pdf_base = Path(coord.get("pdf_name", "unknown")).stem
    
    # Format part for filename (remove special chars)
    part = coord["part"].replace(")", "").replace("(", "").replace(",", "")
    part = part.replace(" ", "_")
    
    return f"{pdf_base}_q{coord['question']}_{part}.png"

def crop_coordinate(doc: pymupdf.Document, coord: Dict, dpi: int = DEFAULT_DPI) -> Optional[Image]:
    """Crop a single coordinate (handles both single and multi-page)."""
    # Normalize first
    coord = normalize_coord(coord)
    
    # Validate page bounds
    if coord["start_page"] > len(doc) or coord["start_page"] < 1:
        return None
    
    # Cap end_page to actual document length
    coord = coord.copy()
    coord["end_page"] = min(coord["end_page"], len(doc))
    
    # Segment if multi-page
    segments = segment_multipage(coord)
    
    images = []
    for seg in segments:
        img = crop_page(doc, seg["start_page"], seg["start_y"], seg["end_y"], dpi=dpi)
        if img is not None:
            images.append(img)
    
    if not images:
        return None
    
    # Merge vertically
    if len(images) == 1:
        return images[0]
    return merge_vertical(images)

def save_coords(coords: List[Dict], pdf_name: str, coords_dir: Path = COORDS_DIR):
    """Save normalized coordinates to JSON file."""
    pdf_base = Path(pdf_name).stem
    output_path = coords_dir / f"{pdf_base}.json"
    
    # Normalize all coords before saving
    normalized = [normalize_coord(c) for c in coords]
    
    with open(output_path, 'w') as f:
        json.dump(normalized, f, indent=2)
    
    return output_path

def process_pdf(
    pdf_path: str,
    coords: List[Dict],
    chunk_type: Literal["image", "coords"] = "image",
    chunk_dir: Path = CHUNK_DIR,
    coords_dir: Path = COORDS_DIR,
    dpi: int = DEFAULT_DPI
) -> Dict:
    """
    Main chunking function.
    
    Args:
        pdf_path: Path to PDF file
        coords: List of coordinate dicts from parser
        chunk_type: "image" (crop and save images) or "coords" (only save coords)
        chunk_dir: Directory for chunk images
        coords_dir: Directory for coords JSON
        dpi: Rendering DPI
    
    Returns:
        Dict with processing metadata
    """
    pdf_path = Path(pdf_path)
    pdf_name = pdf_path.stem
    
    # Create output subdirectory for this PDF
    pdf_chunk_dir = chunk_dir / pdf_name
    pdf_chunk_dir.mkdir(parents=True, exist_ok=True)
    
    # Open PDF
    doc = pymupdf.open(str(pdf_path))
    
    metadata = {
        "pdf_source": pdf_path.name,
        "chunks": [],
        "total_chunks": 0,
        "chunk_type": chunk_type
    }
    
    try:
        if chunk_type in ("image", "both"):
            # Process each coordinate
            for coord in coords:
                # Normalize and segment
                norm_coord = normalize_coord(coord)
                segments = segment_multipage(norm_coord)
                
                # Crop and merge
                images = []
                for seg in segments:
                    img = crop_page(doc, seg["start_page"], seg["start_y"], seg["end_y"], dpi=dpi)
                    if img is not None:
                        images.append(img)
                
                if not images:
                    continue
                
                # Merge vertically
                if len(images) == 1:
                    final_img = images[0]
                else:
                    final_img = merge_vertical(images)
                
                # Save image
                filename = generate_filename(coord.get("pdf_name", pdf_name), coord)
                img_path = pdf_chunk_dir / filename
                final_img.save(img_path, format=IMAGE_FORMAT)
                
                metadata["chunks"].append({
                    "chunk_file": str(img_path.relative_to(chunk_dir)),
                    "pdf_source": pdf_path.name,
                    "question": coord["question"],
                    "part": coord["part"],
                    "coordinates": coord,
                    "page_range": [coord["start_page"], coord["end_page"]],
                    "chunk_type": "image"
                })
        
        if chunk_type in ("coords", "both"):
            # Save normalized coordinates
            save_coords(coords, pdf_name, coords_dir)
            metadata["coords_file"] = f"{pdf_name}.json"
        
        metadata["total_chunks"] = len(metadata["chunks"])
        
    finally:
        doc.close()
    
    return metadata

def batch_process(
    pdf_coords_pairs: List[tuple],
    chunk_type: Literal["image", "coords", "both"] = "image",
    chunk_dir: Path = CHUNK_DIR,
    coords_dir: Path = COORDS_DIR,
    dpi: int = DEFAULT_DPI
) -> List[Dict]:
    """
    Process multiple PDF-coord pairs in batch.
    
    Args:
        pdf_coords_pairs: List of (pdf_path, coords_list) tuples
        chunk_type: "image", "coords", or "both"
        chunk_dir: Chunk output directory
        coords_dir: Coords JSON directory
        dpi: Rendering DPI
    
    Returns:
        List of metadata dicts
    """
    results = []
    for pdf_path, coords in pdf_coords_pairs:
        meta = process_pdf(pdf_path, coords, chunk_type, CHUNK_DIR, COORDS_DIR, DEFAULT_DPI)
        results.append(meta)
    return results