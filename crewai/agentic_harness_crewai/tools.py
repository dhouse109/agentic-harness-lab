"""Thin CrewAI adapters over the frozen shared Drupal operations.

The adapter binds transport-only correlation metadata at construction time. It
does not validate, retry, persist, reshape, or otherwise reimplement the shared
operation semantics.
"""

from __future__ import annotations

from typing import Any

from crewai.tools import BaseTool, tool
from shared.drupal_client.client import DrupalClient


TOOL_NAMES = (
    "find_images_needing_review",
    "get_image_context",
    "submit_recommendation",
    "get_recommendation_status",
)


def build_tools(
    client: DrupalClient,
    *,
    correlation_id: str,
) -> dict[str, BaseTool]:
    """Build the four model-independent CrewAI-facing shared-operation tools."""
    if not correlation_id:
        raise ValueError("correlation_id must be non-empty")

    @tool("find_images_needing_review")
    def find_images_needing_review() -> dict[str, Any]:
        """Return the frozen ordered targets needing accessibility review."""
        return client.find_images_needing_review(correlation_id)

    @tool("get_image_context")
    def get_image_context(target: dict[str, Any]) -> dict[str, Any]:
        """Return permission-scoped context for one frozen target object."""
        return client.get_image_context(target, correlation_id)

    @tool("submit_recommendation")
    def submit_recommendation(recommendation: dict[str, Any]) -> dict[str, Any]:
        """Submit one recommendation through the authoritative shared boundary."""
        return client.submit_recommendation(recommendation, correlation_id)

    @tool("get_recommendation_status")
    def get_recommendation_status(recommendation_id: str) -> dict[str, Any]:
        """Observe recommendation status through the read-only shared boundary."""
        return client.get_recommendation_status(recommendation_id, correlation_id)

    tools = {
        find_images_needing_review.name: find_images_needing_review,
        get_image_context.name: get_image_context,
        submit_recommendation.name: submit_recommendation,
        get_recommendation_status.name: get_recommendation_status,
    }
    if tuple(tools) != TOOL_NAMES:
        raise RuntimeError("CrewAI tool inventory drifted from the frozen boundary")
    return tools
