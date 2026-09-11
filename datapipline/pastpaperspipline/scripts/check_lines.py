import ast

with open(r'D:\chrome download\importantfiles\lines.md', encoding='utf-8', errors='replace') as f:
    data = ast.literal_eval(f.read())

for p in data:
    if p["page_number"] >= 2:
        print(f'\n=== Page {p["page_number"]} ===')
        for line in p["lines"]:
            text = line["text"][:100].encode('ascii', 'replace').decode('ascii')
            print(f'  y={line["y0"]:.1f} x={line["x0"]:.1f}: {text}')