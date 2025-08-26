import os
import requests
import json
import logging

logger = logging.getLogger(__name__)

BASE_URL = "https://api.vapi.ai"
HEADERS = {
    "Authorization": f"Bearer {os.getenv('VAPI_API_KEY')}",
    "Content-Type": "application/json"
}

# --- Tools / Assistant API --- #

def create_tool(payload):
    response = requests.post(f"{BASE_URL}/tool", headers=HEADERS, json=payload)
    logger.info("🔎 Tool creation raw response: %s %s", response.status_code, response.text)
    response.raise_for_status()
    return response.json()


def create_assistant(payload):
    response = requests.post(f"{BASE_URL}/assistant", headers=HEADERS, json=payload)
    logger.info("🔎 Assistant creation raw response: %s %s", response.status_code, response.text)
    response.raise_for_status()
    return response.json()


def update_assistant(assistant_id, payload):
    url = f"{BASE_URL}/assistant/{assistant_id}"
    response = requests.patch(url, headers=HEADERS, json=payload)
    logger.info("🔎 Assistant update raw response: %s %s", response.status_code, response.text)
    response.raise_for_status()
    return response.json()


# --- Store assistant ID locally --- #
def save_assistant_id(assistant_id):
    try:
        with open(".assistant.json", "w") as f:
            json.dump({"assistant_id": assistant_id}, f)
        logger.info("Assistant ID saved locally: %s", assistant_id)
    except Exception as e:
        logger.error("Failed to save assistant ID: %s", e)
        raise


def load_assistant_id():
    if not os.path.exists(".assistant.json"):
        logger.debug("No saved assistant ID file found")
        return None
    try:
        with open(".assistant.json") as f:
            assistant_id = json.load(f).get("assistant_id")
            logger.info("Loaded assistant ID: %s", assistant_id)
            return assistant_id
    except Exception as e:
        logger.error("Failed to load assistant ID: %s", e)
        return None
