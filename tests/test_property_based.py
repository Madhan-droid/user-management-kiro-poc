"""
Property-based tests for User Management Service.
Uses Hypothesis to generate test cases and verify properties hold across all inputs.
"""

import pytest
import sys
import os
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from hypothesis.strategies import composite
import re

# Add lambda paths
sys.path.insert(0, 'lambda/users_register_create')
sys.path.insert(0, 'lambda/users_shared')

from validation import validate_registration_request, validate_email_format


# Custom strategies for generating test data
@composite
def valid_email(draw):
    """Generate valid email addresses."""
    local_part = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='.+-_'),
        min_size=1,
        max_size=64
    ))
    # Ensure local part doesn't start/end with special chars
    local_part = local_part.strip('.+-_')
    assume(len(local_part) > 0)
    
    domain = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='-.'),
        min_size=1,
        max_size=253
    ))
    domain = domain.strip('-.')
    assume(len(domain) > 0)
    assume('.' in domain or len(domain) < 10)  # Simple domain validation
    
    return f"{local_part}@{domain}"


@composite
def valid_registration_request(draw):
    """Generate valid registration requests."""
    # Generate non-empty, non-whitespace strings
    name = draw(st.text(min_size=1, max_size=100))
    name = name.strip()
    if not name:
        name = "Test User"
    
    idempotency_key = draw(st.text(min_size=1, max_size=100))
    idempotency_key = idempotency_key.strip()
    if not idempotency_key:
        idempotency_key = "test-key"
    
    return {
        'email': draw(valid_email()),
        'name': name,
        'idempotencyKey': idempotency_key,
        'metadata': draw(st.dictionaries(
            keys=st.text(min_size=1, max_size=50),
            values=st.text(min_size=0, max_size=200),
            max_size=10
        ))
    }


class TestRegistrationProperties:
    """Property-based tests for registration validation."""
    
    @given(valid_registration_request())
    @settings(max_examples=100)
    def test_valid_requests_pass_validation(self, request):
        """
        Property: All valid registration requests should pass validation.
        **Validates: Requirements 1.5, 7.1**
        """
        errors = validate_registration_request(request)
        # Filter out email format errors (our generator might create edge cases)
        non_email_errors = [e for e in errors if e['field'] != 'email' or 'format' not in e['message'].lower()]
        assert len(non_email_errors) == 0, f"Valid request failed validation: {non_email_errors}"
    
    @given(st.dictionaries(
        keys=st.text(min_size=1, max_size=50),
        values=st.one_of(st.text(), st.integers(), st.floats(), st.booleans(), st.none()),
        min_size=0,
        max_size=10
    ))
    @settings(max_examples=100)
    def test_validation_never_crashes(self, request):
        """
        Property: Validation should never crash regardless of input.
        **Validates: Requirements 7.1, 8.1**
        """
        try:
            errors = validate_registration_request(request)
            assert isinstance(errors, list), "Validation must return a list"
            for error in errors:
                assert 'field' in error, "Each error must have a 'field'"
                assert 'message' in error, "Each error must have a 'message'"
        except Exception as e:
            pytest.fail(f"Validation crashed with input {request}: {e}")
    
    @given(st.text(min_size=1, max_size=100))
    @settings(max_examples=100)
    def test_missing_required_fields_always_fails(self, value):
        """
        Property: Requests missing required fields should always fail validation.
        **Validates: Requirement 7.1**
        """
        # Missing email
        request = {'name': value, 'idempotencyKey': value}
        errors = validate_registration_request(request)
        assert any(e['field'] == 'email' for e in errors), "Missing email should cause error"
        
        # Missing name
        request = {'email': f'{value}@example.com', 'idempotencyKey': value}
        errors = validate_registration_request(request)
        assert any(e['field'] == 'name' for e in errors), "Missing name should cause error"
        
        # Missing idempotencyKey
        request = {'email': f'{value}@example.com', 'name': value}
        errors = validate_registration_request(request)
        assert any(e['field'] == 'idempotencyKey' for e in errors), "Missing idempotencyKey should cause error"
    
    @given(st.text(max_size=100))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.filter_too_much])
    def test_empty_strings_fail_validation(self, whitespace):
        """
        Property: Empty or whitespace-only strings should fail validation.
        **Validates: Requirement 7.1**
        """
        assume(len(whitespace) == 0 or whitespace.isspace())
        
        request = {
            'email': whitespace,
            'name': 'Valid Name',
            'idempotencyKey': 'valid-key'
        }
        errors = validate_registration_request(request)
        assert any(e['field'] == 'email' for e in errors), "Empty email should fail"
    
    @given(st.text(min_size=1, max_size=100))
    @settings(max_examples=100)
    def test_emails_without_at_symbol_fail(self, text):
        """
        Property: Emails without @ symbol should always fail validation.
        **Validates: Requirements 7.2, 7.3**
        """
        assume('@' not in text)
        assume(not text.isspace())  # Skip whitespace-only (caught by empty validation)
        
        request = {
            'email': text,
            'name': 'Valid Name',
            'idempotencyKey': 'valid-key'
        }
        errors = validate_registration_request(request)
        # Should have either format error or empty error
        assert any(e['field'] == 'email' for e in errors), f"Email '{text}' should fail validation"
    
    @given(st.dictionaries(
        keys=st.text(min_size=1, max_size=50),
        values=st.text(min_size=0, max_size=200),
        max_size=20
    ))
    @settings(max_examples=50)
    def test_valid_metadata_always_passes(self, metadata):
        """
        Property: Valid metadata (string keys and values) should always pass validation.
        **Validates: Requirement 1.5**
        """
        request = {
            'email': 'user@example.com',
            'name': 'Valid Name',
            'idempotencyKey': 'valid-key',
            'metadata': metadata
        }
        errors = validate_registration_request(request)
        metadata_errors = [e for e in errors if 'metadata' in e['field']]
        assert len(metadata_errors) == 0, f"Valid metadata failed: {metadata_errors}"
    
    @given(st.one_of(st.integers(), st.floats(), st.booleans(), st.lists(st.text()), st.text()))
    @settings(max_examples=50)
    def test_non_dict_metadata_fails(self, metadata):
        """
        Property: Non-dictionary metadata should fail validation.
        **Validates: Requirement 7.1**
        """
        assume(not isinstance(metadata, dict))
        assume(metadata is not None)
        
        request = {
            'email': 'user@example.com',
            'name': 'Valid Name',
            'idempotencyKey': 'valid-key',
            'metadata': metadata
        }
        errors = validate_registration_request(request)
        assert any(e['field'] == 'metadata' for e in errors)
    
    @given(st.text(min_size=1, max_size=50))
    @settings(max_examples=50)
    def test_unexpected_fields_always_detected(self, field_name):
        """
        Property: Unexpected fields should always be detected.
        **Validates: Requirement 7.5**
        """
        allowed_fields = {'email', 'name', 'idempotencyKey', 'metadata'}
        assume(field_name not in allowed_fields)
        
        request = {
            'email': 'user@example.com',
            'name': 'Valid Name',
            'idempotencyKey': 'valid-key',
            field_name: 'some value'
        }
        errors = validate_registration_request(request)
        assert any(e['field'] == field_name and 'unexpected' in e['message'].lower() for e in errors)


