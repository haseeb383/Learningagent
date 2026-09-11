from langchain_openrouter import ChatOpenRouter
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from extract_lines import extract_lines

pdf_path = "datapipline/pastpaperspipline/downlaods/9709_m26_qp_52.pdf"

lines = extract_lines(pdf_path=pdf_path)

with open("datapipline/pastpaperspipline/scripts/instructions.md", "r", encoding="utf-8") as f:
    instructions = f.read()

model = ChatOpenRouter(
  api_key="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",
  model="nvidia/nemotron-3-ultra-550b-a55b:free"
)


# model = ChatGroq(
#   model="openai/gpt-oss-20b",
#   api_key="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"
# )

ans = model.invoke(instructions + "here is the input" + lines)
print(ans.content)