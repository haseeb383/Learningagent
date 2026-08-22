import os
import time
import shutil
import subprocess
import time
import urllib.request
import urllib.error
from pathlib import Path
from pypdf import PdfReader, PdfWriter

# marker
import subprocess
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.config.parser import ConfigParser
from marker.output import text_from_rendered

# MinerU
from mineru.cli.common import read_fn, do_parse

# docling
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, EasyOcrOptions

INPUT_DIR = "/content/drive/MyDrive/learningagentbooks"
OUTPUT_DIR = "/content/drive/MyDrive/learningagentmarkdown"

os.environ["SURYA_INFERENCE_BACKEND"] = "vllm"
os.environ["SURYA_INFERENCE_URL"] = "http://localhost:8000/v1"
os.environ["SURYA_INFERENCE_KEEP_ALIVE"] = "1"

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "true"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["TORCH_DEVICE"] = "cuda"


def shorten_pdf(input_path, output_path, pages):
  reader = PdfReader(input_path)
  writer = PdfWriter()

  for page_num in range(pages):
    writer.add_page(reader.pages[page_num])

  with open(output_path, "wb") as f:
    writer.write(f)

def check_file_names():
    os.makedirs("/content/drive/MyDrive/learningagentbooks", exist_ok=True)
    os.makedirs("/content/drive/MyDrive/learningagentmarkdown", exist_ok=True)

    visible_files = os.listdir("/content/drive/MyDrive/learningagentbooks")
    visible_files = visible_files + os.listdir("/content/drive/MyDrive/learningagentmarkdown")
    if len(visible_files) == 0:
        print("The folder is EMPTY!")
    else:
        for file in visible_files:
            print(f"Found: {file}")

SURYA_SERVER_URL = "http://localhost:8000/v1"
SURYA_MODEL = "datalab-to/surya-ocr-2"
 
_surya_process = None
 
 
def _surya_server_is_up(timeout: float = 2.0) -> bool:
    try:
        urllib.request.urlopen(f"{SURYA_SERVER_URL}/models", timeout=timeout)
        return True
    except (urllib.error.URLError, ConnectionError, TimeoutError):
        return False
 
 
def _ensure_surya_server(max_wait_seconds: int = 300) -> None:
    """Start the vllm/surya server as a plain background process (no
    Docker) if nothing is already listening on it, then block until it's
    actually ready to accept requests.
    """
    global _surya_process
 
    if _surya_server_is_up():
        return
 
    if _surya_process is None:
        print("Starting surya vllm server (first call only, this can take a "
              "couple of minutes while the model downloads/loads)...")
        _surya_process = subprocess.Popen(
            ["vllm", "serve", SURYA_MODEL, "--port", "8000"]
        )
 
    waited = 0
    while not _surya_server_is_up():
        if _surya_process.poll() is not None:
            raise RuntimeError(
                "surya vllm server process exited before becoming ready. "
                "Check the notebook output above for the actual error."
            )
        if waited >= max_wait_seconds:
            raise TimeoutError(
                f"surya vllm server did not become ready within "
                f"{max_wait_seconds}s."
            )
        time.sleep(5)
        waited += 5
 
    print("surya server is ready.")

def convert_with_marker(file_name: str) -> str:
    _ensure_surya_server()

    input_path = os.path.join(INPUT_DIR, file_name)
    output_path = os.path.join(OUTPUT_DIR, Path(file_name).stem + ".md")

    config = {
        "output_format": "markdown",
        "force_ocr": True,
        "paginate_output": True,
        "disable_image_extraction": True,
    }
    config_parser = ConfigParser(config)

    converter = PdfConverter(
        config=config_parser.generate_config_dict(),
        artifact_dict=create_model_dict(),
        processor_list=config_parser.get_processors(),
        renderer=config_parser.get_renderer(),
        llm_service=config_parser.get_llm_service(),
    )

    rendered = converter(input_path)
    markdown_text, _, _ = text_from_rendered(rendered)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown_text)

    return output_path

def convert_with_mineru(file_name: str) -> str:
    """Convert a PDF to Markdown using MinerU.

    Uses the "pipeline" backend, which runs straight on the GPU via
    torch/paddle -- no Docker, no separate inference server to babysit.
    """
    input_path = os.path.join(INPUT_DIR, file_name)
    stem = Path(file_name).stem
    output_path = os.path.join(OUTPUT_DIR, stem + ".md")

    pdf_bytes = read_fn(input_path)

    do_parse(
        output_dir=OUTPUT_DIR,
        pdf_file_names=[stem],
        pdf_bytes_list=[pdf_bytes],
        p_lang_list=["en"],
        backend="pipeline",
        parse_method="ocr",
        formula_enable=True,
        table_enable=True,
        image_analysis=False,
    )

    nested_md_path = os.path.join(OUTPUT_DIR, stem, "ocr", f"{stem}.md")
    shutil.copyfile(nested_md_path, output_path)

    return output_path

def convert_with_docling(file_name: str) -> str:
    """Convert a PDF to Markdown using Docling."""
    input_path = os.path.join(INPUT_DIR, file_name)
    output_path = os.path.join(OUTPUT_DIR, Path(file_name).stem + ".md")

    pipeline_options = PdfPipelineOptions(
        do_ocr=True,
        do_table_structure=True,
        do_formula_enrichment=True,
        generate_picture_images=False,
    )
    pipeline_options.ocr_options = EasyOcrOptions(force_full_page_ocr=True)

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )

    result = converter.convert(input_path)
    document = result.document

    markdown_text = document.export_to_markdown(
        page_break_placeholder="\n\n---\n\n"
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown_text)

    return output_path

if __name__ == "__main__":
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)