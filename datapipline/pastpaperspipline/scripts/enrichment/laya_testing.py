import time
import requests

# The absolute full address required by Windows network protocols
SERVER_URL = "http://127.0.0.1:8080/v1/systemone"

payload = {
  "state": "The user is attempting to purchase a premium subscription. Their credit card expired last month.",
  "model": "laya-english",
  "questions": {
    "q_fraud": {
      "type": "noul",
      "instructions": "Is there a high likelihood of fraudulent activity?"
    }
  }
}

print("Sending query to Laya memory server...")
print("[Note] If this is your first query, it will take a moment to load the model parameters...")

# We set timeout=120 so the script patiently waits for the initial model load
start_time = time.perf_counter()

try:
    response = requests.post(SERVER_URL, json=payload, timeout=120)
    latency = (time.perf_counter() - start_time) * 1000
    
    if response.status_code == 200:
        print(f"\n[Success] Response received in {latency:.2f}ms!")
        print("-" * 50)
        print(response.json())
    else:
        print(f"\n[Error] Status code: {response.status_code}")
        print(response.text)

except requests.exceptions.Timeout:
    print("\n[Error] The server took too long to load the model files.")
except requests.exceptions.ConnectionError:
    print("\n[Error] Connection refused. Verify your 'run-laya.bat' window is completely open.")
