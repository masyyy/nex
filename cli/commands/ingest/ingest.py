"""
Functions for ingesting documents into the knowledge graph.
"""
import logging
import os
import time

from cli.commands.ingest.chunking import extract_text_from_pdf, extract_text_from_txt
from cli.commands.ingest.models import GraphStructure
from common.message_history import MessageHistory
from common.openai_client import OpenAIClient
from kgraphlib.edge import EntityEdge, EpisodicEdge
from kgraphlib.graph import Graph
from kgraphlib.node import EntityNode, EpisodicNode

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def extract_graph_json(text: str, client: OpenAIClient) -> GraphStructure:
    """Extract entity and relationship information from text using OpenAI.

    Args:
        text: Text to analyze.
        client: OpenAIClient instance.

    Returns:
        GraphStructure containing entities and relationships.
    """
    system_prompt = """
    You are an expert in extracting information from text and representing it as a knowledge graph.

    Extract entities and their relationships from the given text. Identify key people, places,
    organizations, concepts, and the relationships between them.

    Provide your response as a JSON object with the following structure:
    {
        "entity_nodes": [
            {
                "name": "Entity name",
                "entity_type": "generated_entity_type",
                "description": "Brief description of the entity"
            }
        ],
        "edges": [
            {
                "source_name": "Source entity name",
                "target_name": "Target entity name",
                "relation_type": "generated_relationship_type",
                "description": "Brief description of the relationship"
            }
        ]
    }

    Only include well-supported information from the text. Don't invent connections that aren't
    clearly implied. If there are no entities or relationships, return empty arrays.
    """

    user_prompt = f"Extract entities and relationships from the following text:\n\n{text}"

    # Create message history
    history = MessageHistory()
    history.add_system_prompt(system_prompt)
    history.add_user_prompt(user_prompt)

    # Use generate_structured to get the response as a GraphStructure
    result = client.generate_structured(
        history=history,
        output_type=GraphStructure,
    )

    return result

def ingest_pdf(file_path: str) -> dict[str, int]:
    """Ingest a PDF or text file into the knowledge graph.

    Args:
        file_path: Path to the PDF or TXT file.
        graph: Optional Graph instance. If not provided, a new one will be created.

    Returns:
        Dictionary with number of entities and relationships added.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    graph = Graph()

    # Extract text based on file type
    file_ext = os.path.splitext(file_path)[1].lower()
    try:
        if file_ext == ".pdf":
            pages = extract_text_from_pdf(file_path)
        elif file_ext == ".txt":
            pages = extract_text_from_txt(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")
    except Exception as e:
        log.error(f"Text extraction failed: {e}")
        raise

    log.info(f"Extracted {len(pages)} pages from {file_path}")

    # Create OpenAI client
    client = OpenAIClient()

    # For each page, create an EpisodicNode and extract the graph
    total_entities = 0
    total_edges = 0
    for i, page_content in enumerate(pages):
        log.info(f"Processing page {i+1}/{len(pages)}")

        # Skip empty or very small pages
        if not page_content or len(page_content) < 50:
            log.info(f"Skipping page {i+1} - not enough content")
            continue

        # Generate a description for the chunk/page
        page_description = f"Page {i+1}"

        # Create and add the page node
        page_node = EpisodicNode(
            content=page_content,
            description=page_description,
            source=file_path,
            metadata={"file_path": file_path, "page_number": str(i+1)},
        )
        page_node = graph.add_node(page_node)

        # Extract entities and edges from the page
        graph_structure = extract_graph_json(page_content, client)
        entities_added = 0
        edges_added = 0

        # Dictionary to map entity names to their node objects
        entity_name_to_node = {}

        # Create embedding texts for all entities in one batch
        embedding_texts = [f"{entity.name}\n{entity.description or ''}" for entity in graph_structure.entity_nodes]

        if embedding_texts:
            embeddings = client.create_embedding(embedding_texts)
        else:
            embeddings = []

        # Create entity nodes with their corresponding embeddings
        for idx, entity in enumerate(graph_structure.entity_nodes):
            node = EntityNode(
                name=entity.name,
                entity_type=entity.entity_type,
                description=entity.description or "",
                embedding=embeddings[idx]
            )
            node = graph.add_node(node)
            entity_name_to_node[node.name.lower()] = node

            # Add provenance edge from entity to page
            provenance_edge = EpisodicEdge(
                source_id=node.id,
                target_id=page_node.id,
                relation_type="extracted_from",
                description=f"Entity extracted from page {i+1}",
            )
            graph.add_edge(provenance_edge)
            entities_added += 1

        # Second pass: create entity edges using the node IDs
        for edge in graph_structure.edges:
            source_node = entity_name_to_node.get(edge.source_name.lower())
            target_node = entity_name_to_node.get(edge.target_name.lower())

            # Only create edges if both source and target nodes exist
            if source_node is not None and target_node is not None:
                # Create the relationship between entities
                graph.add_edge(
                    EntityEdge(
                        source_id=source_node.id,
                        target_id=target_node.id,
                        relation_type=edge.relation_type,
                        description=edge.description or "",
                    ),
                )
                edges_added += 1

        total_entities += entities_added
        total_edges += edges_added
        log.info(f"Page {i+1}: Added {entities_added} entities and {edges_added} relationships")

    return {
        "entities_added": total_entities,
        "relationships_added": total_edges,
    }