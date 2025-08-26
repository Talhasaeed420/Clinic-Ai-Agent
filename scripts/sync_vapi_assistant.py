from services.vapi_client import (
    create_tool,
    create_assistant,
    update_assistant,
    save_assistant_id,
    load_assistant_id
)
from clinic_configuration.assistant_config import tools_payloads, assistant_payload
import sys

if __name__ == "__main__":
    # 1️⃣ Create tools
    tool_ids = []
    for tool in tools_payloads():
        res = create_tool(tool)
        if "id" not in res:
            sys.exit(1)
        tool_ids.append(res["id"])

    # 2️⃣ Create or update assistant
    assistant_id = load_assistant_id()
    payload = assistant_payload(tool_ids)

    if assistant_id:
        res = update_assistant(assistant_id, payload)
    else:
        res = create_assistant(payload)
        if "id" in res:
            save_assistant_id(res["id"])
