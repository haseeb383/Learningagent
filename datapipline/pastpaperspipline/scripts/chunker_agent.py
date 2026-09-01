import os
import re
import json
import time
from typing import TypedDict, List, Dict, Optional, Any
import fitz
from PIL import Image
import torch
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor, BitsAndBytesConfig
from qwen_vl_utils import process_vision_info
from langgraph.graph import StateGraph, END

MODEL_ID = "Qwen/Qwen2.5-VL-7B-Instruct"
INSTRUCTIONS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instructions.md")
IMAGE_LONG_SIDE = 1120
PATCH = 28
OUTPUT_RENDER_ZOOM = 3.0
CROP_PADDING_PX_AT_OUTPUT_ZOOM = 10
MAX_NEW_TOKENS = 3000
MAX_JSON_RETRIES = 2

_model = None
_processor = None

def load_model():
    global _model, _processor
    if _model is not None:
        return _model, _processor

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )

    print(f"Loading {MODEL_ID} in 4-bit... (first time will download ~5-8GB)")
    _model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        MODEL_ID,
        quantization_config=bnb_config,
        device_map="auto",
        torch_dtype=torch.float16,
    )
    _processor = AutoProcessor.from_pretrained(MODEL_ID)
    print("Model loaded.")
    return _model, _processor

def _resize_for_model(img: Image.Image, long_side=IMAGE_LONG_SIDE, patch=PATCH):
    w, h = img.size
    scale = long_side / max(w, h)
    new_w = max(patch, round(w * scale / patch) * patch)
    new_h = max(patch, round(h * scale / patch) * patch)
    resized = img.resize((new_w, new_h), Image.LANCZOS)
    return resized, new_w, new_h

def _render_page_for_model(doc, page_num_1idx):
    page = doc[page_num_1idx - 1]
    mat = fitz.Matrix(2.0, 2.0)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    return _resize_for_model(img)

_high_res_cache: Dict[int, Image.Image] = {}

def _render_page_high_res(doc, page_num_1idx, cache):
    if page_num_1idx in cache:
        return cache[page_num_1idx]
    page = doc[page_num_1idx - 1]
    mat = fitz.Matrix(OUTPUT_RENDER_ZOOM, OUTPUT_RENDER_ZOOM)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    cache[page_num_1idx] = img
    return img

class ChunkerState(TypedDict):
    pdf_path: str
    output_dir: str
    total_pages: int
    window_size: int
    window_start_page: int
    carry_over: List[Dict[str, Any]]
    finalized: List[Dict[str, Any]]
    warnings: List[str]
    done: bool


def _build_messages(system_prompt: str, window_pages: List[int],
                     page_renders: Dict[int, Any], carry_over: List[Dict]):
    content = []
    if carry_over:
        content.append({
            "type": "text",
            "text": "Carried-over question(s) still open from a previous window:\n"
                    + json.dumps(carry_over, indent=2)
        })
    else:
        content.append({"type": "text", "text": "No carried-over open question."})

    content.append({
        "type": "text",
        "text": f"You are being shown pages {window_pages} of the PDF, in order. "
                f"Analyze all of them and return the JSON array now."
    })

    for p in window_pages:
        img, W, H = page_renders[p]
        content.append({"type": "text", "text": f"--- Page {p} (image is {W}x{H} px) ---"})
        content.append({"type": "image", "image": img})

    messages = [
        {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
        {"role": "user", "content": content},
    ]
    return messages


def _extract_json(text: str):
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"No JSON array found in model output: {text[:300]}")
    return json.loads(text[start:end + 1])


