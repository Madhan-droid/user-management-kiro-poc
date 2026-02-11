"""
User listing validation.

This module implements input validation for user listing requests.
Validates query parameters for listing users.

Follows steering rules:
- Explicit over implicit
- Fail fast on invalid input
- Return detailed validation errors
"""

from typing import Dict, Any, List


def validate_list_request(limit: int, status: str) -> List[Dict[str, str]]:
    """
    Validate a user listing request.
    
    Performs the following validations:
    1. Limit is a positive integer between 1 and 100
    2. Status is one of: active, disabled, deleted
    
    Args:
        limit: Maximum number of users to return
        status: User status to filter by
        
    Returns:
        List of validation errors. Empty list if validation passes.
        Each error is a dict with 'field' and 'message' keys.
    """
    errors: List[Dict[str, str]] = []
    
    # Validate limit (Requirement 5.5)
    if not isinstance(limit, int):
        errors.append({
            'field': 'limit',
            'message': 'Limit must be an integer'
        })
    elif limit < 1:
        errors.append({
            'field': 'limit',
            'message': 'Limit must be at least 1'
        })
    elif limit > 100:
        errors.append({
            'field': 'limit',
            'message': 'Limit cannot exceed 100'
        })
    
    # Validate status (Requirement 5.4)
    valid_statuses = ['active', 'disabled', 'deleted']
    if not isinstance(status, str):
        errors.append({
            'field': 'status',
            'message': 'Status must be a string'
        })
    elif status not in valid_statuses:
        errors.append({
            'field': 'status',
            'message': f'Status must be one of: {", ".join(valid_statuses)}'
        })
    
    return errors
