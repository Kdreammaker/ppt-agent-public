from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]


def run(args: list[str]) -> dict:
    process = subprocess.run(args, cwd=BASE_DIR, capture_output=True, text=True, check=True)
    stdout = process.stdout.strip()
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        payload = {"stdout": stdout}
    return {"command": args, "payload": payload}


def main() -> int:
    checks = [
        run([sys.executable, "scripts/ppt_agent.py", "doctor"]),
        run([sys.executable, "scripts/ppt_agent.py", "validate-guide", "data/fixtures/lumaloop_guide"]),
        run([sys.executable, "scripts/ppt_agent_mcp_adapter.py", "--list-tools"]),
    ]
    tool_names = {tool["name"] for tool in checks[2]["payload"].get("tools", [])}
    required_tools = {
        "mode_choice",
        "sparse_request_intake",
        "intent_strategy_compose",
        "guide_packet_intake",
        "deck_plan_compose",
        "two_variant_auto_build",
        "qa_validation",
        "project_summary",
    }
    missing_tools = sorted(required_tools - tool_names)
    status = "pass" if not missing_tools and checks[0]["payload"].get("status") == "ready" else "fail"
    print(
        json.dumps(
            {
                "status": status,
                "checks": checks,
                "missing_tools": missing_tools,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
