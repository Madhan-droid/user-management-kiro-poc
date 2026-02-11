"""Shared utilities for User Management Service."""

from .types import (
    User,
    UserStatus,
    AuditAction,
    RegistrationRequest,
    UpdateProfileRequest,
    UpdateStatusRequest,
    AssignRoleRequest,
    AuditEvent,
    ErrorResponse
)

from .errors import (
    DomainError,
    ValidationError,
    NotFoundError,
    ConflictError,
    AuthenticationError
)

from .responses import (
    create_success_response,
    create_error_response
)

__all__ = [
    # Types
    'User',
    'UserStatus',
    'AuditAction',
    'RegistrationRequest',
    'UpdateProfileRequest',
    'UpdateStatusRequest',
    'AssignRoleRequest',
    'AuditEvent',
    'ErrorResponse',
    # Errors
    'DomainError',
    'ValidationError',
    'NotFoundError',
    'ConflictError',
    'AuthenticationError',
    # Responses
    'create_success_response',
    'create_error_response',
]
