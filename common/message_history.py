"""
Message history management for OpenAI API compatible chat interactions.
"""
from typing import Dict, List, Any, Optional
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionUserMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionAssistantMessageParam,
)
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall
import json

from common.models import ToolCall


class MessageHistory:
    """Manages chat message history in an OpenAI API compatible format."""

    def __init__(self):
        """Initialize an empty message history."""
        self.messages: List[ChatCompletionMessageParam] = []

    def add_system_prompt(self, system_prompt: str) -> None:
        """
        Add a system prompt to the history.

        Args:
            system_prompt: The system prompt to add.
        """
        self.messages.append(ChatCompletionSystemMessageParam(
            role="system",
            content=system_prompt
        ))

    def add_user_prompt(self, user_prompt: str) -> None:
        """
        Add a user prompt to the history.

        Args:
            user_prompt: The user prompt to add.
        """
        self.messages.append(ChatCompletionUserMessageParam(
            role="user",
            content=user_prompt
        ))


    # TODO: type hint for result once there is a common model for tool call results
    def add_tool_call_result(self, tool_call_id: str, result: Any) -> None:
        """
        Add a tool call result to the history.

        Args:
            tool_call_id: The ID of the tool call this result is for
            result: The result from the tool execution
        """
        # Convert result to JSON string using model_dump
        result_str = json.dumps(result.model_dump())

        self.messages.append(ChatCompletionToolMessageParam(
            role="tool",
            tool_call_id=tool_call_id,
            content=result_str
        ))

    def add_tool_call(self, tool_call: ToolCall) -> None:
        """
        Add a tool call to the history directly from our ToolCall model.

        Args:
            tool_call: Our ToolCall model instance
        """
        # Convert parameters to a JSON string
        tool_args_str = json.dumps(tool_call.parameters.model_dump())

        # Create the OpenAI tool call
        self.messages.append(ChatCompletionAssistantMessageParam(
            role="assistant",
            content=None,
            tool_calls=[ChatCompletionMessageToolCall(
                id=tool_call.id,
                type="function",
                function={
                    "name": tool_call.tool_type,
                    "arguments": tool_args_str
                }
            )]
        ))

    def get_messages(self) -> List[ChatCompletionMessageParam]:
        """
        Get the messages in a format compatible with OpenAI's API.

        Returns:
            List of messages in OpenAI API format.
        """
        return self.messages