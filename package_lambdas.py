#!/usr/bin/env python3
"""
Package Lambda functions with shared dependencies.
This script copies users_shared into each Lambda function directory.
Note: External dependencies (boto3, python-ulid) are provided via Lambda Layer.
"""
import shutil
import os
from pathlib import Path

# Lambda function directories
lambda_functions = [
    'lambda/users_register_create',
    'lambda/users_profile_get',
    'lambda/users_profile_update',
    'lambda/users_status_update',
    'lambda/users_role_assign',
    'lambda/users_role_remove',
    'lambda/users_list_query',
    'lambda/users_audit_query',
]

shared_dir = 'lambda/users_shared'

print("Packaging Lambda functions with shared dependencies...\n")

for func_dir in lambda_functions:
    # Copy users_shared directory
    target_shared = os.path.join(func_dir, 'users_shared')
    
    # Remove existing users_shared if it exists
    if os.path.exists(target_shared):
        shutil.rmtree(target_shared)
        print(f"✓ Removed old users_shared from {func_dir}")
    
    # Copy users_shared into Lambda function directory
    shutil.copytree(shared_dir, target_shared, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', 'test_*.py', '.pytest_cache', 'requirements.txt'))
    print(f"✓ Copied users_shared to {func_dir}")

print("\n✅ All Lambda functions packaged successfully!")
print("\nNote: External dependencies (boto3, python-ulid) are provided via Lambda Layer")
print("Now redeploy with: cd deployments && cdk deploy users-dev-stack")
