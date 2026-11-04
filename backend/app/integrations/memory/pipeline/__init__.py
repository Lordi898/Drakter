"""Deterministic memory candidate pipeline: extract, classify, dedupe, conflicts."""

from app.integrations.memory.pipeline.classify import classify
from app.integrations.memory.pipeline.conflicts import find_contradictions, is_stale
from app.integrations.memory.pipeline.dedupe import find_duplicate
from app.integrations.memory.pipeline.extract import RuleExtractor

__all__ = ["RuleExtractor", "classify", "find_contradictions", "find_duplicate", "is_stale"]
