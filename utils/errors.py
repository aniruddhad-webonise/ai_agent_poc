from typing import Dict, Any, Optional, Tuple

class AIBotError(Exception):
    """Base exception class for AIBot errors."""
    
    def __init__(self, message: str, status_code: int = 500, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the error to a dictionary."""
        error_dict = {
            "error": self.message,
            "status_code": self.status_code
        }
        
        if self.details:
            error_dict["details"] = self.details
            
        return error_dict


class ValidationError(AIBotError):
    """Exception raised for validation errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=400, details=details)


class SQLGenerationError(AIBotError):
    """Exception raised for SQL generation errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=422, details=details)


class DatabaseError(AIBotError):
    """Exception raised for database errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=500, details=details)


class NotFoundError(AIBotError):
    """Exception raised for not found errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=404, details=details)


class AuthenticationError(AIBotError):
    """Exception raised for authentication errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=401, details=details)


def format_error_response(error: Exception) -> Tuple[Dict[str, Any], int]:
    """
    Format an exception into a standard error response.
    
    Args:
        error: The exception to format
        
    Returns:
        Tuple of (error_dict, status_code)
    """
    if isinstance(error, AIBotError):
        return error.to_dict(), error.status_code
    
    # Default error handling for unknown exceptions
    return {
        "error": str(error),
        "status_code": 500
    }, 500