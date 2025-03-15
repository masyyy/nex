"""
EpisodicNode repository implementation.
"""
import datetime
import json
import numpy as np
from typing import Any, List, Optional, Tuple

from kgraphlib.database.database import SessionManager, execute_mariadb_query
from kgraphlib.database.models.episodic_node import EpisodicNode as DBEpisodicNode
from kgraphlib.node import EpisodicNode


class EpisodicNodeRepository:
    """Repository for EpisodicNode models."""

    def __init__(self) -> None:
        """Initialize the repository."""
        pass

    def save(self, domain_model: EpisodicNode) -> EpisodicNode:
        """
        Save an episodic node to the database.

        Args:
            domain_model: The episodic node to save.

        Returns:
            The saved episodic node.
        """
        with SessionManager() as session:
            # Convert domain model to database model
            db_model = self._to_db_model(domain_model)

            # Add to session
            session.add(db_model)
            session.commit()

            # Update domain model with generated ID
            domain_model.id = db_model.id

            return domain_model

    def get_by_id(self, node_id: int) -> Optional[EpisodicNode]:
        """
        Get an episodic node by ID.

        Args:
            node_id: The ID of the episodic node to get.

        Returns:
            The episodic node, or None if not found.
        """
        with SessionManager() as session:
            db_model = session.query(DBEpisodicNode).filter(DBEpisodicNode.id == node_id).first()
            if db_model:
                return self._to_domain_model(db_model)
            return None

    def delete(self, node_id: int) -> bool:
        """
        Delete an episodic node by ID.

        Args:
            node_id: The ID of the episodic node to delete.

        Returns:
            True if the episodic node was deleted, False otherwise.
        """
        with SessionManager() as session:
            db_model = session.query(DBEpisodicNode).filter(DBEpisodicNode.id == node_id).first()
            if db_model:
                session.delete(db_model)
                session.commit()
                return True
            return False

    def _to_db_model(self, domain_model: EpisodicNode) -> DBEpisodicNode:
        """
        Convert a domain EpisodicNode to a database EpisodicNode.

        Args:
            domain_model: The domain EpisodicNode to convert.

        Returns:
            The database EpisodicNode.
        """
        # Get the node data
        node_data = domain_model.model_dump()

        # Create the database model
        db_model = DBEpisodicNode(
            id=node_data.get("id"),
            content=node_data.get("content", ""),
            source=node_data.get("source", ""),
            description=node_data.get("description", ""),
            meta_data=node_data.get("metadata", {}),
            embedding=node_data.get("embedding"),
            timestamp=node_data.get("timestamp"),
            expiration=node_data.get("expiration"),
        )

        return db_model

    def _to_domain_model(self, db_model: DBEpisodicNode) -> EpisodicNode:
        """
        Convert a database EpisodicNode to a domain EpisodicNode.

        Args:
            db_model: The database EpisodicNode to convert.

        Returns:
            The domain EpisodicNode.
        """
        # Get the node data as a dictionary
        node_data = db_model.to_dict()

        # Add embedding data if available
        if hasattr(db_model, "embedding") and db_model.embedding is not None:
            node_data["embedding"] = db_model.embedding
        else:
            node_data["embedding"] = []

        # Create the domain model
        domain_model = EpisodicNode(
            id=node_data.get("id"),
            content=getattr(db_model, "content", ""),
            source=getattr(db_model, "source", ""),
            description=node_data.get("description", ""),
            metadata=node_data.get("metadata", {}),
            embedding=node_data.get("embedding"),
            timestamp=getattr(db_model, "timestamp", None),
            expiration=getattr(db_model, "expiration", None),
        )

        return domain_model

    def get_by_source(self, source: str) -> list[EpisodicNode]:
        """
        Get episodic nodes by source.

        Args:
            source: The source to search for.

        Returns:
            A list of episodic nodes with the given source.
        """
        with SessionManager() as session:
            db_models = session.query(DBEpisodicNode).filter(DBEpisodicNode.source == source).all()
            return [self._to_domain_model(db_model) for db_model in db_models]

    def get_by_time_range(self, start_time: datetime.datetime, end_time: datetime.datetime) -> list[EpisodicNode]:
        """
        Get episodic nodes by time range.

        Args:
            start_time: The start time of the range.
            end_time: The end time of the range.

        Returns:
            A list of episodic nodes within the given time range.
        """
        with SessionManager() as session:
            db_models = session.query(DBEpisodicNode).filter(
                DBEpisodicNode.timestamp >= start_time,
                DBEpisodicNode.timestamp <= end_time,
            ).all()
            return [self._to_domain_model(db_model) for db_model in db_models]

    def search_by_vector(self, embedding: List[float], limit: int = 10, threshold: float = 0.75) -> List[Tuple[EpisodicNode, float]]:
        """
        Search for episodic nodes by vector similarity.

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

        # Search in episodic nodes table using MariaDB vector functions
        query = """
        SELECT n.*, VEC_DISTANCE_COSINE(n.embedding, VEC_FROMTEXT(?)) as distance
        FROM episodic_nodes n
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
                db_nodes = session.query(DBEpisodicNode).limit(limit).all()
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

                db_node = session.query(DBEpisodicNode).filter(DBEpisodicNode.id == node_id).first()
                if db_node:
                    domain_node = self._to_domain_model(db_node)
                    nodes_with_scores.append((domain_node, similarity))

        return nodes_with_scores