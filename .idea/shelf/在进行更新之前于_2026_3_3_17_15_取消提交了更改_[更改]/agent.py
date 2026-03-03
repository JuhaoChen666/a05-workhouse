"""Agent related schemas."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    """Agent execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentConfig(BaseModel):
    """Agent configuration."""

    name: str
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    tools: List[str] = Field(default_factory=list)
    max_iterations: int = Field(default=10, ge=1, le=50)
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=4096, ge=1)
    metadata: Optional[Dict[str, Any]] = None


class AgentExecuteRequest(BaseModel):
    """Agent execution request."""

    agent_id: Optional[str] = None
    input: str
    context: Optional[Dict[str, Any]] = None
    stream: bool = False
    config: Optional[AgentConfig] = None


class AgentStep(BaseModel):
    """Agent execution step."""

    step_number: int
    thought: Optional[str] = None
    action: Optional[str] = None
    action_input: Optional[Dict[str, Any]] = None
    observation: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AgentExecuteResponse(BaseModel):
    """Agent execution response."""

    execution_id: str
    status: AgentStatus
    input: str
    output: Optional[str] = None
    steps: List[AgentStep] = Field(default_factory=list)
    usage: Optional[Dict[str, int]] = None
    execution_time: Optional[float] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ToolInfo(BaseModel):
    """Tool information."""

    name: str
    description: str
    parameters: Optional[Dict[str, Any]] = None
    is_enabled: bool = True


class ToolExecuteRequest(BaseModel):
    """Tool execution request."""

    tool_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class ToolExecuteResponse(BaseModel):
    """Tool execution response."""

    tool_name: str
    success: bool
    result: Any
    execution_time: float
    error: Optional[str] = None