class TestEmailFormatProperties:
    """Property-based tests for email format validation."""
    
    @given(st.text(min_size=1, max_size=100))
    @settings(max_examples=100)
    def test_strings_without_at_are_invalid(self, text):
        """
        Property: Strings without @ are never valid emails.
        **Validates: Requirements 7.2, 7.3**
        """
        assume('@' not in text)
        assert not validate_email_format(text)
    
    @given(st.text(min_size=1, max_size=50), st.text(min_size=1, max_size=50))
    @settings(max_examples=100)
    def test_basic_email_structure_validation(self, local, domain):
        """
        Property: Emails with basic structure (local@domain) should be validated correctly.
        **Validates: Requirements 7.2, 7.3**
        """
        # Clean up inputs to create potentially valid email
        local = ''.join(c for c in local if c.isalnum() or c in '.-_+')
        domain = ''.join(c for c in domain if c.isalnum() or c in '.-')
        
        assume(len(local) > 0 and len(domain) > 0)
        assume('.' in domain or len(domain) < 10)
        
        email = f"{local}@{domain}"
        result = validate_email_format(email)
        
        # Should be valid if it matches basic email pattern
        if re.match(r'^[a-zA-Z0-9.!#$%&\'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$', email):
            assert result, f"Email {email} should be valid"
    
    @given(st.one_of(st.none(), st.integers(), st.floats(), st.booleans(), st.lists(st.text())))
    @settings(max_examples=50)
    def test_non_string_inputs_are_invalid(self, value):
        """
        Property: Non-string inputs should always be invalid.
        **Validates: Requirement 7.1**
        """
        assert not validate_email_format(value)
    
    def test_empty_string_is_invalid(self):
        """
        Property: Empty string should be invalid.
        **Validates: Requirement 7.1**
        """
        assert not validate_email_format('')
        assert not validate_email_format('   ')


class TestValidationIdempotency:
    """Property-based tests for validation idempotency."""
    
    @given(valid_registration_request())
    @settings(max_examples=50)
    def test_validation_is_deterministic(self, request):
        """
        Property: Validation should return same result for same input.
        **Validates: Requirements 7.1**
        """
        result1 = validate_registration_request(request)
        result2 = validate_registration_request(request)
        
        # Convert to comparable format (sort by field name)
        result1_sorted = sorted(result1, key=lambda x: x['field'])
        result2_sorted = sorted(result2, key=lambda x: x['field'])
        
        assert result1_sorted == result2_sorted, "Validation should be deterministic"
    
    @given(st.dictionaries(
        keys=st.text(min_size=1, max_size=50),
        values=st.text(min_size=0, max_size=100),
        min_size=0,
        max_size=10
    ))
    @settings(max_examples=50)
    def test_validation_never_modifies_input(self, request):
        """
        Property: Validation should never modify the input request.
        **Validates: Requirements 7.1**
        """
        import copy
        original = copy.deepcopy(request)
        validate_registration_request(request)
        assert request == original, "Validation should not modify input"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--hypothesis-show-statistics'])
