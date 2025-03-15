"""
Node models for the knowledge graph.
"""
import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from common.openai_client import OpenAIClient


class Node(BaseModel):
    """Base class for node models with common functionality."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: Optional[int] = None  # ID will be set by the database
    embedding: list[float] = Field(default_factory=list)
    description: str = ""  # Human-readable description of the node
    metadata: Dict[str, str] = Field(default_factory=dict)
    outgoing_edge_ids: List[int] = Field(default_factory=list)

    def __init__(self, **data: Any) -> None:
        """
        Initialize a new node.

        Args:
            **data: Node attributes.
        """
        # Generate embedding if not provided but text is available
        if "embedding" not in data:
            text = self._get_text_for_embedding(data)
            if text:
                # Create embedding from text
                openai_client = OpenAIClient()
                data["embedding"] = openai_client.create_embedding([text])[0]
            else:
                # Create a placeholder empty embedding
                data["embedding"] = []

        super().__init__(**data)

    def _get_text_for_embedding(self, data: Dict[str, Any]) -> str:
        """Get text to use for embedding generation."""
        return data.get("description", "")

    def add_edge(self, target_id: int, relation_type: str, **kwargs) -> Any:
        """Add an outgoing edge to this node."""
        # Import here to avoid circular imports
        from kgraphlib.edge import EntityEdge, EpisodicEdge

        # Choose the appropriate edge type based on the node type
        if isinstance(self, EntityNode):
            edge_class = EntityEdge
        else:
            edge_class = EpisodicEdge

        edge = edge_class(
            source_id=self.id,
            target_id=target_id,
            relation_type=relation_type,
            **kwargs
        )
        self.outgoing_edge_ids.append(edge.id)
        return edge


class EntityNode(Node):
    """A node representing a semantic entity (person, place, thing, concept)."""

    name: str
    entity_type: str  # Type of entity, extracted from data

    def _get_text_for_embedding(self, data: Dict[str, Any]) -> str:
        """Get text to use for embedding generation."""
        description = data.get("description", "")
        name = data.get("name", "")
        if name and description:
            return f"{name}\n{description}"
        elif name:
            return name
        return description


class EpisodicNode(Node):
    """A node representing a temporal event or occurrence."""

    content: str  # The actual content/text of the event
    source: str = ""  # Source of the event information
    timestamp: Optional[datetime.datetime] = None
    expiration: Optional[datetime.datetime] = None

    def __init__(self, **data: Any) -> None:
        """
        Initialize a new episodic node.

        Args:
            **data: Node attributes.
        """
        # Set timestamp to current time if not provided
        if "timestamp" not in data:
            data["timestamp"] = datetime.datetime.now(tz=datetime.UTC)

        super().__init__(**data)

    def _get_text_for_embedding(self, data: Dict[str, Any]) -> str:
        """Get text to use for embedding generation."""
        description = data.get("description", "")
        content = data.get("content", "")
        if content and description:
            return f"{content}\n{description}"
        elif content:
            return content
        return description