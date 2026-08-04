#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform

PACKAGES = {
    "langchain": [
        "langchain",
        "langchain-openai",
        "langgraph",
        "langgraph-checkpoint-sqlite",
        "python-dotenv",
        "requests",
    ],
    "crewai": [
        "crewai",
        "crewai-tools",
        "python-dotenv",
        "requests",
    ],
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("environment", choices=sorted(PACKAGES))
    args = parser.parse_args()
    versions = {name: importlib.metadata.version(name) for name in PACKAGES[args.environment]}
    print(json.dumps({
        "environment": args.environment,
        "packages": versions,
        "python": platform.python_version(),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
