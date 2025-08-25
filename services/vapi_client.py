import os, requests

BASE_URL = "https://api.vapi.ai"
HEADERS = {
    "Authorization": f"Bearer {os.getenv('VAPI_API_KEY')}",
    "Content-Type": "application/json"
}

def create_tool(payload):
    response = requests.post(f"{BASE_URL}/tool", headers=HEADERS, json=payload)
    print("🔎 Tool creation raw response:", response.status_code, response.text)
    response.raise_for_status()
    return response.json()

def create_assistant(payload):
    response = requests.post(f"{BASE_URL}/assistant", headers=HEADERS, json=payload)
    print("🔎 Assistant creation raw response:", response.status_code, response.text)
    response.raise_for_status()
    return response.json()