def _call_model(system_prompt: str, window_pages: List[int],
                 page_renders: Dict[int, Any], carry_over: List[Dict]) -> List[Dict]:
    model, processor = load_model()

    messages = _build_messages(system_prompt, window_pages, page_renders, carry_over)
    last_error = None

    for attempt in range(MAX_JSON_RETRIES + 1):
        text_prompt = processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = processor(
            text=[text_prompt],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        ).to(model.device)

        with torch.no_grad():
            generated = model.generate(**inputs, max_new_tokens=MAX_NEW_TOKENS, do_sample=False)
        trimmed = [out[len(inp):] for inp, out in zip(inputs.input_ids, generated)]
        output_text = processor.batch_decode(
            trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )[0]

        try:
            return _extract_json(output_text)
        except Exception as e:
            last_error = e
            # ask it to fix its own output on retry
            messages.append({"role": "assistant", "content": [{"type": "text", "text": output_text}]})
            messages.append({
                "role": "user",
                "content": [{"type": "text", "text":
                    f"That was not valid JSON ({e}). Reply again with ONLY the corrected "
                    f"JSON array, no other text."}]
            })

    raise RuntimeError(f"Model failed to produce valid JSON after retries: {last_error}")

def _key(item):
    return (str(item.get("question_number")), item.get("part"))

def _merge_window_results(model_items: List[Dict], carry_over: List[Dict],
                           finalized: List[Dict], warnings: List[str]):
    carry_by_key = {_key(c): c for c in carry_over}
    seen_carry_keys = set()
    new_carry_over = []

    for item in model_items:
        k = _key(item)
        if k in carry_by_key:
            seen_carry_keys.add(k)
            prior = carry_by_key[k]
            merged = dict(prior)
            merged["pages"] = prior.get("pages", []) + [p for p in item.get("pages", []) if p not in prior.get("pages", [])]
            merged["bbox"] = prior.get("bbox", []) + item.get("bbox", [])
            for field in ("marks", "content_type", "topic_guess", "difficulty_guess"):
                if item.get(field) not in (None, [], ""):
                    merged[field] = item[field]
            if item.get("open"):
                new_carry_over.append(merged)
            else:
                merged["incomplete"] = False
                finalized.append(merged)
        else:
            item = dict(item)
            if item.get("open"):
                new_carry_over.append(item)
            else:
                item["incomplete"] = False
                finalized.append(item)

    for k, prior in carry_by_key.items():
        if k not in seen_carry_keys:
            warnings.append(
                f"Carried-over question {k} was not mentioned again in this window; "
                f"keeping it open one more window."
            )
            new_carry_over.append(prior)

    return new_carry_over

def make_graph(system_prompt: str):

    def node_init(state: ChunkerState) -> ChunkerState:
        doc = fitz.open(state["pdf_path"])
        state["total_pages"] = doc.page_count
        doc.close()
        state["window_start_page"] = 1
        state["carry_over"] = []
        state["finalized"] = []
        state["warnings"] = []
        state["done"] = False
        return state

    def node_process_window(state: ChunkerState) -> ChunkerState:
        doc = fitz.open(state["pdf_path"])
        start = state["window_start_page"]
        end = min(start + state["window_size"] - 1, state["total_pages"])
        window_pages = list(range(start, end + 1))

        page_renders = {p: _render_page_for_model(doc, p) for p in window_pages}
        doc.close()

        print(f"Processing pages {window_pages} (carry_over={[ _key(c) for c in state['carry_over'] ]})...")

        model_items = _call_model(system_prompt, window_pages, page_renders, state["carry_over"])

        state["carry_over"] = _merge_window_results(
            model_items, state["carry_over"], state["finalized"], state["warnings"]
        )
        state["window_start_page"] = end + 1
        return state

    def route(state: ChunkerState):
        if state["window_start_page"] > state["total_pages"]:
            return "finalize"
        return "continue"

    def node_finalize(state: ChunkerState) -> ChunkerState:
        for item in state["carry_over"]:
            item = dict(item)
            item["incomplete"] = True
            state["warnings"].append(
                f"Question {_key(item)} never closed by end of document; saved as-is."
            )
            state["finalized"].append(item)
        state["carry_over"] = []
        state["done"] = True
        return state

    graph = StateGraph(ChunkerState)
    graph.add_node("init", node_init)
    graph.add_node("process_window", node_process_window)
    graph.add_node("finalize", node_finalize)

    graph.set_entry_point("init")
    graph.add_edge("init", "process_window")
    graph.add_conditional_edges("process_window", route, {
        "continue": "process_window",
        "finalize": "finalize",
    })
    graph.add_edge("finalize", END)

    return graph.compile()

