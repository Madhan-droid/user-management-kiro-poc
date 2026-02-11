"""
User Management Service CDK Stack.

This module defines the main CDK stack for the User Management Service.
The stack integrates all constructs (DynamoDB tables, Lambda functions,
API Gateway, EventBridge) into a complete, deployable infrastructure.

Stack naming convention: <service>-<env>-stack (e.g., users-prod-stack)

Architecture:
- DynamoDB tables for user data and idempotency
- EventBridge bus for audit events
- 8 Lambda functions for user operations
- REST API Gateway with IAM authentication
- CloudFormation outputs for API endpoint

Follows steering rules:
- Infrastructure definition only (no business logic)
- Explicit over implicit (all configurations declared)
- Naming conventions: <service>-<env>-stack
- Stack tags for resource organization

Usage Example:
    from aws_cdk import App
    from users.users_stack import UserManagementStack
    
    app = App()
    
    # Development environment
    UserManagementStack(
        app,
        'users-dev-stack',
        env_name='dev',
        description='User Management Service - Development'
    )
    
    # Production environment
    UserManagementStack(
        app,
        'users-prod-stack',
        env_name='prod',
        description='User Management Service - Production'
    )
    
    app.synth()
"""

from aws_cdk import (
    Stack,
    CfnOutput,
    Tags,
)
from constructs import Construct

from .table_construct import UserManagementTablesConstruct
from .eventbridge_construct import UserManagementEventBusConstruct
from .lambda_constructs import UserManagementLambdasConstruct
from .api_construct import UserManagementApiConstruct


class UserManagementStack(Stack):
    """
    Main CDK stack for User Management Service.
    
    This stack creates all infrastructure components for the User Management Service:
    - DynamoDB tables (Users, Idempotency)
    - EventBridge event bus for audit events
    - 8 Lambda functions for user operations
    - REST API Gateway with 8 endpoints
    
    The stack follows CDK best practices:
    - Constructs are composed for modularity
    - Resources are tagged for organization
    - Outputs are exported for cross-stack references
    - Environment-specific naming via env_name parameter
    
    Attributes:
        tables: DynamoDB tables construct
        event_bus: EventBridge bus construct
        lambdas: Lambda functions construct
        api: API Gateway construct
    """
    
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        env_name: str = 'dev',
        **kwargs
    ) -> None:
        """
        Initialize User Management Stack.
        
        Args:
            scope: CDK app scope
            construct_id: Stack identifier (should follow <service>-<env>-stack convention)
            env_name: Environment name (dev, staging, prod, etc.)
            **kwargs: Additional stack properties (env, description, etc.)
        """
        super().__init__(scope, construct_id, **kwargs)
        
        # Store environment name for tagging and naming
        self.env_name = env_name
        
        # Apply stack-level tags for resource organization
        # Tags help with cost allocation, resource filtering, and compliance
        Tags.of(self).add('Service', 'user-management')
        Tags.of(self).add('Environment', env_name)
        Tags.of(self).add('ManagedBy', 'CDK')
        Tags.of(self).add('Domain', 'users')
        
        # 1. Create DynamoDB tables
        # Tables must be created first as they're dependencies for Lambda functions
        self.tables = UserManagementTablesConstruct(
            self,
            'Tables',
        )
        
        # 2. Create EventBridge event bus for audit events
        # Event bus must be created before Lambda functions that publish to it
        self.event_bus = UserManagementEventBusConstruct(
            self,
            'EventBus',
            enable_cloudwatch_logging=True,  # Enable CloudWatch Logs for audit trail
        )
        
        # 3. Create Lambda functions
        # Lambda functions depend on tables and event bus
        self.lambdas = UserManagementLambdasConstruct(
            self,
            'Lambdas',
            users_table=self.tables.users_table,
            idempotency_table=self.tables.idempotency_table,
            event_bus=self.event_bus.event_bus,
        )
        
        # 4. Create API Gateway
        # API Gateway wires Lambda functions to HTTP endpoints
        self.api = UserManagementApiConstruct(
            self,
            'Api',
            register_lambda=self.lambdas.register_lambda,
            profile_get_lambda=self.lambdas.profile_get_lambda,
            profile_update_lambda=self.lambdas.profile_update_lambda,
            status_update_lambda=self.lambdas.status_update_lambda,
            role_assign_lambda=self.lambdas.role_assign_lambda,
            role_remove_lambda=self.lambdas.role_remove_lambda,
            list_query_lambda=self.lambdas.list_query_lambda,
            audit_query_lambda=self.lambdas.audit_query_lambda,
        )
        
        # Export API endpoint URL as CloudFormation output
        # This allows clients to discover the API endpoint programmatically
        CfnOutput(
            self,
            'ApiEndpointUrl',
            value=self.api.api.url,
            description='User Management API endpoint URL',
            export_name=f'{construct_id}-api-url',
        )
        
        # Export API ID for reference in other stacks or tools
        CfnOutput(
            self,
            'ApiId',
            value=self.api.api.rest_api_id,
            description='User Management API Gateway ID',
            export_name=f'{construct_id}-api-id',
        )
        
        # Export Users table name for reference
        CfnOutput(
            self,
            'UsersTableName',
            value=self.tables.users_table.table_name,
            description='Users DynamoDB table name',
            export_name=f'{construct_id}-users-table',
        )
        
        # Export Idempotency table name for reference
        CfnOutput(
            self,
            'IdempotencyTableName',
            value=self.tables.idempotency_table.table_name,
            description='Idempotency DynamoDB table name',
            export_name=f'{construct_id}-idempotency-table',
        )
        
        # Export Event Bus name for reference
        CfnOutput(
            self,
            'EventBusName',
            value=self.event_bus.event_bus.event_bus_name,
            description='User Management audit event bus name',
            export_name=f'{construct_id}-event-bus',
        )
        
        # Export Event Bus ARN for cross-account/cross-region access
        CfnOutput(
            self,
            'EventBusArn',
            value=self.event_bus.event_bus.event_bus_arn,
            description='User Management audit event bus ARN',
            export_name=f'{construct_id}-event-bus-arn',
        )
