"""
User registration service.

This module implements the business logic for user registration, including:
- Email uniqueness validation
- User creation with ULID generation
- Transactional writes to DynamoDB
- Idempotency handling
- Audit event publishing

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

from users_shared.errors import ConflictError, NotFoundError
from users_shared.types import User, RegistrationRequest


class UserService:
    """
    Service class for user registration operations.
    
    This class encapsulates all business logic for user registration,
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
    
    def register_user(self, request: RegistrationRequest, correlation_id: str) -> User:
        """
        Register a new user.
        
        This method implements the complete user registration flow:
        1. Check idempotency to prevent duplicate registrations
        2. Validate email uniqueness
        3. Generate unique user ID (ULID)
        4. Create user record with initial status 'active'
        5. Write all three DynamoDB items transactionally
        6. Store idempotency record
        7. Publish audit event
        
        Args:
            request: Registration request containing email, name, metadata, and idempotency key
            correlation_id: Request correlation ID for logging and tracing
            
        Returns:
            Created user object
            
        Raises:
            ConflictError: If email already exists or idempotency key conflict
        """
        # Check idempotency first
        existing_response = self._check_idempotency(request['idempotencyKey'], request)
        if existing_response:
            return existing_response
        
        # Check email uniqueness
        existing_user = self._find_user_by_email(request['email'])
        if existing_user:
            raise ConflictError(
                f"Email '{request['email']}' is already registered",
                {'email': request['email']}
            )
        
        # Generate unique user ID using ULID
        user_id = str(ULID())
        now = datetime.utcnow().isoformat() + 'Z'
        
        # Create user object
        user: User = {
            'userId': user_id,
            'email': request['email'],
            'name': request['name'],
            'status': 'active',
            'roles': [],
            'metadata': request.get('metadata', {}),
            'createdAt': now,
            'updatedAt': now
        }
        
        # Write all three items transactionally
        self._write_user_items(user)
        
        # Store idempotency record
        self._store_idempotency_key(request['idempotencyKey'], user)
        
        # Publish audit event
        self._publish_audit_event({
            'userId': user_id,
            'action': 'USER_CREATED',
            'actor': 'system',
            'correlationId': correlation_id,
            'changes': {
                'user': {
                    'before': None,
                    'after': user
                }
            }
        })
        
        return user
    
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
            print(f"Error checking idempotency: {e}", {'correlationId': 'unknown'})
            return None
    
    def _find_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Check if a user with the given email already exists.
        
        Queries the USER_EMAIL# partition to check email uniqueness.
        
        Args:
            email: Email address to check
            
        Returns:
            User data if email exists, None otherwise
        """
        try:
            response = self.users_table.get_item(
                Key={
                    'PK': f'USER_EMAIL#{email}',
                    'SK': 'USER'
                }
            )
            return response.get('Item')
        except Exception as e:
            # Log error but don't fail the request
            print(f"Error checking email uniqueness: {e}")
            return None
    
    def _write_user_items(self, user: User) -> None:
        """
        Write all three user items to DynamoDB in a transaction.
        
        Creates three items:
        1. USER#{userId} / PROFILE - Main user profile
        2. USER_EMAIL#{email} / USER - Email uniqueness index
        3. USER_STATUS#{status} / USER#{userId} - Status index for listing
        
        Args:
            user: User object to write
            
        Raises:
            Exception: If transactional write fails
        """
        try:
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
                                'roles': {'L': []},
                                'metadata': {'M': {k: {'S': v} for k, v in user['metadata'].items()}},
                                'createdAt': {'S': user['createdAt']},
                                'updatedAt': {'S': user['updatedAt']},
                                'entityType': {'S': 'USER_PROFILE'}
                            },
                            'ConditionExpression': 'attribute_not_exists(PK)'
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
                            },
                            'ConditionExpression': 'attribute_not_exists(PK)'
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
                                'roles': {'L': []},
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
                    'requestHash': self._hash_request({'email': user['email'], 'name': user['name']}),
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
