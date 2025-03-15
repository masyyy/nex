"""
Repository for relation type database operations.
"""
import logging
from typing import List, Optional, Dict, Any, Union
import numpy as np
import json

from sqlalchemy import select, text
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import func

from kgraphlib.database.database import SessionManager
from kgraphlib.database.models.relation_type import RelationType as DBRelationType
from kgraphlib.relation_type import RelationType

logger = logging.getLogger(__name__)


class RelationTypeRepository:
    """Repository for RelationType database operations."""

    def save(self, relation_type: RelationType) -> Optional[RelationType]:
        """
        Save a relation type to the database.

        Args:
            relation_type: Domain RelationType object to save.

        Returns:
            The saved domain RelationType or None if an error occurred.
        """
        try:
            # Extract data from domain model
            rel_type = relation_type.type
            description = relation_type.description
            embedding = relation_type.embedding

            # Make sure we have an embedding
            if not embedding:
                logger.error("Cannot save relation type without an embedding")
                return None

            # Convert to database model
            db_relation_type = DBRelationType(
                type=rel_type,
                description=description,
                embedding=embedding
            )

            # Ensure embedding is in the correct format
            # If embedding is a numpy array, convert to list
            if hasattr(db_relation_type.embedding, 'tolist'):
                # Handle numpy arrays by converting to list
                db_relation_type.embedding = db_relation_type.embedding.tolist()

            with SessionManager() as session:
                # Add to session and commit
                session.add(db_relation_type)
                session.flush()  # Flush to get the ID

                # Return the domain RelationType (not the DB model)
                return relation_type
        except SQLAlchemyError as e:
            logger.error(f"Error saving relation type: {e}")
            return None

    def get_by_id(self, id: int) -> Optional[RelationType]:
        """
        Get a relation type by ID.

        Args:
            id: Relation type ID.

        Returns:
            The relation type or None if not found.
        """
        try:
            with SessionManager() as session:
                db_type = session.get(DBRelationType, id)
                if not db_type:
                    return None

                # Convert database model to domain model
                return RelationType(
                    type=db_type.type,
                    description=db_type.description,
                    embedding=db_type.embedding
                )

        except SQLAlchemyError as e:
            logger.error(f"Error getting relation type by ID: {e}")
            return None

    def get_by_type(self, type_name: str) -> Optional[RelationType]:
        """
        Get a relation type by its name.

        Args:
            type_name: Relation type name.

        Returns:
            The relation type or None if not found.
        """
        try:
            with SessionManager() as session:
                db_type = session.execute(
                    select(DBRelationType).where(DBRelationType.type == type_name)
                ).scalar_one_or_none()

                if not db_type:
                    return None

                # Convert database model to domain model
                return RelationType(
                    type=db_type.type,
                    description=db_type.description,
                    embedding=db_type.embedding
                )

        except SQLAlchemyError as e:
            logger.error(f"Error getting relation type by name: {e}")
            return None

    def get_all(self, limit: int = 100, offset: int = 0) -> List[RelationType]:
        """
        Get all relation types.

        Args:
            limit: Maximum number of relation types to return.
            offset: Number of relation types to skip.

        Returns:
            List of relation types.
        """
        try:
            with SessionManager() as session:
                db_types = list(session.execute(
                    select(DBRelationType).offset(offset).limit(limit)
                ).scalars().all())

                # Convert database models to domain models
                return [
                    RelationType(
                        type=rt.type,
                        description=rt.description,
                        embedding=rt.embedding
                    )
                    for rt in db_types
                ]

        except SQLAlchemyError as e:
            logger.error(f"Error getting all relation types: {e}")
            return []

    def delete(self, id: int) -> bool:
        """
        Delete a relation type by ID.

        Args:
            id: Relation type ID.

        Returns:
            True if successful, False otherwise.
        """
        try:
            with SessionManager() as session:
                relation_type = session.get(DBRelationType, id)
                if relation_type:
                    session.delete(relation_type)
                    return True
                return False
        except SQLAlchemyError as e:
            logger.error(f"Error deleting relation type: {e}")
            return False

    def find_similar_types(
        self,
        embedding: list[float],
        threshold: float = 0.9,
        limit: int = 5
    ) -> List[RelationType]:
        """
        Find similar relation types based on embedding similarity.

        Args:
            embedding: Vector embedding to compare against.
            threshold: Minimum similarity threshold (0-1).
            limit: Maximum number of results to return.

        Returns:
            List of relation types with similarity score above threshold.
        """
        try:
            with SessionManager() as session:
                # Query to find relation types with similarity above threshold
                # Get all needed fields in a single query
                query = text("""
                    SELECT id, type, description, embedding
                    FROM relation_types
                    WHERE VEC_DISTANCE_COSINE(embedding, VEC_FROMTEXT(:embedding)) <= :distance_threshold
                    ORDER BY VEC_DISTANCE_COSINE(embedding, VEC_FROMTEXT(:embedding))
                    LIMIT :limit
                """)

                # Convert cosine similarity threshold to distance threshold (1-threshold)
                # Cosine similarity of 1.0 = distance of 0.0, similarity of 0.9 = distance of 0.1
                distance_threshold = 1.0 - threshold

                # Format embedding as JSON
                embedding_json = json.dumps(embedding)

                result = session.execute(
                    query,
                    {"embedding": embedding_json, "distance_threshold": distance_threshold, "limit": limit}
                )

                # Convert results directly to domain models
                return [
                    RelationType(
                        type=row.type,
                        description=row.description,
                        embedding=row.embedding
                    )
                    for row in result
                ]

        except SQLAlchemyError as e:
            logger.error(f"Error in vector similarity search: {e}")
            return []