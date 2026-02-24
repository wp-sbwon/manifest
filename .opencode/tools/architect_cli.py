#!/usr/bin/env python3
"""CLI for architect tools: write_prd, write_architecture. Invoked by OpenCode tool definitions."""
import json
import sys
from pathlib import Path

# Project root: .opencode/tools/architect_cli.py -> repo root
_repo = Path(__file__).resolve().parent.parent.parent
_src = _repo / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from manifest.opencode.architect import write_prd, write_architecture


def main() -> int:
    if len(sys.argv) < 3:
        print(json.dumps({"ok": False, "error": "Usage: architect_cli <manifest_dir> <cmd> [payload_json]"}))
        return 1
    manifest_dir = Path(sys.argv[1]).resolve()
    cmd = sys.argv[2]
    payload_raw = sys.argv[3] if len(sys.argv) > 3 else ""

    try:
        if cmd == "write_prd":
            if payload_raw:
                data = json.loads(payload_raw) if payload_raw.startswith("{") else {"mission": payload_raw}
            else:
                data = {"mission": ""}
            result = write_prd(manifest_dir, data)
        elif cmd == "write_architecture":
            payload = json.loads(payload_raw) if payload_raw else {}
            result = write_architecture(manifest_dir, payload)
        else:
            result = {"ok": False, "error": f"Unknown command: {cmd}"}
    except json.JSONDecodeError as e:
        result = {"ok": False, "error": f"Invalid JSON: {e}"}
    except Exception as e:
        result = {"ok": False, "error": str(e)}

    print(json.dumps(result))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
