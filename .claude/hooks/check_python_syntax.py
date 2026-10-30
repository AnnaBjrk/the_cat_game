"""PostToolUse hook: report syntax errors in a Python or JSON file Claude just changed."""

import json
import sys
from pathlib import Path

file_path = json.load(sys.stdin).get("tool_input", {}).get("file_path", "")
path = Path(file_path)

if path.suffix == ".py" and path.exists():
    try:
        compile(path.read_text(encoding="utf-8"), file_path, "exec")
    except SyntaxError as error:
        print(f"Syntax error in {file_path}: {error}", file=sys.stderr)
        sys.exit(2)  # Exit code 2 sends the message back to Claude.

if path.suffix == ".json" and path.exists():
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        print(f"Invalid JSON in {file_path}: {error}", file=sys.stderr)
        sys.exit(2)
