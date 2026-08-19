"""CrewAI-specific integration surfaces for the comparative harness."""

from .canonical_slice import (
    CANONICAL_TARGET,
    MODEL_ID,
    PROMPT_VERSION,
    TEMPERATURE,
    CanonicalSliceState,
    ModelOutput,
    ProviderRequestBudgetExceeded,
    SingleRequestBudget,
    SingleRequestInterceptor,
    build_flow,
    build_live_llm,
)
from .tools import TOOL_NAMES, build_tools

__all__ = [
    "CANONICAL_TARGET",
    "MODEL_ID",
    "PROMPT_VERSION",
    "TEMPERATURE",
    "CanonicalSliceState",
    "ModelOutput",
    "ProviderRequestBudgetExceeded",
    "SingleRequestBudget",
    "SingleRequestInterceptor",
    "TOOL_NAMES",
    "build_flow",
    "build_live_llm",
    "build_tools",
]
