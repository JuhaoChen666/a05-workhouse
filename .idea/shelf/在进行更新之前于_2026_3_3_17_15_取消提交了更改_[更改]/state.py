"""Agent state definition."""

from typing import Annotated, Any, Dict, List, Optional, Sequence

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """State for the agent graph."""

    # Messages history
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # Current input
    input: str

    # Agent configuration
    config: Dict[str, Any]

    # Intermediate steps
    steps: List[Dict[str, Any]]

    # Current iteration
    iteration: int

    # Whether to continue
    continue_loop: bool

    # Final output
    output: Optional[str]

    # Error if any
    error: Optional[str]

    # Metadata
    metadata: Dict[str, Any]


class AgentConfig(TypedDict, total=False):
    """Configuration for agent execution."""

    # Model settings
    temperature: float
    max_tokens: int

    # Agent settings
    max_iterations: int
    system_prompt: Optional[str]

    # Tool settings
    tools: List[str]

    # Memory settings
    use_memory: bool
    memory_session_id: Optional[str]

    # Auxiliary model settings
    use_emotion_analysis: bool
    use_knowledge_base: bool
