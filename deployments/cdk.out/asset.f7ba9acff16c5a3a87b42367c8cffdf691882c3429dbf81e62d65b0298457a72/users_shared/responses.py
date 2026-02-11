"""
Response helper functions for Lambda handlers.

These functions create consistent HTTP responses following the API contract
defined in the design document. All responses follow the steering rule for
consistent error shapes.
"""

import json
from typing import Dict, Any


def create_success_response(status_code: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a successful HTTP response.
    
    Args:
        status_code: HTTP status code (200, 201, etc.)
        data: Response payload to be JSON serialized
        
    Returns:
        Lambda proxy integration response object
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json'
        },
        'body': json.dumps(data)
    }


def create_error_response(
    status_code: int,
    code: str,
    message: str,
    details: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create an error HTTP response with consistent structure.
    
    All error responses follow the format:
    {
        "code": "ERROR_CODE",
        "message": "Human-readable message",
        "details": { ... }
    }
    
    Args:
        status_code: HTTP status code (400, 404, 409, 500, etc.)
        code: Error code string (VALIDATION_ERROR, NOT_FOUND, CONFLICT, etc.)
        message: Human-readable error message
        details: Additional error context (field errors, conflict info, etc.)
        
    Returns:
        Lambda proxy integration response object
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json'
        },
        'body': json.dumps({
            'code': code,
            'message': message,
            'details': details
        })
    }
