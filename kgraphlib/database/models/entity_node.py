"""
EntityNode model for the knowledge graph.
"""
import datetime
from kgraphlib.database.models.base import Base
from kgraphlib.database.types import MariaDBVector
from typing import Any

from sqlalchemy import JSON, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import relationship


class EntityNode(Base):
    """Model for entity nodes in the knowledge graph."""
    __tablename__ = "entity_nodes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

    # Node properties
    name = Column(String(255), nullable=False, index=True)
    entity_type = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    meta_data = Column(JSON, nullable=True)

    # Vector embedding - using MariaDB VECTOR type (3072 is the dimension for OpenAI's text-embedding-3-large)
    embedding = Column(MariaDBVector(3072), nullable=False, default=lambda: [0.0] * 3072)

    # Relationships
    outgoing_edges = relationship("EntityEdge", foreign_keys="EntityEdge.source_id", primaryjoin="EntityNode.id == EntityEdge.source_id", back_populates="source")
    incoming_edges = relationship("EntityEdge", foreign_keys="EntityEdge.target_id", primaryjoin="EntityNode.id == EntityEdge.target_id", back_populates="target")
    incoming_episodic_edges = relationship("EpisodicEdge", foreign_keys="EpisodicEdge.target_id", primaryjoin="EntityNode.id == EpisodicEdge.target_id", back_populates="target")

    def to_dict(self) -> dict[str, Any]:
        """Convert entity node to dictionary."""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "name": self.name,
            "entity_type": self.entity_type,
            "description": self.description,
            "metadata": self.meta_data or {},
        }