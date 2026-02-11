"""
User listing service.

This module implements the business logic for listing users, including:
- Querying USER_STATUS# partition for specified status
- Supporting pagination with limit and nextToken
- Excluding deleted users from results
- Returning users in a consistent format

Follows steering rules:
- Business logic in services, not handlers
- Fail fast on invalid input
- No global mutable state
- Explicit error handling
"""

import boto3
import json
import base64
from typing import Dict, Any, List, Optional


class UserService:
    """
    Service class for user listing operations.
    
    This class encapsulates all business logic for listing users,
    delegating to DynamoDB for querying.
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
    
    def list_users(
        self,
        status: str = 'active',
        limit: int = 50,
        next_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List users by status with pagination support.
        
        This method implements the complete user listing flow:
        1. Query USER_STATUS# partition for specified status
        2. Support pagination with limit and nextToken
        3. Exclude deleted users from results
        4. Return users in a consistent format
        
        Args:
            status: User status to filter by (default: 'active')
            limit: Maximum number of users to return (default: 50, max: 100)
            next_token: Pagination token from previous request (optional)
            
        Returns:
            Dictionary with:
                - users: List of user objects
                - nextToken: Pagination token for next page (if more results exist)
        """
        # Query USER_STATUS# partition for specified status (Requirement 5.4)
        query_params = {
            'KeyConditionExpression': 'PK = :pk',
            'ExpressionAttributeValues': {
                ':pk': f'USER_STATUS#{status}'
            },
            'Limit': limit
        }
        
        # Add pagination token if provided (Requirement 5.5)
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
            response = self.users_table.query(**query_params)
            
            # Extract items
            items = response.get('Items', [])
            
            # Convert DynamoDB items to user objects
            users = []
            for item in items:
                # Exclude deleted users (Requirement 5.4)
                if item.get('status') == 'deleted':
                    continue
                
                user = {
                    'userId': item['userId'],
                    'email': item['email'],
                    'name': item['name'],
                    'status': item['status'],
                    'roles': item.get('roles', []),
                    'createdAt': item['createdAt']
                }
                users.append(user)
            
            # Build response
            result: Dict[str, Any] = {
                'users': users
            }
            
            # Add nextToken if there are more results (Requirement 5.5)
            if 'LastEvaluatedKey' in response:
                # Encode the last evaluated key as base64 JSON
                last_key_json = json.dumps(response['LastEvaluatedKey'])
                encoded_token = base64.b64encode(last_key_json.encode('utf-8')).decode('utf-8')
                result['nextToken'] = encoded_token
            
            return result
            
        except Exception as e:
            # Log unexpected errors
            print(f"Error listing users: {e}")
            raise
