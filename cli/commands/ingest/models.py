"""
Models for representing knowledge graph extraction results.
"""
from typing import List, Optional
from pydantic import BaseModel


class EntityNode(BaseModel):
    """
    Represents a node in the knowledge graph - a real-world entity.

    Attributes:
        name: Unique identifier for the entity
        entity_type: Category of the entity (person, place, organization, concept, etc.)
        description: Brief description of the entity
    """
    name: str
    entity_type: str
    description: Optional[str] = None


class Edge(BaseModel):
    """
    Represents a relationship between two entities in the knowledge graph.

    Attributes:
        source_name: Name of the source entity
        target_name: Name of the target entity
        relation_type: Type of relationship between the entities
        description: Brief description of the relationship
    """
    source_name: str
    target_name: str
    relation_type: str
    description: Optional[str] = None


class GraphStructure(BaseModel):
    """
    Represents a complete structure of entities and relationships extracted from text.

    Attributes:
        entity_nodes: List of entities found in the text
        edges: List of relationships between entities
    """
    entity_nodes: List[EntityNode]
    edges: List[Edge]