#!/usr/bin/env python3
"""
CDK Application Entry Point.

This is the main entry point for the CDK application. It creates and configures
all CDK stacks for deployment.

Usage:
    # Synthesize CloudFormation templates
    cdk synth
    
    # Deploy to development environment
    cdk deploy users-dev-stack
    
    # Deploy to production environment
    cdk deploy users-prod-stack
    
    # Deploy all stacks
    cdk deploy --all

Environment Configuration:
    Stacks can be configured with AWS account and region via environment variables:
    - CDK_DEFAULT_ACCOUNT: AWS account ID
    - CDK_DEFAULT_REGION: AWS region
    
    Or by passing env parameter to stack constructor.

Follows steering rules:
- Explicit over implicit (all configurations declared)
- Environment-specific naming
- Stack naming convention: <service>-<env>-stack
"""

import os
from aws_cdk import App, Environment

from users.users_stack import UserManagementStack


# Create CDK app
app = App()

# Get AWS environment from context or environment variables
# This allows deployment to different accounts/regions
account = os.environ.get('CDK_DEFAULT_ACCOUNT')
region = os.environ.get('CDK_DEFAULT_REGION')

# Create environment configuration if account and region are provided
env = None
if account and region:
    env = Environment(account=account, region=region)

# Development Stack
# Used for development and testing
dev_stack = UserManagementStack(
    app,
    'users-dev-stack',
    env_name='dev',
    env=env,
    description='User Management Service - Development Environment',
)

# Production Stack
# Used for production workloads
# Uncomment when ready to deploy to production
# prod_stack = UserManagementStack(
#     app,
#     'users-prod-stack',
#     env_name='prod',
#     env=env,
#     description='User Management Service - Production Environment',
# )

# Synthesize CloudFormation templates
app.synth()
