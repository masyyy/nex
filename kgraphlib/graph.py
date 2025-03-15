"""
Graph class for managing the knowledge graph structure.
"""
from kgraphlib.database.database import SessionManager
from kgraphlib.database.repositories import EntityNodeRepository, EpisodicNodeRepository, EntityEdgeRepository, EpisodicEdgeRepository
from kgraphlib.edge import Edge, EntityEdge, EpisodicEdge
from kgraphlib.node import Node, EntityNode, EpisodicNode
from kgraphlib.relation_index import RelationIndex
from typing import Any, List, Optional, Tuple, Union
from common.openai_client import OpenAIClient
from datetime import datetime


class Graph:
    """Main class for managing the graph structure."""

    def __init__(
        self,
        name: str = "default",
        similarity_threshold: float = 0.95
    ) -> None:
        """
        Initialize a new graph.

        Args:
            name: The name of the graph.
            similarity_threshold: Minimum similarity score for node deduplication (default 0.95).
        """
        self.name = name
        self._nodes: dict[int, Node] = {}
        self._edges: dict[int, Edge] = {}

        # Deduplication settings
        self.similarity_threshold = similarity_threshold

        self.entity_node_repository = EntityNodeRepository()
        self.episodic_node_repository = EpisodicNodeRepository()
        self.entity_edge_repository = EntityEdgeRepository()
        self.episodic_edge_repository = EpisodicEdgeRepository()
        self.relation_index = RelationIndex()

    def add_node(self, node: Node) -> Node:
        """
        Add a node to the graph with deduplication for EntityNodes.

        Args:
            node: The node to add.

        Returns:
            The added node or a merged node if a duplicate was found.
        """
        # Only perform deduplication for EntityNodes
        if isinstance(node, EntityNode):
            # First check for exact name matches
            if node.name:
                exact_matches = self.entity_node_repository.get_by_name(node.name)
                if exact_matches:
                    # Merge with the first node that has an exact name match
                    merged_node = self._merge_entity_nodes(node, exact_matches[0])
                    return merged_node

            # Fall back to embedding similarity if no exact name match and embedding exists
            if node.embedding is not None:
                # Check for potential duplicates using vector similarity across whole database
                similar_nodes = self.entity_node_repository.search_by_vector(
                    embedding=node.embedding,
                    limit=1,  # Only check the most similar node
                    threshold=self.similarity_threshold  # Only consider high-confidence matches
                )

                if similar_nodes:
                    # Get the most similar node and check if it exceeds our threshold
                    candidate_node, similarity_score = similar_nodes[0]
                    # Merge information while preserving the existing node's relationships
                    merged_node = self._merge_entity_nodes(node, candidate_node)
                    return merged_node

        # If no duplicate found or node is not an EntityNode, proceed with normal addition
        # Save node to database based on type
        if isinstance(node, EntityNode):
            self.entity_node_repository.save(node)
        elif isinstance(node, EpisodicNode):
            self.episodic_node_repository.save(node)
        else:
            raise ValueError(f"Unsupported node type: {type(node)}")

        # Add to in-memory cache
        if node.id is not None:
            self._nodes[node.id] = node

        return node

    def _merge_entity_nodes(self, new_node: EntityNode, existing_node: EntityNode) -> EntityNode:
        """
        Merge information from two entity nodes representing the same entity.

        Args:
            new_node: The new node being added
            existing_node: The existing node found as a duplicate

        Returns:
            A merged node containing information from both sources
        """
        from cli.commands.ingest.models import EntityNode as EntityNodeModel
        from common.message_history import MessageHistory

        openai_client = OpenAIClient()

        # Create message history for the structured output request
        history = MessageHistory()
        history.add_system_prompt(
            "You are a knowledge graph assistant. Your task is to merge information about entities."
        )

        # Create a prompt for merging node content
        merge_prompt = f"""
        Merge these two entity descriptions into a single, comprehensive description.

        Entity 1:
        Name: {new_node.name}
        Type: {new_node.entity_type}
        Description: {new_node.description}

        Entity 2:
        Name: {existing_node.name}
        Type: {existing_node.entity_type}
        Description: {existing_node.description}

        Create a merged entity that combines all unique information from both sources.
        Choose the most specific entity type if they differ.
        """

        history.add_user_prompt(merge_prompt)

        # Use OpenAI's structured output capability with the EntityNode Pydantic model
        merged_entity = openai_client.generate_structured(
            history=history,
            output_type=EntityNodeModel,
            temperature=0.0
        )

        # Create a new embedding for the merged content
        embedding_text = f"{merged_entity.name}\n{merged_entity.description}"
        merged_embedding = openai_client.create_embedding([embedding_text])[0]

        # Create merged node (preserve existing node's ID and relationships)
        merged_node = EntityNode(
            id=existing_node.id,
            name=merged_entity.name,
            description=merged_entity.description,
            entity_type=merged_entity.entity_type,
            embedding=merged_embedding
        )

        # Update the node in the database
        self.entity_node_repository.save(merged_node)

        # Update in-memory cache
        if merged_node.id is not None:
            self._nodes[merged_node.id] = merged_node

        return merged_node

    def add_edge(self, edge: Edge) -> Edge:
        """
        Add an edge to the graph with deduplication for EntityEdges.

        Args:
            edge: The edge to add.

        Returns:
            The added edge or a merged edge if a duplicate was found.
        """
        # Use relation type deduplication to get canonical label
        canonical_label = self.relation_index.get_or_create_relation_type(
            relation_type=edge.relation_type,
            description=edge.description or f"Relationship from {edge.source_id} to {edge.target_id}"
        )

        # Update the edge relation_type if a similar relation type was found
        if canonical_label != edge.relation_type:
            edge.relation_type = canonical_label

        # Only perform deduplication for EntityEdges
        if isinstance(edge, EntityEdge):
            # Check for existing edges between same source and target
            existing_edges = self.get_edges_between(
                source_id=str(edge.source_id),
                target_id=str(edge.target_id)
            )

            if existing_edges:
                # Check for edges with the same relation type
                same_relation_edges = [e for e in existing_edges if e.relation_type == edge.relation_type]

                if same_relation_edges:
                    # For edges with identical source, target, and relation type, merge them
                    merged_edge = self._merge_entity_edges(edge, same_relation_edges[0])
                    return merged_edge

        # Save edge to database based on type
        if isinstance(edge, EntityEdge):
            self.entity_edge_repository.save(edge)
        elif isinstance(edge, EpisodicEdge):
            self.episodic_edge_repository.save(edge)
        else:
            raise ValueError(f"Unsupported edge type: {type(edge)}")

        # Add to in-memory cache
        if edge.id is not None:
            self._edges[edge.id] = edge

        return edge

    def _merge_entity_edges(self, new_edge: EntityEdge, existing_edge: EntityEdge) -> EntityEdge:
        """
        Merge information from two edges representing the same relationship.

        Args:
            new_edge: The new edge being added
            existing_edge: The existing edge found as a duplicate

        Returns:
            A merged edge containing information from both sources
        """
        from cli.commands.ingest.models import Edge as EdgeModel
        from common.message_history import MessageHistory

        # Only merge if descriptions differ and aren't empty
        if (new_edge.description and existing_edge.description and
            new_edge.description != existing_edge.description):

            openai_client = OpenAIClient()

            # Get node content for context
            source_node = self.get_node(int(existing_edge.source_id))
            target_node = self.get_node(int(existing_edge.target_id))

            # Get appropriate fields based on node type
            if isinstance(source_node, EntityNode):
                source_content = f"{source_node.name}: {source_node.description}" if source_node else f"Node {existing_edge.source_id}"
            else:
                source_content = source_node.description if source_node else f"Node {existing_edge.source_id}"

            if isinstance(target_node, EntityNode):
                target_content = f"{target_node.name}: {target_node.description}" if target_node else f"Node {existing_edge.target_id}"
            else:
                target_content = target_node.description if target_node else f"Node {existing_edge.target_id}"

            # Create message history for the structured output request
            history = MessageHistory()
            history.add_system_prompt(
                "You are a knowledge graph assistant. Your task is to merge information about relationships."
            )

            # Create prompt for merging edge descriptions
            merge_prompt = f"""
            Merge these two relationship descriptions into a single, comprehensive description.

            Source Entity: {source_content}
            Target Entity: {target_content}
            Relationship Type: {existing_edge.relation_type}

            Description 1: {new_edge.description}
            Description 2: {existing_edge.description}

            Create a merged relationship description that combines all unique information from both sources.
            """

            history.add_user_prompt(merge_prompt)

            # Use OpenAI's structured output capability with the Edge Pydantic model
            merged_edge_model = openai_client.generate_structured(
                history=history,
                output_type=EdgeModel,
                temperature=0.0
            )

            # Create merged edge (preserve existing edge's ID and relationships)
            merged_edge = EntityEdge(
                id=existing_edge.id,
                source_id=existing_edge.source_id,
                target_id=existing_edge.target_id,
                relation_type=existing_edge.relation_type,
                description=merged_edge_model.description
            )

            # Update the edge in the database
            self.entity_edge_repository.save(merged_edge)

            # Update in-memory cache
            if merged_edge.id is not None:
                self._edges[merged_edge.id] = merged_edge

            return merged_edge

        # If descriptions are the same or empty, just return the existing edge
        return existing_edge

    def remove_edge(self, edge_id: int) -> bool:
        """
        Remove an edge from the graph.

        Args:
            edge_id: The ID of the edge to remove.

        Returns:
            True if the edge was removed, False otherwise.
        """
        # Get the edge
        edge = self.get_edge(edge_id)
        if not edge:
            return False

        # Remove from database
        if isinstance(edge, EntityEdge):
            self.entity_edge_repository.delete(edge_id)
        elif isinstance(edge, EpisodicEdge):
            self.episodic_edge_repository.delete(edge_id)

        # Remove from in-memory cache
        if edge_id in self._edges:
            del self._edges[edge_id]

        return True

    def get_node(self, node_id: int) -> Node | None:
        """
        Get a node by ID.

        Args:
            node_id: The ID of the node.

        Returns:
            The node, or None if not found.
        """
        # Check in-memory cache first
        if node_id in self._nodes:
            return self._nodes[node_id]

        # If not in cache, try to load from database
        node = self.entity_node_repository.get_by_id(node_id)
        if node:
            # Add to cache
            self._nodes[node_id] = node
            return node

        # Try episodic nodes
        node = self.episodic_node_repository.get_by_id(node_id)
        if node:
            # Add to cache
            self._nodes[node_id] = node
            return node

        return None

    def get_edge(self, edge_id: int) -> Edge | None:
        """
        Get an edge by ID.

        Args:
            edge_id: The ID of the edge.

        Returns:
            The edge, or None if not found.
        """
        # Check in-memory cache first
        if edge_id in self._edges:
            return self._edges[edge_id]

        # If not in cache, try to load from database
        edge = self.entity_edge_repository.get_by_id(edge_id)
        if edge:
            # Add to cache
            self._edges[edge_id] = edge
            return edge

        # Try episodic edges
        edge = self.episodic_edge_repository.get_by_id(edge_id)
        if edge:
            # Add to cache
            self._edges[edge_id] = edge
            return edge

        return None

    def get_nodes(self, limit: int = 100, offset: int = 0) -> list[Node]:
        """
        Get all nodes in the graph.

        Args:
            limit: Maximum number of nodes to return.
            offset: Number of nodes to skip.

        Returns:
            List of nodes.
        """
        # Get entity nodes from database
        entity_nodes = self.entity_node_repository.get_all(limit=limit, offset=offset)

        # Get episodic nodes from database
        episodic_nodes = self.episodic_node_repository.get_all(limit=limit, offset=offset)

        # Combine and limit results
        nodes = entity_nodes + episodic_nodes
        nodes = nodes[:limit]

        # Update cache
        for node in nodes:
            if node.id is not None:
                self._nodes[node.id] = node

        return nodes

    def get_edges(self, limit: int = 100, offset: int = 0) -> list[Edge]:
        """
        Get all edges in the graph.

        Args:
            limit: Maximum number of edges to return.
            offset: Number of edges to skip.

        Returns:
            List of edges.
        """
        # Get entity edges from database
        entity_edges = self.entity_edge_repository.get_all(limit=limit, offset=offset)

        # Get episodic edges from database
        episodic_edges = self.episodic_edge_repository.get_all(limit=limit, offset=offset)

        # Combine and limit results
        edges = entity_edges + episodic_edges
        edges = edges[:limit]

        # Update cache
        for edge in edges:
            if edge.id is not None:
                self._edges[edge.id] = edge

        return edges

    def get_outgoing_edges(self, node_id: str, relation_type: str | None = None) -> list[Edge]:
        """
        Get outgoing edges from a node.

        Args:
            node_id: The ID of the node.
            relation_type: Optional relation type to filter by.

        Returns:
            List of outgoing edges.
        """
        # Convert string ID to int for repository
        int_node_id = int(node_id)

        # Get edges from appropriate repositories
        entity_edges = self.entity_edge_repository.get_edges_by_source(
            source_id=int_node_id,
            relation_type=relation_type
        )

        episodic_edges = self.episodic_edge_repository.get_edges_by_source(
            source_id=int_node_id,
            relation_type=relation_type
        )

        # Combine results
        edges = entity_edges + episodic_edges

        # Update cache
        for edge in edges:
            if edge.id is not None:
                self._edges[edge.id] = edge

        return edges

    def get_incoming_edges(self, node_id: str, relation_type: str | None = None) -> list[Edge]:
        """
        Get incoming edges to a node.

        Args:
            node_id: The ID of the node.
            relation_type: Optional relation type to filter by.

        Returns:
            List of incoming edges.
        """
        # Convert string ID to int for repository
        int_node_id = int(node_id)

        # Get edges from appropriate repositories
        entity_edges = self.entity_edge_repository.get_edges_by_target(
            target_id=int_node_id,
            relation_type=relation_type
        )

        episodic_edges = self.episodic_edge_repository.get_edges_by_target(
            target_id=int_node_id,
            relation_type=relation_type
        )

        # Combine results
        edges = entity_edges + episodic_edges

        # Update cache
        for edge in edges:
            if edge.id is not None:
                self._edges[edge.id] = edge

        return edges

    def get_neighbors(self, node_id: str, direction: str = "both") -> list[tuple[Edge, Node]]:
        """
        Get neighbors of a node.

        Args:
            node_id: The ID of the node.
            direction: Direction of edges to consider. One of "outgoing", "incoming", or "both".

        Returns:
            List of (edge, neighbor) tuples.
        """
        neighbors = []

        # Get outgoing edges
        if direction in ["outgoing", "both"]:
            outgoing_edges = self.get_outgoing_edges(node_id)
            for edge in outgoing_edges:
                # Get the target node using target_id
                target_node = self.get_node(int(edge.target_id))
                if target_node:
                    neighbors.append((edge, target_node))

        # Get incoming edges
        if direction in ["incoming", "both"]:
            incoming_edges = self.get_incoming_edges(node_id)
            for edge in incoming_edges:
                # Get the source node using source_id
                source_node = self.get_node(int(edge.source_id))
                if source_node:
                    neighbors.append((edge, source_node))

        return neighbors

    def get_edges_between(self, source_id: str, target_id: str, relation_type: str | None = None) -> list[Edge]:
        """
        Get edges between two nodes.

        Args:
            source_id: The ID of the source node.
            target_id: The ID of the target node.
            relation_type: Optional relation type to filter by.

        Returns:
            List of edges between the nodes.
        """
        # Convert string IDs to int for repository
        int_source_id = int(source_id)
        int_target_id = int(target_id)

        # Get edges from appropriate repositories
        entity_edges = self.entity_edge_repository.get_edges_between(
            source_id=int_source_id,
            target_id=int_target_id,
            relation_type=relation_type
        )

        episodic_edges = self.episodic_edge_repository.get_edges_between(
            source_id=int_source_id,
            target_id=int_target_id,
            relation_type=relation_type
        )

        # Combine results
        edges = entity_edges + episodic_edges

        # Update cache
        for edge in edges:
            if edge.id is not None:
                self._edges[edge.id] = edge

        return edges

    def search(self, query: str, limit: int = 10) -> list[tuple[Node, float]]:
        """
        Search for nodes using vector similarity.

        Args:
            query: The search query.
            limit: Maximum number of results to return.

        Returns:
            List of (node, score) tuples sorted by relevance.
        """
        # Generate embedding for the query
        openai_client = OpenAIClient()
        query_embedding = openai_client.create_embedding([query])[0]
        # No need to convert to list as the OpenAIClient now returns lists

        # Use the NodeRepository's search_by_vector method directly
        return self.entity_node_repository.search_by_vector(
            embedding=query_embedding,
            limit=limit,
            threshold=0.0  # No threshold to get all results
        )

    def query(
        self,
        start_node_id: int,
        relation_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Tuple[Node, Edge]]:
        """
        Find nodes directly connected to the start node, filtered by relationship type and time range.

        Args:
            start_node_id: ID of the node to start from
            relation_type: Optional filter for specific relationship type
            start_time: Optional filter for relationships active after this time
            end_time: Optional filter for relationships active before this time

        Returns:
            List of tuples containing (target_node, edge) pairs that match the criteria
        """
        # Get the starting node
        start_node = self.get_node(start_node_id)
        if not start_node:
            return []

        # Get all edges connected to this node (both incoming and outgoing)
        outgoing_edges = self.get_outgoing_edges(str(start_node_id), relation_type)
        incoming_edges = self.get_incoming_edges(str(start_node_id), relation_type)
        all_edges = outgoing_edges + incoming_edges

        # Filter edges by time if specified
        if start_time or end_time:
            filtered_edges = []
            for edge in all_edges:
                edge_start = getattr(edge, 'start_time', None)
                edge_end = getattr(edge, 'end_time', None)

                # Check if edge is active during the specified time range
                if start_time and edge_end and edge_end < start_time:
                    continue
                if end_time and edge_start and edge_start > end_time:
                    continue

                filtered_edges.append(edge)
            all_edges = filtered_edges

        # Build the result list
        result = []
        for edge in all_edges:
            # Determine which node is the target (not the start node)
            if edge.source_id == start_node_id:
                target_id = edge.target_id
            else:
                target_id = edge.source_id

            target_node = self.get_node(target_id)
            if target_node:
                result.append((target_node, edge))

        return result

    def traverse(
        self,
        start_node_id: str,
        query_pattern: list[dict[str, Any]],
        max_depth: int = 3,
    ) -> list[list[Node | Edge]]:
        """
        Execute a traversal query on the graph.

        Args:
            start_node_id: The ID of the starting node.
            query_pattern: List of query steps. Each step is a dictionary with keys:
                - direction: Direction of the edge. One of "outgoing", "incoming", or "both".
                - label: Optional label of the edge.
                - node_type: Optional type of the target node.
            max_depth: Maximum depth of the traversal.

        Returns:
            List of paths. Each path is a list of alternating nodes and edges.
        """
        # Get the starting node
        start_node = self.get_node(int(start_node_id))
        if not start_node:
            return []

        # Initialize paths with the starting node
        paths = [[start_node]]
        completed_paths = []

        # Traverse the graph
        for _ in range(max_depth):
            new_paths = []

            for path in paths:
                # Get the last node in the path
                last_node = path[-1]
                if not isinstance(last_node, Node):
                    continue

                # Get the current step in the query pattern
                step_index = (len(path) - 1) // 2
                if step_index >= len(query_pattern):
                    # We've completed this path
                    completed_paths.append(path)
                    continue

                step = query_pattern[step_index]
                direction = step.get("direction", "outgoing")
                label = step.get("label")
                node_type = step.get("node_type")

                # Get neighbors based on direction
                if direction == "outgoing":
                    edges = self.get_outgoing_edges(str(last_node.id), label)
                elif direction == "incoming":
                    edges = self.get_incoming_edges(str(last_node.id), label)
                else:
                    # Both directions
                    edges = (
                        self.get_outgoing_edges(str(last_node.id), label)
                        + self.get_incoming_edges(str(last_node.id), label)
                    )

                # Filter edges by node type if specified
                if node_type:
                    filtered_edges = []
                    for edge in edges:
                        if direction == "outgoing":
                            neighbor_id = edge.target_id
                        else:
                            neighbor_id = edge.source_id

                        neighbor = self.get_node(int(neighbor_id))
                        if neighbor and neighbor.__class__.__name__.lower() == node_type.lower():
                            filtered_edges.append(edge)
                    edges = filtered_edges

                # Add new paths
                for edge in edges:
                    if direction == "outgoing":
                        neighbor_id = edge.target_id
                    else:
                        neighbor_id = edge.source_id

                    neighbor = self.get_node(int(neighbor_id))
                    if not neighbor:
                        continue

                    # Check for cycles
                    if any(isinstance(item, Node) and item.id == neighbor.id for item in path):
                        continue

                    # Add new path
                    new_path = path.copy()
                    new_path.append(edge)
                    new_path.append(neighbor)
                    new_paths.append(new_path)

            # Update paths
            paths = new_paths

            # If no more paths to explore, break
            if not paths:
                break

        # Add any remaining paths
        completed_paths.extend(paths)

        return completed_paths

    def get_relation_types(self) -> List:
        """
        Get all available relation types in the graph.

        Returns:
            List of relation types with their descriptions
        """
        # Simply return relation types directly from the index
        return self.relation_index.get_relation_types()

    def clear(self) -> None:
        """Clear the graph."""
        self._nodes = {}
        self._edges = {}