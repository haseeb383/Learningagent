import json
import requests
from dotenv import dotenv_values

config = dotenv_values(".env")

OPENROUTER_API_KEY = config.get("OPENROUTER_API_KEY")
OPENCODE_ZEN_API_KEY = config.get("OPENCODE_ZEN_API_KEY")

def query_jev_decision():
  app_state = {
      "user_role": "free_tier_user",
      "action_requested": "export_10k_records",
      "billing_status": "past_due",
      "device_trusted": False,
      "consecutive_failures": 3
  }
  
  url = "https://opencode.ai/inference/systemone/v1/systemone"
  headers = {
    "Authorization": f"Bearer {OPENCODE_ZEN_API_KEY}",
    "Content-Type": "application/json"
}
  
  payload = {
    "model": "jev-1.13-free", 
    "state": json.dumps(app_state),
    "questions": {
        "deny_access": {
          "type": "noul",
          "instructions": "Should this high-volume account action be denied based on billing and failure state?"
        },
        "is_suspicious": {
          "type": "noul",
          "instructions": "Does this activity look like an automated bot or high-frequency abuse?"
        }
      }
    }
  
  try:
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    
    data = response.json()
    print("--- Jev Decision Structured Output ---")
    print(json.dumps(data, indent=2))
    
    answers = data.get("answers", {})
    if answers.get("deny_access", {}).get("probability", 0) > 0.80:
      print("\n🚨 Application Logic Triggered: Request Blocked.")
          
  except requests.exceptions.RequestException as e:
    print(f"API Error communicating with Zen Gateway: {e}")

if __name__ == "__main__":
  query_jev_decision()
