"""
Lambda function constructs for User Management Service.

This module defines all Lambda function constructs for the User Management Service.
Each Lambda follows the lambda-per-operation pattern with:
- Explicit environment variable configuration
- Least privilege IAM permissions
- Consistent memory and timeout settings
- Python 3.11 runtime

Follows steering rules:
- Infrastructure definition only (no business logic)
- Explicit over implicit (all configurations declared)
- Least privilege IAM permissions
- Naming conventions: <domain>-<capability>-<action>

Lambda Functions:
1. users-register-create: User registration
2. users-profile-get: User profile retrieval
3. users-profile-update: User profile updates
4. users-status-update: User status management
5. users-role-assign: Role assignment
6. users-role-remove: Role removal
7. users-list-query: User listing
8. users-audit-query: Audit log retrieval
"""

from aws_cdk import (
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_dynamodb as dynamodb,
    aws_events as events,
    Duration,
    BundlingOptions,
)
from constructs import Construct
from typing import Dict
import os


class UserManagementLambdasConstruct(Construct):
    """
    Construct that creates all Lambda functions for User Management Service.
    
    This construct creates 8 Lambda functions with appropriate IAM permissions,
    environment variables, and configurations based on each function's requirements.
    
    Attributes:
        register_lambda: User registration Lambda function
        profile_get_lambda: User profile retrieval Lambda function
        profile_update_lambda: User profile update Lambda function
        status_update_lambda: User status update Lambda function
        role_assign_lambda: Role assignment Lambda function
        role_remove_lambda: Role removal Lambda function
        list_query_lambda: User listing Lambda function
        audit_query_lambda: Audit log query Lambda function
        dependencies_layer: Lambda Layer with python-ulid dependency
    """
    
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        users_table: dynamodb.Table,
        idempotency_table: dynamodb.Table,
        event_bus: events.EventBus,
        **kwargs
    ) -> None:
        """
        Initialize Lambda functions construct.
        
        Args:
            scope: CDK construct scope
            construct_id: Unique construct identifier
            users_table: DynamoDB users table
            idempotency_table: DynamoDB idempotency table
            event_bus: EventBridge event bus for audit events
        """
        super().__init__(scope, construct_id, **kwargs)
        
        # Create Lambda Layer for dependencies (python-ulid)
        # Note: boto3 is already available in Lambda runtime
        self.dependencies_layer = lambda_.LayerVersion(
            self,
            'DependenciesLayer',
            code=lambda_.Code.from_asset('../lambda_layer'),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_11],
            description='Python dependencies: python-ulid'
        )
        
        # Common Lambda configuration
        common_config = {
            'runtime': lambda_.Runtime.PYTHON_3_11,
            'memory_size': 256,  # MB
            'timeout': Duration.seconds(30),
            'tracing': lambda_.Tracing.ACTIVE,  # Enable X-Ray tracing
            'layers': [self.dependencies_layer],  # Add dependencies layer
        }
        
        # 1. User Registration Lambda
        # Requires: DynamoDB write, EventBridge publish, idempotency check
        self.register_lambda = self._create_register_lambda(
            common_config,
            users_table,
            idempotency_table,
            event_bus
        )
        
        # 2. User Profile Get Lambda
        # Requires: DynamoDB read only
        self.profile_get_lambda = self._create_profile_get_lambda(
            common_config,
            users_table
        )
        
        # 3. User Profile Update Lambda
        # Requires: DynamoDB read/write, EventBridge publish, idempotency check
        self.profile_update_lambda = self._create_profile_update_lambda(
            common_config,
            users_table,
            idempotency_table,
            event_bus
        )
        
        # 4. User Status Update Lambda
        # Requires: DynamoDB read/write, EventBridge publish
        self.status_update_lambda = self._create_status_update_lambda(
            common_config,
            users_table,
            event_bus
        )
        
        # 5. Role Assignment Lambda
        # Requires: DynamoDB read/write, EventBridge publish
        self.role_assign_lambda = self._create_role_assign_lambda(
            common_config,
            users_table,
            event_bus
        )
        
        # 6. Role Removal Lambda
        # Requires: DynamoDB read/write, EventBridge publish
        self.role_remove_lambda = self._create_role_remove_lambda(
            common_config,
            users_table,
            event_bus
        )
        
        # 7. User List Query Lambda
        # Requires: DynamoDB read only (query by status)
        self.list_query_lambda = self._create_list_query_lambda(
            common_config,
            users_table
        )
        
        # 8. Audit Query Lambda
        # Requires: EventBridge/audit store read only
        # Note: Audit implementation may vary (EventBridge archive, separate DynamoDB table, etc.)
        self.audit_query_lambda = self._create_audit_query_lambda(
            common_config,
            users_table  # Placeholder - actual audit store TBD
        )
    
    def _create_register_lambda(
        self,
        common_config: Dict,
        users_table: dynamodb.Table,
        idempotency_table: dynamodb.Table,
        event_bus: events.EventBus
    ) -> lambda_.Function:
        """
        Create user registration Lambda function.
        
        Operations: Create user, check email uniqueness, store idempotency key, publish audit event
        Permissions: DynamoDB write (users + idempotency), EventBridge publish
        """
        fn = lambda_.Function(
            self,
            'RegisterLambda',
            function_name='users-register-create',
            description='User registration - creates new users with email uniqueness validation',
            code=lambda_.Code.from_asset('../lambda/users_register_create'),
            handler='handler.handler',
            environment={
                'USERS_TABLE_NAME': users_table.table_name,
                'IDEMPOTENCY_TABLE_NAME': idempotency_table.table_name,
                'EVENT_BUS_NAME': event_bus.event_bus_name,
            },
            **common_config
        )
        
        # Grant DynamoDB permissions - read and write for users table
        users_table.grant_read_write_data(fn)
        
        # Grant DynamoDB permissions - read and write for idempotency table
        idempotency_table.grant_read_write_data(fn)
        
        # Grant EventBridge publish permissions
        event_bus.grant_put_events_to(fn)
        
        return fn
    
    def _create_profile_get_lambda(
        self,
        common_config: Dict,
        users_table: dynamodb.Table
    ) -> lambda_.Function:
        """
        Create user profile retrieval Lambda function.
        
        Operations: Get user by ID
        Permissions: DynamoDB read only
        """
        fn = lambda_.Function(
            self,
            'ProfileGetLambda',
            function_name='users-profile-get',
            description='User profile retrieval - gets user by ID',
            code=lambda_.Code.from_asset('../lambda/users_profile_get'),
            handler='get_handler.handler',
            environment={
                'USERS_TABLE_NAME': users_table.table_name,
            },
            **common_config
        )
        
        # Grant DynamoDB read permissions only
        users_table.grant_read_data(fn)
        
        return fn
    
    def _create_profile_update_lambda(
        self,
        common_config: Dict,
        users_table: dynamodb.Table,
        idempotency_table: dynamodb.Table,
        event_bus: events.EventBus
    ) -> lambda_.Function:
        """
        Create user profile update Lambda function.
        
        Operations: Update user profile, check idempotency, publish audit event
        Permissions: DynamoDB read/write (users + idempotency), EventBridge publish
        """
        fn = lambda_.Function(
            self,
            'ProfileUpdateLambda',
            function_name='users-profile-update',
            description='User profile update - updates user name and metadata',
            code=lambda_.Code.from_asset('../lambda/users_profile_update'),
            handler='update_handler.handler',
            environment={
                'USERS_TABLE_NAME': users_table.table_name,
                'IDEMPOTENCY_TABLE_NAME': idempotency_table.table_name,
                'EVENT_BUS_NAME': event_bus.event_bus_name,
            },
            **common_config
        )
        
        # Grant DynamoDB permissions
        users_table.grant_read_write_data(fn)
        idempotency_table.grant_read_write_data(fn)
        
        # Grant EventBridge publish permissions
        event_bus.grant_put_events_to(fn)
        
        return fn
    
    def _create_status_update_lambda(
        self,
        common_config: Dict,
        users_table: dynamodb.Table,
        event_bus: events.EventBus
    ) -> lambda_.Function:
        """
        Create user status update Lambda function.
        
        Operations: Update user status (active/disabled/deleted), publish audit event
        Permissions: DynamoDB read/write, EventBridge publish
        """
        fn = lambda_.Function(
            self,
            'StatusUpdateLambda',
            function_name='users-status-update',
            description='User status management - updates user status lifecycle',
            code=lambda_.Code.from_asset('../lambda/users_status_update'),
            handler='handler.handler',
            environment={
                'USERS_TABLE_NAME': users_table.table_name,
                'EVENT_BUS_NAME': event_bus.event_bus_name,
            },
            **common_config
        )
        
        # Grant DynamoDB permissions
        users_table.grant_read_write_data(fn)
        
        # Grant EventBridge publish permissions
        event_bus.grant_put_events_to(fn)
        
        return fn
    
    def _create_role_assign_lambda(
        self,
        common_config: Dict,
        users_table: dynamodb.Table,
        event_bus: events.EventBus
    ) -> lambda_.Function:
        """
        Create role assignment Lambda function.
        
        Operations: Assign role to user, publish audit event
        Permissions: DynamoDB read/write, EventBridge publish
        """
        fn = lambda_.Function(
            self,
            'RoleAssignLambda',
            function_name='users-role-assign',
            description='Role assignment - assigns roles to users',
            code=lambda_.Code.from_asset('../lambda/users_role_assign'),
            handler='assign_handler.handler',
            environment={
                'USERS_TABLE_NAME': users_table.table_name,
                'EVENT_BUS_NAME': event_bus.event_bus_name,
            },
            **common_config
        )
        
        # Grant DynamoDB permissions
        users_table.grant_read_write_data(fn)
        
        # Grant EventBridge publish permissions
        event_bus.grant_put_events_to(fn)
        
        return fn
    
    def _create_role_remove_lambda(
        self,
        common_config: Dict,
        users_table: dynamodb.Table,
        event_bus: events.EventBus
    ) -> lambda_.Function:
        """
        Create role removal Lambda function.
        
        Operations: Remove role from user, publish audit event
        Permissions: DynamoDB read/write, EventBridge publish
        """
        fn = lambda_.Function(
            self,
            'RoleRemoveLambda',
            function_name='users-role-remove',
            description='Role removal - removes roles from users',
            code=lambda_.Code.from_asset('../lambda/users_role_remove'),
            handler='remove_handler.handler',
            environment={
                'USERS_TABLE_NAME': users_table.table_name,
                'EVENT_BUS_NAME': event_bus.event_bus_name,
            },
            **common_config
        )
        
        # Grant DynamoDB permissions
        users_table.grant_read_write_data(fn)
        
        # Grant EventBridge publish permissions
        event_bus.grant_put_events_to(fn)
        
        return fn
    
    def _create_list_query_lambda(
        self,
        common_config: Dict,
        users_table: dynamodb.Table
    ) -> lambda_.Function:
        """
        Create user listing Lambda function.
        
        Operations: Query users by status with pagination
        Permissions: DynamoDB read only
        """
        fn = lambda_.Function(
            self,
            'ListQueryLambda',
            function_name='users-list-query',
            description='User listing - queries users by status with pagination',
            code=lambda_.Code.from_asset('../lambda/users_list_query'),
            handler='handler.handler',
            environment={
                'USERS_TABLE_NAME': users_table.table_name,
            },
            **common_config
        )
        
        # Grant DynamoDB read permissions only
        users_table.grant_read_data(fn)
        
        return fn
    
    def _create_audit_query_lambda(
        self,
        common_config: Dict,
        users_table: dynamodb.Table
    ) -> lambda_.Function:
        """
        Create audit log query Lambda function.
        
        Operations: Query audit logs for a user
        Permissions: Read from audit store (implementation-dependent)
        
        Note: This is a placeholder implementation. The actual audit store
        (EventBridge archive, separate DynamoDB table, etc.) will determine
        the final permissions and environment variables.
        """
        fn = lambda_.Function(
            self,
            'AuditQueryLambda',
            function_name='users-audit-query',
            description='Audit log retrieval - queries audit events for users',
            code=lambda_.Code.from_asset('../lambda/users_audit_query'),
            handler='handler.handler',
            environment={
                'USERS_TABLE_NAME': users_table.table_name,
                # TODO: Add audit store configuration when implemented
                # 'AUDIT_TABLE_NAME': audit_table.table_name,
                # or
                # 'EVENT_BUS_NAME': event_bus.event_bus_name,
            },
            **common_config
        )
        
        # Grant read permissions to audit store
        # TODO: Update when audit store implementation is finalized
        users_table.grant_read_data(fn)
        
        return fn
