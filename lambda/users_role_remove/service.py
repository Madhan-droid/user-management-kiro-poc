"""
User role removal service.

This module implements the business logic for role removal, including:
- Retrieving existing user
- Removing role from user's roles list
- Transactional writes to DynamoDB
- Audit event publishing with role removal tracking

Follows steering rules:
- Business logic in services, not handlers
- Fail fast on invalid input
- No global mutable state
- Explicit error handling
"""

import boto3
import json
from datetime import datetime
from typing import Dict, Any
from ulid import ULID

from users_shared.errors import NotFoundError
from users_shared.types import User


class UserService:
    """
    Service class for user role removal operations.
    
    This class encapsulates all business logic for role removal,
    delegating to DynamoDB for persistence and EventBridge for audit events.
    """
    
    def __init__(self, config: Dict[str, str]):
        """
        Initialize the UserService with configuration.
        
        Args:
            config: Dictionary containing:
                - users_table_name: Name of the DynamoDB users table
                - event_bus_name: Name of the EventBridge bus for audit events
        """
        self.config = config
        self.dynamodb = boto3.resource('dynamodb')
        self.dynamodb_client = boto3.client('dynamodb')
        self.users_table = self.dynamodb.Table(config['users_table_name'])
        self.eventbridge = boto3.client('events')
    
    def remove_role(
        self,
        user_id: str,
        role: str,
        correlation_id: str
    ) -> Dict[str, Any]:
        """
        Remove a role from a user.
        
        This method implements the complete role removal flow:
        1. Retrieve existing user record
        2. Remove role from user's roles list
        3. Update user record in USER# and USER_STATUS# items
        4. Publish audit event with role removal
        
        Args:
            user_id: The unique user ID to remove role from
            role: Role name to remove
            correlation_id: Request correlation ID for logging and tracing
            
        Returns:
            Dictionary with userId, roles, and updatedAt
            
        Raises:
            NotFoundError: If user does not exist, is deleted, or role not found
        """
        # Retrieve existing user (Requirement 4.4)
        existing_user = self._get_user_by_id(user_id)
        
        # Check if role exists in user's roles list
        current_roles = existing_user.get('roles', [])
        if role not in current_roles:
            # Role not found, raise NotFoundError (Requirement 4.2)
            raise NotFoundError(f"Role '{role}' not found for user '{user_id}'")
        
        # Remove role from user's roles list (Requirement 4.2)
        updated_roles = [r for r in current_roles if r != role]
        updated_user = existing_user.copy()
        updated_user['roles'] = updated_roles
        updated_user['updatedAt'] = datetime.utcnow().isoformat() + 'Z'
        
        # Update user record in USER# and USER_STATUS# items (Requirement 4.2)
        self._write_user_items(updated_user)
        
        # Publish audit event with role removal (Requirement 4.3)
        self._publish_audit_event({
            'userId': user_id,
            'action': 'ROLE_REMOVED',
            'actor': 'system',  # TODO: Extract from authentication context
            'correlationId': correlation_id,
            'changes': {
                'role': {
                    'before': role,
                    'after': None
                },
                'roles': {
                    'before': current_roles,
                    'after': updated_roles
                }
            }
        })
        
        return {
            'userId': user_id,
            'roles': updated_roles,
            'updatedAt': updated_user['updatedAt']
        }
    
    def _get_user_by_id(self, user_id: str) -> User:
        """
        Retrieve a user by their user ID.
        
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
            
            # Check if user exists (Requirement 4.4)
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
    
    def _write_user_items(self, user: User) -> None:
        """
        Write user items to DynamoDB in a transaction.
        
        Updates three items:
        1. USER#{userId} / PROFILE - Main user profile
        2. USER_EMAIL#{email} / USER - Email uniqueness index
        3. USER_STATUS#{status} / USER#{userId} - Status index for listing
        
        Args:
            user: User object to write
            
        Raises:
            Exception: If transactional write fails
        """
        try:
            # Serialize roles list
            roles_list = [{'S': role} for role in user['roles']]
            
            # Serialize metadata
            metadata_map = {k: {'S': v} for k, v in user['metadata'].items()}
            
            self.dynamodb_client.transact_write_items(
                TransactItems=[
                    {
                        'Put': {
                            'TableName': self.config['users_table_name'],
                            'Item': {
                                'PK': {'S': f"USER#{user['userId']}"},
                                'SK': {'S': 'PROFILE'},
                                'userId': {'S': user['userId']},
                                'email': {'S': user['email']},
                                'name': {'S': user['name']},
                                'status': {'S': user['status']},
                                'roles': {'L': roles_list},
                                'metadata': {'M': metadata_map},
                                'createdAt': {'S': user['createdAt']},
                                'updatedAt': {'S': user['updatedAt']},
                                'entityType': {'S': 'USER_PROFILE'}
                            }
                        }
                    },
                    {
                        'Put': {
                            'TableName': self.config['users_table_name'],
                            'Item': {
                                'PK': {'S': f"USER_EMAIL#{user['email']}"},
                                'SK': {'S': 'USER'},
                                'userId': {'S': user['userId']},
                                'email': {'S': user['email']},
                                'status': {'S': user['status']},
                                'entityType': {'S': 'EMAIL_INDEX'}
                            }
                        }
                    },
                    {
                        'Put': {
                            'TableName': self.config['users_table_name'],
                            'Item': {
                                'PK': {'S': f"USER_STATUS#{user['status']}"},
                                'SK': {'S': f"USER#{user['userId']}"},
                                'userId': {'S': user['userId']},
                                'email': {'S': user['email']},
                                'name': {'S': user['name']},
                                'status': {'S': user['status']},
                                'roles': {'L': roles_list},
                                'createdAt': {'S': user['createdAt']},
                                'entityType': {'S': 'STATUS_INDEX'}
                            }
                        }
                    }
                ]
            )
        except Exception as e:
            print(f"Error writing user items: {e}")
            raise
    
    def _publish_audit_event(self, event_data: Dict[str, Any]) -> None:
        """
        Publish audit event to EventBridge.
        
        Args:
            event_data: Event data containing userId, action, actor, correlationId, and changes
        """
        try:
            event_id = str(ULID())
            timestamp = datetime.utcnow().isoformat() + 'Z'
            
            self.eventbridge.put_events(
                Entries=[
                    {
                        'Source': 'user-management.users',
                        'DetailType': 'UserAuditEvent',
                        'Detail': json.dumps({
                            'eventId': event_id,
                            'userId': event_data['userId'],
                            'timestamp': timestamp,
                            'action': event_data['action'],
                            'actor': event_data['actor'],
                            'correlationId': event_data['correlationId'],
                            'changes': event_data['changes']
                        }),
                        'EventBusName': self.config['event_bus_name']
                    }
                ]
            )
        except Exception as e:
            # Log error but don't fail the request
            # Audit events are important but shouldn't block user operations
            print(f"Error publishing audit event: {e}")
    
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
