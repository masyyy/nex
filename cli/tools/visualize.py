"""
Visualization tool for rendering graph segments.
"""
from typing import Dict, List, Any, Optional, Literal
import json

from pydantic import BaseModel, Field

from kgraphlib.graph import Graph
from kgraphlib.node import Node
from kgraphlib.edge import Edge
from common.openai_client import ToolParameters


class VisualizeParameters(ToolParameters):
    """Parameters for the visualize tool."""

    node_ids: List[int] = Field(description="List of node IDs to include in the visualization.")
    include_neighbors: Optional[bool] = Field(None, description="Whether to include neighbors of the specified nodes. Default is True if not specified.")
    max_neighbors: Optional[int] = Field(None, description="Maximum number of neighbors to include per node. Default is 5 if not specified.")

    model_config = {
        "json_schema_extra": {
            "title": "visualize",
            "description": "Generate a visualization of a subgraph when requested by the user."
        }
    }

    def get_include_neighbors(self) -> bool:
        """Get include_neighbors with default value if None."""
        return True if self.include_neighbors is None else self.include_neighbors

    def get_max_neighbors(self) -> int:
        """Get max_neighbors with default value if None."""
        return 5 if self.max_neighbors is None else self.max_neighbors


class VisualNodeData(BaseModel):
    """Node data for visualization."""

    id: int = Field(description="Node ID")
    label: str = Field(description="Node label/name")
    title: str = Field(description="Node title/description")
    type: str = Field(description="Node type")
    entity_type: Optional[str] = Field(default=None, description="Type of entity for EntityNodes")
    source: Optional[str] = Field(default=None, description="Source of information for EpisodicNodes")
    timestamp: Optional[str] = Field(default=None, description="Timestamp for EpisodicNodes")
    metadata: Dict[str, str] = Field(default_factory=dict, description="Additional metadata")


class VisualEdgeData(BaseModel):
    """Edge data for visualization."""

    id: int = Field(description="Edge ID")
    from_node: int = Field(alias="from", description="Source node ID")
    to_node: int = Field(alias="to", description="Target node ID")
    label: str = Field(description="Edge label")
    title: str = Field(description="Edge title/description")
    type: str = Field(description="Edge type")
    weight: float = Field(description="Edge weight")

    model_config = {
        "populate_by_name": True
    }


class VisualizationData(BaseModel):
    """Data for visualization."""

    nodes: List[VisualNodeData] = Field(description="List of nodes")
    edges: List[VisualEdgeData] = Field(description="List of edges")


class VisualizeResponse(BaseModel):
    """Response from the visualize tool."""

    visualization_data: VisualizationData = Field(description="Data for visualization")
    text_representation: str = Field(description="Text representation of the graph")
    node_count: int = Field(description="Number of nodes in the visualization")
    edge_count: int = Field(description="Number of edges in the visualization")


def _format_node(node: Node) -> VisualNodeData:
    """Format a node for visualization."""
    # For EntityNode, use name as label; for EpisodicNode, use a summary of content
    # For any other node type, use ID as label
    # TODO: This is dirty, we should use a better way to do this
    if hasattr(node, 'name'):
        label = node.name
    elif hasattr(node, 'content'):
        # For content, use first 20 chars as label
        label = node.content[:20] + "..." if len(node.content) > 20 else node.content
    else:
        label = f"Node {node.id}"

    # Get individual field values
    entity_type = getattr(node, 'entity_type', None)
    source = getattr(node, 'source', None)
    timestamp = str(node.timestamp) if hasattr(node, 'timestamp') and node.timestamp else None

    return VisualNodeData(
        id=node.id,
        label=label,
        title=node.description or "",
        type=node.__class__.__name__,
        entity_type=entity_type,
        source=source,
        timestamp=timestamp,
        metadata=node.metadata
    )


def _format_edge(edge: Edge) -> VisualEdgeData:
    """Format an edge for visualization."""
    return VisualEdgeData(
        id=edge.id,
        from_node=edge.source_id,
        to_node=edge.target_id,
        label=edge.relation_type,
        title=edge.description or json.dumps(edge.metadata) if edge.metadata else "",
        type=edge.__class__.__name__,
        weight=1.0  # Default weight as this attribute doesn't exist in Edge
    )


