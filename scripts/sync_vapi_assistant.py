from clinic_configuration.bot_tools import tools_payloads
import logging
logger = logging.getLogger(__name__)
import sys
import requests
import os

from services.vapi_client import (
    create_tool,
    create_assistant,
    update_assistant,
    save_assistant_id,
    load_assistant_id
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


def sync_assistant():
    """Main logic: create tools, fetch config, and create/update assistant."""
    # 1️⃣ Create tools from local file
    tool_ids = []
    for tool in tools_payloads():
        res = create_tool(tool)
        if "id" not in res:
            logger.error("Tool creation failed: %s", res)
            raise RuntimeError(f"Tool creation failed: {res}")
        logger.info("🔎 Tool created: %s", res["id"])
        tool_ids.append(res["id"])

    # 2️⃣ Fetch assistant config from API
    config = fetch_assistant_config()

    # 3️⃣ Merge DB assistant config with tool IDs
    payload = {
        **config,
        "model": {
            **config["model"],
            "toolIds": tool_ids
        }
    }

    # 4️⃣ Load assistant ID and create/update
    assistant_id = load_assistant_id()
    res = None

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
