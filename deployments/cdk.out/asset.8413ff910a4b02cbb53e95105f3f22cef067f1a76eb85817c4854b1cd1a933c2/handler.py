"""
User listing Lambda handler.

This handler implements the API entry point for listing users.
It follows the Lambda-per-operation pattern with clear separation of concerns:
- Handler: Parse request, extract query parameters, map errors to HTTP responses
- Validation: Input validation (in validation.py)
- Service: Business logic (in service.py)

Follows steering rules:
- One handler per file
- Business logic in services, not handlers
- Fail fast on invalid input
- Configuration read once at startup
- Validate env vars on boot
- Log request lifecycle with correlation ID
"""

import json
import os
from typing import Dict, Any, Optional

from service import UserService
from validation import validate_list_request
from users_shared.responses import create_error_response, create_success_response
from users_shared.errors import DomainError
from users_shared.logger import create_logger


# Configuration loaded once at startup (Requirement 12.1)
# Fail fast if environment variables are missing
def _load_config() -> Dict[str, str]:
    """
    Load and validate environment variables at startup.
    
    Follows steering rule: "Read once at startup, validate env vars on boot"
    
    Returns:
        Configuration dictionary
        
    Raises:
        ValueError: If any required environment variable is missing
    """
    required_vars = ['USERS_TABLE_NAME']
    config = {}
    missing_vars = []
    
    for var in required_vars:
        value = os.environ.get(var)
        if not value:
            missing_vars.append(var)
        else:
            # Convert to snake_case for internal use
            key = var.lower()
            config[key] = value
    
    if missing_vars:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )
    
    return config


# Load configuration at module initialization (cold start)
# This will fail fast if configuration is invalid
config = _load_config()

# Initialize service once at cold start
user_service = UserService(config)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for user listing.
    
    This handler processes GET /users requests to list users with optional filtering and pagination.
    
    Request flow:
    1. Create structured logger with correlation ID
    2. Log request start
    3. Extract query parameters (limit, nextToken, status)
    4. Validate query parameters
    5. Delegate to service layer for business logic
    6. Map domain errors to appropriate HTTP responses
    7. Log request completion with latency
    
    Args:
        event: API Gateway Lambda proxy integration event
        context: Lambda context object
        
    Returns:
        API Gateway Lambda proxy integration response
        
    Response codes:
        200: Users retrieved successfully
        400: Validation error (invalid query parameters)
        500: Internal error
    """
    # Create structured logger with correlation ID (Requirement 12.1)
    logger = create_logger(event, operation='users-list-query')
    
    # Log request start (Requirement 12.1)
    logger.log_request_start(
        path=event.get('path', '/users'),
        method=event.get('httpMethod', 'GET')
    )
    
    try:
        # Extract query parameters (Requirement 5.4, 5.5)
        query_params = event.get('queryStringParameters') or {}
        
        # Parse limit parameter (default: 50)
        limit = 50  # Default value
        if 'limit' in query_params:
            try:
                limit = int(query_params['limit'])
            except ValueError:
                # Log validation failure (Requirement 12.2)
                logger.log_validation_error(
                    errors={'limit': 'Limit must be an integer'}
                )
                
                return create_error_response(
                    400,
                    'VALIDATION_ERROR',
                    'Invalid limit parameter',
                    {'limit': 'Limit must be an integer'}
                )
        
        # Parse status parameter (default: 'active')
        status = query_params.get('status', 'active')
        
        # Parse nextToken parameter (optional)
        next_token: Optional[str] = query_params.get('nextToken')
        
        # Validate query parameters (Requirements 5.4, 5.5, 7.1)
        validation_errors = validate_list_request(limit=limit, status=status)
        
        if validation_errors:
            # Log validation failure (Requirement 12.2)
            logger.log_validation_error(errors=validation_errors)
            
            return create_error_response(
                400,
                'VALIDATION_ERROR',
                'Invalid request',
                {'errors': validation_errors}
            )
        
        # Delegate to service layer (Requirements 5.4, 5.5)
        result = user_service.list_users(
            status=status,
            limit=limit,
            next_token=next_token
        )
        
        # Log successful user listing with latency (Requirement 12.2)
        logger.log_request_complete(
            status_code=200,
            userCount=len(result['users']),
            status=status,
            hasNextToken='nextToken' in result
        )
        
        # Return success response (Requirement 5.4, 5.5)
        return create_success_response(200, result)
        
    except DomainError as error:
        # Map domain errors to HTTP responses (Requirement 8.1)
        # Domain errors are expected business logic errors
        
        # Log domain error with latency (Requirement 12.3)
        logger.log_domain_error(
            error_code=error.code,
            error_message=error.message
        )
        
        # Map error codes to HTTP status codes
        status_code_map = {
            'VALIDATION_ERROR': 400,
            'NOT_FOUND': 404,
            'CONFLICT': 409,
            'AUTHENTICATION_ERROR': 401
        }
        status_code = status_code_map.get(error.code, 500)
        
        # Publish CloudWatch metrics (Requirement 12.5)
        logger.publish_metrics()
        
        return create_error_response(
            status_code,
            error.code,
            error.message,
            error.details
        )
    
    except Exception as error:
        # Check if it's a domain error by checking for 'code' attribute
        # This handles cases where isinstance doesn't work due to import paths
        if hasattr(error, 'code') and hasattr(error, 'message') and hasattr(error, 'details'):
            # Log domain error with latency (Requirement 12.3)
            logger.log_domain_error(
                error_code=error.code,
                error_message=error.message
            )
            
            # Map error codes to HTTP status codes
            status_code_map = {
                'VALIDATION_ERROR': 400,
                'NOT_FOUND': 404,
                'CONFLICT': 409,
                'AUTHENTICATION_ERROR': 401
            }
            status_code = status_code_map.get(error.code, 500)
            
            # Publish CloudWatch metrics (Requirement 12.5)
            logger.publish_metrics()
            
            return create_error_response(
                status_code,
                error.code,
                error.message,
                error.details
            )
        
        # Log unexpected error with context and latency (Requirement 12.3)
        # Do not log sensitive data (Requirement 12.4)
        logger.log_unexpected_error(
            error_type=type(error).__name__,
            error_message=str(error)
        )
        
        # Publish CloudWatch metrics (Requirement 12.5)
        logger.publish_metrics()
        
        # Return generic error message (Requirement 8.5)
        # Do not expose internal details to client
        return create_error_response(
            500,
            'INTERNAL_ERROR',
            'An unexpected error occurred',
            {}
        )

