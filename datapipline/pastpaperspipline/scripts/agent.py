import os
import numpy as np
from dotenv import dotenv_values
from extract_lines import extract_lines
from langchain_openrouter import ChatOpenRouter

config = dotenv_values(".env")

OPENROUTER_API_KEY = config.get("OPENROUTER_API_KEY")

pdf_path = "datapipline/pastpaperspipline/scripts/9709_w25_qp_55.pdf"

lines = extract_lines(pdf_path=pdf_path)

with open("datapipline/pastpaperspipline/scripts/instructions.md", "r", encoding="utf-8") as f:
    instructions = f.read()

model = ChatOpenRouter(
  api_key=OPENROUTER_API_KEY,
  model="nvidia/nemotron-3-ultra-550b-a55b:free"
)

ans = model.invoke(instructions + "here is the input" + lines)
np.savez('datapipline/pastpaperspipline/scripts/coordinates.npz', values=ans.content,)
print(ans.content)
print(f"coordinates are saved in coordinates.npz")