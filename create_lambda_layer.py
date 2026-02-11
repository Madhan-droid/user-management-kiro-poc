#!/usr/bin/env python3
"""
Create Lambda Layer with python-ulid dependency and all its dependencies.
Note: boto3 is already available in Lambda runtime, so we only need python-ulid.
"""
import subprocess
import os
import shutil
from pathlib import Path

# Create layer directory structure
layer_dir = 'lambda_layer/python'
os.makedirs(layer_dir, exist_ok=True)

print("Creating Lambda Layer...")
print(f"Layer directory: {layer_dir}\n")

# Install python-ulid and typing-extensions with all dependencies into the layer
print("Installing python-ulid and typing-extensions with dependencies...")
result = subprocess.run(
    [
        'pip', 'install',
        'python-ulid>=2.2.0',
        'typing-extensions>=4.0.0',
        '-t', layer_dir,
        '--upgrade',
        '--no-cache-dir'  # Force fresh install
    ],
    capture_output=True,
    text=True
)

if result.returncode == 0:
    print("✓ Installed python-ulid, typing-extensions and dependencies")
    if result.stdout:
        print(f"  {result.stdout[:200]}...")
else:
    print(f"✗ Failed to install dependencies")
    print(f"Error: {result.stderr}")
    exit(1)

# List what was installed
print("\nInstalled packages:")
for item in os.listdir(layer_dir):
    if os.path.isdir(os.path.join(layer_dir, item)) and not item.startswith('__'):
        print(f"  - {item}")

# Clean up unnecessary files but keep dist-info for dependency tracking
print("\nCleaning up unnecessary files...")
patterns_to_remove = [
    '__pycache__',
    '*.pyc',
    'bin'
]

for pattern in patterns_to_remove:
    for item in Path(layer_dir).rglob(pattern):
        if item.is_dir():
            shutil.rmtree(item)
            print(f"  ✓ Removed {item.relative_to(layer_dir)}/")
        else:
            item.unlink()
            print(f"  ✓ Removed {item.relative_to(layer_dir)}")

print("\n✅ Lambda Layer created successfully!")
print(f"\nLayer location: {layer_dir}")
print("\nNext steps:")
print("1. Deploy with: cd deployments && cdk deploy users-dev-stack")

