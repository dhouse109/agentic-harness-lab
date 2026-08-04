from __future__ import annotations

import importlib.metadata
import json

import crewai
import crewai_tools
from crewai.flow import Flow, listen, start

packages = {
    name: importlib.metadata.version(name)
    for name in ("crewai", "crewai-tools")
}
assert Flow is not None and listen is not None and start is not None
print(json.dumps({"test_id": "PY-CR-002", "packages": packages, "status": "pass"}, sort_keys=True))