def _safe_name(question_number, part):
    base = f"q{question_number}"
    if part:
        base += str(part)
    return re.sub(r"[^a-zA-Z0-9_\-]", "_", base)


def _crop_item(doc, item, high_res_cache):
    crops = []
    for entry in item.get("bbox", []):
        page_num = entry["page"]
        model_img, model_w, model_h = _render_page_for_model(doc, page_num)
        high_img = _render_page_high_res(doc, page_num, high_res_cache)
        hw, hh = high_img.size

        fx1 = max(0.0, min(1.0, entry["x1"] / model_w))
        fy1 = max(0.0, min(1.0, entry["y1"] / model_h))
        fx2 = max(0.0, min(1.0, entry["x2"] / model_w))
        fy2 = max(0.0, min(1.0, entry["y2"] / model_h))
        if fx2 <= fx1 or fy2 <= fy1:
            continue

        x1 = int(fx1 * hw) - CROP_PADDING_PX_AT_OUTPUT_ZOOM
        y1 = int(fy1 * hh) - CROP_PADDING_PX_AT_OUTPUT_ZOOM
        x2 = int(fx2 * hw) + CROP_PADDING_PX_AT_OUTPUT_ZOOM
        y2 = int(fy2 * hh) + CROP_PADDING_PX_AT_OUTPUT_ZOOM
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(hw, x2), min(hh, y2)
        if x2 <= x1 or y2 <= y1:
            continue

        crops.append(high_img.crop((x1, y1, x2, y2)))

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
            padded = Image.new("RGB", (width, c.height), "white")
            padded.paste(c, (0, 0))
            c = padded
        combined.paste(c, (0, y_off))
        y_off += c.height
    return combined

def _save_outputs(pdf_path: str, output_dir: str, finalized: List[Dict], warnings: List[str]):
    os.makedirs(output_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    high_res_cache: Dict[int, Image.Image] = {}

    metadata = []
    for item in finalized:
        img = _crop_item(doc, item, high_res_cache)
        fname = None
        if img is not None:
            fname = _safe_name(item.get("question_number"), item.get("part")) + ".png"
            img.save(os.path.join(output_dir, fname))
        else:
            warnings.append(f"Could not crop {_key(item)}: no valid bbox.")

        metadata.append({
            "question_number": item.get("question_number"),
            "part": item.get("part"),
            "pages": item.get("pages"),
            "marks": item.get("marks"),
            "content_type": item.get("content_type"),
            "topic_guess": item.get("topic_guess"),
            "difficulty_guess": item.get("difficulty_guess"),
            "incomplete": item.get("incomplete", False),
            "image_file": fname,
        })

    doc.close()

    with open(os.path.join(output_dir, "metadata.json"), "w") as f:
        json.dump({"source_pdf": pdf_path, "questions": metadata, "warnings": warnings}, f, indent=2)

    return metadata

def run_pipeline(pdf_path: str, output_root: str, window_size: int = 3):
    load_model()

    with open(INSTRUCTIONS_PATH, "r") as f:
        system_prompt = f.read()

    pdf_stem = os.path.splitext(os.path.basename(pdf_path))[0]
    output_dir = os.path.join(output_root, pdf_stem)

    graph = make_graph(system_prompt)

    initial_state: ChunkerState = {
        "pdf_path": pdf_path,
        "output_dir": output_dir,
        "total_pages": 0,
        "window_size": window_size,
        "window_start_page": 1,
        "carry_over": [],
        "finalized": [],
        "warnings": [],
        "done": False,
    }

    t0 = time.time()
    final_state = graph.invoke(initial_state, config={"recursion_limit": 500})
    elapsed = time.time() - t0

    metadata = _save_outputs(pdf_path, output_dir, final_state["finalized"], final_state["warnings"])

    print(f"\nDone in {elapsed:.1f}s. {len(metadata)} question/part chunks -> {output_dir}")
    if final_state["warnings"]:
        print(f"\n{len(final_state['warnings'])} warning(s):")
        for w in final_state["warnings"]:
            print(f"  - {w}")

    return metadata
