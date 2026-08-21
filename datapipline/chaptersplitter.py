import os
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered
from pathlib import Path
import logging
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, ImageRefMode
from docling.document_converter import DocumentConverter, PdfFormatOption

# os.environ["TORCH_DEVICE"] = "cuda"
# os.environ["IN_MEMORY_MAX_PAGES"] = "2"
# os.environ["VRAM_PER_TASK"] = "2.0"
# os.environ["OCR_ENGINE"] = "ocrmypdf"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "true"

input_pdf = "test_text_book.pdf"

def convertpdf2markdown(input_pdf):
  model_dict = create_model_dict()
  converter =  PdfConverter(artifact_dict=model_dict)

  rendered_doc = converter(input_pdf)
  full_text, _, _ = text_from_rendered(rendered_doc)
  output_md = "test_output.md"
  with open(output_md, "w", encoding="utf-8") as f:
      f.write(full_text)

def main(input_pdf_path: str):
    # Establish workspace directories
    output_dir = Path("output_dataset")
    images_dir = output_dir / "extracted_images"
    images_dir.mkdir(parents=True, exist_ok=True)
    
    input_path = Path(input_pdf_path)
    print(f"Initializing processing pipeline for: {input_path.name}")

    # 2. Configure Extraction Pipeline Options Safely
    pipeline_options = PdfPipelineOptions()
    
    # Drops the image resolution slightly to protect from Out-of-Memory (OOM) crashes
    pipeline_options.images_scale = 1.0  
    
    # Keep embedded image extraction enabled for structural layouts
    pipeline_options.generate_page_images = False  
    pipeline_options.generate_picture_images = True  
    
    # Directs OCR to read small bounding boxes/equations (Crucial for textbooks)
    pipeline_options.ocr_options.bitmap_area_threshold = 0.0  
    pipeline_options.ocr_options.force_full_page_ocr = True   

    # Bind options to the PDF Converter format
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )

    # 3. Parse Document
    print("Parsing document layout tree (this may take a few minutes for large textbooks)...")
    conversion_result = converter.convert(input_path)
    docling_doc = conversion_result.document

    # 4. Export Markdown using native Image resolution references
    print("Exporting document structure and saving local image assets...")

    def custom_image_provider(element, doc):
        """
        Executes inside Docling's markdown rendering hook.
        Safely isolates the visual element, assigns a unique name, and writes it to disk.
        """
        # Safely extract unique token path string from schema definition
        clean_id = element.self_ref.replace("#/", "").replace("/", "_")
        image_filename = f"graph_{clean_id}.png"
        image_save_path = images_dir / image_filename
        
        # Save image if visual data exists
        if hasattr(element, "image") and element.image:
            element.image.pil_image.save(image_save_path)
            
        # Return the clean relative text snippet that goes inside the generated Markdown markdown file
        return f"extracted_images/{image_filename}"

    # Render Document with Image References
    markdown_content = docling_doc.export_to_markdown(
        image_placeholder="<!-- image -->",
        image_resolution_provider=custom_image_provider
    )

    # 5. Save final Markdown file out to workspace root
    output_md_path = output_dir / f"{input_path.stem}_structured.md"
    with open(output_md_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)

    print("\n" + "="*40)
    print("SUCCESS: Pipeline executed completely!")
    print(f"Structured Text written to: {output_md_path}")
    print(f"Total extracted figures saved to: {images_dir}/")
    print("="*40)

if __name__ == "__main__":
   main(input_pdf)