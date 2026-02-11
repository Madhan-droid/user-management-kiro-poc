"""
Audit query validation.

This module implements input validation for audit query requests.
Validates query parameters for retrieving audit logs.

Follows steering rules:
- Explicit over implicit
- Fail fast on invalid input
- Return detailed validation errors
"""

from typing import Dict, Any, List


def validate_audit_request(limit: int) -> List[Dict[str, str]]:
    """
    Validate an audit query request.
    
    Performs the following validations:
    1. Limit is a positive integer between 1 and 100
    
    Args:
        limit: Maximum number of audit events to return
        
    Returns:
        List of validation errors. Empty list if validation passes.
        Each error is a dict with 'field' and 'message' keys.
    """
    errors: List[Dict[str, str]] = []
    
    # Validate limit (Requirement 6.3)
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
    
    return errors
