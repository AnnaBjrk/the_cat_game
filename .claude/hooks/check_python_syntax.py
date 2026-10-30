"""PostToolUse hook: report syntax errors in a Python file Claude just changed."""

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
