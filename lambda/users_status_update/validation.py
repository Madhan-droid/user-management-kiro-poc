"""
User status update validation.

This module implements input validation for user status update requests.
Follows the "fail fast" principle - all validation happens before business logic.

Validates:
- status field is present
- status is one of: active, disabled, deleted
- No unexpected fields present

Follows steering rules:
- Explicit over implicit
- Fail fast on invalid input
- Return detailed validation errors
"""

from typing import Dict, Any, List


def validate_status_request(request: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Validate a user status update request.
    
    Performs the following validations:
    1. status field is present (Requirement 7.1)
    2. status is one of: active, disabled, deleted (Requirements 3.1, 3.2, 3.6)
    3. No unexpected fields are present (Requirement 7.1)
    
    Args:
        request: Status update request payload
        
    Returns:
        List of validation errors. Empty list if validation passes.
        Each error is a dict with 'field' and 'message' keys.
        
    Examples:
        >>> validate_status_request({'status': 'active'})
        []
        
        >>> validate_status_request({'status': 'invalid'})
        [{'field': 'status', 'message': 'Status must be one of: active, disabled, deleted'}]
        
        >>> validate_status_request({})
        [{'field': 'status', 'message': 'Field is required'}]
    """
    errors: List[Dict[str, str]] = []
    
    # Define allowed fields (Requirement 7.1)
    allowed_fields = {'status'}
    
    # Check for unexpected fields (Requirement 7.1)
    unexpected_fields = set(request.keys()) - allowed_fields
    if unexpected_fields:
        for field in unexpected_fields:
            errors.append({
                'field': field,
                'message': 'Unexpected field in request'
            })
    
    # Validate status field is present (Requirement 7.1)
    if 'status' not in request:
        errors.append({
            'field': 'status',
            'message': 'Field is required'
        })
        # Return early if status is missing - can't validate further
        return errors
    
    status = request['status']
    
    # Validate status is a string
    if not isinstance(status, str):
        errors.append({
            'field': 'status',
            'message': 'Status must be a string'
        })
        return errors
    
    # Validate status is not empty
    if not status or not status.strip():
        errors.append({
            'field': 'status',
            'message': 'Status cannot be empty'
        })
        return errors
    
    # Validate status is one of the allowed values (Requirements 3.1, 3.2, 3.6)
    valid_statuses = {'active', 'disabled', 'deleted'}
    if status not in valid_statuses:
        errors.append({
            'field': 'status',
            'message': f'Status must be one of: {", ".join(sorted(valid_statuses))}'
        })
    
    return errors
