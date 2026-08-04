from __future__ import annotations

import json
import sys

version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
if sys.version_info[:2] != (3, 12):
    raise SystemExit(f"Expected Python 3.12, received {version}")
print(json.dumps({"test_id": "PY-CR-001", "python": version, "status": "pass"}, sort_keys=True))
