"""
Domain error classes for the User Management Service.

These error classes provide explicit, typed exceptions that map cleanly to API responses.
All errors follow the principle of "fail fast" and provide clear error codes and messages.
"""

from typing import Dict, Any


class DomainError(Exception):
    """
    Base class for all domain errors.
    
    Domain errors are explicit business logic errors that should be mapped
    to appropriate HTTP responses by the handler layer.
    """
    
    def __init__(self, code: str, message: str, details: Dict[str, Any] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


class ValidationError(DomainError):
    """
    Raised when input validation fails.
    
    Maps to HTTP 400 Bad Request.
    Details should contain field-level validation errors.
    """
    
    def __init__(self, message: str, details: Dict[str, Any]):
        super().__init__('VALIDATION_ERROR', message, details)


class NotFoundError(DomainError):
    """
    Raised when a requested resource does not exist.
    
    Maps to HTTP 404 Not Found.
    """
    
    def __init__(self, message: str):
        super().__init__('NOT_FOUND', message, {})


class ConflictError(DomainError):
    """
    Raised when an operation conflicts with existing state.
    
    Maps to HTTP 409 Conflict.
    Examples: duplicate email, idempotency key mismatch.
    """
    
    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__('CONFLICT', message, details or {})


class AuthenticationError(DomainError):
    """
    Raised when authentication fails.
    
    Maps to HTTP 401 Unauthorized.
    """
    
    def __init__(self, message: str):
        super().__init__('AUTHENTICATION_ERROR', message, {})
