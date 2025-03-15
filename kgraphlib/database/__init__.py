"""
Database connection and models for the knowledge graph.
"""
from kgraphlib.database.database import (
    SessionManager,
    connect_mariadb,
    create_tables,
    get_engine,
    get_session,
    get_session_factory,
    execute_mariadb_query,
    init_db,
    check_tables_exist,
    drop_tables,
)
from kgraphlib.database.models import (
    Base,
    EntityEdge,
    EntityNode,
    EpisodicEdge,
    EpisodicNode,
)
from kgraphlib.database.repositories import (
    EntityNodeRepository,
    EpisodicNodeRepository,
    EntityEdgeRepository,
    EpisodicEdgeRepository,
)

__all__ = [
    "Base",
    "EntityEdge",
    "EntityEdgeRepository",
    "EntityNode",
    "EntityNodeRepository",
    "EpisodicEdge",
    "EpisodicEdgeRepository",
    "EpisodicNode",
    "EpisodicNodeRepository",
    "SessionManager",
    "connect_mariadb",
    "create_tables",
    "get_engine",
    "get_session",
    "get_session_factory",
    "execute_mariadb_query",
    "init_db",
    "check_tables_exist",
    "drop_tables",
]