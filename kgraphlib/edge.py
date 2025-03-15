"""
Edge models for the knowledge graph.
"""
import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class Edge(BaseModel):
    """Base class for edge models with common functionality."""

    id: Optional[int] = None  # ID will be set by the database
    source_id: int
    target_id: int
    relation_type: str  # The normalized relation type from the Graph's relationship type index
    description: str = ""  # Human readable description of the relationship
    start_time: Optional[datetime.datetime] = None  # When the relationship began
    end_time: Optional[datetime.datetime] = None    # When the relationship ended
    metadata: Dict[str, str] = Field(default_factory=dict)


class EntityEdge(Edge):
    """An edge connecting two EntityNodes."""
    pass


class EpisodicEdge(Edge):
    """An edge connecting an EpisodicNode to an EntityNode."""
    pass