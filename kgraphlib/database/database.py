"""
Database connection management for the knowledge graph.
"""
import logging
import types
from contextlib import contextmanager
from typing import Any, Dict, Generator, List, Optional
import os

import mariadb
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from common.config import config

# Configure logger
logger = logging.getLogger(__name__)

# Get database configuration
db_config = config.get_database_config()

logger.info(f"Database configuration: host={db_config.host}, port={db_config.port}, user={db_config.user}, database={db_config.database}")
logger.info(f"Database URL: {db_config.url}")

# Force TCP/IP connection by using 127.0.0.1 instead of localhost
host = "127.0.0.1" if db_config.host == "localhost" else db_config.host

def create_database_if_not_exists() -> None:
    """
    Create the database if it doesn't exist.
    """
    try:
        # Connect without specifying a database
        conn = mariadb.connect(
            user=db_config.user,
            password=db_config.password,
            host=host,
            port=db_config.port
        )
        cursor = conn.cursor()

        # Create database if it doesn't exist
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_config.database}")
        logger.info(f"Created database: {db_config.database}")

        # Close connection
        cursor.close()
        conn.close()
    except Exception as e:
        logger.error(f"Error creating database: {str(e)}")
        raise

def connect_mariadb() -> mariadb.Connection:
    """
    Create a MariaDB connection for SQLAlchemy.

    Returns:
        A MariaDB connection.
    """
    logger.info(f"Connecting to MariaDB: user={db_config.user}, host={host}, port={db_config.port}, database={db_config.database}")

    try:
        conn = mariadb.connect(
            user=db_config.user,
            password=db_config.password,
            host=host,
            port=db_config.port,
            database=db_config.database
        )
        logger.info("MariaDB connection successful")
        return conn
    except Exception as e:
        logger.error(f"MariaDB connection error: {str(e)}")
        raise

# Create database if it doesn't exist
try:
    create_database_if_not_exists()
except Exception as e:
    logger.error(f"Failed to create database: {str(e)}")

# Create engine with MariaDB connection
engine = create_engine(
    "mariadb+mariadbconnector://",
    creator=connect_mariadb,
    echo=False,
    pool_pre_ping=True
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    Get a database session.

    Yields:
        Database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_engine() -> Engine:
    """
    Get the SQLAlchemy engine.

    Returns:
        The SQLAlchemy engine.
    """
    return engine

def get_session_factory() -> type[Session]:
    """
    Get the SQLAlchemy session factory.

    Returns:
        The SQLAlchemy session factory.
    """
    return SessionLocal

def execute_mariadb_query(query: str, params: Dict[int, Any] = None) -> List[Dict[str, Any]]:
    """
    Execute a raw MariaDB query.

    Args:
        query: SQL query
        params: Query parameters as a dictionary with integer keys

    Returns:
        Query results as a list of dictionaries
    """
    try:
        conn = connect_mariadb()
        cursor = conn.cursor(dictionary=True)

        # Convert dictionary params to tuple if provided
        if params:
            # Find the highest key to determine tuple size
            max_key = max(params.keys()) if params else 0
            # Create a tuple with the right size
            param_tuple = tuple(params.get(i, None) for i in range(1, max_key + 1))
            cursor.execute(query, param_tuple)
        else:
            cursor.execute(query)

        # For SELECT queries, return results
        if query.strip().lower().startswith("select"):
            results = cursor.fetchall()
            cursor.close()
            conn.close()
            return results

        # For other queries, commit and return empty list
        conn.commit()
        cursor.close()
        conn.close()
        return []
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        raise

class SessionManager:
    """
    Context manager for database sessions.

    Example:
        ```
        with SessionManager() as session:
            # Use session here
            session.query(...)
        ```
    """

    def __init__(self) -> None:
        self.session: Session | None = None

    def __enter__(self) -> Session:
        self.session = SessionLocal()
        return self.session

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None = None,
    ) -> None:
        if self.session:
            if exc_type is not None:
                self.session.rollback()
            else:
                self.session.commit()
            self.session.close()

