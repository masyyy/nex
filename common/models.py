"""
Common models used across the application.
"""
from typing import List, Optional
from pydantic import BaseModel, Field

class ToolParameters(BaseModel):
    """Base model for all tool parameters.

    This model serves as a common type for all tool parameter classes,
    allowing them to be used generically in the agent loop and OpenAI client.
    """
    @classmethod
    def get_schema_title(cls) -> str:
        """Get the tool name (schema title) for this tool."""
        schema = cls.model_json_schema()
        return schema.get("title")

    @classmethod
    def get_schema_description(cls) -> str:
        """Get the tool description for this tool."""
        schema = cls.model_json_schema()
        return schema.get("description")


class ToolCall(BaseModel):
    """Wrapper for tool calls with metadata."""
    parameters: ToolParameters
    tool_type: str
    id: Optional[str] = None

    model_config = {"arbitrary_types_allowed": True}


class LLMResponse(BaseModel):
    """Response from the LLM."""
    content: Optional[str] = None
    tool_calls: List[ToolCall] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}

    def get_called_tool_types(self) -> List[str]:
        """Get the list of tool types that were called in this response."""
        return [tool_call.tool_type for tool_call in self.tool_calls]