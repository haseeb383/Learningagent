import base64
import yaml
import json
from openai import OpenAI
from pathlib import Path
from dotenv import dotenv_values
from chunker import create_text_chunks
from extract_lines import extract_lines

"""fields to extract
1. marks
2. topic from a topic list
3. keywords list of keywords
4. 
"""
config = dotenv_values(".env")
with open("subject.yaml") as f:
  SYLLABUS = yaml.safe_load(f)
SCALE_DOWN_CDMS_API_KEY = config.get("SCALE_DOWN_CDMS_API_KEY")
CDMS_API_KEY = config.get("CDMS_API_KEY_PROD")

def encode_document(path):
  with open(path, "rb") as f:
    document = base64.b64encode(f.read()).decode()
  return document

def _topics_for(subject_code: str, paper: int) -> list[dict]:
  return [t['name'] for t in SYLLABUS[subject_code]["topics"] if paper in t["papers"]]

def find_topic_list(coord):
  question_info = coord['chunk_id'].split('_')
  paper_number = int(question_info[3][0])
  subject_code = question_info[0]
  topics = _topics_for(subject_code, paper_number)
  return topics

def extract_fields(topics, question_text, client):
  r = client.chat.completions.create(
  model="extract",
  messages=[{"role": "user", "content": f"Classify and extract from the following question {question_text} \n the topic into exactly one topic from this list: {topics} \n and the total marks of the question usually the marks are written in square brakets like this [Total: 4] but if it is multiple choice question it is of 1 mark"}],
  response_format={
    "type": "json_schema",
    "json_schema": {
        "name": "invoice",
        "schema": {
          "type": "object",
          "properties": {
            "topic": {"type": "string", "description": "which topic this question is from the list"},
            "marks": {"type": "string", "description": "the total marks of the question"}
          },
        },
      },
    },
  )
  result = json.loads(r.choices[0].message.content)
  print(result["entities"])

if __name__ == "__main__":
  client = OpenAI(base_url="https://api.scaledown.xyz/v1", api_key=SCALE_DOWN_CDMS_API_KEY)
  second_client = OpenAI(base_url="https://api.scaledown.xyz/v1", api_key=CDMS_API_KEY)
  pdf_path = "datapipline/pastpaperspipline/downlaods/9702_s26_qp_22.pdf"
  coord_path = f"datapipline\pastpaperspipline\coords\{Path(pdf_path).stem + ".json"}"
  with open(coord_path, "r") as f:
    coords = json.load(f)

  lines = extract_lines(pdf_path)
  text_chunks = create_text_chunks(lines, coords)
  topics = find_topic_list(coords[0])
  print(coords[0], "\n\n\n\n\n\n")
  print(topics, "\n\n\n\n\n\n")
  print(text_chunks[0], "\n\n\n\n\n\n")
  extract_fields(topics, text_chunks[0], second_client)
