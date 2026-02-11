"""
Shared type definitions for the User Management Service.

This module defines TypedDict classes for request/response types and domain models.
"""

from typing import TypedDict, Literal, List, Dict, Any, Optional

# User status literal type
UserStatus = Literal['active', 'disabled', 'deleted']

# Audit action literal type
AuditAction = Literal[
    'USER_CREATED',
    'USER_UPDATED',
    'STATUS_CHANGED',
    'ROLE_ASSIGNED',
    'ROLE_REMOVED'
]


class User(TypedDict):
    """Complete user domain model."""
    userId: str
    email: str
    name: str
    status: UserStatus
    roles: List[str]
    metadata: Dict[str, str]
    createdAt: str
    updatedAt: str


class RegistrationRequest(TypedDict):
    """Request payload for user registration."""
    idempotencyKey: str
    email: str
    name: str
    metadata: Optional[Dict[str, str]]


class UpdateProfileRequest(TypedDict):
    """Request payload for profile updates."""
    idempotencyKey: str
    name: Optional[str]
    metadata: Optional[Dict[str, str]]


class UpdateStatusRequest(TypedDict):
    """Request payload for status updates."""
    status: UserStatus


class AssignRoleRequest(TypedDict):
    """Request payload for role assignment."""
    role: str


class AuditEvent(TypedDict):
    """Audit event structure for EventBridge."""
    eventId: str
    userId: str
    timestamp: str
    action: AuditAction
    actor: str
    correlationId: str
    changes: Dict[str, Dict[str, Any]]


class ErrorResponse(TypedDict):
    """Standard error response structure."""
    code: str
    message: str
    details: Dict[str, Any]
