"""
Unit tests for validation functions.
Tests all validation logic for user management operations.
"""

import pytest
import sys
import os

# Add lambda paths
sys.path.insert(0, 'lambda/users_register_create')
sys.path.insert(0, 'lambda/users_shared')

from validation import validate_registration_request, validate_email_format


class TestRegistrationValidation:
    """Test user registration validation (Requirements 1.5, 7.1-7.5)."""
    
    def test_valid_registration_request(self):
        """Test validation passes for valid request."""
        request = {
            'email': 'user@example.com',
            'name': 'John Doe',
            'idempotencyKey': 'key-123',
            'metadata': {'department': 'Engineering'}
        }
        errors = validate_registration_request(request)
        assert errors == []
    
    def test_missing_email(self):
        """Test validation fails when email is missing (Requirement 7.1)."""
        request = {
            'name': 'John Doe',
            'idempotencyKey': 'key-123'
        }
        errors = validate_registration_request(request)
        assert any(e['field'] == 'email' and 'required' in e['message'].lower() for e in errors)
    
    def test_missing_name(self):
        """Test validation fails when name is missing (Requirement 7.1)."""
        request = {
            'email': 'user@example.com',
            'idempotencyKey': 'key-123'
        }
        errors = validate_registration_request(request)
        assert any(e['field'] == 'name' and 'required' in e['message'].lower() for e in errors)
    
    def test_missing_idempotency_key(self):
        """Test validation fails when idempotencyKey is missing (Requirement 7.1)."""
        request = {
            'email': 'user@example.com',
            'name': 'John Doe'
        }
        errors = validate_registration_request(request)
        assert any(e['field'] == 'idempotencyKey' and 'required' in e['message'].lower() for e in errors)
    
    def test_empty_email(self):
        """Test validation fails for empty email."""
        request = {
            'email': '',
            'name': 'John Doe',
            'idempotencyKey': 'key-123'
        }
        errors = validate_registration_request(request)
        assert any(e['field'] == 'email' for e in errors)
    
    def test_whitespace_only_email(self):
        """Test validation fails for whitespace-only email."""
        request = {
            'email': '   ',
            'name': 'John Doe',
            'idempotencyKey': 'key-123'
        }
        errors = validate_registration_request(request)
        assert any(e['field'] == 'email' for e in errors)
    
    def test_invalid_email_format_no_at(self):
        """Test validation fails for email without @ (Requirement 7.2, 7.3)."""
        request = {
            'email': 'notanemail',
            'name': 'John Doe',
            'idempotencyKey': 'key-123'
        }
        errors = validate_registration_request(request)
        assert any(e['field'] == 'email' and 'format' in e['message'].lower() for e in errors)
    
    def test_invalid_email_format_no_domain(self):
        """Test validation fails for email without domain."""
        request = {
            'email': 'user@',
            'name': 'John Doe',
            'idempotencyKey': 'key-123'
        }
        errors = validate_registration_request(request)
        assert any(e['field'] == 'email' and 'format' in e['message'].lower() for e in errors)
    
    def test_invalid_email_format_no_local_part(self):
        """Test validation fails for email without local part."""
        request = {
            'email': '@example.com',
            'name': 'John Doe',
            'idempotencyKey': 'key-123'
        }
        errors = validate_registration_request(request)
        assert any(e['field'] == 'email' and 'format' in e['message'].lower() for e in errors)
    
    def test_valid_email_formats(self):
        """Test various valid email formats are accepted (Requirement 7.3)."""
        valid_emails = [
            'user@example.com',
            'user.name@example.com',
            'user+tag@example.co.uk',
            'user_name@sub.example.com',
            'user123@example.org',
            'first.last@example.com'
        ]
        
        for email in valid_emails:
            request = {
                'email': email,
                'name': 'John Doe',
                'idempotencyKey': 'key-123'
            }
            errors = validate_registration_request(request)
            assert not any(e['field'] == 'email' for e in errors), f"Email {email} should be valid"
    
    def test_unexpected_fields(self):
        """Test validation fails for unexpected fields (Requirement 7.5)."""
        request = {
            'email': 'user@example.com',
            'name': 'John Doe',
            'idempotencyKey': 'key-123',
            'unexpectedField': 'value'
        }
        errors = validate_registration_request(request)
        assert any(e['field'] == 'unexpectedField' and 'unexpected' in e['message'].lower() for e in errors)
    
    def test_metadata_valid_object(self):
        """Test metadata validation accepts valid object."""
        request = {
            'email': 'user@example.com',
            'name': 'John Doe',
            'idempotencyKey': 'key-123',
            'metadata': {'key1': 'value1', 'key2': 'value2'}
        }
        errors = validate_registration_request(request)
        assert not any(e['field'].startswith('metadata') for e in errors)
    
    def test_metadata_invalid_type(self):
        """Test metadata validation fails for non-object."""
        request = {
            'email': 'user@example.com',
            'name': 'John Doe',
            'idempotencyKey': 'key-123',
            'metadata': 'not an object'
        }
        errors = validate_registration_request(request)
        assert any(e['field'] == 'metadata' for e in errors)
    
    def test_metadata_non_string_values(self):
        """Test metadata validation fails for non-string values."""
        request = {
            'email': 'user@example.com',
            'name': 'John Doe',
            'idempotencyKey': 'key-123',
            'metadata': {'key': 123}
        }
        errors = validate_registration_request(request)
        assert any('metadata' in e['field'] for e in errors)
    
    def test_field_type_validation(self):
        """Test validation fails for incorrect field types."""
        # Email as number
        request = {
            'email': 123,
            'name': 'John Doe',
            'idempotencyKey': 'key-123'
        }
        errors = validate_registration_request(request)
        assert any(e['field'] == 'email' and 'string' in e['message'].lower() for e in errors)
        
        # Name as number
        request = {
            'email': 'user@example.com',
            'name': 123,
            'idempotencyKey': 'key-123'
        }
        errors = validate_registration_request(request)
        assert any(e['field'] == 'name' and 'string' in e['message'].lower() for e in errors)


class TestEmailFormatValidation:
    """Test email format validation function."""
    
    def test_valid_emails(self):
        """Test valid email formats."""
        valid_emails = [
            'user@example.com',
            'user.name@example.com',
            'user+tag@example.com',
            'user_name@example.com',
            'user123@example.com',
            'first.last@sub.example.co.uk'
        ]
        
        for email in valid_emails:
            assert validate_email_format(email), f"Email {email} should be valid"
    
    def test_invalid_emails(self):
        """Test invalid email formats."""
        invalid_emails = [
            'notanemail',
            '@example.com',
            'user@',
            'user space@example.com',
            '',
            None,
            123
        ]
        
        for email in invalid_emails:
            assert not validate_email_format(email), f"Email {email} should be invalid"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
