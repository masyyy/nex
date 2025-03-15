"""
Query tool for retrieving connected nodes.
"""
from typing import Dict, List, Any, Optional, Literal
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from kgraphlib.graph import Graph
from kgraphlib.node import Node
from kgraphlib.edge import Edge
from common.openai_client import ToolParameters


class QueryParameters(ToolParameters):
    """Parameters for the query tool."""

    start_node_id: int = Field(
        description="ID of the node to start from."
    )
    relation_type: Optional[str] = Field(
        default=None,
        description="Optional filter for specific relationship type available in the graph."
        "Available relation_types can be queried using the QueryRelationTypeParameters tool."
    )
    start_time: Optional[str] = Field(
        default=None,
        description="Optional filter for relationships active after this time. Format: YYYY-MM-DD or ISO format."
    )
    end_time: Optional[str] = Field(
        default=None,
        description="Optional filter for relationships active before this time. Format: YYYY-MM-DD or ISO format."
    )

    # Parsed datetime objects (not visible in the schema)
    _start_time_dt: Optional[datetime] = None
    _end_time_dt: Optional[datetime] = None

    @model_validator(mode='after')
    def parse_dates(self):
        """Parse string dates into datetime objects."""
        if self.start_time:
            try:
                self._start_time_dt = datetime.fromisoformat(self.start_time)
            except ValueError:
                try:
                    self._start_time_dt = datetime.strptime(self.start_time, "%Y-%m-%d")
                except ValueError:
                    # Invalid date format, will be handled in execute_query
                    pass

        if self.end_time:
            try:
                self._end_time_dt = datetime.fromisoformat(self.end_time)
            except ValueError:
                try:
                    self._end_time_dt = datetime.strptime(self.end_time, "%Y-%m-%d")
                except ValueError:
                    # Invalid date format, will be handled in execute_query
                    pass

        return self


class NodeInfo(BaseModel):
    """Information about a node."""

    id: int = Field(description="Node ID")
    name: str = Field(description="Node name or label")
    description: str = Field(description="Node description")
    type: str = Field(description="Node type")
    entity_type: Optional[str] = Field(default=None, description="Entity type (for entity nodes)")
    metadata: Dict[str, str] = Field(default_factory=dict, description="Node metadata")


class EdgeInfo(BaseModel):
    """Information about an edge."""

    id: int = Field(description="Edge ID")
    relation_type: str = Field(description="Relation type")
    source_id: int = Field(description="Source node ID")
    target_id: int = Field(description="Target node ID")
    description: str = Field(default="", description="Edge description")
    metadata: Dict[str, str] = Field(default_factory=dict, description="Edge metadata")
    start_time: Optional[datetime] = Field(default=None, description="When the relationship began")
    end_time: Optional[datetime] = Field(default=None, description="When the relationship ended")


class ConnectionInfo(BaseModel):
    """Information about a node-edge connection."""

    node: NodeInfo = Field(description="Target node information")
    edge: EdgeInfo = Field(description="Edge connecting to the target")


class QueryResponse(BaseModel):
    """Response from the query tool."""

    start_node: NodeInfo = Field(description="Starting node information")
    connections: List[ConnectionInfo] = Field(description="List of connected nodes and edges")
    count: int = Field(description="Number of connections found")
    relation_type: Optional[str] = Field(default=None, description="Relation type filter used")
    error: Optional[str] = Field(default=None, description="Error message if any")


def execute_query(parameters: QueryParameters, graph: Graph) -> QueryResponse:
    """
    Execute the query with validated parameters.

    Args:
        parameters: Validated query parameters
        graph: The knowledge graph instance

    Returns:
        Query response with results
    """
    # Get the starting node
    start_node = graph.get_node(parameters.start_node_id)
    if not start_node:
        return QueryResponse(
            start_node=NodeInfo(
                id=parameters.start_node_id,
                name="",
                description="",
                type=""
            ),
            connections=[],
            count=0,
            relation_type=parameters.relation_type,
            error=f"Node with ID {parameters.start_node_id} not found."
        )

    # Check for date parsing errors
    if parameters.start_time and parameters._start_time_dt is None:
        return QueryResponse(
            start_node=NodeInfo(
                id=start_node.id,
                name=getattr(start_node, "name", str(start_node.id)),
                description=getattr(start_node, "description", ""),
                type=start_node.__class__.__name__,
                entity_type=getattr(start_node, "entity_type", None),
                metadata=getattr(start_node, "metadata", {})
            ),
            connections=[],
            count=0,
            relation_type=parameters.relation_type,
            error=f"Invalid date format for start_time: {parameters.start_time}. Use YYYY-MM-DD or ISO format."
        )

    if parameters.end_time and parameters._end_time_dt is None:
        return QueryResponse(
            start_node=NodeInfo(
                id=start_node.id,
                name=getattr(start_node, "name", str(start_node.id)),
                description=getattr(start_node, "description", ""),
                type=start_node.__class__.__name__,
                entity_type=getattr(start_node, "entity_type", None),
                metadata=getattr(start_node, "metadata", {})
            ),
            connections=[],
            count=0,
            relation_type=parameters.relation_type,
            error=f"Invalid date format for end_time: {parameters.end_time}. Use YYYY-MM-DD or ISO format."
        )

    # Query the graph for connections
    connections = graph.query(
        start_node_id=parameters.start_node_id,
        relation_type=parameters.relation_type,
        start_time=parameters._start_time_dt,
        end_time=parameters._end_time_dt
    )

    # Format the results
    formatted_connections = []
    for target_node, edge in connections:
        formatted_connections.append(ConnectionInfo(
            node=NodeInfo(
                id=target_node.id,
                name=getattr(target_node, "name", str(target_node.id)),
                description=getattr(target_node, "description", ""),
                type=target_node.__class__.__name__,
                entity_type=getattr(target_node, "entity_type", None),
                metadata=getattr(target_node, "metadata", {})
            ),
            edge=EdgeInfo(
                id=edge.id,
                relation_type=edge.relation_type,
                source_id=edge.source_id,
                target_id=edge.target_id,
                description=getattr(edge, "description", ""),
                metadata=getattr(edge, "metadata", {}),
                start_time=getattr(edge, "start_time", None),
                end_time=getattr(edge, "end_time", None)
            )
        ))

    return QueryResponse(
        start_node=NodeInfo(
            id=start_node.id,
            name=getattr(start_node, "name", str(start_node.id)),
            description=getattr(start_node, "description", ""),
            type=start_node.__class__.__name__,
            entity_type=getattr(start_node, "entity_type", None),
            metadata=getattr(start_node, "metadata", {})
        ),
        connections=formatted_connections,
        count=len(formatted_connections),
        relation_type=parameters.relation_type
    )