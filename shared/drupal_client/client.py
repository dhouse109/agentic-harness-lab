#!/usr/bin/env python3
"""Standard-library client for shared deterministic Drupal operations.

This module owns HTTP/auth/envelope transport only. It intentionally contains no
prompt, model, framework orchestration, retry policy, sequencing, or persistence.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import ssl
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


class DrupalClientError(RuntimeError):
    """Sanitized client error that never includes credentials or auth headers."""

    def __init__(self, message: str, *, status: int | None = None, body: str = "") -> None:
        super().__init__(message)
        self.status = status
        self.body = body[:1000]


@dataclass(frozen=True)
class DrupalClient:
    base_url: str
    username: str
    password: str
    verify_tls: bool = True
    timeout_seconds: int = 60

    def find_images_needing_review(self, correlation_id: str) -> dict[str, Any]:
        return self._request(
            "GET",
            "/api/agentic-harness/v1/images-needing-review",
            correlation_id=correlation_id,
            operation_name="discovery",
        )

    def get_image_context(
        self,
        target: dict[str, Any],
        correlation_id: str,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/agentic-harness/v1/image-context",
            correlation_id=correlation_id,
            payload=target,
            operation_name="image-context",
        )

    def submit_recommendation(
        self,
        recommendation: dict[str, Any],
        correlation_id: str,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/agentic-harness/v1/recommendations",
            correlation_id=correlation_id,
            payload=recommendation,
            operation_name="recommendation-submission",
        )

    def get_recommendation_status(
        self,
        recommendation_id: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        identifier = recommendation_id.strip()
        if not identifier:
            raise DrupalClientError("A recommendation identifier is required.")
        return self._request(
            "GET",
            (
                "/api/agentic-harness/v1/recommendations/"
                f"{quote(identifier, safe='')}/status"
            ),
            correlation_id=correlation_id,
            operation_name="recommendation-status",
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        correlation_id: str,
        operation_name: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.base_url.startswith(("https://", "http://")):
            raise DrupalClientError("Drupal base URL must use http or https.")
        if not self.username or not self.password:
            raise DrupalClientError("Drupal username and password are required.")
        if not correlation_id:
            raise DrupalClientError("A correlation ID is required.")

        token = base64.b64encode(
            f"{self.username}:{self.password}".encode("utf-8")
        ).decode("ascii")
        body = None
        headers = {
            "Accept": "application/json",
            "Authorization": f"Basic {token}",
            "X-Correlation-ID": correlation_id,
            "User-Agent": "agentic-harness-lab-shared-client/1.0",
        }
        if payload is not None:
            body = json.dumps(
                payload,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = Request(
            self.base_url.rstrip("/") + path,
            data=body,
            method=method,
            headers=headers,
        )
        context = None if self.verify_tls else ssl._create_unverified_context()
        try:
            with urlopen(request, timeout=self.timeout_seconds, context=context) as response:
                raw = response.read().decode("utf-8", errors="replace")
                if response.status != 200:
                    raise DrupalClientError(
                        f"Drupal {operation_name} operation returned HTTP {response.status}.",
                        status=response.status,
                        body=raw,
                    )
        except HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            raise DrupalClientError(
                f"Drupal {operation_name} operation returned HTTP {exc.code}.",
                status=exc.code,
                body=raw,
            ) from None
        except URLError as exc:
            raise DrupalClientError(f"Unable to reach Drupal: {exc.reason}") from None

        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise DrupalClientError(f"Drupal returned invalid JSON: {exc}") from None
        if not isinstance(value, dict):
            raise DrupalClientError("Drupal response must be a JSON object.")
        return value


def _load_json_object(path: str, label: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise DrupalClientError(f"Unable to read {label} file: {exc}") from None
    except json.JSONDecodeError as exc:
        raise DrupalClientError(f"{label.capitalize()} file contains invalid JSON: {exc}") from None
    if not isinstance(value, dict):
        raise DrupalClientError(f"{label.capitalize()} file must contain one JSON object.")
    return value


def _main() -> int:
    parser = argparse.ArgumentParser(description="Call a shared deterministic Drupal tool.")
    parser.add_argument(
        "command",
        choices=[
            "find-images",
            "get-image-context",
            "submit-recommendation",
            "get-recommendation-status",
        ],
    )
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password-env", required=True)
    parser.add_argument("--correlation-id", required=True)
    parser.add_argument("--target-file")
    parser.add_argument("--recommendation-file")
    parser.add_argument("--recommendation-id")
    parser.add_argument("--insecure-local", action="store_true")
    args = parser.parse_args()

    password = os.environ.get(args.password_env, "")
    if not password:
        print(f"[ERROR] Password environment variable is empty: {args.password_env}", file=sys.stderr)
        return 2

    client = DrupalClient(
        base_url=args.base_url,
        username=args.username,
        password=password,
        verify_tls=not args.insecure_local,
    )
    try:
        if args.command == "find-images":
            result = client.find_images_needing_review(args.correlation_id)
        elif args.command == "get-image-context":
            if not args.target_file:
                raise DrupalClientError("--target-file is required for get-image-context.")
            result = client.get_image_context(
                _load_json_object(args.target_file, "target"),
                args.correlation_id,
            )
        elif args.command == "submit-recommendation":
            if not args.recommendation_file:
                raise DrupalClientError(
                    "--recommendation-file is required for submit-recommendation."
                )
            result = client.submit_recommendation(
                _load_json_object(args.recommendation_file, "recommendation"),
                args.correlation_id,
            )
        elif args.command == "get-recommendation-status":
            if not args.recommendation_id:
                raise DrupalClientError(
                    "--recommendation-id is required for get-recommendation-status."
                )
            result = client.get_recommendation_status(
                args.recommendation_id,
                args.correlation_id,
            )
        else:  # pragma: no cover
            raise AssertionError("Unhandled command")
    except DrupalClientError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        if exc.body:
            try:
                body = json.loads(exc.body)
                error = body.get("error") if isinstance(body, dict) else None
                if isinstance(error, dict):
                    code = str(error.get("code", "UNKNOWN_ERROR"))[:64]
                    message = str(error.get("message", ""))[:500]
                    print(f"[ERROR] Drupal tool error {code}: {message}", file=sys.stderr)
            except json.JSONDecodeError:
                pass
        return 1

    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
