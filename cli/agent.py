"""
Core agent implementation for the knowledge graph agent.
"""

from pydantic import BaseModel, Field
from rich.console import Console
from rich.panel import Panel

from cli.tools import (
    AnswerParameters,
    QueryParameters,
    SearchParameters,
    VisualizeParameters,
    execute_answer,
    execute_query,
    execute_search,
    execute_visualize,
    execute_query_relation_type,
    QueryRelationTypeParameters,
)
from common.message_history import MessageHistory
from common.models import ToolCall, ToolParameters
from common.openai_client import OpenAIClient
from kgraphlib.graph import Graph


class AgentContext(BaseModel):
    """Context for the agent."""

    history: MessageHistory = Field(default_factory=MessageHistory)
    graph: Graph | None = None

    model_config = {"arbitrary_types_allowed": True}


class Agent:
    """Core agent implementation."""

    def __init__(self, graph: Graph | None = None) -> None:
        """
        Initialize a new agent.

        Args:
            graph: Optional graph to use. If not provided, a new graph will be created.
        """
        self.graph = graph or Graph()
        self.context = AgentContext(graph=self.graph, history=MessageHistory())
        self.console = Console()
        self.openai_client = OpenAIClient()
        self.system_prompt = (
            "You are a knowledge graph agent that helps users explore and query a knowledge graph. "
            "When you have enough information to answer the user's query, use the 'answer' tool "
            "to provide a final response. "
            "When using the 'visualize' tool, always include the full text_representation "
            "from the visualization response in your answer. "
            "Format the visualization text as a code block for better readability."
        )

        # List of tool parameter models
        self.tools: list[type[ToolParameters]] = [
            SearchParameters,
            QueryParameters,
            VisualizeParameters,
            AnswerParameters,
            QueryRelationTypeParameters,
        ]

    def process(self, query: str) -> str:
        """
        Process a user query.

        Args:
            query: The user query.

        Returns:
            The agent's response.
        """
        # Initialize history with system prompt
        self.context.history.add_system_prompt(self.system_prompt)

        # Add the user query to the history
        self.context.history.add_user_prompt(query)

        # Process the query
        return self._agent_loop()

    def _agent_loop(self) -> str:
        """
        Run the agent loop.

        Returns:
            The final response to the user.
        """
        while True:
            response = self.openai_client.generate(
                history=self.context.history,
                tools=self.tools,
                tool_choice="required",
            )

            for tool_call in response.tool_calls:
                self._display_tool_call(tool_call)

                try:
                    match tool_call.tool_type:
                        case "search":
                            result = execute_search(tool_call.parameters, self.graph)
                        case "query":
                            result = execute_query(tool_call.parameters, self.graph)
                        case "visualize":
                            result = execute_visualize(tool_call.parameters, self.graph)
                        case "answer":
                            result = execute_answer(tool_call.parameters, self.graph)
                            return result.answer
                        case "relation_type":
                            result = execute_query_relation_type(tool_call.parameters, self.graph)
                        case _:
                            self.console.print(
                                f"[bold red]Unknown tool type:[/bold red] {tool_call.tool_type}",
                            )
                            continue

                    # Add the tool call to history using the new method
                    self.context.history.add_tool_call(tool_call)

                    # Add the result to history
                    self.context.history.add_tool_call_result(
                        tool_call_id=tool_call.id,
                        result=result,
                    )

                except Exception as e:
                    self.console.print(f"[bold red]Error executing tool:[/bold red] {e!s}")

        # This line is not reachable, but kept for type checking
        return "Failed to generate a response"

    def _display_tool_call(self, tool_call: ToolCall) -> None:
        """
        Display a tool call with rich.

        Args:
            tool_call: The tool call to display
        """
        param_str = ", ".join(
            f"{k}={v}" for k, v in tool_call.parameters.model_dump().items()
            if v is not None and not k.startswith("_")
        )

        self.console.print()
        self.console.print(
            Panel(
                f"[bold cyan]Tool Call:[/bold cyan] {tool_call.tool_type}({param_str})",
                expand=False,
            ),
        )
