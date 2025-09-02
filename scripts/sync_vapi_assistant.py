import logging
import requests
import os

from services.vapi_client import (
    create_assistant,
    update_assistant,
    save_assistant_id,
    load_assistant_id,
    get_assistant,   # make sure this exists in vapi_client.py
)

logger = logging.getLogger(__name__)
API_BASE_URL = os.getenv("PUBLIC_BASE_URL")

# -------------------------------
# Fetch configs from your FastAPI
# -------------------------------

def fetch_assistant_config():
    """Fetch assistant config (voice, model, transcriber, webhook) from DB API."""
    url = f"{API_BASE_URL}/bot-config"
    res = requests.get(url, timeout=10)
    res.raise_for_status()
    logger.info("Fetched assistant config successfully from %s", url)
    return res.json()


def fetch_tool_ids():
    """Fetch available tool IDs from DB API."""
    url = f"{API_BASE_URL}/get-tools"
    res = requests.get(url, timeout=10)
    res.raise_for_status()
    logger.info("Fetched tool IDs successfully from %s", url)

    tools = res.json()
    # Extract just the AVAILABLE_TOOL_IDS values
    return [tool["AVAILABLE_TOOL_IDS"] for tool in tools if "AVAILABLE_TOOL_IDS" in tool]


# -------------------------------
# Utility
# -------------------------------

READ_ONLY_FIELDS = {"id", "orgId", "createdAt", "updatedAt", "isServerUrlSecretSet"}

def clean_payload(payload: dict) -> dict:
    """Remove fields not allowed in update."""
    return {k: v for k, v in payload.items() if k not in READ_ONLY_FIELDS}


# -------------------------------
# Main sync function
# -------------------------------

def sync_assistant():
    config = fetch_assistant_config()
    assistant_id = load_assistant_id()
    res = None

    existing_assistant = None
    if assistant_id:
        try:
            # ✅ Proper fetch using GET /assistants/{id}
            existing_assistant = get_assistant(assistant_id)
        except Exception as e:
            logger.warning("Could not fetch existing assistant: %s", e)

    # 🔥 Fetch dynamic tool IDs from your FastAPI API
    tool_ids = fetch_tool_ids()

    payload = {
        **(existing_assistant or {}),  # preserve fields like systemPrompt
        **config,                      # override with DB config
        "model": {
            **(existing_assistant.get("model", {}) if existing_assistant else {}),
            **config.get("model", {}),
            "toolIds": tool_ids,
        }
    }

    # 🚀 Clean up payload before sending
    payload = clean_payload(payload)

    if assistant_id:
        try:
            res = update_assistant(assistant_id, payload)
            logger.info("Assistant updated: %s", res)
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                logger.info("Saved assistant not found in VAPI, creating a new one...")
                res = create_assistant(payload)
                if "id" in res:
                    save_assistant_id(res["id"])
                logger.info("Assistant created: %s", res)
            else:
                logger.exception("Failed to update assistant")
                raise
    else:
        res = create_assistant(payload)
        if "id" in res:
            save_assistant_id(res["id"])
        logger.info("Assistant created: %s", res)

    return res
