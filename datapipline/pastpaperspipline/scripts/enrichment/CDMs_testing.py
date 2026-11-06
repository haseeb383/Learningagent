import base64
import requests
import json
from openai import OpenAI
from dotenv import dotenv_values

config = dotenv_values(".env")
SCALE_DOWN_CDMS_API_KEY = config.get("SCALE_DOWN_CDMS_API_KEY")
CDMS_API_KEY = config.get("CDMS_API_KEY_PROD")

client = OpenAI(base_url="https://api.scaledown.xyz/v1", api_key=SCALE_DOWN_CDMS_API_KEY)
second_client = OpenAI(base_url="https://api.scaledown.xyz/v1", api_key=CDMS_API_KEY)

def encode_document(path):
  with open(path, "rb") as f:
    document = base64.b64encode(f.read()).decode()
  return document

def extract_coordinates(client, question_lines, current_state, instruction):
  r = client.chat.completions.create(
    model="extract",
    messages=[{"role": "user", "content": instruction + "\n" + "here is the input" + "\n" + question_lines + f"\nand here is the current state {current_state}"}],
    response_format={
      "type": "json_schema",
      "json_schema": {
          "name": "pdf lines",
          "schema": {
            "type": "object",
            "properties": {
              "start_y": {"type": "float", "description": "the start_y corrdinate"},
              "end_y": {"type": "float", "description": "the end_y corrdinate"},
              "start_page": {"type": "integer", "description": "the start_page number"},
              "end_page": {"type": "integer", "description": "the end_page number"},
              "question": {"type": "string", "description": "the question and part you extracted"}
            },
          },
        },
      },
    )
  result = json.loads(r.choices[0].message.content)
  return result["entities"]

def choose_topic_and_rate(client, image, topic_list):
  r = client.chat.completions.create(
    model="extract",
    messages=[{"role": "user", "content": f"Classify the following question into exactly one topic from this list: {topic_list}"}],
    response_format={
      "type": "json_schema",
      "json_schema": {
          "name": "invoice",
          "schema": {
            "type": "object",
            "properties": {
              "vendor": {"type": "string", "description": "which topic this question is from the list"},
            },
          },
        },
      },
    extra_body={"document": image, "document_mime_type": "image/jpeg"},
  )
  result = json.loads(r.choices[0].message.content)
  print(result["entities"])

topic_list = ["user defined datatypes", "file organization and access", "recursion", "programming paradigms", "file processing and exceptions handeling", "unclassified"]
image_path = "datapipline/pastpaperspipline/chunks/9618_s26_qp_41/9618_s26_qp_41_q1_.png"
base64_image = encode_document(image_path)
choose_topic_and_rate(second_client, base64_image, topic_list)
