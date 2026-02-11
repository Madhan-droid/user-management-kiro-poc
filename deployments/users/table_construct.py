"""
DynamoDB table construct for User Management Service.

This module defines the DynamoDB tables required for the User Management Service:
1. Users table - Primary user data store with single-table design
2. Idempotency table - Idempotency key tracking with 24h TTL

Architecture:
- Single-table design for Users table using PK/SK patterns
- No GSIs or LSIs - all access patterns via PK/SK combinations
- On-demand billing mode for variable workloads
- TTL enabled on Idempotency table for automatic cleanup

Access Patterns:
1. Get User by ID: PK=USER#{userId}, SK=PROFILE
2. Check Email Uniqueness: PK=USER_EMAIL#{email}, SK=USER
3. List Users by Status: PK=USER_STATUS#{status}, SK=USER#{userId}
"""

from aws_cdk import (
    aws_dynamodb as dynamodb,
    RemovalPolicy,
    Duration,
)
from constructs import Construct


class UserManagementTablesConstruct(Construct):
    """
    Construct that creates DynamoDB tables for User Management Service.
    
    Creates two tables:
    1. Users table - Stores user profiles with multiple access patterns
    2. Idempotency table - Tracks idempotency keys with automatic expiration
    
    Attributes:
        users_table: The Users DynamoDB table
        idempotency_table: The Idempotency DynamoDB table
    """
    
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Create Users table with single-table design
        self.users_table = dynamodb.Table(
            self,
            "UsersTable",
            # Primary key configuration
            partition_key=dynamodb.Attribute(
                name="PK",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="SK",
                type=dynamodb.AttributeType.STRING
            ),
            # Billing configuration
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            # Data protection
            point_in_time_recovery=True,
            # Deletion policy - retain for production safety
            removal_policy=RemovalPolicy.RETAIN,
            # Table name will be auto-generated with stack prefix
            # This ensures uniqueness across environments
        )
        
        # Create Idempotency table with TTL
        self.idempotency_table = dynamodb.Table(
            self,
            "IdempotencyTable",
            # Primary key configuration
            partition_key=dynamodb.Attribute(
                name="PK",
                type=dynamodb.AttributeType.STRING
            ),
            # Billing configuration
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            # TTL configuration for automatic cleanup after 24 hours
            time_to_live_attribute="ttl",
            # Data protection
            point_in_time_recovery=True,
            # Deletion policy - retain for production safety
            removal_policy=RemovalPolicy.RETAIN,
            # Table name will be auto-generated with stack prefix
        )
