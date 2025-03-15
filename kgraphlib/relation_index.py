"""
Relation index for efficient relation type deduplication.
"""
import logging
import re
from typing import Any, List, Optional

from common.openai_client import OpenAIClient
from kgraphlib.database.repositories.relation_type_repository import RelationTypeRepository
from kgraphlib.relation_type import RelationType


logger = logging.getLogger(__name__)


class RelationIndex:
    """
    Index for relation type deduplication using vector similarity.

    This class helps manage relation types in the knowledge graph by
    deduplicating similar relation types through vector similarity.
    """

    def __init__(self, similarity_threshold: float = 0.9) -> None:
        """
        Initialize a new relation index.

        Args:
            similarity_threshold: Threshold for considering relation types similar (0-1)
        """
        self._similarity_threshold = similarity_threshold
        self._repository = RelationTypeRepository()
        self._openai_client = OpenAIClient()

    def _slugify_relation_type(self, relation_type: str) -> str:
        """
        Convert relation type to slug format (lowercase with underscores).

        Args:
            relation_type: The relation type to slugify

        Returns:
            Slugified relation type string
        """
        # Convert to lowercase
        slug = relation_type.lower()

        # Replace spaces and hyphens with underscores
        slug = re.sub(r'[\s-]+', '_', slug)

        # Replace multiple consecutive underscores with a single one
        slug = re.sub(r'_+', '_', slug)

        # Remove leading/trailing underscores
        slug = slug.strip('_')

        return slug

    def get_or_create_relation_type(
        self,
        relation_type: str,
        description: str,
    ) -> str:
        """
        Get an existing similar relation type or create a new one.

        Args:
            relation_type: Proposed relation type string
            description: Description of the relationship

        Returns:
            The canonical relation type string to use
        """
        # Slugify the relation type
        slugified_type = self._slugify_relation_type(relation_type)

        # Check database for exact string match with the slugified version
        existing_type = self._repository.get_by_type(slugified_type)
        if existing_type:
            return slugified_type

        # Create embedding for the relation type and description
        text_to_embed = f"{slugified_type}: {description}"
        embedding_list = self._openai_client.create_embedding([text_to_embed])[0]

        # Try to find similar types - this may fail if vector operations aren't supported
        try:
            similar_types = self._repository.find_similar_types(
                embedding=embedding_list,
                threshold=self._similarity_threshold,
                limit=1
            )

            if similar_types:
                # Found a similar relation type
                similar_type = similar_types[0]
                logger.info(
                    f"Found similar relation type: '{similar_type.type}' for '{slugified_type}'"
                )
                # Return the canonical type
                return similar_type.type
        except Exception as e:
            # If similarity search fails, log it but continue with creating a new type
            logger.warning(f"Similarity search failed: {e}. Creating new relation type.")

        # No similar type found or similarity search failed, create a new one
        try:
            # Create a domain model instance with the embedding
            new_relation_type = RelationType(
                type=slugified_type,
                description=description,
                embedding=embedding_list
            )

            # Save to database
            saved_type = self._repository.save(new_relation_type)
            if not saved_type:
                logger.error(f"Failed to save relation type '{slugified_type}'")
                # Still return the original type since we couldn't save a new one
                return slugified_type

            return slugified_type
        except Exception as e:
            # If saving fails, log the error but return the original type
            logger.error(f"Failed to save relation type: {e}")
            return slugified_type

    def get_relation_types(self) -> List[RelationType]:
        """
        Get all available relation types in the index.

        Returns:
            List of all relation types with their descriptions
        """
        # Fetch all relation types from the database
        return self._repository.get_all(limit=1000)

    # Compatibility method for old code
    def clear(self) -> None:
        """Clear the relation index cache (does not delete from database)."""
        # No-op since we don't have a cache anymore
        pass