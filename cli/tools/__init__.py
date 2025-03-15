"""
Tools for the knowledge graph agent.
"""
# Tool parameter models
from cli.tools.search import SearchParameters
from cli.tools.query import QueryParameters
from cli.tools.visualize import VisualizeParameters
from cli.tools.answer import AnswerParameters
from cli.tools.relation_type import QueryRelationTypeParameters

# Tool execution functions
from cli.tools.search import execute_search
from cli.tools.query import execute_query
from cli.tools.visualize import execute_visualize
from cli.tools.answer import execute_answer
from cli.tools.relation_type import execute_query_relation_type

# Legacy compatibility
from cli.tools.search import search
from cli.tools.visualize import visualize

__all__ = [
    # Parameter models
    "SearchParameters",
    "QueryParameters",
    "VisualizeParameters",
    "AnswerParameters",
    "QueryRelationTypeParameters",

    # Execution functions
    "execute_search",
    "execute_query",
    "execute_visualize",
    "execute_answer",
    "execute_query_relation_type",

    # Legacy
    "search",
    "visualize"
]