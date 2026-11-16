import base64
import yaml
import json
from openai import OpenAI
import time
import requests
from pathlib import Path
from dotenv import dotenv_values
from chunker import create_text_chunks
from extract_lines import extract_lines

"""fields to extract
1. marks
2. topic from a topic list
3. keywords list of keywords
"""
config = dotenv_values(".env")
with open("subject.yaml") as f:
  SYLLABUS = yaml.safe_load(f)
SCALE_DOWN_CDMS_API_KEY = config.get("SCALE_DOWN_CDMS_API_KEY")
CDMS_API_KEY = config.get("CDMS_API_KEY_PROD")
JEV_API_KEY = config.get("OPENCODE_ZEN_API_KEY")
LAYA_SERVER_URL = "http://127.0.0.1:8080/v1/systemone"
JEV_SERVER_URL = "https://opencode.ai/inference/systemone/v1/systemone"

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

def extract_fields_CDM(topics, question_text, client):
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

def extract_field_laya(topics, question_text):
  payload = {
    "state": f"Classify and extract from the following question {question_text} \n the topic into exactly one topic from this list: {topics}",
    "model": "laya-multilingual",
    "max_len": 8192,
    "questions": {
      "q_topic": {
        "type": "choice",
        "instructions": "which topic this question is from the list",
        "criteria": topics
      }
    }
  }
  start_time = time.perf_counter()
  response = requests.post(LAYA_SERVER_URL, json=payload, timeout=120)
  latency = (time.perf_counter() - start_time) * 1000
  print(f"[Success] Response received in {latency}ms")
  print(response.json())
  return response.json()

def extract_feilds_JEV(topics, question_text):
  payload = {
    "state": {"question": f"Classify and extract from the following question {question_text} \n the topic into exactly one topic from this list: {topics}"},
    "model": "jev-1.13-free",
    "questions": {
      "q_topic": {
        "type": "choice",
        "instructions": "which topic this question is from the list",
        "criteria": {topic: f"Questions related to {topic}" for topic in topics}
      }
    }
  }

  header = {
    "Authorization": f"Bearer {JEV_API_KEY}",
    "Content-Type": "application/json"
  }

  start_time = time.perf_counter()
  response = requests.post(url=JEV_SERVER_URL, headers=header, json=payload)
  latency = (time.perf_counter() - start_time) * 1000
  print(f"[Success] Response received in {latency}ms")
  print(response.json())
  return response.json()

def extract_fields_LLM(topics, question_text):
  pass


if __name__ == "__main__":
  client = OpenAI(base_url="https://api.scaledown.xyz/v1", api_key=SCALE_DOWN_CDMS_API_KEY)
  second_client = OpenAI(base_url="https://api.scaledown.xyz/v1", api_key=CDMS_API_KEY)
  pdf_path = "datapipline/pastpaperspipline/downlaods/9702_m26_qp_12.pdf"
  # datapipline/pastpaperspipline/downlaods/9618_s26_qp_41.pdf
  # datapipline/pastpaperspipline/downlaods/9702_m26_qp_12.pdf
  coord_path = f"datapipline\pastpaperspipline\coords\{Path(pdf_path).stem + ".json"}"
  with open(coord_path, "r") as f:
    coords = json.load(f)

  lines = extract_lines(pdf_path)
  text_chunks = create_text_chunks(lines, coords)
  topics = find_topic_list(coords[0])
  # extract_fields_CDM(topics, text_chunks[0], second_client)
  # extract_field_laya(topics, text_chunks[0])
  # extract_feilds_JEV(topics, text_chunks[0])
