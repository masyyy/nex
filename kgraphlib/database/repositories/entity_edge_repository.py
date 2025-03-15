"""
EntityEdge repository implementation.
"""
from typing import Any, List, Optional

from kgraphlib.database.database import SessionManager
from kgraphlib.database.models.entity_edge import EntityEdge as DBEntityEdge
from kgraphlib.edge import EntityEdge


class EntityEdgeRepository:
    """Repository for EntityEdge models."""

    def __init__(self) -> None:
        """Initialize the repository."""
        pass

    def save(self, domain_model: EntityEdge) -> EntityEdge:
        """
        Save an entity edge to the database.

        Args:
            domain_model: The entity edge to save.

        Returns:
            The saved entity edge.
        """
        with SessionManager() as session:
            # Convert domain model to database model
            db_model = self._to_db_model(domain_model)

            # Check if this is an update (ID exists) or an insert (no ID or ID doesn't exist)
            if db_model.id is not None:
                # Try to find existing record
                existing = session.query(DBEntityEdge).filter(DBEntityEdge.id == db_model.id).first()

                if existing:
                    # Update existing record with new values
                    existing.relation_type = db_model.relation_type
                    existing.description = db_model.description
                    existing.start_time = db_model.start_time
                    existing.end_time = db_model.end_time
                    existing.meta_data = db_model.meta_data
                    existing.source_id = db_model.source_id
                    existing.target_id = db_model.target_id
                    session.commit()

                    # Return the updated domain model
                    return domain_model

            # If no ID or no existing record found, proceed with insert
            session.add(db_model)
            session.commit()

            # Update domain model with generated ID
            domain_model.id = db_model.id

            return domain_model

    def get_by_id(self, edge_id: int) -> Optional[EntityEdge]:
        """
        Get an entity edge by ID.

        Args:
            edge_id: The ID of the entity edge to get.

        Returns:
            The entity edge, or None if not found.
        """
        with SessionManager() as session:
            db_model = session.query(DBEntityEdge).filter(DBEntityEdge.id == edge_id).first()
            if db_model:
                return self._to_domain_model(db_model)
            return None

    def delete(self, edge_id: int) -> bool:
        """
        Delete an entity edge by ID.

        Args:
            edge_id: The ID of the entity edge to delete.

        Returns:
            True if the entity edge was deleted, False otherwise.
        """
        with SessionManager() as session:
            db_model = session.query(DBEntityEdge).filter(DBEntityEdge.id == edge_id).first()
            if db_model:
                session.delete(db_model)
                session.commit()
                return True
            return False

    def _to_db_model(self, domain_model: EntityEdge) -> DBEntityEdge:
        """
        Convert a domain EntityEdge to a database EntityEdge.

        Args:
            domain_model: The domain EntityEdge to convert.

        Returns:
            The database EntityEdge.
        """
        # Get the edge data
        edge_data = domain_model.model_dump()

        # Create the database model
        db_model = DBEntityEdge(
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

    def _to_domain_model(self, db_model: DBEntityEdge) -> EntityEdge:
        """
        Convert a database EntityEdge to a domain EntityEdge.

        Args:
            db_model: The database EntityEdge to convert.

        Returns:
            The domain EntityEdge.
        """
        # Get the edge data as a dictionary
        edge_data = db_model.to_dict()

        # Create the domain model
        domain_model = EntityEdge(
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

    def get_by_source_id(self, source_id: int) -> list[EntityEdge]:
        """
        Get entity edges by source ID.

        Args:
            source_id: The source ID to search for.

        Returns:
            A list of entity edges with the given source ID.
        """
        with SessionManager() as session:
            db_models = session.query(DBEntityEdge).filter(DBEntityEdge.source_id == source_id).all()
            return [self._to_domain_model(db_model) for db_model in db_models]

    def get_by_target_id(self, target_id: int) -> list[EntityEdge]:
        """
        Get entity edges by target ID.

        Args:
            target_id: The target ID to search for.

        Returns:
            A list of entity edges with the given target ID.
        """
        with SessionManager() as session:
            db_models = session.query(DBEntityEdge).filter(DBEntityEdge.target_id == target_id).all()
            return [self._to_domain_model(db_model) for db_model in db_models]

    def get_by_relation_type(self, relation_type: str) -> list[EntityEdge]:
        """
        Get entity edges by relation type.

        Args:
            relation_type: The relation type to search for.

        Returns:
            A list of entity edges with the given relation type.
        """
        with SessionManager() as session:
            db_models = session.query(DBEntityEdge).filter(DBEntityEdge.relation_type == relation_type).all()
            return [self._to_domain_model(db_model) for db_model in db_models]

    def get_between_nodes(self, source_id: int, target_id: int) -> list[EntityEdge]:
        """
        Get entity edges between two nodes.

        Args:
            source_id: The source ID to search for.
            target_id: The target ID to search for.

        Returns:
            A list of entity edges between the given nodes.
        """
        with SessionManager() as session:
            db_models = session.query(DBEntityEdge).filter(
                DBEntityEdge.source_id == source_id,
                DBEntityEdge.target_id == target_id,
            ).all()
            return [self._to_domain_model(db_model) for db_model in db_models]

    def get_edges_by_source(self, source_id: int, relation_type: Optional[str] = None) -> list[EntityEdge]:
        """
        Get entity edges by source ID, optionally filtered by relation type.

        Args:
            source_id: The source ID to search for.
            relation_type: Optional relation type to filter by.

        Returns:
            A list of entity edges with the given source ID and relation type.
        """
        with SessionManager() as session:
            query = session.query(DBEntityEdge).filter(DBEntityEdge.source_id == source_id)

            # Apply relation type filter if specified
            if relation_type is not None:
                query = query.filter(DBEntityEdge.relation_type == relation_type)

            db_models = query.all()
            return [self._to_domain_model(db_model) for db_model in db_models]

    def get_edges_by_target(self, target_id: int, relation_type: Optional[str] = None) -> list[EntityEdge]:
        """
        Get entity edges by target ID, optionally filtered by relation type.

        Args:
            target_id: The target ID to search for.
            relation_type: Optional relation type to filter by.

        Returns:
            A list of entity edges with the given target ID and relation type.
        """
        with SessionManager() as session:
            query = session.query(DBEntityEdge).filter(DBEntityEdge.target_id == target_id)

            # Apply relation type filter if specified
            if relation_type is not None:
                query = query.filter(DBEntityEdge.relation_type == relation_type)

            db_models = query.all()
            return [self._to_domain_model(db_model) for db_model in db_models]

    def get_edges_between(self, source_id: int, target_id: int, relation_type: Optional[str] = None) -> list[EntityEdge]:
        """
        Get entity edges between two nodes, optionally filtered by relation type.

        Args:
            source_id: The source ID to search for.
            target_id: The target ID to search for.
            relation_type: Optional relation type to filter by.

        Returns:
            A list of entity edges between the given nodes with the specified relation type.
        """
        with SessionManager() as session:
            query = session.query(DBEntityEdge).filter(
                DBEntityEdge.source_id == source_id,
                DBEntityEdge.target_id == target_id
            )

            # Apply relation type filter if specified
            if relation_type is not None:
                query = query.filter(DBEntityEdge.relation_type == relation_type)

            db_models = query.all()
            return [self._to_domain_model(db_model) for db_model in db_models]

    def get_all(self, limit: int = 100, offset: int = 0) -> list[EntityEdge]:
        """
        Get all entity edges, with pagination.

        Args:
            limit: Maximum number of edges to return.
            offset: Number of edges to skip.

        Returns:
            A list of entity edges.
        """
        with SessionManager() as session:
            db_models = session.query(DBEntityEdge).offset(offset).limit(limit).all()
            return [self._to_domain_model(db_model) for db_model in db_models]