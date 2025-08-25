from services.vapi_client import create_tool, create_assistant
from clinic_configuration.assistant_config import tools_payloads, assistant_payload
import sys

if __name__ == "__main__":
    # 1. Create tools
    tool_ids = []
    for tool in tools_payloads():
        res = create_tool(tool)
        print("Created tool response:", res)

        if "id" not in res:
            print("❌ Failed to create tool. Exiting.")
            sys.exit(1)

        tool_ids.append(res["id"])

    # 2. Create assistant
    payload = assistant_payload(tool_ids)
    res = create_assistant(payload)
    print("Created assistant response:", res)

    if "id" not in res:
        print("❌ Failed to create assistant.")
        sys.exit(1)
