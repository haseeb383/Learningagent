import base64
import json
from openai import OpenAI
from dotenv import dotenv_values


config = dotenv_values(".env")
SCALE_DOWN_CDMS_API_KEY = config.get("SCALE_DOWN_CDMS_API_KEY")

client = OpenAI(base_url="https://api.scaledown.xyz/v1", api_key=SCALE_DOWN_CDMS_API_KEY)

image_path = "datapipline/pastpaperspipline/chunks/9702_s26_qp_22/9702_s26_qp_22_q1_a.png"
def encode_image(image_path):
  with open(image_path, "rb") as image_file:
    base64_image = base64.b64encode(image_file.read()).decode("utf-8")
    return base64_image

base64_image = encode_image(image_path)
test_invoice = "Acme Corp invoiced $500 on 2024-01-05."


def extract_from_invoice(client, content):
  r = client.chat.completions.create(
    model="extract",
    messages=[{"role": "user", "content": content}],
    response_format={
      "type": "json_schema",
      "json_schema": {
          "name": "invoice",
          "schema": {
            "type": "object",
            "properties": {
              "vendor": {"type": "string", "description": "company name"},
              "amount": {"type": "string", "description": "dollar amount"},
              "date": {"type": "string", "description": "invoice date"},
            },
          },
        },
      },
    )
  result = json.loads(r.choices[0].message.content)
  return result["entities"]

def extract_marks_from_images(image):
  pass
  r = client.chat.completions.create(
    model="extract",
    messages=[{"role": "user", "content": "Extract the marks of the question."}],
    response_format={
      "type": "json_schema",
      "json_schema": {
        "name": "question",
        "schema": {
            "type": "object",
            "properties": {
              "marks": {"type": "integer", "description": "marks of the quesiton"},
          },
        },
      },
    },
    extra_body={"document": image, "document_mime_type": "image/png"},
  )
  print(r)
  # return json.loads(r.choices[0].message.content)["entities"]

extract_marks_from_images(base64_image)