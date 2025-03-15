"""
RelationType model for the knowledge graph.
"""
import datetime
from kgraphlib.database.models.base import Base
from kgraphlib.database.types import MariaDBVector
from typing import Any

from sqlalchemy import Column, DateTime, Integer, String, Text


class RelationType(Base):
    """Model for relation types in the knowledge graph."""
    __tablename__ = "relation_types"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

    # Properties
    type = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    embedding = Column(MariaDBVector(3072), nullable=False, default=lambda: [0.0] * 3072)

    def to_dict(self) -> dict[str, Any]:
        """Convert relation type to dictionary."""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "type": self.type,
            "description": self.description,
        }