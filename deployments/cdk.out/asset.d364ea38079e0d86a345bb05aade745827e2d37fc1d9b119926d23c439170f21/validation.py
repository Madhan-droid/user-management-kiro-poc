"""
User role assignment validation.

This module implements input validation for role assignment requests.
Follows the "fail fast" principle - all validation happens before business logic.

Validates:
- role field is present and non-empty
- No unexpected fields present

Follows steering rules:
- Explicit over implicit
- Fail fast on invalid input
- Return detailed validation errors
"""

from typing import Dict, Any, List


def validate_role_request(request: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Validate a role assignment request.
    
    Performs the following validations:
    1. role field is present (Requirement 7.1)
    2. role is non-empty (Requirement 4.5)
    3. No unexpected fields are present (Requirement 7.1)
    
    Args:
        request: Role assignment request payload
        
    Returns:
        List of validation errors. Empty list if validation passes.
        Each error is a dict with 'field' and 'message' keys.
        
    Examples:
        >>> validate_role_request({'role': 'admin'})
        []
        
        >>> validate_role_request({'role': ''})
        [{'field': 'role', 'message': 'Role cannot be empty'}]
        
        >>> validate_role_request({})
        [{'field': 'role', 'message': 'Field is required'}]
    """
    errors: List[Dict[str, str]] = []
    
    # Define allowed fields (Requirement 7.1)
    allowed_fields = {'role'}
    
    # Check for unexpected fields (Requirement 7.1)
    unexpected_fields = set(request.keys()) - allowed_fields
    if unexpected_fields:
        for field in unexpected_fields:
            errors.append({
                'field': field,
                'message': 'Unexpected field in request'
            })
    
    # Validate role field is present (Requirement 7.1)
    if 'role' not in request:
        errors.append({
            'field': 'role',
            'message': 'Field is required'
        })
        # Return early if role is missing - can't validate further
        return errors
    
    role = request['role']
    
    # Validate role is a string
    if not isinstance(role, str):
        errors.append({
            'field': 'role',
            'message': 'Role must be a string'
        })
        return errors
    
    # Validate role is non-empty (Requirement 4.5)
    if not role or not role.strip():
        errors.append({
            'field': 'role',
            'message': 'Role cannot be empty'
        })
    
    return errors
