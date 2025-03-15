"""
Search tool for finding nodes and relationships in the graph.
"""
from typing import Dict, Any, List, Optional, Literal

from pydantic import BaseModel, Field

from kgraphlib.graph import Graph
from common.openai_client import ToolParameters


class SearchParameters(ToolParameters):
    """Parameters for the search tool."""

    query: str = Field(description="The search query.")
    limit: Optional[int] = Field(None, description="Maximum number of results to return. Default is 5 if not specified.")

    model_config = {
        "json_schema_extra": {
            "title": "search",
            "description": "Search for nodes in the knowledge graph using semantic similarity."
        }
    }

    def get_limit(self) -> int:
        """Get the limit with default value if None."""
        return 5 if self.limit is None else self.limit


class SearchResult(BaseModel):
    """A single search result."""

    id: str = Field(description="Node ID")
    name: str = Field(description="Node name")
    description: str = Field(description="Node description")
    type: str = Field(description="Node type")
    score: float = Field(description="Similarity score")
    entity_type: str = Field(default="", description="Entity type (for entity nodes)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Node metadata")


class SearchResponse(BaseModel):
    """Response from the search tool."""

    query: str = Field(description="The original search query")
    results: List[SearchResult] = Field(description="List of search results")
    count: int = Field(description="Number of results returned")


def execute_search(parameters: SearchParameters, graph: Graph) -> SearchResponse:
    """
    Execute the search with validated parameters.

    Args:
        parameters: Validated search parameters
        graph: The knowledge graph instance

    Returns:
        Search response with results
    """
    # Perform semantic search
    results = graph.search(parameters.query, limit=parameters.get_limit())

    # Format results
    formatted_results = []
    for node, score in results:
        formatted_results.append(SearchResult(
            id=str(node.id),
            name=getattr(node, "name", ""),
            description=getattr(node, "description", ""),
            type=node.__class__.__name__,
            score=score,
            entity_type=getattr(node, "entity_type", ""),
            metadata=getattr(node, "metadata", {})
        ))

    return SearchResponse(
        query=parameters.query,
        results=formatted_results,
        count=len(formatted_results)
    )


# Legacy function for backward compatibility
def search(graph: Graph, query: str, limit: int = 10) -> Dict[str, Any]:
    """
    Legacy search function for backward compatibility.

    Args:
        graph: The knowledge graph.
        query: The search query.
        limit: Maximum number of results to return.

    Returns:
        Dictionary with search results.
    """
    return execute_search(SearchParameters(query=query, limit=limit), graph).model_dump()