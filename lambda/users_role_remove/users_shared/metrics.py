"""
CloudWatch metrics utility for Lambda handlers.

This module provides a centralized metrics utility that emits custom CloudWatch
metrics for request count, error rate, and latency across all Lambda handlers.

Follows steering rules:
- Explicit over implicit
- Fail fast on invalid input
- No global mutable state

Requirements:
- 12.5: Emit metrics for request count, error rate, and latency
"""

import boto3
from typing import Dict, Any, Optional, List
from datetime import datetime


# Metric namespace for all user management metrics
METRIC_NAMESPACE = 'UserManagement'


class MetricsClient:
    """
    CloudWatch metrics client for Lambda handlers.
    
    This client provides methods for emitting custom CloudWatch metrics
    with consistent dimensions and namespace across all Lambda handlers.
    
    Usage:
        metrics = MetricsClient(operation='users-register-create')
        metrics.emit_request_count()
        metrics.emit_latency(latency_ms=150)
        metrics.emit_error()
    """
    
    def __init__(self, operation: str):
        """
        Initialize the metrics client.
        
        Args:
            operation: Operation name (e.g., 'users-register-create', 'users-profile-get')
        """
        if not operation or not operation.strip():
            raise ValueError('Operation name is required for metrics')
        
        self.operation = operation
        self.cloudwatch = boto3.client('cloudwatch')
        self._metric_data: List[Dict[str, Any]] = []
    
    def _add_metric(
        self,
        metric_name: str,
        value: float,
        unit: str,
        dimensions: Optional[List[Dict[str, str]]] = None
    ) -> None:
        """
        Add a metric to the batch for publishing.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            unit: Metric unit (e.g., 'Count', 'Milliseconds')
            dimensions: Additional dimensions (optional)
        """
        # Default dimensions include operation
        default_dimensions = [
            {
                'Name': 'Operation',
                'Value': self.operation
            }
        ]
        
        # Merge with additional dimensions if provided
        all_dimensions = default_dimensions
        if dimensions:
            all_dimensions.extend(dimensions)
        
        metric_data = {
            'MetricName': metric_name,
            'Value': value,
            'Unit': unit,
            'Timestamp': datetime.utcnow(),
            'Dimensions': all_dimensions
        }
        
        self._metric_data.append(metric_data)
    
    def emit_request_count(self, count: int = 1) -> None:
        """
        Emit request count metric.
        
        This metric tracks the number of requests processed by the Lambda function.
        
        Args:
            count: Number of requests (default: 1)
            
        Example:
            metrics.emit_request_count()
        """
        self._add_metric(
            metric_name='RequestCount',
            value=float(count),
            unit='Count'
        )
    
    def emit_error(self, error_code: Optional[str] = None) -> None:
        """
        Emit error metric.
        
        This metric tracks the number of errors that occurred during request processing.
        Optionally includes error code as a dimension for detailed error tracking.
        
        Args:
            error_code: Error code (e.g., 'VALIDATION_ERROR', 'NOT_FOUND') (optional)
            
        Example:
            metrics.emit_error(error_code='NOT_FOUND')
        """
        dimensions = []
        if error_code:
            dimensions.append({
                'Name': 'ErrorCode',
                'Value': error_code
            })
        
        self._add_metric(
            metric_name='ErrorCount',
            value=1.0,
            unit='Count',
            dimensions=dimensions if dimensions else None
        )
    
    def emit_latency(self, latency_ms: int) -> None:
        """
        Emit latency metric.
        
        This metric tracks the request processing latency in milliseconds.
        
        Args:
            latency_ms: Latency in milliseconds
            
        Example:
            metrics.emit_latency(latency_ms=150)
        """
        if latency_ms < 0:
            raise ValueError('Latency must be non-negative')
        
        self._add_metric(
            metric_name='Latency',
            value=float(latency_ms),
            unit='Milliseconds'
        )
    
    def publish(self) -> None:
        """
        Publish all accumulated metrics to CloudWatch.
        
        This method sends all metrics that have been added via emit_* methods
        to CloudWatch in a single batch. It should be called at the end of
        request processing.
        
        Note: CloudWatch PutMetricData has a limit of 20 metrics per request.
        If more than 20 metrics are accumulated, they will be sent in multiple batches.
        
        Example:
            metrics = MetricsClient(operation='users-register-create')
            metrics.emit_request_count()
            metrics.emit_latency(latency_ms=150)
            metrics.publish()
        """
        if not self._metric_data:
            # No metrics to publish
            return
        
        # CloudWatch PutMetricData limit is 20 metrics per request
        batch_size = 20
        
        try:
            # Send metrics in batches
            for i in range(0, len(self._metric_data), batch_size):
                batch = self._metric_data[i:i + batch_size]
                
                self.cloudwatch.put_metric_data(
                    Namespace=METRIC_NAMESPACE,
                    MetricData=batch
                )
            
            # Clear metric data after successful publish
            self._metric_data = []
            
        except Exception as error:
            # Log error but don't fail the request
            # Metrics are important but not critical to request success
            print(f'Failed to publish metrics: {error}')
            # Clear metric data to prevent retry attempts
            self._metric_data = []


def create_metrics_client(operation: str) -> MetricsClient:
    """
    Create a metrics client for a Lambda operation.
    
    This is a convenience function that creates a MetricsClient instance
    with the specified operation name.
    
    Args:
        operation: Operation name (e.g., 'users-register-create')
        
    Returns:
        MetricsClient instance
        
    Example:
        def handler(event, context):
            metrics = create_metrics_client('users-register-create')
            metrics.emit_request_count()
            metrics.emit_latency(latency_ms=150)
            metrics.publish()
    """
    return MetricsClient(operation)
