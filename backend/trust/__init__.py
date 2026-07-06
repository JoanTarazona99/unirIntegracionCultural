"""
Trustworthy-AI package for KubGU-RAG.

Provides grounding/faithfulness estimation and an abstention guard so that, for
high-stakes migration information, the assistant only answers when the response
is supported by retrieved official sources, and otherwise abstains with a safe
fallback message pointing to the official source.
"""

from .hallucination import estimate_faithfulness, sentence_support, GroundingLevel, analyze_grounding_improved
from .citation import GroundingResult, enforce_grounding, format_citations, enforce_grounding_improved

__all__ = [
    "estimate_faithfulness",
    "sentence_support",
    "GroundingResult",
    "enforce_grounding",
    "enforce_grounding_improved",
    "format_citations",
    "GroundingLevel",
    "analyze_grounding_improved",
]
