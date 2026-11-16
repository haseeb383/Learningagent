import json
import time
import requests
import sys
import base64
from pathlib import Path

HOST = "http://127.0.0.1:11434"
MODEL = "qwen35-2b-q4:latest"

EXAMPLE_PROMPT = """here three images one is the question this is math question i have attempted then an answer this is the answer which i have written and then a marking scheme this is the marking scheme of the question i want you to check my answer against the marking scheme tell me exactly how many marks i get what i missed what i got wrong with proper quotations from my answer image and proper quotation from the marking scheme no need to be linient be as harsh as possible give a reason behing each mark i get and how how that is specified in the marking scheme that i should get the mark"""

IMAGE_PATH = "datapipline/pastpaperspipline/scripts/enrichment/"
IMAGE_NAMES = ["E:\coding\Projects\learningagent\datapipline\pastpaperspipline\scripts\enrichment\markingscheme.png",
               "E:\coding\Projects\learningagent\datapipline\pastpaperspipline\scripts\enrichment\answer.png",
               "E:\coding\Projects\learningagent\datapipline\pastpaperspipline\scripts\enrichment\question.png"]

def t0_bs64(image_path):
  return base64.b64encode(image_path.read_bytes()).decode()

def ask(prompt):
  # check if the server is up and running
  try:
    requests.get(f"{HOST}/api/version", timeout=5).raise_for_status()
  except requests.RequestException as e:
    sys.exit(f"Ollama not reachable at {HOST}. Start with: E:\\ollamaa\\ollama.exe serve\n{e}")

  images_b64 = [t0_bs64(Path(p)) for p in IMAGE_NAMES]

  payload = {
    "model": MODEL,
    "messages": [{"role": "user", "content": prompt, "images": images_b64}],
    "stream": True,
    }

  parts = []
  started = time.time()
  res = requests.post(url=f"{HOST}/api/chat", json=payload, stream=True, timeout=(5, 600))
  sys.exit(res)
  res.raise_for_status()
  for line in res.iter_lines():
    if not line:
      continue
    chunk = json.loads(line)
    if chunk.get("error"):
      sys.exit(chunk["error"])
    text = chunk.get("message", {}).get("content", "")
    if text:
      parts.append(text)
      print(text, end="", flush=True)
    if chunk.get("done"):
      tokens = chunk.get("eval_count", 0)
      seconds = chunk.get("eval_duration", 1) / 1e9
      print(f"\n\n[{tokens} tokens, {tokens / seconds:.1f} tok/s, {time.time() - started:.1f}s total]")
  return "".join(parts)

if "__main__" == __name__:
  # ask(" ".join(sys.argv[1:]) or "In one sentence, what is a tensor?")
  # images_b64 = [t0_bs64(Path(IMAGE_PATH + p)) for p in IMAGE_NAMES]
  # print(images_b64)
  ask(EXAMPLE_PROMPT)