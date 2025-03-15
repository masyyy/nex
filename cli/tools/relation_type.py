"""
Relation type query tool for retrieving available relation types in the graph.
"""

from pydantic import BaseModel, Field

from common.models import ToolParameters
from kgraphlib.graph import Graph


class QueryRelationTypeParameters(ToolParameters):
    """
    Parameters for the relation type query tool.
    Needs to be called before QueryParameters, unless the exact relation type is known
    """


class RelationTypeInfo(BaseModel):
    """Information about a relation type."""

    type: str = Field(description="The relation type name or label.")
    description: str = Field(description="Description of the relation type.")


class QueryRelationTypeResponse(BaseModel):
    """Response from the relation type query tool."""

    relation_types: list[RelationTypeInfo] = Field(
        description="List of relation types found in the graph.",
    )
    count: int = Field(description="Number of relation types returned.")


def execute_query_relation_type(
    _: QueryRelationTypeParameters, graph: Graph,
) -> QueryRelationTypeResponse:
    """
    Execute a query for relation types with validated parameters.

    Args:
        _: Validated query parameters (unused)
        graph: The knowledge graph instance

    Returns:
        Query response with results
    """
    # Get all relation types from the graph
    relation_types = graph.get_relation_types()

    # Format response - convert from RelationType to RelationTypeInfo
    relation_type_infos = [
        RelationTypeInfo(
            type=rt.type,
            description=rt.description,
        ) for rt in relation_types
    ]

    return QueryRelationTypeResponse(
        relation_types=relation_type_infos,
        count=len(relation_type_infos),
    )