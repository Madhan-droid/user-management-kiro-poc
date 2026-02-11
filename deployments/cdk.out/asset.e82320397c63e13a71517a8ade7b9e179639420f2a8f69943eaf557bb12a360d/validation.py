"""
User registration validation.

This module implements input validation for user registration requests.
Follows the "fail fast" principle - all validation happens before business logic.

Validates:
- Required fields (email, name, idempotencyKey)
- Email format using regex
- No unexpected fields present

Follows steering rules:
- Explicit over implicit
- Fail fast on invalid input
- Return detailed validation errors
"""

import re
from typing import Dict, Any, List, Optional


# Email regex pattern (RFC 5322 simplified)
# Validates: local-part@domain with basic character restrictions
EMAIL_PATTERN = re.compile(
    r'^[a-zA-Z0-9.!#$%&\'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$'
)


def validate_registration_request(request: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Validate a user registration request.
    
    Performs the following validations:
    1. Required fields are present (email, name, idempotencyKey)
    2. Email format is valid (RFC 5322 simplified)
    3. No unexpected fields are present
    4. Field types are correct
    
    Args:
        request: Registration request payload
        
    Returns:
        List of validation errors. Empty list if validation passes.
        Each error is a dict with 'field' and 'message' keys.
        
    Examples:
        >>> validate_registration_request({
        ...     'email': 'user@example.com',
        ...     'name': 'John Doe',
        ...     'idempotencyKey': 'abc123'
        ... })
        []
        
        >>> validate_registration_request({'email': 'invalid'})
        [
            {'field': 'name', 'message': 'Field is required'},
            {'field': 'idempotencyKey', 'message': 'Field is required'},
            {'field': 'email', 'message': 'Invalid email format'}
        ]
    """
    errors: List[Dict[str, str]] = []
    
    # Define allowed fields
    allowed_fields = {'email', 'name', 'idempotencyKey', 'metadata'}
    
    # Check for unexpected fields (Requirement 7.5)
    unexpected_fields = set(request.keys()) - allowed_fields
    if unexpected_fields:
        for field in unexpected_fields:
            errors.append({
                'field': field,
                'message': 'Unexpected field in request'
            })
    
    # Validate required fields (Requirements 1.5, 7.1)
    required_fields = ['email', 'name', 'idempotencyKey']
    for field in required_fields:
        if field not in request:
            errors.append({
                'field': field,
                'message': 'Field is required'
            })
        elif not isinstance(request[field], str):
            errors.append({
                'field': field,
                'message': 'Field must be a string'
            })
        elif not request[field] or not request[field].strip():
            errors.append({
                'field': field,
                'message': 'Field cannot be empty'
            })
    
    # Validate email format (Requirements 7.2, 7.3)
    if 'email' in request and isinstance(request.get('email'), str):
        email = request['email'].strip()
        if email and not EMAIL_PATTERN.match(email):
            errors.append({
                'field': 'email',
                'message': 'Invalid email format'
            })
    
    # Validate metadata if present (optional field)
    if 'metadata' in request:
        metadata = request['metadata']
        if metadata is not None:
            if not isinstance(metadata, dict):
                errors.append({
                    'field': 'metadata',
                    'message': 'Metadata must be an object'
                })
            else:
                # Validate metadata values are strings
                for key, value in metadata.items():
                    if not isinstance(key, str):
                        errors.append({
                            'field': f'metadata.{key}',
                            'message': 'Metadata keys must be strings'
                        })
                    if not isinstance(value, str):
                        errors.append({
                            'field': f'metadata.{key}',
                            'message': 'Metadata values must be strings'
                        })
    
    return errors


def validate_email_format(email: str) -> bool:
    """
    Validate email format using regex.
    
    Uses a simplified RFC 5322 pattern that covers most common email formats.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if email format is valid, False otherwise
        
    Examples:
        >>> validate_email_format('user@example.com')
        True
        
        >>> validate_email_format('invalid-email')
        False
        
        >>> validate_email_format('user@domain.co.uk')
        True
    """
    if not email or not isinstance(email, str):
        return False
    
    return EMAIL_PATTERN.match(email.strip()) is not None
