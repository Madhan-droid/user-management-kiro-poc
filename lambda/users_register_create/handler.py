"""
User registration Lambda handler.

This handler implements the API entry point for user registration.
It follows the Lambda-per-operation pattern with clear separation of concerns:
- Handler: Parse request, validate input, map errors to HTTP responses
- Service: Business logic (in service.py)
- Validation: Input validation (in validation.py)

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
from validation import validate_registration_request
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
    required_vars = ['USERS_TABLE_NAME', 'IDEMPOTENCY_TABLE_NAME', 'EVENT_BUS_NAME']
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
    Lambda handler for user registration.
    
    This handler processes POST /users requests to register new users.
    
    Request flow:
    1. Create structured logger with correlation ID
    2. Log request start
    3. Parse and validate request body
    4. Delegate to service layer for business logic
    5. Map domain errors to appropriate HTTP responses
    6. Log request completion with latency
    
    Args:
        event: API Gateway Lambda proxy integration event
        context: Lambda context object
        
    Returns:
        API Gateway Lambda proxy integration response
        
    Response codes:
        201: User created successfully
        400: Validation error (missing fields, invalid email)
        409: Conflict (email already exists, idempotency key mismatch)
        500: Internal error
    """
    # Create structured logger with correlation ID (Requirement 12.1)
    logger = create_logger(event, operation='users-register-create')
    
    # Log request start (Requirement 12.1)
    logger.log_request_start(
        path=event.get('path', '/users'),
        method=event.get('httpMethod', 'POST')
    )
    
    try:
        # Parse request body (Requirement 1.1)
        body = event.get('body', '{}')
        if isinstance(body, str):
            try:
                request = json.loads(body)
            except json.JSONDecodeError:
                logger.log_validation_error(
                    errors={'body': 'Request body must be valid JSON'}
                )
                return create_error_response(
                    400,
                    'VALIDATION_ERROR',
                    'Invalid JSON in request body',
                    {'body': 'Request body must be valid JSON'}
                )
        else:
            request = body
        
        # Validate input (Requirements 1.5, 7.1, 7.2, 7.3, 7.5)
        # Fail fast - validate before any business logic
        validation_errors = validate_registration_request(request)
        
        if validation_errors:
            # Log validation failure (Requirement 12.2)
            logger.log_validation_error(errors=validation_errors)
            
            return create_error_response(
                400,
                'VALIDATION_ERROR',
                'Invalid request data',
                {'errors': validation_errors}
            )
        
        # Delegate to service layer (Requirements 1.1, 1.2, 1.3, 1.4)
        user = user_service.register_user(request, logger.correlation_id)
        
        # Log successful registration with latency (Requirement 12.2)
        logger.log_request_complete(
            status_code=201,
            userId=user['userId'],
            email=user['email']
        )
        
        # Publish CloudWatch metrics (Requirement 12.5)
        logger.publish_metrics()
        
        # Return success response (Requirement 1.1)
        return create_success_response(201, user)
        
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
