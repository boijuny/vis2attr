"""Core data models for the vis2attr pipeline."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, timezone

from .constants import DEFAULT_MAX_TOKENS, DEFAULT_TEMPERATURE


@dataclass
class Item:
    """Represents an item with images to be processed."""
    item_id: str
    images: List[Union[bytes, str]]  # Image data or URIs
    meta: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.meta is None:
            self.meta = {}


@dataclass
class VLMRequest:
    """Request to be sent to a VLM provider."""
    model: str
    messages: List[Dict[str, Any]]
    images: List[Union[bytes, str]]
    max_tokens: int = DEFAULT_MAX_TOKENS
    temperature: float = DEFAULT_TEMPERATURE


@dataclass
class VLMRaw:
    """Raw response from a VLM provider."""
    content: str
    usage: Dict[str, Any]  # Token usage, cost, etc.
    latency_ms: float
    provider: str
    model: str
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


@dataclass
class Attributes:
    """Structured attributes extracted from images."""
    data: Dict[str, Any]  # The actual attribute values
    confidences: Dict[str, float]  # Confidence scores per field
    tags: set = None  # Quality tags
    notes: str = ""
    lineage: Dict[str, Any] = None  # Processing lineage
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = set()
        if self.lineage is None:
            self.lineage = {}


@dataclass
class Decision:
    """Decision made about the quality and acceptance of attributes."""
    accepted: bool
    field_flags: Dict[str, str] = None  # Field-specific flags and reasons
    reasons: List[str] = None  # General reasons for the decision
    confidence_score: float = 0.0
    
    def __post_init__(self):
        if self.field_flags is None:
            self.field_flags = {}
        if self.reasons is None:
            self.reasons = []
