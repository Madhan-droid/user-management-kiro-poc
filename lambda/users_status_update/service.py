"""
User status update service.

This module implements the business logic for user status updates, including:
- Status transition validation (active/disabled/deleted)
- Transactional writes to DynamoDB with status partition moves
- Audit event publishing with status change tracking

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
from users_shared.types import User, UserStatus


class UserService:
    """
    Service class for user status update operations.
    
    This class encapsulates all business logic for user status updates,
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
    
    def update_user_status(
        self,
        user_id: str,
        new_status: UserStatus,
        correlation_id: str
    ) -> Dict[str, Any]:
        """
        Update a user's status.
        
        This method implements the complete user status update flow:
        1. Retrieve existing user record
        2. Validate status transition (all transitions are valid per requirements)
        3. Update user status in all three DynamoDB items transactionally
        4. Move USER_STATUS# item between partitions (delete old, create new)
        5. Publish audit event with status change
        
        Valid transitions:
        - active → disabled (disable operation)
        - disabled → active (enable operation)
        - any status → deleted (delete operation)
        
        Args:
            user_id: The unique user ID to update
            new_status: New status value (active, disabled, or deleted)
            correlation_id: Request correlation ID for logging and tracing
            
        Returns:
            Dictionary with userId, status, and updatedAt
            
        Raises:
            NotFoundError: If user does not exist
        """
        # Retrieve existing user
        existing_user = self._get_user_by_id(user_id)
        old_status = existing_user['status']
        
        # If status hasn't changed, return current state
        if old_status == new_status:
            return {
                'userId': user_id,
                'status': new_status,
                'updatedAt': existing_user['updatedAt']
            }
        
        # Update user record with new status
        updated_user = existing_user.copy()
        updated_user['status'] = new_status
        updated_user['updatedAt'] = datetime.utcnow().isoformat() + 'Z'
        
        # Write all items transactionally, moving USER_STATUS# item between partitions
        self._write_user_items_with_status_move(updated_user, old_status)
        
        # Publish audit event with status change
        self._publish_audit_event({
            'userId': user_id,
            'action': 'STATUS_CHANGED',
            'actor': 'system',  # TODO: Extract from authentication context
            'correlationId': correlation_id,
            'changes': {
                'status': {
                    'before': old_status,
                    'after': new_status
                }
            }
        })
        
        return {
            'userId': user_id,
            'status': new_status,
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
            NotFoundError: If user does not exist
            
        Note: Unlike profile retrieval, status updates can operate on deleted users
        to support re-enabling or status corrections.
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
    
    def _write_user_items_with_status_move(
        self,
        user: User,
        old_status: UserStatus
    ) -> None:
        """
        Write all user items to DynamoDB in a transaction, moving status partition.
        
        Updates three items:
        1. USER#{userId} / PROFILE - Main user profile with new status
        2. USER_EMAIL#{email} / USER - Email index with new status
        3. Delete old USER_STATUS#{oldStatus} / USER#{userId} item
        4. Create new USER_STATUS#{newStatus} / USER#{userId} item
        
        Args:
            user: User object with updated status
            old_status: Previous status value (for deleting old status index item)
            
        Raises:
            Exception: If transactional write fails
        """
        try:
            # Serialize roles list
            roles_list = [{'S': role} for role in user['roles']]
            
            # Serialize metadata
            metadata_map = {k: {'S': v} for k, v in user['metadata'].items()}
            
            # Build transaction items
            transaction_items = [
                # Update main user profile
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
                # Update email index with new status
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
                # Delete old status index item
                {
                    'Delete': {
                        'TableName': self.config['users_table_name'],
                        'Key': {
                            'PK': {'S': f"USER_STATUS#{old_status}"},
                            'SK': {'S': f"USER#{user['userId']}"}
                        }
                    }
                },
                # Create new status index item
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
            
            self.dynamodb_client.transact_write_items(
                TransactItems=transaction_items
            )
        except Exception as e:
            print(f"Error writing user items with status move: {e}")
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
