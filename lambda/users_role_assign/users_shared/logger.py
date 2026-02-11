"""
Structured logging utility for Lambda handlers.

This module provides a centralized logging utility that implements structured logging
with correlation IDs, latency tracking, and consistent JSON formatting across all
Lambda handlers.

Follows steering rules:
- Log request lifecycle with correlation ID
- Log errors with context (no sensitive data)
- Use consistent log format
- Fail fast on invalid input

Requirements:
- 12.1: Log requests with correlation ID
- 12.2: Log request completion with latency
- 12.3: Log errors with context
- 12.4: Do not log sensitive data
- 12.5: Emit metrics for request count, error rate, and latency
"""

import json
import time
from typing import Dict, Any, Optional, List
from datetime import datetime

from users_shared.metrics import create_metrics_client, MetricsClient


# Sensitive field names that should never be logged
SENSITIVE_FIELDS = {
    'password',
    'token',
    'secret',
    'apiKey',
    'api_key',
    'authorization',
    'auth',
    'credentials',
    'privateKey',
    'private_key',
    'accessToken',
    'access_token',
    'refreshToken',
    'refresh_token',
    'sessionId',
    'session_id'
}


class StructuredLogger:
    """
    Structured logger for Lambda handlers.
    
    This logger provides methods for logging request lifecycle events with
    correlation IDs, latency tracking, and consistent JSON formatting.
    It also integrates CloudWatch metrics emission.
    
    Usage:
        logger = StructuredLogger(correlation_id='abc-123', operation='users-register-create')
        logger.log_request_start(path='/users', method='POST')
        # ... process request ...
        logger.log_request_complete(status_code=201, user_id='user-123')
        logger.publish_metrics()
    """
    
    def __init__(self, correlation_id: str, operation: str):
        """
        Initialize the structured logger.
        
        Args:
            correlation_id: Unique identifier for request tracing
            operation: Operation name for metrics (e.g., 'users-register-create')
        """
        self.correlation_id = correlation_id
        self.operation = operation
        self.start_time = time.time()
        self.metrics = create_metrics_client(operation)
    
    def _sanitize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove sensitive fields from log data.
        
        This method recursively removes any fields that might contain sensitive
        information like passwords, tokens, or API keys.
        
        Args:
            data: Dictionary that may contain sensitive fields
            
        Returns:
            Sanitized dictionary with sensitive fields removed
        """
        if not isinstance(data, dict):
            return data
        
        sanitized = {}
        for key, value in data.items():
            # Check if field name is sensitive
            if key.lower() in SENSITIVE_FIELDS:
                sanitized[key] = '[REDACTED]'
            elif isinstance(value, dict):
                # Recursively sanitize nested dictionaries
                sanitized[key] = self._sanitize_data(value)
            elif isinstance(value, list):
                # Sanitize list items if they are dictionaries
                sanitized[key] = [
                    self._sanitize_data(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _log(self, event: str, **kwargs: Any) -> None:
        """
        Internal method to write structured log entry.
        
        Args:
            event: Event type/name
            **kwargs: Additional fields to include in log entry
        """
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'correlationId': self.correlation_id,
            'event': event,
            **self._sanitize_data(kwargs)
        }
        
        # Use print for CloudWatch Logs
        print(json.dumps(log_entry))
    
    def log_request_start(
        self,
        path: str,
        method: str,
        **additional_fields: Any
    ) -> None:
        """
        Log request start event.
        
        This should be called at the beginning of request processing.
        
        Args:
            path: Request path (e.g., '/users/{userId}')
            method: HTTP method (e.g., 'POST', 'GET')
            **additional_fields: Additional fields to include in log
            
        Example:
            logger.log_request_start(
                path='/users',
                method='POST',
                userId='user-123'
            )
        """
        self._log(
            'request_start',
            path=path,
            httpMethod=method,
            **additional_fields
        )
    
    def log_request_complete(
        self,
        status_code: int,
        **additional_fields: Any
    ) -> None:
        """
        Log request completion event with latency.
        
        This should be called when request processing completes successfully.
        Automatically calculates and includes latency in milliseconds.
        Also emits CloudWatch metrics for request count and latency.
        
        Args:
            status_code: HTTP status code (e.g., 200, 201)
            **additional_fields: Additional fields to include in log
            
        Example:
            logger.log_request_complete(
                status_code=201,
                userId='user-123',
                email='user@example.com'
            )
        """
        latency_ms = int((time.time() - self.start_time) * 1000)
        
        self._log(
            'request_complete',
            statusCode=status_code,
            latencyMs=latency_ms,
            **additional_fields
        )
        
        # Emit CloudWatch metrics (Requirement 12.5)
        self.metrics.emit_request_count()
        self.metrics.emit_latency(latency_ms)
    
    def log_validation_error(
        self,
        errors: Dict[str, Any],
        **additional_fields: Any
    ) -> None:
        """
        Log validation error event.
        
        Args:
            errors: Validation error details
            **additional_fields: Additional fields to include in log
            
        Example:
            logger.log_validation_error(
                errors={'email': 'Invalid email format'}
            )
        """
        latency_ms = int((time.time() - self.start_time) * 1000)
        
        self._log(
            'validation_error',
            errors=errors,
            latencyMs=latency_ms,
            **additional_fields
        )
    
    def log_domain_error(
        self,
        error_code: str,
        error_message: str,
        **additional_fields: Any
    ) -> None:
        """
        Log domain error event.
        
        Domain errors are expected business logic errors (e.g., user not found,
        email already exists).
        Also emits CloudWatch error metric.
        
        Args:
            error_code: Error code (e.g., 'NOT_FOUND', 'CONFLICT')
            error_message: Human-readable error message
            **additional_fields: Additional fields to include in log
            
        Example:
            logger.log_domain_error(
                error_code='NOT_FOUND',
                error_message='User not found',
                userId='user-123'
            )
        """
        latency_ms = int((time.time() - self.start_time) * 1000)
        
        self._log(
            'domain_error',
            errorCode=error_code,
            errorMessage=error_message,
            latencyMs=latency_ms,
            **additional_fields
        )
        
        # Emit CloudWatch error metric (Requirement 12.5)
        self.metrics.emit_error(error_code=error_code)
        self.metrics.emit_latency(latency_ms)
    
    def log_unexpected_error(
        self,
        error_type: str,
        error_message: str,
        **additional_fields: Any
    ) -> None:
        """
        Log unexpected error event.
        
        Unexpected errors are system errors that should not occur during normal
        operation (e.g., database connection failures, unexpected exceptions).
        Also emits CloudWatch error metric.
        
        Args:
            error_type: Error type/class name
            error_message: Error message
            **additional_fields: Additional fields to include in log
            
        Example:
            logger.log_unexpected_error(
                error_type='ValueError',
                error_message='Invalid configuration'
            )
        """
        latency_ms = int((time.time() - self.start_time) * 1000)
        
        self._log(
            'unexpected_error',
            errorType=error_type,
            errorMessage=error_message,
            latencyMs=latency_ms,
            **additional_fields
        )
        
        # Emit CloudWatch error metric (Requirement 12.5)
        self.metrics.emit_error(error_code='INTERNAL_ERROR')
        self.metrics.emit_latency(latency_ms)
    
    def log_info(
        self,
        message: str,
        **additional_fields: Any
    ) -> None:
        """
        Log informational event.
        
        Use this for logging significant events during request processing
        (e.g., user created, status updated).
        
        Args:
            message: Informational message
            **additional_fields: Additional fields to include in log
            
        Example:
            logger.log_info(
                message='user_created',
                userId='user-123',
                email='user@example.com'
            )
        """
        self._log(
            'info',
            message=message,
            **additional_fields
        )
    
    def publish_metrics(self) -> None:
        """
        Publish all accumulated metrics to CloudWatch.
        
        This method should be called at the end of request processing to
        send all metrics to CloudWatch. It's safe to call even if no metrics
        were emitted.
        
        Example:
            logger = create_logger(event, operation='users-register-create')
            # ... process request ...
            logger.publish_metrics()
        """
        self.metrics.publish()


def create_logger(event: Dict[str, Any], operation: str) -> StructuredLogger:
    """
    Create a structured logger from Lambda event.
    
    This is a convenience function that extracts the correlation ID from
    the Lambda event and creates a StructuredLogger instance with metrics support.
    
    Args:
        event: API Gateway Lambda proxy integration event
        operation: Operation name for metrics (e.g., 'users-register-create')
        
    Returns:
        StructuredLogger instance
        
    Example:
        def handler(event, context):
            logger = create_logger(event, operation='users-register-create')
            logger.log_request_start(
                path=event.get('path'),
                method=event.get('httpMethod')
            )
            # ... process request ...
            logger.publish_metrics()
    """
    correlation_id = event.get('requestContext', {}).get('requestId', 'unknown')
    return StructuredLogger(correlation_id, operation)
