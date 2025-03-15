"""
Base SQLAlchemy model for the knowledge graph.
"""

from sqlalchemy.ext.declarative import declarative_base

# Create a properly typed Base class
Base = declarative_base()
# Define a type alias for the Base class
DeclarativeBase = type[Base]