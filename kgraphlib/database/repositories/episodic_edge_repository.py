"""
EpisodicEdge repository implementation.
"""
from typing import Any, List, Optional

from kgraphlib.database.database import SessionManager
from kgraphlib.database.models.episodic_edge import EpisodicEdge as DBEpisodicEdge
from kgraphlib.edge import EpisodicEdge


class EpisodicEdgeRepository:
    """Repository for EpisodicEdge models."""

    def __init__(self) -> None:
        """Initialize the repository."""
        pass

    def save(self, domain_model: EpisodicEdge) -> EpisodicEdge:
        """
        Save an episodic edge to the database.

        Args:
            domain_model: The episodic edge to save.

        Returns:
            The saved episodic edge.
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

    def get_by_id(self, edge_id: int) -> Optional[EpisodicEdge]:
        """
        Get an episodic edge by ID.

        Args:
            edge_id: The ID of the episodic edge to get.

        Returns:
            The episodic edge, or None if not found.
        """
        with SessionManager() as session:
            db_model = session.query(DBEpisodicEdge).filter(DBEpisodicEdge.id == edge_id).first()
            if db_model:
                return self._to_domain_model(db_model)
            return None

    def delete(self, edge_id: int) -> bool:
        """
        Delete an episodic edge by ID.

        Args:
            edge_id: The ID of the episodic edge to delete.

        Returns:
            True if the episodic edge was deleted, False otherwise.
        """
        with SessionManager() as session:
            db_model = session.query(DBEpisodicEdge).filter(DBEpisodicEdge.id == edge_id).first()
            if db_model:
                session.delete(db_model)
                session.commit()
                return True
            return False

    def _to_db_model(self, domain_model: EpisodicEdge) -> DBEpisodicEdge:
        """
        Convert a domain EpisodicEdge to a database EpisodicEdge.

        Args:
            domain_model: The domain EpisodicEdge to convert.

        Returns:
            The database EpisodicEdge.
        """
        # Get the edge data
        edge_data = domain_model.model_dump()

        # Create the database model
        db_model = DBEpisodicEdge(
            id=edge_data.get("id"),
            relation_type=edge_data.get("relation_type", ""),
            description=edge_data.get("description", ""),
            start_time=edge_data.get("start_time"),
            end_time=edge_data.get("end_time"),
            meta_data=edge_data.get("metadata", {}),
            source_id=edge_data.get("source_id"),
            target_id=edge_data.get("target_id"),
        )

        return db_model

    def _to_domain_model(self, db_model: DBEpisodicEdge) -> EpisodicEdge:
        """
        Convert a database EpisodicEdge to a domain EpisodicEdge.

        Args:
            db_model: The database EpisodicEdge to convert.

        Returns:
            The domain EpisodicEdge.
        """
        # Get the edge data as a dictionary
        edge_data = db_model.to_dict()

        # Create the domain model
        domain_model = EpisodicEdge(
            id=edge_data.get("id"),
            source_id=edge_data.get("source_id"),
            target_id=edge_data.get("target_id"),
            relation_type=edge_data.get("relation_type", ""),
            description=edge_data.get("description", ""),
            start_time=edge_data.get("start_time"),
            end_time=edge_data.get("end_time"),
            metadata=edge_data.get("metadata", {}),
        )

        return domain_model

    def get_by_source_id(self, source_id: int) -> list[EpisodicEdge]:
        """
        Get episodic edges by source ID.

        Args:
            source_id: The source ID to search for.

        Returns:
            A list of episodic edges with the given source ID.
        """
        with SessionManager() as session:
            db_models = session.query(DBEpisodicEdge).filter(DBEpisodicEdge.source_id == source_id).all()
            return [self._to_domain_model(db_model) for db_model in db_models]

    def get_by_target_id(self, target_id: int) -> list[EpisodicEdge]:
        """
        Get episodic edges by target ID.

        Args:
            target_id: The target ID to search for.

        Returns:
            A list of episodic edges with the given target ID.
        """
        with SessionManager() as session:
            db_models = session.query(DBEpisodicEdge).filter(DBEpisodicEdge.target_id == target_id).all()
            return [self._to_domain_model(db_model) for db_model in db_models]

    def get_by_relation_type(self, relation_type: str) -> list[EpisodicEdge]:
        """
        Get episodic edges by relation type.

        Args:
            relation_type: The relation type to search for.

        Returns:
            A list of episodic edges with the given relation type.
        """
        with SessionManager() as session:
            db_models = session.query(DBEpisodicEdge).filter(DBEpisodicEdge.relation_type == relation_type).all()
            return [self._to_domain_model(db_model) for db_model in db_models]

    def get_between_nodes(self, source_id: int, target_id: int) -> list[EpisodicEdge]:
        """
        Get episodic edges between two nodes.

        Args:
            source_id: The source ID to search for.
            target_id: The target ID to search for.

        Returns:
            A list of episodic edges between the given nodes.
        """
        with SessionManager() as session:
            db_models = session.query(DBEpisodicEdge).filter(
                DBEpisodicEdge.source_id == source_id,
                DBEpisodicEdge.target_id == target_id,
            ).all()
            return [self._to_domain_model(db_model) for db_model in db_models]

    def get_edges_by_source(self, source_id: int, relation_type: Optional[str] = None) -> list[EpisodicEdge]:
        """
        Get episodic edges by source ID, optionally filtered by relation type.

        Args:
            source_id: The source ID to search for.
            relation_type: Optional relation type to filter by.

        Returns:
            A list of episodic edges with the given source ID and relation type.
        """
        with SessionManager() as session:
            query = session.query(DBEpisodicEdge).filter(DBEpisodicEdge.source_id == source_id)

            # Apply relation type filter if specified
            if relation_type is not None:
                query = query.filter(DBEpisodicEdge.relation_type == relation_type)

            db_models = query.all()
            return [self._to_domain_model(db_model) for db_model in db_models]

    def get_edges_by_target(self, target_id: int, relation_type: Optional[str] = None) -> list[EpisodicEdge]:
        """
        Get episodic edges by target ID, optionally filtered by relation type.

        Args:
            target_id: The target ID to search for.
            relation_type: Optional relation type to filter by.

        Returns:
            A list of episodic edges with the given target ID and relation type.
        """
        with SessionManager() as session:
            query = session.query(DBEpisodicEdge).filter(DBEpisodicEdge.target_id == target_id)

            # Apply relation type filter if specified
            if relation_type is not None:
                query = query.filter(DBEpisodicEdge.relation_type == relation_type)

            db_models = query.all()
            return [self._to_domain_model(db_model) for db_model in db_models]

    def get_edges_between(self, source_id: int, target_id: int, relation_type: Optional[str] = None) -> list[EpisodicEdge]:
        """
        Get episodic edges between two nodes, optionally filtered by relation type.

        Args:
            source_id: The source ID to search for.
            target_id: The target ID to search for.
            relation_type: Optional relation type to filter by.

        Returns:
            A list of episodic edges between the given nodes with the specified relation type.
        """
        with SessionManager() as session:
            query = session.query(DBEpisodicEdge).filter(
                DBEpisodicEdge.source_id == source_id,
                DBEpisodicEdge.target_id == target_id
            )

            # Apply relation type filter if specified
            if relation_type is not None:
                query = query.filter(DBEpisodicEdge.relation_type == relation_type)

            db_models = query.all()
            return [self._to_domain_model(db_model) for db_model in db_models]

    def get_all(self, limit: int = 100, offset: int = 0) -> list[EpisodicEdge]:
        """
        Get all episodic edges, with pagination.

        Args:
            limit: Maximum number of edges to return.
            offset: Number of edges to skip.

        Returns:
            A list of episodic edges.
        """
        with SessionManager() as session:
            db_models = session.query(DBEpisodicEdge).offset(offset).limit(limit).all()
            return [self._to_domain_model(db_model) for db_model in db_models]
