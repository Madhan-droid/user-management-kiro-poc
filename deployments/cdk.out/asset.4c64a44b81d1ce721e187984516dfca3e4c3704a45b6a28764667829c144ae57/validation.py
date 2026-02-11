"""
User profile update validation.

This module implements input validation for user profile update requests.
Follows the "fail fast" principle - all validation happens before business logic.

Validates:
- idempotencyKey is present
- userId is not in request body (immutable field)
- At least one field is being updated
- No unexpected fields present

Follows steering rules:
- Explicit over implicit
- Fail fast on invalid input
- Return detailed validation errors
"""

from typing import Dict, Any, List


def validate_update_request(request: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Validate a user profile update request.
    
    Performs the following validations:
    1. idempotencyKey is present and non-empty (Requirement 7.1)
    2. userId is not in request body (Requirement 2.4 - immutable field)
    3. At least one field is being updated (Requirement 2.5)
    4. No unexpected fields are present (Requirement 7.5)
    5. Field types are correct
    
    Args:
        request: Profile update request payload
        
    Returns:
        List of validation errors. Empty list if validation passes.
        Each error is a dict with 'field' and 'message' keys.
        
    Examples:
        >>> validate_update_request({
        ...     'idempotencyKey': 'abc123',
        ...     'name': 'Jane Doe'
        ... })
        []
        
        >>> validate_update_request({
        ...     'idempotencyKey': 'abc123',
        ...     'userId': 'user123'
        ... })
        [{'field': 'userId', 'message': 'User ID cannot be modified'}]
        
        >>> validate_update_request({'idempotencyKey': 'abc123'})
        [{'field': 'request', 'message': 'At least one field must be updated'}]
    """
    errors: List[Dict[str, str]] = []
    
    # Define allowed fields (Requirement 7.5)
    allowed_fields = {'idempotencyKey', 'name', 'metadata'}
    
    # Check for unexpected fields (Requirement 7.5)
    unexpected_fields = set(request.keys()) - allowed_fields
    if unexpected_fields:
        for field in unexpected_fields:
            errors.append({
                'field': field,
                'message': 'Unexpected field in request'
            })
    
    # Validate idempotencyKey is present (Requirement 7.1)
    if 'idempotencyKey' not in request:
        errors.append({
            'field': 'idempotencyKey',
            'message': 'Field is required'
        })
    elif not isinstance(request['idempotencyKey'], str):
        errors.append({
            'field': 'idempotencyKey',
            'message': 'Field must be a string'
        })
    elif not request['idempotencyKey'] or not request['idempotencyKey'].strip():
        errors.append({
            'field': 'idempotencyKey',
            'message': 'Field cannot be empty'
        })
    
    # Validate userId is NOT in request body (Requirement 2.4)
    # User ID is immutable and should never be in an update request
    if 'userId' in request:
        errors.append({
            'field': 'userId',
            'message': 'User ID cannot be modified'
        })
    
    # Validate at least one field is being updated (Requirement 2.5)
    # Check if any updatable fields are present
    updatable_fields = {'name', 'metadata'}
    has_update = any(field in request for field in updatable_fields)
    
    if not has_update:
        errors.append({
            'field': 'request',
            'message': 'At least one field must be updated'
        })
    
    # Validate name if present (optional field)
    if 'name' in request:
        name = request['name']
        if name is not None:
            if not isinstance(name, str):
                errors.append({
                    'field': 'name',
                    'message': 'Name must be a string'
                })
            elif not name.strip():
                errors.append({
                    'field': 'name',
                    'message': 'Name cannot be empty'
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
                # Validate metadata keys and values are strings
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
