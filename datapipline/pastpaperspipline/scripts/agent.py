from langchain_openrouter import ChatOpenRouter
import os
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from extract_lines import extract_lines

load_dotenv()

OPENROUTER = os.getenv("OPENROUTER_API_KEY")
GROQ = os.getenv("GROQ_API_KEY")

pdf_path = "datapipline/pastpaperspipline/downlaods/9709_m26_qp_52.pdf"

lines = extract_lines(pdf_path=pdf_path)

with open("datapipline/pastpaperspipline/scripts/instructions.md", "r", encoding="utf-8") as f:
    instructions = f.read()

model = ChatOpenRouter(
  api_key=OPENROUTER,
  model="nvidia/nemotron-3-ultra-550b-a55b:free"
)


# model = ChatGroq(
#   model="openai/gpt-oss-20b",
#   api_key=GROQ
# )

ans = model.invoke(instructions + "here is the input" + lines)
print(ans.content)