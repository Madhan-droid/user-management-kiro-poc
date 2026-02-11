"""
EventBridge bus construct for User Management Service.

This module defines the EventBridge event bus for audit events in the User Management Service.
The event bus receives audit events from all write operations (register, update, status change,
role assign/remove) and can route them to various audit storage destinations.

Architecture:
- Custom event bus for user management audit events
- Event source: user-management.users
- Event detail-type: UserAuditEvent
- Decoupled audit logging from primary operations

Event Schema:
{
  "source": "user-management.users",
  "detail-type": "UserAuditEvent",
  "detail": {
    "eventId": "string (ULID)",
    "userId": "string",
    "timestamp": "ISO8601 timestamp",
    "action": "USER_CREATED | USER_UPDATED | STATUS_CHANGED | ROLE_ASSIGNED | ROLE_REMOVED",
    "actor": "string (authenticated user ID or 'system')",
    "correlationId": "string",
    "changes": {
      "field": {
        "before": "value",
        "after": "value"
      }
    }
  }
}

Follows steering rules:
- Infrastructure definition only (no business logic)
- Explicit over implicit (all configurations declared)
- Naming conventions: <domain>-<capability>-<action>

Usage Example:
    from aws_cdk import Stack
    from constructs import Construct
    from .eventbridge_construct import UserManagementEventBusConstruct
    
    class UserManagementStack(Stack):
        def __init__(self, scope: Construct, construct_id: str, **kwargs):
            super().__init__(scope, construct_id, **kwargs)
            
            # Create EventBridge bus
            event_bus = UserManagementEventBusConstruct(self, "EventBus")
            
            # Use event bus in Lambda constructs
            lambdas = UserManagementLambdasConstruct(
                self, "Lambdas",
                users_table=tables.users_table,
                idempotency_table=tables.idempotency_table,
                event_bus=event_bus.event_bus
            )
"""

from aws_cdk import (
    aws_events as events,
    aws_events_targets as targets,
    aws_logs as logs,
    RemovalPolicy,
    Duration,
)
from constructs import Construct


class UserManagementEventBusConstruct(Construct):
    """
    Construct that creates the EventBridge event bus for User Management Service audit events.
    
    This construct creates a custom event bus for publishing and routing audit events
    from user management operations. The bus can be configured with rules to route
    events to various audit storage destinations (DynamoDB, S3, CloudWatch Logs, etc.).
    
    Attributes:
        event_bus: The EventBridge event bus for audit events
        audit_log_group: CloudWatch Logs log group for audit events (optional)
    """
    
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        enable_cloudwatch_logging: bool = True,
        **kwargs
    ) -> None:
        """
        Initialize EventBridge bus construct.
        
        Args:
            scope: CDK construct scope
            construct_id: Unique construct identifier
            enable_cloudwatch_logging: Whether to enable CloudWatch Logs for audit events
        """
        super().__init__(scope, construct_id, **kwargs)
        
        # Create custom event bus for user management audit events
        self.event_bus = events.EventBus(
            self,
            'UserAuditEventBus',
            event_bus_name='user-management-audit-events',
            description='Event bus for User Management Service audit events'
        )
        
        # Optional: Create CloudWatch Logs log group for audit events
        # This provides a simple audit trail without additional infrastructure
        if enable_cloudwatch_logging:
            self.audit_log_group = logs.LogGroup(
                self,
                'AuditLogGroup',
                log_group_name='/aws/events/user-management/audit',
                retention=logs.RetentionDays.ONE_YEAR,  # Retain audit logs for 1 year
                removal_policy=RemovalPolicy.RETAIN,  # Retain logs on stack deletion
            )
            
            # Create event rule to route all audit events to CloudWatch Logs
            audit_rule = events.Rule(
                self,
                'AuditEventRule',
                event_bus=self.event_bus,
                rule_name='user-audit-to-cloudwatch',
                description='Route all user audit events to CloudWatch Logs',
                event_pattern=events.EventPattern(
                    source=['user-management.users'],
                    detail_type=['UserAuditEvent']
                ),
                enabled=True,
            )
            
            # Add CloudWatch Logs as target
            # The entire event will be logged to CloudWatch Logs
            audit_rule.add_target(
                targets.CloudWatchLogGroup(self.audit_log_group)
            )
        
        # Archive all events for compliance and replay capability
        # EventBridge archives provide long-term storage and event replay
        self.event_archive = events.Archive(
            self,
            'AuditEventArchive',
            archive_name='user-management-audit-archive',
            description='Archive of all user management audit events for compliance',
            source_event_bus=self.event_bus,
            event_pattern=events.EventPattern(
                source=['user-management.users'],
                detail_type=['UserAuditEvent']
            ),
            retention=Duration.days(365),  # Retain for 1 year
        )
    
    def add_audit_target(
        self,
        target_id: str,
        target: targets.IRuleTarget,
        event_pattern: events.EventPattern = None
    ) -> events.Rule:
        """
        Add a custom target for audit events.
        
        This method allows adding additional targets for audit events beyond the
        default CloudWatch Logs target. Examples include:
        - DynamoDB table for queryable audit logs
        - S3 bucket for long-term archival
        - SNS topic for audit notifications
        - Lambda function for custom processing
        
        Args:
            target_id: Unique identifier for the target rule
            target: EventBridge rule target (DynamoDB, S3, SNS, Lambda, etc.)
            event_pattern: Optional event pattern to filter events (defaults to all audit events)
        
        Returns:
            The created EventBridge rule
        
        Example:
            # Add DynamoDB table as audit target
            audit_table = dynamodb.Table(...)
            event_bus.add_audit_target(
                'AuditTableTarget',
                targets.DynamoDbTable(audit_table),
                event_pattern=events.EventPattern(
                    source=['user-management.users'],
                    detail_type=['UserAuditEvent'],
                    detail={
                        'action': ['USER_CREATED', 'USER_UPDATED']
                    }
                )
            )
        """
        # Default event pattern matches all audit events
        if event_pattern is None:
            event_pattern = events.EventPattern(
                source=['user-management.users'],
                detail_type=['UserAuditEvent']
            )
        
        rule = events.Rule(
            self,
            f'{target_id}Rule',
            event_bus=self.event_bus,
            rule_name=f'user-audit-{target_id.lower()}',
            description=f'Route user audit events to {target_id}',
            event_pattern=event_pattern,
            enabled=True,
        )
        
        rule.add_target(target)
        
        return rule
