"""
Custom SQLAlchemy types for the knowledge graph database.
"""
import json
from sqlalchemy.types import UserDefinedType


class MariaDBVector(UserDefinedType):
    """Native MariaDB VECTOR type for SQLAlchemy."""

    def __init__(self, dimensions):
        """Initialize with vector dimensions.

        Args:
            dimensions: Number of dimensions in the vector
        """
        self.dimensions = dimensions

    def get_col_spec(self, **kw):
        """Return the DDL for this column type.

        Returns:
            SQL DDL string for this type
        """
        return f"VECTOR({self.dimensions})"

    def bind_expression(self, bindvalue):
        """Convert the bind parameter to a SQL expression.

        This is called when inserting data into the database.

        Args:
            bindvalue: The bind parameter

        Returns:
            SQL expression
        """
        # Import here to avoid circular imports
        from sqlalchemy.sql import func

        # Use MariaDB's VEC_FromText function to convert JSON array to VECTOR
        return func.VEC_FromText(bindvalue)

    def bind_processor(self, dialect):
        """Process the value from Python to DB parameter format.

        Args:
            dialect: SQLAlchemy dialect

        Returns:
            Function to process values
        """
        def process(value):
            if value is None:
                return None
            # Convert Python list to JSON string for VEC_FromText
            return json.dumps(value)
        return process

    def column_expression(self, col):
        """Convert the column to a text expression when selected.

        Args:
            col: The column being selected

        Returns:
            An SQL expression using VEC_TOTEXT to convert the vector to JSON
        """
        from sqlalchemy.sql import func
        # Use MariaDB's VEC_TOTEXT to convert binary vector to JSON string during select
        return func.VEC_TOTEXT(col)

    def result_processor(self, dialect, coltype):
        """Process the value from DB result to Python format.

        Args:
            dialect: SQLAlchemy dialect
            coltype: Column type

        Returns:
            Function to process values
        """
        def process(value):
            if value is None:
                return None

            # When using column_expression with VEC_TOTEXT, we should get string JSON
            if isinstance(value, str):
                try:
                    # Parse the JSON string to get the list of floats
                    return json.loads(value)
                except json.JSONDecodeError as e:
                    # Raise explicit exception for invalid JSON
                    raise ValueError(f"Invalid JSON format for vector data: {e}") from e

            # If it's already a list, return it
            if isinstance(value, list):
                return value

            # For any other type, raise an exception
            raise TypeError(f"Unexpected data type for vector: {type(value)}. Expected JSON string or list, got: {value}")
        return process