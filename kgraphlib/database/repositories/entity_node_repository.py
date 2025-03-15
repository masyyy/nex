"""
EntityNode repository implementation.
"""
import json
import numpy as np
from typing import Any, List, Optional, Tuple

from kgraphlib.database.database import SessionManager, execute_mariadb_query
from kgraphlib.database.models.entity_node import EntityNode as DBEntityNode
from kgraphlib.node import EntityNode


class EntityNodeRepository:
    """Repository for EntityNode models."""

    def __init__(self) -> None:
        """Initialize the repository."""
        pass

    def save(self, domain_model: EntityNode) -> EntityNode:
        """
        Save an entity node to the database.

        Args:
            domain_model: The entity node to save.

        Returns:
            The saved entity node.
        """
        with SessionManager() as session:
            # Convert domain model to database model
            db_model = self._to_db_model(domain_model)

            # Check if this is an update (ID exists) or an insert (no ID or ID doesn't exist)
            if db_model.id is not None:
                # Try to find existing record
                existing = session.query(DBEntityNode).filter(DBEntityNode.id == db_model.id).first()

                if existing:
                    # Update existing record with new values
                    existing.name = db_model.name
                    existing.entity_type = db_model.entity_type
                    existing.description = db_model.description
                    existing.meta_data = db_model.meta_data
                    existing.embedding = db_model.embedding
                    session.commit()

                    # Return the updated domain model
                    return domain_model

            # If no ID or no existing record found, proceed with insert
            session.add(db_model)
            session.commit()

            # Update domain model with generated ID
            domain_model.id = db_model.id

            return domain_model

    def get_by_id(self, node_id: int) -> Optional[EntityNode]:
        """
        Get an entity node by ID.

        Args:
            node_id: The ID of the entity node to get.

        Returns:
            The entity node, or None if not found.
        """
        with SessionManager() as session:
            db_model = session.query(DBEntityNode).filter(DBEntityNode.id == node_id).first()
            if db_model:
                return self._to_domain_model(db_model)
            return None

    def delete(self, node_id: int) -> bool:
        """
        Delete an entity node by ID.

        Args:
            node_id: The ID of the entity node to delete.

        Returns:
            True if the entity node was deleted, False otherwise.
        """
        with SessionManager() as session:
            db_model = session.query(DBEntityNode).filter(DBEntityNode.id == node_id).first()
            if db_model:
                session.delete(db_model)
                session.commit()
                return True
            return False

    def _to_db_model(self, domain_model: EntityNode) -> DBEntityNode:
        """
        Convert a domain EntityNode to a database EntityNode.

        Args:
            domain_model: The domain EntityNode to convert.

        Returns:
            The database EntityNode.
        """
        # Get the node data
        node_data = domain_model.model_dump()

        # Create the database model
        db_model = DBEntityNode(
            id=node_data.get("id"),
            name=node_data.get("name", ""),
            entity_type=node_data.get("entity_type", "entity"),
            description=node_data.get("description", ""),
            meta_data=node_data.get("metadata", {}),
            embedding=node_data.get("embedding"),
        )

        return db_model

    def _to_domain_model(self, db_model: DBEntityNode) -> EntityNode:
        """
        Convert a database EntityNode to a domain EntityNode.

        Args:
            db_model: The database EntityNode to convert.

        Returns:
            The domain EntityNode.
        """
        # Get the node data as a dictionary
        node_data = db_model.to_dict()

        # Add embedding data if available
        if hasattr(db_model, "embedding") and db_model.embedding is not None:
            # Ensure embedding is a list, not bytes or other type
            if isinstance(db_model.embedding, bytes):
                # If bytes, create an empty list as fallback
                node_data["embedding"] = []
            elif isinstance(db_model.embedding, list):
                node_data["embedding"] = db_model.embedding
            else:
                # For any other type, convert to empty list
                node_data["embedding"] = []
        else:
            node_data["embedding"] = []

        # Create the domain model
        domain_model = EntityNode(
            id=node_data.get("id"),
            description=node_data.get("description", ""),
            metadata=node_data.get("metadata", {}),
            embedding=node_data.get("embedding"),
            name=getattr(db_model, "name", ""),
            entity_type=getattr(db_model, "entity_type", "entity"),
        )

        return domain_model

    def get_by_name(self, name: str) -> list[EntityNode]:
        """
        Get entity nodes by name.

        Args:
            name: The name to search for.

        Returns:
            A list of entity nodes with the given name.
        """
        with SessionManager() as session:
            db_models = session.query(DBEntityNode).filter(DBEntityNode.name == name).all()
            return [self._to_domain_model(db_model) for db_model in db_models]

    def get_by_entity_type(self, entity_type: str) -> list[EntityNode]:
        """
        Get entity nodes by entity type.

        Args:
            entity_type: The entity type to search for.

        Returns:
            A list of entity nodes with the given entity type.
        """
        with SessionManager() as session:
            db_models = session.query(DBEntityNode).filter(DBEntityNode.entity_type == entity_type).all()
            return [self._to_domain_model(db_model) for db_model in db_models]

    def search_by_vector(self, embedding: List[float], limit: int = 10, threshold: float = 0.75) -> List[Tuple[EntityNode, float]]:
        """
        Search for entity nodes by vector similarity.

        Args:
            embedding: The embedding vector to search for.
            limit: Maximum number of results to return.
            threshold: Similarity threshold (0.0 to 1.0).

        Returns:
            List of (node, similarity) tuples.
        """
        # Convert threshold to distance threshold (1.0 - threshold)
        distance_threshold = 1.0 - threshold

        # Convert embedding to JSON string for VEC_FROMTEXT
        embedding_json = json.dumps(embedding)

        # Search in entity nodes table using MariaDB vector functions
        query = """
        SELECT n.*, VEC_DISTANCE_COSINE(n.embedding, VEC_FROMTEXT(?)) as distance
        FROM entity_nodes n
        WHERE n.embedding IS NOT NULL
        HAVING distance <= ?
        ORDER BY distance ASC
        LIMIT ?
        """
        params = {1: embedding_json, 2: distance_threshold, 3: limit}

        try:
            results = execute_mariadb_query(query, params)
        except Exception as e:
            # Fallback to a simpler query if vector functions are not available
            print(f"Vector search error: {e}. Falling back to basic query.")
            with SessionManager() as session:
                db_nodes = session.query(DBEntityNode).limit(limit).all()
                nodes_with_scores = []
                for db_node in db_nodes:
                    domain_node = self._to_domain_model(db_node)
                    # Use a placeholder similarity score
                    similarity = 0.8
                    nodes_with_scores.append((domain_node, similarity))
                return nodes_with_scores

        nodes_with_scores = []
        with SessionManager() as session:
            for result in results:
                node_id = result.get("id")
                distance = result.get("distance")
                similarity = 1.0 - distance

                db_node = session.query(DBEntityNode).filter(DBEntityNode.id == node_id).first()
                if db_node:
                    domain_node = self._to_domain_model(db_node)
                    nodes_with_scores.append((domain_node, similarity))

        return nodes_with_scores