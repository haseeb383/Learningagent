import logging
import time
from pathlib import Path

from docling_core.types.doc import ImageRefMode, PictureItem, TableItem
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

logging.basicConfig(level=logging.INFO)
_log = logging.getLogger(__name__)

input_pdf = "test_text_book.pdf"

def main(input_pdf_path: str):
    output_dir = Path("output_dataset")
    images_dir = output_dir / "extracted_images"
    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    input_path = Path(input_pdf_path)
    _log.info(f"Processing: {input_path.name}")

    # Pipeline options - based on official export_figures example
    pipeline_options = PdfPipelineOptions()
    pipeline_options.images_scale = 2.0  # higher resolution for equations/diagrams
    pipeline_options.generate_page_images = True
    pipeline_options.generate_picture_images = True
    pipeline_options.generate_table_images = True
    
    # OCR - use current API (force_full_page_ocr is on OcrAutoOptions)
    pipeline_options.ocr_options.force_full_page_ocr = True
    # pipeline_options.ocr_options.lang = ["en"]  # optional: specify language

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )

    _log.info("Parsing document...")
    start_time = time.time()
    conv_res = converter.convert(input_path)
    _log.info(f"Parsed in {time.time() - start_time:.2f}s")

    doc = conv_res.document
    doc_filename = input_path.stem

    # 1. Save page images (optional, but useful)
    for page_no, page in doc.pages.items():
        page_image_path = images_dir / f"{doc_filename}-page-{page_no}.png"
        page.image.pil_image.save(page_image_path, format="PNG")

    # 2. Save figure/table images
    table_counter = 0
    picture_counter = 0
    for element, _level in doc.iterate_items():
        if isinstance(element, TableItem):
            table_counter += 1
            img_path = images_dir / f"{doc_filename}-table-{table_counter}.png"
            element.get_image(doc).save(img_path, "PNG")
        elif isinstance(element, PictureItem):
            picture_counter += 1
            img_path = images_dir / f"{doc_filename}-picture-{picture_counter}.png"
            element.get_image(doc).save(img_path, "PNG")

    _log.info(f"Saved {table_counter} tables, {picture_counter} pictures")

    # 3. Save markdown with REFERENCED images (links to extracted_images/)
    md_path = output_dir / f"{doc_filename}_structured.md"
    doc.save_as_markdown(md_path, image_mode=ImageRefMode.REFERENCED)

    _log.info(f"Done. Markdown: {md_path}")
    _log.info(f"Images in: {images_dir}")

if __name__ == "__main__":
    main(input_pdf)