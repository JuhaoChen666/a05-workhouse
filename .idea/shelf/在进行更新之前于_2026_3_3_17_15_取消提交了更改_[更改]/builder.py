"""LangGraph builder for agent workflow."""

from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from app.agent.graph.state import AgentState
from app.agent.tools.base import get_tool_registry
from app.core.logging import get_logger
from app.llm.deepseek import get_deepseek_provider

logger = get_logger(__name__)


class AgentGraphBuilder:
    """Builder for agent execution graphs."""

    def __init__(self) -> None:
        """Initialize graph builder."""
        self.tool_registry = get_tool_registry()
        self.llm_provider = get_deepseek_provider()

    def build_graph(
        self,
        tools: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
        max_iterations: int = 10,
    ) -> StateGraph:
        """Build agent execution graph."""
        # Get tools
        langchain_tools = self.tool_registry.get_langchain_tools(tools)
        tool_node = ToolNode(langchain_tools) if langchain_tools else None

        # Create graph
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("agent", self._create_agent_node(system_prompt))
        if tool_node:
            workflow.add_node("tools", tool_node)

        # Add edges
        workflow.set_entry_point("agent")

        if tool_node:
            workflow.add_conditional_edges(
                "agent",
                self._should_continue,
                {
                    "continue": "tools",
                    "end": END,
                },
            )
            workflow.add_edge("tools", "agent")
        else:
            workflow.add_edge("agent", END)

        return workflow.compile()

    def _create_agent_node(self, system_prompt: Optional[str] = None):
        """Create agent node function."""

        async def agent_node(state: AgentState) -> Dict[str, Any]:
            """Agent node execution."""
            messages = list(state["messages"])

            # Add system prompt if provided
            if system_prompt and not any(
                isinstance(m, SystemMessage) for m in messages
            ):
                messages.insert(0, SystemMessage(content=system_prompt))

            # Get LLM
            llm = self.llm_provider.get_chat_model()

            # Bind tools if available
            tools = self.tool_registry.get_langchain_tools(
                state["config"].get("tools")
            )
            if tools:
                llm = llm.bind_tools(tools)

            # Invoke LLM
            response = await llm.ainvoke(messages)

            return {
                "messages": [response],
                "iteration": state["iteration"] + 1,
            }

        return agent_node

    def _should_continue(self, state: AgentState) -> str:
        """Determine if agent should continue or end."""
        messages = state["messages"]
        last_message = messages[-1] if messages else None

        # Check max iterations
        max_iter = state["config"].get("max_iterations", 10)
        if state["iteration"] >= max_iter:
            return "end"

        # Check if last message has tool calls
        if last_message and hasattr(last_message, "tool_calls"):
            if last_message.tool_calls:
                return "continue"

        return "end"


def create_agent(
    tools: Optional[List[str]] = None,
    system_prompt: Optional[str] = None,
    max_iterations: int = 10,
):
    """Create and compile agent graph."""
    builder = AgentGraphBuilder()
    return builder.build_graph(tools, system_prompt, max_iterations)
