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

def extract_fields():
  pass