def check_tables_exist() -> bool:
    """
    Check if the required tables exist.

    Returns:
        True if all required tables exist, False otherwise.
    """
    try:
        # Check if entity_nodes, entity_edges, episodic_nodes, episodic_edges, and relation_types tables exist
        result = execute_mariadb_query("""
            SELECT COUNT(*) as count
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
            AND table_name IN ('entity_nodes', 'entity_edges', 'episodic_nodes', 'episodic_edges', 'relation_types')
        """)

        # If we found 5 tables, all required tables exist
        return result[0]["count"] == 5
    except Exception as e:
        logger.error(f"Error checking tables: {str(e)}")
        return False

def drop_tables() -> None:
    """
    Drop all tables.
    """
    try:
        # Disable foreign key checks to allow dropping tables with dependencies
        execute_mariadb_query("SET FOREIGN_KEY_CHECKS = 0")

        # Drop all tables
        execute_mariadb_query("DROP TABLE IF EXISTS entity_edges")
        execute_mariadb_query("DROP TABLE IF EXISTS episodic_edges")
        execute_mariadb_query("DROP TABLE IF EXISTS entity_nodes")
        execute_mariadb_query("DROP TABLE IF EXISTS episodic_nodes")
        execute_mariadb_query("DROP TABLE IF EXISTS relation_types")

        # Re-enable foreign key checks
        execute_mariadb_query("SET FOREIGN_KEY_CHECKS = 1")

        logger.info("All tables dropped successfully")
    except Exception as e:
        logger.error(f"Error dropping tables: {str(e)}")

def init_db(force_reset: bool = False) -> None:
    """
    Initialize the database.

    Args:
        force_reset: If True, drop and recreate all tables
    """
    try:
        # Check if tables already exist
        tables_exist = check_tables_exist()

        # Only drop tables if force_reset is True
        if force_reset:
            logger.info("Force reset requested, dropping all tables")
            drop_tables()
            create_tables()
        elif not tables_exist:
            logger.info("Tables don't exist, creating them")
            create_tables()
        else:
            logger.info("Tables already exist, skipping initialization")
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")

def create_tables() -> None:
    """
    Create all tables defined in the models.
    """
    try:
        from .models import Base
        from .models.entity_node import EntityNode
        from .models.episodic_node import EpisodicNode
        from .models.entity_edge import EntityEdge
        from .models.episodic_edge import EpisodicEdge
        from .models.relation_type import RelationType

        # Create node tables
        EntityNode.__table__.create(bind=engine, checkfirst=True)
        logger.info("Created entity_nodes table")

        EpisodicNode.__table__.create(bind=engine, checkfirst=True)
        logger.info("Created episodic_nodes table")

        # Create relation_types table
        RelationType.__table__.create(bind=engine, checkfirst=True)
        logger.info("Created relation_types table")

        # Create edge tables
        EntityEdge.__table__.create(bind=engine, checkfirst=True)
        logger.info("Created entity_edges table")

        EpisodicEdge.__table__.create(bind=engine, checkfirst=True)
        logger.info("Created episodic_edges table")

        # Add vector index to the embedding column if MariaDB supports it
        try:
            # Check if MariaDB version supports vector indexes
            version_result = execute_mariadb_query("SELECT @@version")
            version = version_result[0]["@@version"]

            # Only add vector indexes if MariaDB version is 10.11 or higher
            if version.startswith("10.11") or version.startswith("11."):
                logger.info(f"MariaDB version {version} supports vector indexes")

                # Add vector indexes to all tables with embedding columns
                execute_mariadb_query("""
                    CREATE VECTOR INDEX IF NOT EXISTS idx_entity_nodes_embedding
                    ON entity_nodes(embedding)
                """)
                logger.info("Created vector index on entity_nodes.embedding")

                execute_mariadb_query("""
                    CREATE VECTOR INDEX IF NOT EXISTS idx_episodic_nodes_embedding
                    ON episodic_nodes(embedding)
                """)
                logger.info("Created vector index on episodic_nodes.embedding")

                execute_mariadb_query("""
                    CREATE VECTOR INDEX IF NOT EXISTS idx_relation_types_embedding
                    ON relation_types(embedding)
                """)
                logger.info("Created vector index on relation_types.embedding")
            else:
                logger.warning(f"MariaDB version {version} does not support vector indexes")
        except Exception as e:
            logger.error(f"Error creating vector indexes: {str(e)}")
    except Exception as e:
        logger.error(f"Error creating tables: {str(e)}")