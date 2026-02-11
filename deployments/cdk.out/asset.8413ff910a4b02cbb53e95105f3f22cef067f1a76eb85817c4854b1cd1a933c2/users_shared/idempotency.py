"""
Idempotency service for user management operations.

This module implements idempotency handling to ensure write operations
are safe against retries. It provides:
- Idempotency key checking
- Request hash calculation for conflict detection
- Idempotency record storage with TTL

Follows steering rules:
- Explicit over implicit
- Fail fast on conflicts
- No global mutable state
"""

import boto3
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from users_shared.errors import ConflictError


class IdempotencyService:
    """
    Service class for idempotency operations.
    
    This class encapsulates all logic for idempotency handling,
    including checking for existing keys, storing new keys, and
    detecting conflicts when keys are reused with different data.
    """
    
    def __init__(self, idempotency_table_name: str):
        """
        Initialize the IdempotencyService.
        
        Args:
            idempotency_table_name: Name of the DynamoDB idempotency table
        """
        self.dynamodb = boto3.resource('dynamodb')
        self.idempotency_table = self.dynamodb.Table(idempotency_table_name)
    
    def check_idempotency(
        self,
        idempotency_key: str,
        request: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Check if this request has already been processed.
        
        If the idempotency key exists:
        - If request hash matches, return the stored response
        - If request hash differs, raise ConflictError
        
        This implements Requirement 11.1 (idempotent creation) and 11.4
        (conflict detection for key reuse with different data).
        
        Args:
            idempotency_key: Unique key for this request
            request: Request payload for hash comparison
            
        Returns:
            Stored response if idempotency key exists with matching hash,
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
                request_hash = self._calculate_request_hash(request)
                
                # Check if request data matches
                if item['requestHash'] != request_hash:
                    raise ConflictError(
                        f"Idempotency key '{idempotency_key}' already used with different request data",
                        {'idempotencyKey': idempotency_key}
                    )
                
                # Return stored response (idempotent retry)
                return json.loads(item['response'])
            
            return None
            
        except ConflictError:
            # Re-raise conflict errors
            raise
        except Exception as e:
            # Log error but don't fail the request
            # Idempotency check failures should not block operations
            print(f"Error checking idempotency: {e}")
            return None
    
    def store_idempotency_key(
        self,
        idempotency_key: str,
        request: Dict[str, Any],
        response: Dict[str, Any]
    ) -> None:
        """
        Store idempotency record with 24-hour TTL.
        
        This implements Requirement 11.3 (maintain keys for minimum 24 hours).
        The TTL attribute enables automatic cleanup after expiration.
        
        Args:
            idempotency_key: Unique key for this request
            request: Request payload to hash for conflict detection
            response: Response to store for idempotent retries
        """
        try:
            now = datetime.utcnow()
            ttl = int((now + timedelta(hours=24)).timestamp())
            
            self.idempotency_table.put_item(
                Item={
                    'PK': f'IDEM#{idempotency_key}',
                    'idempotencyKey': idempotency_key,
                    'requestHash': self._calculate_request_hash(request),
                    'response': json.dumps(response),
                    'createdAt': int(now.timestamp()),
                    'ttl': ttl
                }
            )
        except Exception as e:
            # Log error but don't fail the request
            # Idempotency storage failures should not block operations
            print(f"Error storing idempotency key: {e}")
    
    def _calculate_request_hash(self, request: Dict[str, Any]) -> str:
        """
        Calculate SHA-256 hash of request for conflict detection.
        
        This implements Requirement 11.4 (detect conflicts when idempotency
        key is reused with different request data).
        
        The hash is calculated from a JSON representation of the request
        with sorted keys to ensure consistent hashing regardless of key order.
        
        Args:
            request: Request payload to hash
            
        Returns:
            SHA-256 hash of the request as hexadecimal string
        """
        # Sort keys for consistent hashing
        request_str = json.dumps(request, sort_keys=True)
        return hashlib.sha256(request_str.encode()).hexdigest()
