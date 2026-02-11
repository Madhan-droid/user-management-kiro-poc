"""
User status update Lambda handler.

This handler implements the API entry point for updating user status.
It follows the Lambda-per-operation pattern with clear separation of concerns:
- Handler: Parse request, extract path parameters, map errors to HTTP responses
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
from typing import Dict, Any

from service import UserService
from validation import validate_status_request
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
    required_vars = ['USERS_TABLE_NAME', 'EVENT_BUS_NAME']
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
    Lambda handler for user status updates.
    
    This handler processes PUT /users/{userId}/status requests to update user status.
    
    Request flow:
    1. Create structured logger with correlation ID
    2. Log request start
    3. Extract userId from path parameters
    4. Parse and validate request body
    5. Delegate to service layer for business logic
    6. Map domain errors to appropriate HTTP responses
    7. Log request completion with latency
    
    Args:
        event: API Gateway Lambda proxy integration event
        context: Lambda context object
        
    Returns:
        API Gateway Lambda proxy integration response
        
    Response codes:
        200: User status updated successfully
        400: Validation error (invalid status value)
        404: User not found
        500: Internal error
    """
    # Create structured logger with correlation ID (Requirement 12.1)
    logger = create_logger(event, operation='users-status-update')
    
    # Log request start (Requirement 12.1)
    logger.log_request_start(
        path=event.get('path', '/users/{userId}/status'),
        method=event.get('httpMethod', 'PUT')
    )
    
    try:
        # Extract userId from path parameters (Requirement 3.1)
        path_parameters = event.get('pathParameters', {})
        if not path_parameters or 'userId' not in path_parameters:
            # Log validation failure (Requirement 12.2)
            logger.log_validation_error(
                errors={'userId': 'userId is required in path'}
            )
            
            return create_error_response(
                400,
                'VALIDATION_ERROR',
                'Missing userId in path parameters',
                {'userId': 'userId is required in path'}
            )
        
        user_id = path_parameters['userId']
        
        # Validate userId is not empty
        if not user_id or not user_id.strip():
            # Log validation failure (Requirement 12.2)
            logger.log_validation_error(
                errors={'userId': 'userId cannot be empty'}
            )
            
            return create_error_response(
                400,
                'VALIDATION_ERROR',
                'Invalid userId',
                {'userId': 'userId cannot be empty'}
            )
        
        # Parse request body (Requirement 3.1)
        try:
            request_body = json.loads(event.get('body', '{}'))
        except json.JSONDecodeError as e:
            # Log JSON parse error (Requirement 12.2)
            logger.log_validation_error(
                errors={'body': 'Request body must be valid JSON'}
            )
            
            return create_error_response(
                400,
                'VALIDATION_ERROR',
                'Invalid JSON in request body',
                {'body': 'Request body must be valid JSON'}
            )
        
        # Validate request body (Requirements 3.1, 3.2, 3.6, 7.1)
        validation_errors = validate_status_request(request_body)
        
        if validation_errors:
            # Log validation failure (Requirement 12.2)
            logger.log_validation_error(errors=validation_errors)
            
            return create_error_response(
                400,
                'VALIDATION_ERROR',
                'Invalid request',
                {'errors': validation_errors}
            )
        
        # Delegate to service layer (Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6)
        result = user_service.update_user_status(
            user_id,
            request_body['status'],
            logger.correlation_id
        )
        
        # Log successful status update with latency (Requirement 12.2)
        logger.log_request_complete(
            status_code=200,
            userId=result['userId'],
            status=result['status']
        )
        
        # Publish CloudWatch metrics (Requirement 12.5)
        logger.publish_metrics()
        
        # Return success response (Requirement 3.1)
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
