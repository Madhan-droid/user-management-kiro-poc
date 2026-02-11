"""
User profile service.

This module implements the business logic for user profile operations, including:
- User retrieval by ID
- Profile updates
- Handling deleted users

Follows steering rules:
- Business logic in services, not handlers
- Fail fast on invalid input
- No global mutable state
- Explicit error handling
"""

import boto3
from typing import Dict, Any, Optional
from datetime import datetime

from users_shared.errors import NotFoundError
from users_shared.types import User


class UserService:
    """
    Service class for user profile operations.
    
    This class encapsulates all business logic for user profile retrieval
    and updates, delegating to DynamoDB for persistence.
    """
    
    def __init__(self, config: Dict[str, str]):
        """
        Initialize the UserService with configuration.
        
        Args:
            config: Dictionary containing:
                - users_table_name: Name of the DynamoDB users table
        """
        self.config = config
        self.dynamodb = boto3.resource('dynamodb')
        self.users_table = self.dynamodb.Table(config['users_table_name'])
    
    def get_user_by_id(self, user_id: str) -> User:
        """
        Retrieve a user by their user ID.
        
        This method queries the USER# partition with PROFILE sort key to retrieve
        the complete user profile. It handles two error cases:
        1. User does not exist - raises NotFoundError
        2. User exists but is deleted - raises NotFoundError
        
        Args:
            user_id: The unique user ID (ULID format)
            
        Returns:
            User object with all profile information
            
        Raises:
            NotFoundError: If user does not exist or is deleted
        """
        try:
            # Query USER# partition with PROFILE sort key
            response = self.users_table.get_item(
                Key={
                    'PK': f'USER#{user_id}',
                    'SK': 'PROFILE'
                }
            )
            
            # Check if user exists
            if 'Item' not in response:
                raise NotFoundError(f"User with ID '{user_id}' not found")
            
            item = response['Item']
            
            # Check if user is deleted (soft delete)
            if item.get('status') == 'deleted':
                raise NotFoundError(f"User with ID '{user_id}' not found")
            
            # Convert DynamoDB item to User type
            user: User = {
                'userId': item['userId'],
                'email': item['email'],
                'name': item['name'],
                'status': item['status'],
                'roles': item.get('roles', []),
                'metadata': self._deserialize_metadata(item.get('metadata', {})),
                'createdAt': item['createdAt'],
                'updatedAt': item['updatedAt']
            }
            
            return user
            
        except NotFoundError:
            # Re-raise NotFoundError as-is
            raise
        except Exception as e:
            # Log unexpected errors
            print(f"Error retrieving user {user_id}: {e}")
            raise
    
    def _deserialize_metadata(self, metadata: Any) -> Dict[str, str]:
        """
        Deserialize metadata from DynamoDB format.
        
        DynamoDB stores maps in a nested format. This method converts
        the DynamoDB map format to a simple Python dictionary.
        
        Args:
            metadata: Metadata in DynamoDB format (could be dict or DynamoDB Map)
            
        Returns:
            Simple dictionary with string keys and values
        """
        if not metadata:
            return {}
        
        # If metadata is already a simple dict, return it
        if isinstance(metadata, dict) and all(isinstance(v, str) for v in metadata.values()):
            return metadata
        
        # If metadata is in DynamoDB Map format, deserialize it
        result = {}
        if isinstance(metadata, dict):
            for key, value in metadata.items():
                if isinstance(value, dict) and 'S' in value:
                    result[key] = value['S']
                elif isinstance(value, str):
                    result[key] = value
        
        return result
