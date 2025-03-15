"""
EpisodicNode model for the knowledge graph.
"""
import datetime
from kgraphlib.database.models.base import Base
from kgraphlib.database.types import MariaDBVector
from typing import Any

from sqlalchemy import JSON, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import relationship


class EpisodicNode(Base):
    """Model for episodic nodes in the knowledge graph."""
    __tablename__ = "episodic_nodes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

    # Node properties
    content = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    source = Column(String(255), nullable=True)
    timestamp = Column(DateTime, nullable=True)
    expiration = Column(DateTime, nullable=True)
    meta_data = Column(JSON, nullable=True)

    # Vector embedding - using MariaDB VECTOR type (3072 is the dimension for OpenAI's text-embedding-3-large)
    # TODO: no default, this has to be provided by
    embedding = Column(MariaDBVector(3072), nullable=False, default=lambda: [0.0] * 3072)

    # Relationships
    outgoing_edges = relationship("EpisodicEdge", foreign_keys="EpisodicEdge.source_id", primaryjoin="EpisodicNode.id == EpisodicEdge.source_id", back_populates="source")
    # Note: EpisodicNode should not have incoming edges from EpisodicEdge since EpisodicEdge.target_id points to EntityNode
    # incoming_edges = relationship("EpisodicEdge", foreign_keys="EpisodicEdge.target_id", primaryjoin="EpisodicNode.id == EpisodicEdge.target_id")

    def to_dict(self) -> dict[str, Any]:
        """Convert episodic node to dictionary."""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "content": self.content,
            "source": self.source,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "expiration": self.expiration.isoformat() if self.expiration else None,
            "description": self.description,
            "metadata": self.meta_data or {},
        }