def _generate_text_representation(nodes: List[VisualNodeData], edges: List[VisualEdgeData]) -> str:
    """Generate a text representation of the graph."""
    # Create a mapping of node IDs to labels
    node_labels = {node.id: node.label for node in nodes}

    # Generate text
    lines = []

    # Add nodes
    lines.append("Nodes:")
    for node in nodes:
        node_type = node.type
        node_label = node.label
        node_desc = node.title or "No description"
        lines.append(f"  - {node_label} ({node_type}): {node_desc}")

    # Add edges
    lines.append("\nRelationships:")
    for edge in edges:
        source_label = node_labels.get(edge.from_node, str(edge.from_node))
        target_label = node_labels.get(edge.to_node, str(edge.to_node))
        edge_label = edge.label
        lines.append(f"  - {source_label} --[{edge_label}]--> {target_label}")

    return "\n".join(lines)


def execute_visualize(parameters: VisualizeParameters, graph: Graph) -> VisualizeResponse:
    """
    Execute the visualization with validated parameters.

    Args:
        parameters: Validated visualization parameters
        graph: The knowledge graph instance

    Returns:
        Visualization response with results
    """
    # Get the nodes
    nodes = []
    edges = []
    node_set = set()
    edge_set = set()

    # Add the specified nodes
    for node_id in parameters.node_ids:
        node = graph.get_node(node_id)
        if node:
            nodes.append(_format_node(node))
            node_set.add(node_id)

            # Add neighbors if requested
            if parameters.get_include_neighbors():
                neighbors = graph.get_neighbors(node_id)

                # Limit the number of neighbors
                for i, (edge, neighbor) in enumerate(neighbors):
                    if i >= parameters.get_max_neighbors():
                        break

                    # Add neighbor node if not already included
                    if neighbor.id not in node_set:
                        nodes.append(_format_node(neighbor))
                        node_set.add(neighbor.id)

                    # Add edge if not already included
                    if edge.id not in edge_set:
                        edges.append(_format_edge(edge))
                        edge_set.add(edge.id)

    # Get edges between the specified nodes
    for i, node_id1 in enumerate(parameters.node_ids):
        for node_id2 in parameters.node_ids[i+1:]:
            # Get edges from node1 to node2
            edges_1_to_2 = graph.get_edges_between(node_id1, node_id2)
            for edge in edges_1_to_2:
                if edge.id not in edge_set:
                    edges.append(_format_edge(edge))
                    edge_set.add(edge.id)

            # Get edges from node2 to node1
            edges_2_to_1 = graph.get_edges_between(node_id2, node_id1)
            for edge in edges_2_to_1:
                if edge.id not in edge_set:
                    edges.append(_format_edge(edge))
                    edge_set.add(edge.id)

    # Generate visualization data
    visualization_data = VisualizationData(
        nodes=nodes,
        edges=edges
    )

    # Generate a text representation
    text_representation = _generate_text_representation(nodes, edges)

    return VisualizeResponse(
        visualization_data=visualization_data,
        text_representation=text_representation,
        node_count=len(nodes),
        edge_count=len(edges)
    )


# Legacy function for backward compatibility
def visualize(graph: Graph, node_ids: List[int], include_neighbors: bool = True, max_neighbors: int = 5) -> Dict[str, Any]:
    """
    Legacy visualize function for backward compatibility.

    Args:
        graph: The knowledge graph.
        node_ids: List of node IDs to include in the visualization.
        include_neighbors: Whether to include neighbors of the specified nodes.
        max_neighbors: Maximum number of neighbors to include per node.

    Returns:
        Dictionary with visualization data.
    """
    return execute_visualize(
        VisualizeParameters(
            node_ids=node_ids,
            include_neighbors=include_neighbors,
            max_neighbors=max_neighbors
        ),
        graph
    ).model_dump()