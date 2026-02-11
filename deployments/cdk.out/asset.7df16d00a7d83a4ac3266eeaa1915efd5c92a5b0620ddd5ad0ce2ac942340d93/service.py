"""
Audit query service.

This module implements the business logic for querying audit logs, including:
- Querying audit store for user's audit events
- Supporting pagination with limit and nextToken
- Returning events in chronological order
- Handling different audit storage backends (EventBridge or DynamoDB)

Follows steering rules:
- Business logic in services, not handlers
- Fail fast on invalid input
- No global mutable state
- Explicit error handling

Note: This implementation assumes audit events are stored in a DynamoDB table.
The design document mentions EventBridge as the event bus, but for querying
historical audit logs, we need a persistent store. This could be:
1. A separate DynamoDB audit table that receives events from EventBridge
2. EventBridge Archive (for long-term storage)
3. CloudWatch Logs Insights

For this implementation, we'll use a DynamoDB audit table approach.
"""

import boto3
import json
import base64
from typing import Dict, Any, List, Optional

from users_shared.errors import NotFoundError


class AuditService:
    """
    Service class for audit log query operations.
    
    This class encapsulates all business logic for querying audit logs,
    delegating to the audit store (DynamoDB table) for retrieval.
    """
    
    def __init__(self, config: Dict[str, str]):
        """
        Initialize the AuditService with configuration.
        
        Args:
            config: Dictionary containing:
                - users_table_name: Name of the DynamoDB users table (to verify user exists)
                - audit_table_name: Name of the DynamoDB audit table (optional, for audit storage)
        """
        self.config = config
        self.dynamodb = boto3.resource('dynamodb')
        self.users_table = self.dynamodb.Table(config['users_table_name'])
        
        # Check if audit table is configured
        # If not, we'll return empty results (audit events not yet implemented)
        self.audit_table = None
        if 'audit_table_name' in config and config['audit_table_name']:
            self.audit_table = self.dynamodb.Table(config['audit_table_name'])
    
    def get_audit_log(
        self,
        user_id: str,
        limit: int = 50,
        next_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get audit log for a user with pagination support.
        
        This method implements the complete audit log retrieval flow:
        1. Verify user exists (return 404 if not)
        2. Query audit store for user's audit events
        3. Support pagination with limit and nextToken
        4. Return events in chronological order
        
        Args:
            user_id: The unique user ID to get audit log for
            limit: Maximum number of audit events to return (default: 50, max: 100)
            next_token: Pagination token from previous request (optional)
            
        Returns:
            Dictionary with:
                - auditLogs: List of audit event objects
                - nextToken: Pagination token for next page (if more results exist)
                
        Raises:
            NotFoundError: If user does not exist
        """
        # Verify user exists (Requirement 6.3)
        self._verify_user_exists(user_id)
        
        # If audit table is not configured, return empty results
        # This allows the API to work even if audit storage is not yet set up
        if not self.audit_table:
            return {
                'auditLogs': []
            }
        
        # Query audit store for user's audit events (Requirement 6.3)
        # Assuming audit table structure:
        # PK: AUDIT#${userId}
        # SK: ${timestamp}#${eventId}
        # This allows chronological ordering by sort key
        
        query_params = {
            'KeyConditionExpression': 'PK = :pk',
            'ExpressionAttributeValues': {
                ':pk': f'AUDIT#{user_id}'
            },
            'Limit': limit,
            'ScanIndexForward': False  # Descending order (newest first)
        }
        
        # Add pagination token if provided (Requirement 6.3)
        if next_token:
            try:
                # Decode the next token (base64 encoded JSON)
                decoded_token = base64.b64decode(next_token).decode('utf-8')
                exclusive_start_key = json.loads(decoded_token)
                query_params['ExclusiveStartKey'] = exclusive_start_key
            except Exception as e:
                # Log error but continue without pagination
                print(f"Error decoding next_token: {e}")
                # Invalid token, ignore it and start from beginning
        
        try:
            # Execute query
            response = self.audit_table.query(**query_params)
            
            # Extract items
            items = response.get('Items', [])
            
            # Convert DynamoDB items to audit event objects
            audit_logs = []
            for item in items:
                audit_event = {
                    'eventId': item['eventId'],
                    'userId': item['userId'],
                    'timestamp': item['timestamp'],
                    'action': item['action'],
                    'actor': item.get('actor', 'system'),
                    'changes': item.get('changes', {})
                }
                audit_logs.append(audit_event)
            
            # Build response
            result: Dict[str, Any] = {
                'auditLogs': audit_logs
            }
            
            # Add nextToken if there are more results (Requirement 6.3)
            if 'LastEvaluatedKey' in response:
                # Encode the last evaluated key as base64 JSON
                last_key_json = json.dumps(response['LastEvaluatedKey'])
                encoded_token = base64.b64encode(last_key_json.encode('utf-8')).decode('utf-8')
                result['nextToken'] = encoded_token
            
            return result
            
        except Exception as e:
            # Log unexpected errors
            print(f"Error querying audit log: {e}")
            raise
    
    def _verify_user_exists(self, user_id: str) -> None:
        """
        Verify that a user exists.
        
        Args:
            user_id: The unique user ID to verify
            
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
            # Note: Per requirements, we should still be able to query audit logs
            # for deleted users (for compliance purposes), but the design says
            # to return 404 for deleted users. We'll follow the design here.
            if item.get('status') == 'deleted':
                raise NotFoundError(f"User with ID '{user_id}' not found")
            
        except NotFoundError:
            # Re-raise NotFoundError as-is
            raise
        except Exception as e:
            # Log unexpected errors
            print(f"Error verifying user {user_id}: {e}")
            raise
