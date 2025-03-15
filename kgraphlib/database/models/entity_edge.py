"""
EntityEdge model for the knowledge graph.
"""
import datetime
from kgraphlib.database.models.base import Base
from typing import Any

from sqlalchemy import JSON, Column, DateTime, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship


class EntityEdge(Base):
    """Model for entity edges in the knowledge graph."""
    __tablename__ = "entity_edges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

    # Edge properties
    relation_type = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    meta_data = Column(JSON, nullable=True)

    # Relationship endpoints
    source_id = Column(Integer, index=True, nullable=False)
    target_id = Column(Integer, index=True, nullable=False)

    # Relationships
    source = relationship("EntityNode", foreign_keys=[source_id], back_populates="outgoing_edges", primaryjoin="EntityNode.id == EntityEdge.source_id")
    target = relationship("EntityNode", foreign_keys=[target_id], back_populates="incoming_edges", primaryjoin="EntityNode.id == EntityEdge.target_id")

    def to_dict(self) -> dict[str, Any]:
        """Convert entity edge to dictionary."""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "relation_type": self.relation_type,
            "description": self.description,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "metadata": self.meta_data or {},
            "source_id": self.source_id,
            "target_id": self.target_id,
        }