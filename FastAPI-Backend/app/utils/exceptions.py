"""Custom exceptions."""


class Emo2VecException(Exception):
    """Base exception for Emo2Vec."""

    def __init__(self, message: str, error_code: str = "UNKNOWN_ERROR") -> None:
        """Initialize exception."""
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class LLMException(Emo2VecException):
    """LLM-related exception."""

    def __init__(self, message: str, error_code: str = "LLM_ERROR") -> None:
        super().__init__(message, error_code)


class ToolException(Emo2VecException):
    """Tool execution exception."""

    def __init__(self, message: str, error_code: str = "TOOL_ERROR") -> None:
        super().__init__(message, error_code)


class ValidationException(Emo2VecException):
    """Validation exception."""

    def __init__(self, message: str, error_code: str = "VALIDATION_ERROR") -> None:
        super().__init__(message, error_code)


class NotFoundException(Emo2VecException):
    """Resource not found exception."""

    def __init__(self, message: str, error_code: str = "NOT_FOUND") -> None:
        super().__init__(message, error_code)
