"""
OpenAI API client for the knowledge graph.
"""
import json
import logging
import os
from collections.abc import Sequence
from typing import Any, Literal, TypeVar, Type, Union

import openai
from openai import pydantic_function_tool
from pydantic import BaseModel

from common.config import config
from common.message_history import MessageHistory
from common.models import LLMResponse, ToolCall, ToolParameters

# Set up logger
logger = logging.getLogger(__name__)

# Get OpenAI configuration
openai_config = config.get_openai_config()

# Type variable for Pydantic models
T = TypeVar('T', bound=BaseModel)

class OpenAIClient:
    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY") or openai_config.api_key
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        self.client = openai.OpenAI(api_key=api_key)
        self.async_client = openai.AsyncOpenAI(api_key=api_key)
        self.completion_model = openai_config.completion_model
        self.embedding_model = openai_config.embedding_model

    # ruff: noqa: PLR0913
    def generate(
        self,
        history: MessageHistory,
        tools: Sequence[type[ToolParameters]] | None = None,
        tool_choice: Literal["none", "auto", "required"] | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """
        Generate a chat completion using the OpenAI API with a MessageHistory instance.

        Args:
            history: MessageHistory instance containing the conversation history
            tools: Optional list of tool parameter models that inherit from ToolParameters
            tool_choice: How the model should use tools. One of "none", "auto", or "required"
            model: Optional model override. If not provided, uses the model from config
            temperature: Optional temperature override
            max_tokens: Optional max tokens override

        Returns:
            LLMResponse containing either content or tool calls or both
        """
        # Get the completion model from config if not provided
        model = model or self.completion_model

        # Create OpenAI tool definitions with one line
        openai_tools = [pydantic_function_tool(tool_cls) for tool_cls in tools] if tools else None

        # Make the API call
        response = self.client.chat.completions.create(
            model=model,
            messages=history.get_messages(),
            tools=openai_tools,
            tool_choice=tool_choice,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # Parse the response
        message = response.choices[0].message
        tool_calls = []

        # Parse any tool calls
        if message.tool_calls:
            # Import tools here to avoid circular imports
            from cli.tools import (
                AnswerParameters,
                QueryParameters,
                SearchParameters,
                VisualizeParameters,
                QueryRelationTypeParameters,
            )

            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)

                # Direct mapping based on tool name
                # TODO: maybe don't parse here, the dependency is circular
                if tool_name == "SearchParameters":
                    params = SearchParameters(**args)
                    tool_type = "search"
                elif tool_name == "QueryParameters":
                    params = QueryParameters(**args)
                    tool_type = "query"
                elif tool_name == "VisualizeParameters":
                    params = VisualizeParameters(**args)
                    tool_type = "visualize"
                elif tool_name == "AnswerParameters":
                    params = AnswerParameters(**args)
                    tool_type = "answer"
                elif tool_name == "QueryRelationTypeParameters":
                    params = QueryRelationTypeParameters(**args)
                    tool_type = "relation_type"
                else:
                    error_message = f"Unknown tool name: {tool_name}"
                    raise ValueError(error_message)

                # Create the tool call
                tool_calls.append(ToolCall(
                    parameters=params,
                    tool_type=tool_type,
                    id=tool_call.id,
                ))

        return LLMResponse(
            content=message.content,
            tool_calls=tool_calls,
        )

    def create_embedding(self, texts: list[str]) -> list[list[float]]:
        """
        Create embeddings for a batch of texts.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors.
        """
        # Create embeddings for the batch
        response = self.client.embeddings.create(
            model=self.embedding_model,
            input=texts,
        )

        # Return all embeddings as regular Python lists to ensure JSON serialization works
        return [list(data.embedding) for data in response.data]

    def generate_structured(
        self,
        history: MessageHistory,
        output_type: Type[T],
        temperature: float = 0.0
    ) -> T:
        """
        Generate a structured response using OpenAI model (synchronous version)

        Args:
            history: MessageHistory instance containing the conversation history
            output_type: The Pydantic model class to use for structured output
            temperature: Controls randomness (lower is more deterministic)

        Returns:
            An instance of the specified output_type Pydantic model
        """
        try:
            # Use the parse method with OpenAI client
            completion = self.client.beta.chat.completions.parse(
                model=self.completion_model,
                messages=history.get_messages(),
                response_format=output_type,
                temperature=temperature,
            )

            # The response is already parsed into the specified Pydantic model
            return completion.choices[0].message.parsed
        except Exception as e:
            # If the model can't parse into the requested format,
            # we can't create a generic fallback, so re-raise
            raise ValueError(f"Failed to generate structured output: {str(e)}") from e

    async def generate_structured_async(
        self,
        history: MessageHistory,
        output_type: Type[T],
        temperature: float = 0.2
    ) -> T:
        """
        Generate a structured response using OpenAI model (async version)

        Args:
            history: MessageHistory instance containing the conversation history
            output_type: The Pydantic model class to use for structured output
            temperature: Controls randomness (lower is more deterministic)

        Returns:
            An instance of the specified output_type Pydantic model
        """
        try:
            # Use the async parse method with AsyncOpenAI client
            completion = await self.async_client.beta.chat.completions.parse(
                model=self.completion_model,
                messages=history.get_messages(),
                response_format=output_type,
                temperature=temperature,
            )

            # The response is already parsed into the specified Pydantic model
            return completion.choices[0].message.parsed
        except Exception as e:
            # If the model can't parse into the requested format,
            # we can't create a generic fallback, so re-raise
            raise ValueError(f"Failed to generate structured output: {str(e)}") from e