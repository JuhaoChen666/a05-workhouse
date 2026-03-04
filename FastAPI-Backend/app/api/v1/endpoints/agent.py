"""Agent API endpoints."""

from typing import List

from fastapi import APIRouter, HTTPException, status

from app.core.logging import get_logger
from app.models.schemas.agent import (
    AgentConfig,
    AgentExecuteRequest,
    AgentExecuteResponse,
    ToolExecuteRequest,
    ToolExecuteResponse,
    ToolInfo,
)
from app.models.schemas.common import DataResponse, ListResponse
from app.services.agent_service import get_agent_service

logger = get_logger(__name__)
router = APIRouter(prefix="/agent", tags=["Agent"])


@router.post("/execute", response_model=DataResponse[AgentExecuteResponse])
async def execute_agent(request: AgentExecuteRequest) -> DataResponse[AgentExecuteResponse]:
    """Execute agent with input."""
    try:
        service = get_agent_service()
        response = await service.execute(request)
        return DataResponse(data=response)
    except Exception as e:
        logger.error("Agent execution error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent execution failed: {str(e)}",
        )


@router.post("/execute/stream")
async def execute_agent_stream(request: AgentExecuteRequest):
    """Stream agent execution (placeholder)."""
    # TODO: Implement streaming agent execution
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Streaming agent execution not yet implemented",
    )


@router.get("/tools", response_model=ListResponse[ToolInfo])
async def list_tools(category: str | None = None) -> ListResponse[ToolInfo]:
    """List available tools."""
    try:
        service = get_agent_service()
        tools = service.list_tools(category)
        return ListResponse(data=tools, total=len(tools))
    except Exception as e:
        logger.error("List tools error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tools: {str(e)}",
        )


@router.post("/tools/execute", response_model=DataResponse[ToolExecuteResponse])
async def execute_tool(request: ToolExecuteRequest) -> DataResponse[ToolExecuteResponse]:
    """Execute a specific tool."""
    try:
        service = get_agent_service()
        response = await service.execute_tool(request)
        return DataResponse(data=response)
    except Exception as e:
        logger.error("Tool execution error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tool execution failed: {str(e)}",
        )


@router.get("/config/example", response_model=DataResponse[AgentConfig])
async def get_example_config() -> DataResponse[AgentConfig]:
    """Get example agent configuration."""
    config = AgentConfig(
        name="emo2vec-assistant",
        description="An emotional AI assistant powered by DeepSeek and ModelScope",
        system_prompt="You are a helpful AI assistant with emotional intelligence. "
                     "You can understand user emotions and respond appropriately.",
        tools=["emotion_analysis", "web_search"],
        max_iterations=10,
        temperature=0.7,
        max_tokens=4096,
    )
    return DataResponse(data=config)
