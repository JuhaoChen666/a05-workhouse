"""Base tool interface."""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel


class ToolMetadata(BaseModel):
    """Tool metadata."""

    name: str
    description: str
    parameters: Optional[Dict[str, Any]] = None
    category: str = "general"
    is_async: bool = True


class BaseAgentTool(ABC):
    """Base class for agent tools."""

    def __init__(self) -> None:
        """Initialize tool."""
        self._metadata = self._get_metadata()

    @abstractmethod
    def _get_metadata(self) -> ToolMetadata:
        """Get tool metadata."""
        pass

    @abstractmethod
    async def execute(self, **kwargs: Any) -> Any:
        """Execute the tool."""
        pass

    @property
    def metadata(self) -> ToolMetadata:
        """Get tool metadata."""
        return self._metadata

    def to_langchain_tool(self) -> BaseTool:
        """Convert to LangChain tool."""
        from langchain_core.tools import StructuredTool

        return StructuredTool.from_function(
            coroutine=self.execute if self._metadata.is_async else None,
            func=None if self._metadata.is_async else self.execute,
            name=self._metadata.name,
            description=self._metadata.description,
        )


class ToolRegistry:
    """Registry for tools."""

    def __init__(self) -> None:
        """Initialize registry."""
        self._tools: Dict[str, BaseAgentTool] = {}
        self._categories: Dict[str, list] = {}

    def register(self, tool: BaseAgentTool) -> None:
        """Register a tool."""
        self._tools[tool.metadata.name] = tool

        category = tool.metadata.category
        if category not in self._categories:
            self._categories[category] = []
        self._categories[category].append(tool.metadata.name)

    def get(self, name: str) -> Optional[BaseAgentTool]:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self, category: Optional[str] = None) -> list:
        """List all tools or tools in a category."""
        if category:
            return [
                self._tools[name].metadata.model_dump()
                for name in self._categories.get(category, [])
            ]
        return [tool.metadata.model_dump() for tool in self._tools.values()]

    def get_langchain_tools(self, names: Optional[list] = None) -> list:
        """Get LangChain tools."""
        if names:
            return [
                self._tools[name].to_langchain_tool()
                for name in names
                if name in self._tools
            ]
        return [tool.to_langchain_tool() for tool in self._tools.values()]


# Global registry
_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get global tool registry."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry
