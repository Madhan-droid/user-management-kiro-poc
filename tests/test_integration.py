"""
Integration tests for User Management Service.

Tests the complete flow of all Lambda functions with real AWS services.
Requires AWS credentials and deployed infrastructure.
"""

import pytest
import json
import time
from datetime import datetime
from typing import Dict, Any
import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import requests

# Test configuration
API_ENDPOINT = "https://ac9a51tp48.execute-api.ap-south-1.amazonaws.com/prod"
REGION = "ap-south-1"


class TestUserRegistration:
    """Integration tests for user registration (Requirement 1)."""
    
    def setup_method(self):
        """Setup for each test."""
        self.session = boto3.Session()
        self.credentials = self.session.get_credentials()
        self.test_email = f"test-{int(time.time())}@example.com"
        self.idempotency_key = f"test-key-{int(time.time())}"
    
    def _sign_request(self, method: str, url: str, body: str = None) -> requests.Response:
        """Sign and send AWS SigV4 authenticated request."""
        request = AWSRequest(method=method, url=url, data=body)
        SigV4Auth(self.credentials, "execute-api", REGION).add_auth(request)
        return requests.request(
            method=method,
            url=url,
            headers=dict(request.headers),
            data=body
        )
    
    def test_create_user_success(self):
        """Test successful user creation (Requirement 1.1)."""
        # Arrange
        payload = {
            "email": self.test_email,
            "name": "Test User",
            "idempotencyKey": self.idempotency_key,
            "metadata": {"department": "Engineering"}
        }
        
        # Act
        response = self._sign_request(
            "POST",
            f"{API_ENDPOINT}/users",
            json.dumps(payload)
        )
        
        # Assert
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "userId" in data
        assert data["email"] == self.test_email
        assert data["name"] == "Test User"
        assert data["status"] == "active"
        assert data["roles"] == []
        assert data["metadata"]["department"] == "Engineering"
        assert "createdAt" in data
        assert "updatedAt" in data
    
    def test_email_uniqueness(self):
        """Test email uniqueness constraint (Requirement 1.2)."""
        # Arrange - Create first user
        payload1 = {
            "email": self.test_email,
            "name": "First User",
            "idempotencyKey": self.idempotency_key
        }
        response1 = self._sign_request("POST", f"{API_ENDPOINT}/users", json.dumps(payload1))
        assert response1.status_code == 201
        
        # Act - Try to create second user with same email
        payload2 = {
            "email": self.test_email,
            "name": "Second User",
            "idempotencyKey": f"{self.idempotency_key}-2"
        }
        response2 = self._sign_request("POST", f"{API_ENDPOINT}/users", json.dumps(payload2))
        
        # Assert
        assert response2.status_code == 409, f"Expected 409, got {response2.status_code}"
        error = response2.json()
        assert error["code"] == "CONFLICT"
        assert "email" in error["message"].lower()
    
    def test_idempotency_same_request(self):
        """Test idempotency with same request (Requirement 1.3)."""
        # Arrange
        payload = {
            "email": self.test_email,
            "name": "Test User",
            "idempotencyKey": self.idempotency_key
        }
        
        # Act - Send same request twice
        response1 = self._sign_request("POST", f"{API_ENDPOINT}/users", json.dumps(payload))
        response2 = self._sign_request("POST", f"{API_ENDPOINT}/users", json.dumps(payload))
        
        # Assert
        assert response1.status_code == 201
        assert response2.status_code == 201
        
        data1 = response1.json()
        data2 = response2.json()
        
        # Should return same user
        assert data1["userId"] == data2["userId"]
        assert data1["email"] == data2["email"]
    
    def test_idempotency_different_request(self):
        """Test idempotency key conflict with different data (Requirement 1.4)."""
        # Arrange - Create first user
        payload1 = {
            "email": self.test_email,
            "name": "First Name",
            "idempotencyKey": self.idempotency_key
        }
        response1 = self._sign_request("POST", f"{API_ENDPOINT}/users", json.dumps(payload1))
        assert response1.status_code == 201
        
        # Act - Try same idempotency key with different data
        payload2 = {
            "email": f"different-{self.test_email}",
            "name": "Different Name",
            "idempotencyKey": self.idempotency_key
        }
        response2 = self._sign_request("POST", f"{API_ENDPOINT}/users", json.dumps(payload2))
        
        # Assert
        assert response2.status_code == 409
        error = response2.json()
        assert error["code"] == "CONFLICT"
        assert "idempotency" in error["message"].lower()
    
    def test_missing_required_fields(self):
        """Test validation for missing required fields (Requirement 1.5, 7.1)."""
        # Test missing email
        payload = {
            "name": "Test User",
            "idempotencyKey": self.idempotency_key
        }
        response = self._sign_request("POST", f"{API_ENDPOINT}/users", json.dumps(payload))
        assert response.status_code == 400
        error = response.json()
        assert error["code"] == "VALIDATION_ERROR"
        
        # Test missing name
        payload = {
            "email": self.test_email,
            "idempotencyKey": self.idempotency_key
        }
        response = self._sign_request("POST", f"{API_ENDPOINT}/users", json.dumps(payload))
        assert response.status_code == 400
        
        # Test missing idempotencyKey
        payload = {
            "email": self.test_email,
            "name": "Test User"
        }
        response = self._sign_request("POST", f"{API_ENDPOINT}/users", json.dumps(payload))
        assert response.status_code == 400
    
    def test_invalid_email_format(self):
        """Test email format validation (Requirement 7.2, 7.3)."""
        invalid_emails = [
            "not-an-email",
            "@example.com",
            "user@",
            "user space@example.com",
            ""
        ]
        
        for invalid_email in invalid_emails:
            payload = {
                "email": invalid_email,
                "name": "Test User",
                "idempotencyKey": f"{self.idempotency_key}-{invalid_email}"
            }
            response = self._sign_request("POST", f"{API_ENDPOINT}/users", json.dumps(payload))
            assert response.status_code == 400, f"Email '{invalid_email}' should be invalid"


class TestUserProfile:
    """Integration tests for user profile operations (Requirements 2)."""
    
    def setup_method(self):
        """Setup for each test - create a test user."""
        self.session = boto3.Session()
        self.credentials = self.session.get_credentials()
        self.test_email = f"test-{int(time.time())}@example.com"
        self.idempotency_key = f"test-key-{int(time.time())}"
        
        # Create test user
        payload = {
            "email": self.test_email,
            "name": "Test User",
            "idempotencyKey": self.idempotency_key
        }
        response = self._sign_request("POST", f"{API_ENDPOINT}/users", json.dumps(payload))
        assert response.status_code == 201
        self.user_id = response.json()["userId"]
    
    def _sign_request(self, method: str, url: str, body: str = None) -> requests.Response:
        """Sign and send AWS SigV4 authenticated request."""
        request = AWSRequest(method=method, url=url, data=body)
        SigV4Auth(self.credentials, "execute-api", REGION).add_auth(request)
        return requests.request(
            method=method,
            url=url,
            headers=dict(request.headers),
            data=body
        )
    
    def test_get_user_profile(self):
        """Test retrieving user profile (Requirement 2.1)."""
        # Act
        response = self._sign_request("GET", f"{API_ENDPOINT}/users/{self.user_id}")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["userId"] == self.user_id
        assert data["email"] == self.test_email
        assert data["name"] == "Test User"
    
    def test_get_nonexistent_user(self):
        """Test getting non-existent user (Requirement 2.2)."""
        # Act
        response = self._sign_request("GET", f"{API_ENDPOINT}/users/01HXXX0000000000000000")
        
        # Assert
        assert response.status_code == 404
        error = response.json()
        assert error["code"] == "NOT_FOUND"
    
    def test_update_user_profile(self):
        """Test updating user profile (Requirement 2.3)."""
        # Arrange
        payload = {
            "name": "Updated Name",
            "metadata": {"department": "Sales"},
            "idempotencyKey": f"{self.idempotency_key}-update"
        }
        
        # Act
        response = self._sign_request(
            "PUT",
            f"{API_ENDPOINT}/users/{self.user_id}",
            json.dumps(payload)
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["metadata"]["department"] == "Sales"
        assert data["updatedAt"] > data["createdAt"]


class TestUserStatus:
    """Integration tests for user status management (Requirements 3)."""
    
    def setup_method(self):
        """Setup for each test - create a test user."""
        self.session = boto3.Session()
        self.credentials = self.session.get_credentials()
        self.test_email = f"test-{int(time.time())}@example.com"
        self.idempotency_key = f"test-key-{int(time.time())}"
        
        # Create test user
        payload = {
            "email": self.test_email,
            "name": "Test User",
            "idempotencyKey": self.idempotency_key
        }
        response = self._sign_request("POST", f"{API_ENDPOINT}/users", json.dumps(payload))
        assert response.status_code == 201
        self.user_id = response.json()["userId"]
    
    def _sign_request(self, method: str, url: str, body: str = None) -> requests.Response:
        """Sign and send AWS SigV4 authenticated request."""
        request = AWSRequest(method=method, url=url, data=body)
        SigV4Auth(self.credentials, "execute-api", REGION).add_auth(request)
        return requests.request(
            method=method,
            url=url,
            headers=dict(request.headers),
            data=body
        )
    
    def test_update_status_to_disabled(self):
        """Test updating user status to disabled (Requirement 3.1, 3.2)."""
        # Act
        payload = {"status": "disabled"}
        response = self._sign_request(
            "PUT",
            f"{API_ENDPOINT}/users/{self.user_id}/status",
            json.dumps(payload)
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "disabled"
    
    def test_update_status_to_deleted(self):
        """Test updating user status to deleted (Requirement 3.1, 3.2)."""
        # Act
        payload = {"status": "deleted"}
        response = self._sign_request(
            "PUT",
            f"{API_ENDPOINT}/users/{self.user_id}/status",
            json.dumps(payload)
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"
    
    def test_invalid_status_value(self):
        """Test invalid status value (Requirement 3.6)."""
        # Act
        payload = {"status": "invalid-status"}
        response = self._sign_request(
            "PUT",
            f"{API_ENDPOINT}/users/{self.user_id}/status",
            json.dumps(payload)
        )
        
        # Assert
        assert response.status_code == 400
        error = response.json()
        assert error["code"] == "VALIDATION_ERROR"


class TestUserRoles:
    """Integration tests for role management (Requirements 4)."""
    
    def setup_method(self):
        """Setup for each test - create a test user."""
        self.session = boto3.Session()
        self.credentials = self.session.get_credentials()
        self.test_email = f"test-{int(time.time())}@example.com"
        self.idempotency_key = f"test-key-{int(time.time())}"
        
        # Create test user
        payload = {
            "email": self.test_email,
            "name": "Test User",
            "idempotencyKey": self.idempotency_key
        }
        response = self._sign_request("POST", f"{API_ENDPOINT}/users", json.dumps(payload))
        assert response.status_code == 201
        self.user_id = response.json()["userId"]
    
    def _sign_request(self, method: str, url: str, body: str = None) -> requests.Response:
        """Sign and send AWS SigV4 authenticated request."""
        request = AWSRequest(method=method, url=url, data=body)
        SigV4Auth(self.credentials, "execute-api", REGION).add_auth(request)
        return requests.request(
            method=method,
            url=url,
            headers=dict(request.headers),
            data=body
        )
    
    def test_assign_role(self):
        """Test assigning role to user (Requirement 4.1)."""
        # Act
        payload = {"role": "admin"}
        response = self._sign_request(
            "POST",
            f"{API_ENDPOINT}/users/{self.user_id}/roles",
            json.dumps(payload)
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "admin" in data["roles"]
    
    def test_assign_multiple_roles(self):
        """Test assigning multiple roles (Requirement 4.3)."""
        # Assign first role
        payload1 = {"role": "admin"}
        response1 = self._sign_request(
            "POST",
            f"{API_ENDPOINT}/users/{self.user_id}/roles",
            json.dumps(payload1)
        )
        assert response1.status_code == 200
        
        # Assign second role
        payload2 = {"role": "editor"}
        response2 = self._sign_request(
            "POST",
            f"{API_ENDPOINT}/users/{self.user_id}/roles",
            json.dumps(payload2)
        )
        assert response2.status_code == 200
        
        data = response2.json()
        assert "admin" in data["roles"]
        assert "editor" in data["roles"]
    
    def test_remove_role(self):
        """Test removing role from user (Requirement 4.2)."""
        # Arrange - Assign role first
        payload = {"role": "admin"}
        self._sign_request(
            "POST",
            f"{API_ENDPOINT}/users/{self.user_id}/roles",
            json.dumps(payload)
        )
        
        # Act - Remove role
        response = self._sign_request(
            "DELETE",
            f"{API_ENDPOINT}/users/{self.user_id}/roles/admin"
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "admin" not in data["roles"]


class TestUserListing:
    """Integration tests for user listing (Requirements 5)."""
    
    def setup_method(self):
        """Setup for each test."""
        self.session = boto3.Session()
        self.credentials = self.session.get_credentials()
    
    def _sign_request(self, method: str, url: str, body: str = None) -> requests.Response:
        """Sign and send AWS SigV4 authenticated request."""
        request = AWSRequest(method=method, url=url, data=body)
        SigV4Auth(self.credentials, "execute-api", REGION).add_auth(request)
        return requests.request(
            method=method,
            url=url,
            headers=dict(request.headers),
            data=body
        )
    
    def test_list_users_default(self):
        """Test listing users with default parameters (Requirement 5.4)."""
        # Act
        response = self._sign_request("GET", f"{API_ENDPOINT}/users")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert isinstance(data["users"], list)
    
    def test_list_users_with_limit(self):
        """Test listing users with limit parameter (Requirement 5.5)."""
        # Act
        response = self._sign_request("GET", f"{API_ENDPOINT}/users?limit=10")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["users"]) <= 10
    
    def test_list_users_by_status(self):
        """Test listing users filtered by status (Requirement 5.4)."""
        # Act
        response = self._sign_request("GET", f"{API_ENDPOINT}/users?status=active")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        for user in data["users"]:
            assert user["status"] == "active"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
