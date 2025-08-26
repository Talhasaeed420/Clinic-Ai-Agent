import os, requests
import json

BASE_URL = "https://api.vapi.ai"
HEADERS = {
    "Authorization": f"Bearer {os.getenv('VAPI_API_KEY')}",
    "Content-Type": "application/json"
}

# --- Tools / Assistant API --- #

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


def update_assistant(assistant_id, payload):
    url = f"{BASE_URL}/assistant/{assistant_id}"
    response = requests.patch(url, headers=HEADERS, json=payload)
    print("🔎 Assistant update raw response:", response.status_code, response.text)
    response.raise_for_status()
    return response.json()


# --- Store assistant ID locally --- #
def save_assistant_id(assistant_id):
    with open(".assistant.json", "w") as f:
        json.dump({"assistant_id": assistant_id}, f)


def load_assistant_id():
    if not os.path.exists(".assistant.json"):
        return None
    with open(".assistant.json") as f:
        return json.load(f).get("assistant_id")
