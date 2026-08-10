"""Thin LangChain-native tools over the frozen shared Drupal client."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Callable

from langchain_core.tools import BaseTool, tool

from shared.drupal_client.client import DrupalClient, DrupalClientError


def _error_envelope(
    *,
    tool_name: str,
    correlation_id: str,
    error: DrupalClientError,
) -> dict[str, Any]:
    """Preserve safe substrate errors; sanitize route/transport failures."""
    if error.body:
        try:
            value = json.loads(error.body)
        except json.JSONDecodeError:
            value = None
        if (
            isinstance(value, dict)
            and set(value) == {
                "schema_version",
                "tool_name",
                "ok",
                "timestamp",
                "correlation_id",
                "data",
                "error",
            }
            and value.get("schema_version") == 1
            and value.get("tool_name") == tool_name
            and value.get("correlation_id") == correlation_id
            and value.get("ok") is False
            and value.get("data") is None
            and isinstance(value.get("error"), dict)
            and set(value["error"]) == {"code", "message", "retryable"}
        ):
            return value

    status = error.status
    if status in (401, 403):
        code = "ACCESS_DENIED"
        message = "Access to the Drupal shared operation was denied."
        retryable = False
    elif status is not None:
        code = "DRUPAL_HTTP_ERROR"
        message = "The Drupal shared operation returned an HTTP error."
        retryable = status >= 500
    else:
        code = "DRUPAL_TRANSPORT_ERROR"
        message = "The Drupal shared operation could not be reached."
        retryable = True

    return {
        "schema_version": 1,
        "tool_name": tool_name,
        "ok": False,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "correlation_id": correlation_id,
        "data": None,
        "error": {
            "code": code,
            "message": message,
            "retryable": retryable,
        },
    }


def _invoke(
    *,
    tool_name: str,
    correlation_id: str,
    operation: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    try:
        return operation()
    except DrupalClientError as error:
        return _error_envelope(
            tool_name=tool_name,
            correlation_id=correlation_id,
            error=error,
        )


def build_tools(client: DrupalClient, *, correlation_id: str) -> dict[str, BaseTool]:
    """Build the exact four frozen semantic tools around one Drupal client.

    The wrappers add no retries, persistence, sequencing, business validation,
    target lookup, or recommendation persistence. They preserve safe substrate
    tool-result envelopes and only sanitize route/transport failures that occur
    before a substrate envelope is available.
    """
    if not correlation_id:
        raise ValueError("correlation_id is required")

    @tool("find_images_needing_review")
    def find_images_needing_review() -> dict[str, Any]:
        """Find the frozen set of Drupal image-field usages needing editor review."""
        return _invoke(
            tool_name="find_images_needing_review",
            correlation_id=correlation_id,
            operation=lambda: client.find_images_needing_review(correlation_id),
        )

    @tool("get_image_context")
    def get_image_context(target: dict[str, Any]) -> dict[str, Any]:
        """Get permitted Drupal page and image context for one frozen target."""
        return _invoke(
            tool_name="get_image_context",
            correlation_id=correlation_id,
            operation=lambda: client.get_image_context(target, correlation_id),
        )

    @tool("submit_recommendation")
    def submit_recommendation(recommendation: dict[str, Any]) -> dict[str, Any]:
        """Submit one validated recommendation to the frozen Drupal review queue."""
        return _invoke(
            tool_name="submit_recommendation",
            correlation_id=correlation_id,
            operation=lambda: client.submit_recommendation(recommendation, correlation_id),
        )

    @tool("get_recommendation_status")
    def get_recommendation_status(recommendation_id: str) -> dict[str, Any]:
        """Read the current Drupal review status for one recommendation."""
        return _invoke(
            tool_name="get_recommendation_status",
            correlation_id=correlation_id,
            operation=lambda: client.get_recommendation_status(
                recommendation_id,
                correlation_id,
            ),
        )

    built = {
        find_images_needing_review.name: find_images_needing_review,
        get_image_context.name: get_image_context,
        submit_recommendation.name: submit_recommendation,
        get_recommendation_status.name: get_recommendation_status,
    }
    expected = {
        "find_images_needing_review",
        "get_image_context",
        "submit_recommendation",
        "get_recommendation_status",
    }
    if set(built) != expected:
        raise RuntimeError("LangGraph tool surface does not match the frozen operation set")
    return built
