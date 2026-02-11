#!/usr/bin/env python3
"""
Clean up installed dependencies from Lambda directories.
These should be in a Lambda Layer instead.
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

# Directories to remove (installed dependencies)
dirs_to_remove = [
    'boto3',
    'botocore',
    'ulid',
    'python_ulid-2.7.0.dist-info',
    'boto3-1.36.9.dist-info',
    'botocore-1.36.9.dist-info',
    's3transfer',
    's3transfer-0.11.1.dist-info',
    'jmespath',
    'jmespath-1.0.1.dist-info',
    'dateutil',
    'python_dateutil-2.9.0.post0.dist-info',
    'six-1.17.0.dist-info',
    'six.py',
    'urllib3',
    'urllib3-2.3.0.dist-info',
    '_distutils_hack',
    'bin'
]

print("Cleaning up Lambda dependencies...\n")

for func_dir in lambda_functions:
    print(f"Cleaning {func_dir}...")
    
    # Remove all dist-info directories
    for item in Path(func_dir).glob('*.dist-info'):
        if item.is_dir():
            shutil.rmtree(item)
            print(f"  ✓ Removed {item.name}/")
    
    # Remove specific directories
    for dir_name in dirs_to_remove:
        dir_path = os.path.join(func_dir, dir_name)
        if os.path.exists(dir_path):
            if os.path.isdir(dir_path):
                shutil.rmtree(dir_path)
                print(f"  ✓ Removed {dir_name}/")
            else:
                os.remove(dir_path)
                print(f"  ✓ Removed {dir_name}")
    
    # Also remove requirements.txt (will be in layer instead)
    req_file = os.path.join(func_dir, 'requirements.txt')
    if os.path.exists(req_file):
        os.remove(req_file)
        print(f"  ✓ Removed requirements.txt")

print("\n✅ All Lambda dependencies cleaned up!")
print("\nNext: Create Lambda Layer for shared dependencies")
