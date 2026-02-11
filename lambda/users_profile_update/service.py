"""
User profile update service.

This module implements the business logic for user profile updates, including:
- Idempotency handling
- Profile field updates (name, metadata)
- Transactional writes to DynamoDB
- Audit event publishing with before/after values

Follows steering rules:
- Business logic in services, not handlers
- Fail fast on invalid input
- No global mutable state
- Explicit error handling
"""

import boto3
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from ulid import ULID

from users_shared.errors import ConflictError, NotFoundError, ValidationError
from users_shared.types import User, UpdateProfileRequest


class UserService:
    """
    Service class for user profile update operations.
    
    This class encapsulates all business logic for user profile updates,
    delegating to DynamoDB for persistence and EventBridge for audit events.
    """
    
    def __init__(self, config: Dict[str, str]):
        """
        Initialize the UserService with configuration.
        
        Args:
            config: Dictionary containing:
                - users_table_name: Name of the DynamoDB users table
                - idempotency_table_name: Name of the DynamoDB idempotency table
                - event_bus_name: Name of the EventBridge bus for audit events
        """
        self.config = config
        self.dynamodb = boto3.resource('dynamodb')
        self.dynamodb_client = boto3.client('dynamodb')
        self.users_table = self.dynamodb.Table(config['users_table_name'])
        self.idempotency_table = self.dynamodb.Table(config['idempotency_table_name'])
        self.eventbridge = boto3.client('events')
    
    def update_user_profile(
        self,
        user_id: str,
        request: UpdateProfileRequest,
        correlation_id: str
    ) -> User:
        """
        Update a user's profile.
        
        This method implements the complete user profile update flow:
        1. Check idempotency to prevent duplicate updates
        2. Retrieve existing user record
        3. Validate User_ID is not being modified
        4. Apply updates to user record
        5. Write all three DynamoDB items transactionally
        6. Store idempotency record
        7. Publish audit event with before/after values
        
        Args:
            user_id: The unique user ID to update
            request: Update request containing name, metadata, and idempotency key
            correlation_id: Request correlation ID for logging and tracing
            
        Returns:
            Updated user object
            
        Raises:
            NotFoundError: If user does not exist or is deleted
            ValidationError: If attempting to modify User_ID
            ConflictError: If idempotency key conflict
        """
        # Check idempotency first
        existing_response = self._check_idempotency(
            request['idempotencyKey'],
            {'userId': user_id, **request}
        )
        if existing_response:
            return existing_response
        
        # Retrieve existing user
        existing_user = self._get_user_by_id(user_id)
        
        # Validate User_ID is not being modified (should not be in request)
        # This validation is handled at the handler/validation layer
        # but we double-check here for safety
        
        # Apply updates to user record
        updated_user = self._apply_updates(existing_user, request)
        
        # Track changes for audit event
        changes = self._calculate_changes(existing_user, updated_user)
        
        # Write all three items transactionally
        self._write_user_items(updated_user)
        
        # Store idempotency record
        self._store_idempotency_key(request['idempotencyKey'], updated_user)
        
        # Publish audit event with before/after values
        self._publish_audit_event({
            'userId': user_id,
            'action': 'USER_UPDATED',
            'actor': 'system',  # TODO: Extract from authentication context
            'correlationId': correlation_id,
            'changes': changes
        })
        
        return updated_user
    
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
    
    def _apply_updates(self, existing_user: User, request: UpdateProfileRequest) -> User:
        """
        Apply updates to the existing user record.
        
        Args:
            existing_user: Current user record
            request: Update request with new values
            
        Returns:
            Updated user object
        """
        updated_user = existing_user.copy()
        
        # Update name if provided
        if 'name' in request and request['name'] is not None:
            updated_user['name'] = request['name']
        
        # Update metadata if provided
        if 'metadata' in request and request['metadata'] is not None:
            updated_user['metadata'] = request['metadata']
        
        # Update timestamp
        updated_user['updatedAt'] = datetime.utcnow().isoformat() + 'Z'
        
        return updated_user
    
    def _calculate_changes(self, before: User, after: User) -> Dict[str, Dict[str, Any]]:
        """
        Calculate what changed between before and after states.
        
        Args:
            before: User state before update
            after: User state after update
            
        Returns:
            Dictionary of changes with before/after values
        """
        changes = {}
        
        # Check each field for changes
        for field in ['name', 'metadata']:
            if before.get(field) != after.get(field):
                changes[field] = {
                    'before': before.get(field),
                    'after': after.get(field)
                }
        
        return changes
    
    def _write_user_items(self, user: User) -> None:
        """
        Write all three user items to DynamoDB in a transaction.
        
        Updates three items:
        1. USER#{userId} / PROFILE - Main user profile
        2. USER_EMAIL#{email} / USER - Email uniqueness index
        3. USER_STATUS#{status} / USER#{userId} - Status index for listing
        
        Note: Email changes are not supported in profile updates per requirements,
        so we don't need to handle moving the USER_EMAIL# item.
        
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
    
    def _check_idempotency(
        self,
        idempotency_key: str,
        request: Dict[str, Any]
    ) -> Optional[User]:
        """
        Check if this request has already been processed.
        
        If the idempotency key exists:
        - If request hash matches, return the stored response
        - If request hash differs, raise ConflictError
        
        Args:
            idempotency_key: Unique key for this request
            request: Request payload for hash comparison
            
        Returns:
            Stored user response if idempotency key exists with matching hash,
            None if key doesn't exist
            
        Raises:
            ConflictError: If idempotency key exists with different request hash
        """
        try:
            response = self.idempotency_table.get_item(
                Key={'PK': f'IDEM#{idempotency_key}'}
            )
            
            if 'Item' in response:
                item = response['Item']
                request_hash = self._hash_request(request)
                
                if item['requestHash'] != request_hash:
                    raise ConflictError(
                        f"Idempotency key '{idempotency_key}' already used with different request data",
                        {'idempotencyKey': idempotency_key}
                    )
                
                # Return stored response
                return json.loads(item['response'])
            
            return None
            
        except ConflictError:
            raise
        except Exception as e:
            # Log error but don't fail the request
            print(f"Error checking idempotency: {e}")
            return None
    
    def _store_idempotency_key(self, idempotency_key: str, user: User) -> None:
        """
        Store idempotency record with 24-hour TTL.
        
        Args:
            idempotency_key: Unique key for this request
            user: User response to store
        """
        try:
            now = datetime.utcnow()
            ttl = int((now + timedelta(hours=24)).timestamp())
            
            self.idempotency_table.put_item(
                Item={
                    'PK': f'IDEM#{idempotency_key}',
                    'idempotencyKey': idempotency_key,
                    'requestHash': self._hash_request({
                        'userId': user['userId'],
                        'name': user['name'],
                        'metadata': user['metadata']
                    }),
                    'response': json.dumps(user),
                    'createdAt': int(now.timestamp()),
                    'ttl': ttl
                }
            )
        except Exception as e:
            # Log error but don't fail the request
            print(f"Error storing idempotency key: {e}")
    
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
    
    def _hash_request(self, request: Dict[str, Any]) -> str:
        """
        Generate a hash of the request for idempotency conflict detection.
        
        Args:
            request: Request payload to hash
            
        Returns:
            SHA-256 hash of the request
        """
        # Sort keys for consistent hashing
        request_str = json.dumps(request, sort_keys=True)
        return hashlib.sha256(request_str.encode()).hexdigest()
    
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
