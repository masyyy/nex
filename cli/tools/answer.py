"""
Answer tool for generating responses based on graph knowledge.
"""
from typing import Dict, Any, Literal

from pydantic import BaseModel, Field

from kgraphlib.graph import Graph
from common.openai_client import ToolParameters


class AnswerParameters(ToolParameters):
    """Parameters for the answer tool."""

    answer: str = Field(
        description="The final answer to the user's query."
    )

    model_config = {
        "json_schema_extra": {
            "title": "answer",
            "description": "Provide a final answer to the user's query when enough information has been gathered."
        }
    }


class AnswerResponse(BaseModel):
    """Response from the answer tool."""

    answer: str = Field(
        description="The final answer to the user's query."
    )


def execute_answer(parameters: AnswerParameters, graph: Graph) -> AnswerResponse:
    """
    Execute the answer tool with validated parameters.

    Args:
        parameters: Validated answer parameters
        graph: The knowledge graph instance

    Returns:
        Answer response
    """
    return AnswerResponse(
        answer=parameters.answer
    )


# Legacy function for backward compatibility
def answer(graph: Graph, answer: str) -> Dict[str, Any]:
    """
    Legacy answer function for backward compatibility.

    Args:
        graph: The knowledge graph.
        answer: The answer to provide to the user.

    Returns:
        Dictionary with the answer.
    """
    return execute_answer(AnswerParameters(answer=answer), graph)