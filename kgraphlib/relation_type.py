"""
RelationType model for the knowledge graph.
"""
from typing import List, Optional, NamedTuple


class RelationType(NamedTuple):
    """Represents a relation type with its description."""
    type: str
    description: str
    embedding: Optional[List[float]] = None