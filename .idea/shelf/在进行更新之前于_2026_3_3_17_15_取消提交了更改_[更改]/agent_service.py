"""Agent service."""

import time
import uuid
from typing import Any, AsyncIterator, Dict, List, Optional

from app.agent.graph.builder import create_agent
from app.agent.graph.state import AgentState
from app.agent.tools.modelscope_tools import register_modelscope_tools
from app.agent.tools.web_search import register_web_search_tool
from app.core.logging import get_logger
from app.models.schemas.agent import (
    AgentExecuteRequest,
    AgentExecuteResponse,
    AgentStatus,
    AgentStep,
    ToolExecuteRequest,
    ToolExecuteResponse,
    ToolInfo,
)

logger = get_logger(__name__)

# Register tools on module load
register_modelscope_tools()
register_web_search_tool()


class AgentService:
    """Service for agent operations."""

    def __init__(self) -> None:
        """Initialize agent service."""
        from app.agent.tools.base import get_tool_registry

        self.tool_registry = get_tool_registry()

    async def execute(
        self,
        request: AgentExecuteRequest,
    ) -> AgentExecuteResponse:
        """Execute agent with input."""
        execution_id = str(uuid.uuid4())
        start_time = time.time()

        logger.info(
            "Starting agent execution",
            execution_id=execution_id,
            input_length=len(request.input),
        )

        try:
            # Create agent graph
            config = request.config
            graph = create_agent(
                tools=config.tools if config else None,
                system_prompt=config.system_prompt if config else None,
                max_iterations=config.max_iterations if config else 10,
            )

            # Prepare initial state
            from langchain_core.messages import HumanMessage

            initial_state: AgentState = {
                "messages": [HumanMessage(content=request.input)],
                "input": request.input,
                "config": config.model_dump() if config else {},
                "steps": [],
                "iteration": 0,
                "continue_loop": True,
                "output": None,
                "error": None,
                "metadata": request.context or {},
            }

            # Execute graph
            result = await graph.ainvoke(initial_state)

            # Extract output
            output = None
            if result["messages"]:
                last_message = result["messages"][-1]
                output = last_message.content

            execution_time = time.time() - start_time

            return AgentExecuteResponse(
                execution_id=execution_id,
                status=AgentStatus.COMPLETED,
                input=request.input,
                output=output,
                steps=[AgentStep(**step) for step in result.get("steps", [])],
                execution_time=execution_time,
            )

        except Exception as e:
            logger.error("Agent execution failed", error=str(e))
            return AgentExecuteResponse(
                execution_id=execution_id,
                status=AgentStatus.FAILED,
                input=request.input,
                error=str(e),
                execution_time=time.time() - start_time,
            )

    async def execute_tool(
        self,
        request: ToolExecuteRequest,
    ) -> ToolExecuteResponse:
        """Execute a specific tool."""
        start_time = time.time()

        tool = self.tool_registry.get(request.tool_name)
        if not tool:
            return ToolExecuteResponse(
                tool_name=request.tool_name,
                success=False,
                result=None,
                execution_time=0,
                error=f"Tool '{request.tool_name}' not found",
            )

        try:
            result = await tool.execute(**request.parameters)
            return ToolExecuteResponse(
                tool_name=request.tool_name,
                success=True,
                result=result,
                execution_time=time.time() - start_time,
            )
        except Exception as e:
            logger.error("Tool execution failed", tool=request.tool_name, error=str(e))
            return ToolExecuteResponse(
                tool_name=request.tool_name,
                success=False,
                result=None,
                execution_time=time.time() - start_time,
                error=str(e),
            )

    def list_tools(self, category: Optional[str] = None) -> List[ToolInfo]:
        """List available tools."""
        tools_data = self.tool_registry.list_tools(category)
        return [ToolInfo(**tool) for tool in tools_data]


# Singleton
_agent_service: Optional[AgentService] = None


def get_agent_service() -> AgentService:
    """Get agent service singleton."""
    global _agent_service
    if _agent_service is None:
        _agent_service = AgentService()
    return _agent_service
