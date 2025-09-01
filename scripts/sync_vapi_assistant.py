import logging
import requests
import os

from services.vapi_client import (
    create_assistant,
    update_assistant,
    save_assistant_id,
    load_assistant_id,
    get_assistant,   # 👈 you’ll need to add this helper in vapi_client.py
)

logger = logging.getLogger(__name__)
API_BASE_URL = os.getenv("PUBLIC_BASE_URL")

def fetch_assistant_config():
    """Fetch assistant config (voice, model, transcriber, webhook) from DB API."""
    url = f"{API_BASE_URL}/bot-config"
    res = requests.get(url, timeout=10)
    res.raise_for_status()
    logger.info("Fetched assistant config successfully from %s", url)
    return res.json()

# Put your actual tool IDs from VAPI dashboard
AVAILABLE_TOOL_IDS = [
    "1c4d2fd4-67b5-46b0-a695-a0ca4f6def25",  # get_doctors_by_specialty
    "1aa5d70f-59d2-4c65-9546-5cef1a726ff6"   # book_appointment
]

READ_ONLY_FIELDS = {"id", "orgId", "createdAt", "updatedAt", "isServerUrlSecretSet"}

def clean_payload(payload: dict) -> dict:
    """Remove fields not allowed in update."""
    return {k: v for k, v in payload.items() if k not in READ_ONLY_FIELDS}

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

    payload = {
        **(existing_assistant or {}),  # preserve fields like systemPrompt
        **config,                      # override with DB config
        "model": {
            **(existing_assistant.get("model", {}) if existing_assistant else {}),
            **config.get("model", {}),
            "toolIds": AVAILABLE_TOOL_IDS,
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
