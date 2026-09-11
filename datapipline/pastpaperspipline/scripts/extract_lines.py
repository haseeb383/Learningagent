import ast
import fitz

def extract_lines(pdf_path: str) -> list[dict]:
  doc = fitz.open(pdf_path)
  pages_out = []

  for page_index in range(len(doc)):
    page = doc[page_index]
    raw = page.get_text("dict")

    lines_out = []
    for block in raw["blocks"]:
      if block.get("type") != 0:
        continue
      for line in block["lines"]:
          spans = line["spans"]
          if not spans:
            continue
          text = "".join(s["text"] for s in spans).strip()
          if not text:
            continue
          x0, y0, x1, y1 = line["bbox"]
          lines_out.append(
            {"text": text, "x0": round(x0, 1), "y0": round(y0, 1),
            "x1": round(x1, 1), "y1": round(y1, 1)}
          )

    lines_out.sort(key=lambda l: (l["y0"], l["x0"]))
    pages_out.append({"page_number": page_index + 1, "lines": lines_out})

  doc.close()
  data = ast.literal_eval(str(pages_out))
  lines = ""
  for p in data:
      if p["page_number"] >= 2:
          lines = lines + f'=== Page {p["page_number"]} === \n'
          # print(f'\n=== Page {p["page_number"]} === \n')
          for line in p["lines"]:
              text = line["text"][:100].encode('ascii', 'replace').decode('ascii')
              lines = lines + f'  y={line["y0"]:.1f} x={line["x0"]:.1f}: {text} \n'
              # print(f'  y={line["y0"]:.1f} x={line["x0"]:.1f}: {text}')
  return lines