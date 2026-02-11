# Implementation Plan: User Management Service

## Overview

This implementation plan breaks down the User Management Service into discrete coding tasks. The service will be implemented using Python for both Lambda functions (in `lambda/users/`) and CDK infrastructure (in `deployments/`). Each task builds incrementally, with testing integrated throughout to validate correctness early.

## Tasks

- [x] 1. Set up project structure and shared utilities
  - Create directory structure: `lambda/users/shared/`, `lambda/users/register/`, `lambda/users/profile/`, `lambda/users/status/`, `lambda/users/roles/`, `lambda/users/list/`, `lambda/users/audit/`
  - Create shared Python types in `lambda/users/shared/types.py` (User, UserStatus, request/response TypedDicts)
  - Create shared error classes in `lambda/users/shared/errors.py` (DomainError, ValidationError, NotFoundError, ConflictError)
  - Create shared response helpers in `lambda/users/shared/responses.py` (create_success_response, create_error_response)
  - Set up requirements.txt with dependencies: boto3, python-ulid, hypothesis (for testing)
  - Create __init__.py files in all directories for proper Python module structure
  - _Requirements: 8.1, 8.2, 8.3, 8.4_

- [ ]* 1.1 Write unit tests for shared utilities
  - Test error response formatting matches API contract
  - Test success response formatting
  - Test domain error classes
  - _Requirements: 8.1_

- [ ] 2. Implement user registration Lambda
  - [x] 2.1 Create registration service class
    - Implement `UserService.register_user()` method in `lambda/users/register/service.py`
    - Implement email uniqueness check (query USER_EMAIL# partition)
    - Implement user creation with ULID generation
    - Implement transactional write for all three items (USER#, USER_EMAIL#, USER_STATUS#)
    - Implement idempotency check and storage
    - Implement audit event publishing to EventBridge
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 10.1, 10.3, 10.4, 11.1_
  
  - [x] 2.2 Create registration validation
    - Implement `validate_registration_request()` in `lambda/users/register/validation.py`
    - Validate required fields (email, name, idempotencyKey)
    - Validate email format using regex
    - Validate no unexpected fields present
    - _Requirements: 1.5, 7.1, 7.2, 7.3, 7.5_
  
  - [x] 2.3 Create registration handler
    - Implement Lambda handler in `lambda/users/register/handler.py`
    - Load and validate environment variables at startup (USERS_TABLE_NAME, IDEMPOTENCY_TABLE_NAME, EVENT_BUS_NAME)
    - Parse request body and validate input
    - Call service layer and map errors to HTTP responses
    - Log request lifecycle with correlation ID
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 12.1, 12.2_
  
  - [ ]* 2.4 Write property test for user registration
    - **Property 1: User Creation Generates Unique IDs**
    - **Property 2: Email Uniqueness Enforcement**
    - **Property 3: New Users Start Active**
    - **Validates: Requirements 1.1, 1.2, 1.3**
  
  - [ ]* 2.5 Write property test for registration validation
    - **Property 4: Invalid Registration Requests Are Rejected**
    - **Validates: Requirements 1.5, 7.1, 7.2, 7.3, 7.5**
  
  - [ ]* 2.6 Write property test for audit events
    - **Property 14: All Changes Generate Audit Events**
    - **Validates: Requirements 1.4, 6.1, 6.5**

- [ ] 3. Implement user profile retrieval Lambda
  - [x] 3.1 Create profile retrieval service
    - Implement `UserService.get_user_by_id()` in `lambda/users/profile/service.py`
    - Query USER# partition with PROFILE sort key
    - Handle non-existent users (raise NotFoundError)
    - Handle deleted users (raise NotFoundError)
    - _Requirements: 5.1, 5.2, 5.3_
  
  - [x] 3.2 Create profile retrieval handler
    - Implement Lambda handler in `lambda/users/profile/get_handler.py`
    - Extract userId from path parameters
    - Call service layer and map errors to HTTP responses
    - Log request lifecycle with correlation ID
    - _Requirements: 5.1, 5.2, 5.3, 12.1, 12.2_
  
  - [ ]* 3.3 Write property tests for user retrieval
    - **Property 6: Operations on Non-Existent Users Fail**
    - **Property 9: Deleted Users Are Soft Deleted**
    - **Validates: Requirements 5.1, 5.2, 5.3**

- [ ] 4. Implement user profile update Lambda
  - [x] 4.1 Create profile update service
    - Implement `UserService.update_user_profile()` in `lambda/users/profile/service.py`
    - Check idempotency key
    - Retrieve existing user
    - Validate User_ID is not being modified
    - Apply updates to user record
    - Update all three items in transaction (USER#, USER_EMAIL# if email changed, USER_STATUS#)
    - Publish audit event with before/after values
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 10.1, 10.5, 11.2_
  
  - [x] 4.2 Create profile update validation
    - Implement `validate_update_request()` in `lambda/users/profile/validation.py`
    - Validate idempotencyKey is present
    - Validate userId is not in request body
    - Validate at least one field is being updated
    - Validate no unexpected fields
    - _Requirements: 2.4, 2.5, 7.1, 7.5_
  
  - [x] 4.3 Create profile update handler
    - Implement Lambda handler in `lambda/users/profile/update_handler.py`
    - Extract userId from path parameters
    - Parse and validate request body
    - Call service layer and map errors to HTTP responses
    - Log request lifecycle with correlation ID
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 12.1, 12.2_
  
  - [ ]* 4.4 Write property tests for profile updates
    - **Property 5: Profile Updates Persist Changes**
    - **Property 7: User_ID Is Immutable**
    - **Property 15: Audit Events Contain Before/After Values**
    - **Validates: Requirements 2.1, 2.3, 2.4, 10.1, 10.5**
  
  - [ ]* 4.5 Write property test for update idempotency
    - **Property 20: Idempotent User Updates**
    - **Validates: Requirements 11.2**

- [x] 5. Checkpoint - Ensure core user operations work
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. Implement user status management Lambda
  - [x] 6.1 Create status update service
    - Implement `UserService.update_user_status()` in `lambda/users/status/service.py`
    - Retrieve existing user
    - Validate status transition (active/disabled/deleted)
    - Update user status in all three items (USER#, USER_STATUS# - move between partitions)
    - Publish audit event with status change
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_
  
  - [x] 6.2 Create status update validation
    - Implement `validate_status_request()` in `lambda/users/status/validation.py`
    - Validate status is one of: active, disabled, deleted
    - _Requirements: 3.1, 3.2, 3.6, 7.1_
  
  - [x] 6.3 Create status update handler
    - Implement Lambda handler in `lambda/users/status/handler.py`
    - Extract userId from path parameters
    - Parse and validate request body
    - Call service layer and map errors to HTTP responses
    - Log request lifecycle with correlation ID
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 12.1, 12.2_
  
  - [ ]* 6.4 Write property tests for status transitions
    - **Property 8: Status Transitions Work Correctly**
    - **Property 9: Deleted Users Are Soft Deleted**
    - **Validates: Requirements 3.1, 3.2, 3.5, 3.6, 5.3**

- [ ] 7. Implement role assignment Lambda
  - [x] 7.1 Create role assignment service
    - Implement `UserService.assign_role()` in `lambda/users/roles/service.py`
    - Retrieve existing user
    - Validate role name (non-empty, valid format)
    - Add role to user's roles list (if not already present)
    - Update user record in USER# and USER_STATUS# items
    - Publish audit event with role assignment
    - _Requirements: 4.1, 4.3, 4.4, 4.5_
  
  - [x] 7.2 Create role assignment validation
    - Implement `validate_role_request()` in `lambda/users/roles/validation.py`
    - Validate role field is present and non-empty
    - _Requirements: 4.5, 7.1_
  
  - [x] 7.3 Create role assignment handler
    - Implement Lambda handler in `lambda/users/roles/assign_handler.py`
    - Extract userId from path parameters
    - Parse and validate request body
    - Call service layer and map errors to HTTP responses
    - Log request lifecycle with correlation ID
    - _Requirements: 4.1, 4.3, 4.4, 4.5, 12.1, 12.2_
  
  - [ ]* 7.4 Write property tests for role assignment
    - **Property 10: Role Assignment and Removal**
    - **Property 11: Invalid Role Operations Fail**
    - **Validates: Requirements 4.1, 4.5, 4.6**

- [ ] 8. Implement role removal Lambda
  - [x] 8.1 Create role removal service
    - Implement `UserService.remove_role()` in `lambda/users/roles/service.py`
    - Retrieve existing user
    - Remove role from user's roles list
    - Update user record in USER# and USER_STATUS# items
    - Publish audit event with role removal
    - _Requirements: 4.2, 4.3, 4.4_
  
  - [x] 8.2 Create role removal handler
    - Implement Lambda handler in `lambda/users/roles/remove_handler.py`
    - Extract userId and role from path parameters
    - Call service layer and map errors to HTTP responses
    - Log request lifecycle with correlation ID
    - _Requirements: 4.2, 4.3, 4.4, 12.1, 12.2_

- [ ] 9. Implement user listing Lambda
  - [x] 9.1 Create user listing service
    - Implement `UserService.list_users()` in `lambda/users/list/service.py`
    - Query USER_STATUS# partition for specified status (default: active)
    - Support pagination with limit and nextToken
    - Exclude deleted users from results
    - _Requirements: 5.4, 5.5_
  
  - [x] 9.2 Create user listing validation
    - Implement `validate_list_request()` in `lambda/users/list/validation.py`
    - Validate limit is between 1 and 100 (default: 50)
    - Validate status is one of: active, disabled (if provided)
    - _Requirements: 5.4, 5.5, 7.1_
  
  - [x] 9.3 Create user listing handler
    - Implement Lambda handler in `lambda/users/list/handler.py`
    - Extract query parameters (limit, nextToken, status)
    - Validate query parameters
    - Call service layer and map errors to HTTP responses
    - Log request lifecycle with correlation ID
    - _Requirements: 5.4, 5.5, 12.1, 12.2_
  
  - [ ]* 9.4 Write property tests for user listing
    - **Property 12: List Users Excludes Deleted**
    - **Property 13: Pagination Works Correctly**
    - **Validates: Requirements 5.4, 5.5**

- [ ] 10. Implement audit log retrieval Lambda
  - [x] 10.1 Create audit query service
    - Implement `AuditService.get_audit_log()` in `lambda/users/audit/service.py`
    - Query audit store (EventBridge or separate DynamoDB table) for user's audit events
    - Support pagination with limit and nextToken
    - Return events in chronological order
    - _Requirements: 6.3_
  
  - [x] 10.2 Create audit query validation
    - Implement `validate_audit_request()` in `lambda/users/audit/validation.py`
    - Validate limit is between 1 and 100 (default: 50)
    - _Requirements: 6.3, 7.1_
  
  - [x] 10.3 Create audit query handler
    - Implement Lambda handler in `lambda/users/audit/handler.py`
    - Extract userId from path parameters and query parameters
    - Validate query parameters
    - Call service layer and map errors to HTTP responses
    - Log request lifecycle with correlation ID
    - _Requirements: 6.3, 12.1, 12.2_
  
  - [ ]* 10.4 Write property test for audit log ordering
    - **Property 16: Audit Logs Are Chronologically Ordered**
    - **Validates: Requirements 6.3**

- [x] 11. Checkpoint - Ensure all Lambda functions work
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 12. Implement idempotency handling
  - [x] 12.1 Create idempotency service
    - Implement `IdempotencyService` in `lambda/users/shared/idempotency.py`
    - Implement `check_idempotency()` to query idempotency table
    - Implement `store_idempotency_key()` to save idempotency record with TTL
    - Implement request hash calculation for conflict detection
    - _Requirements: 11.1, 11.2, 11.3, 11.4_
  
  - [ ]* 12.2 Write property tests for idempotency
    - **Property 19: Idempotent User Creation**
    - **Property 21: Idempotency Key Conflict Detection**
    - **Validates: Requirements 11.1, 11.4**

- [ ] 13. Implement error handling and validation
  - [x] 13.1 Add comprehensive input validation
    - Ensure all handlers validate inputs before processing
    - Ensure validation errors include all failures in details
    - Ensure error responses match API contract structure
    - _Requirements: 7.1, 7.2, 7.4, 7.5, 8.1, 8.2_
  
  - [ ]* 13.2 Write property tests for error handling
    - **Property 17: Error Responses Have Consistent Structure**
    - **Validates: Requirements 8.1, 8.2, 8.3, 8.4**

- [ ] 14. Implement CDK infrastructure
  - [x] 14.1 Create DynamoDB table construct
    - Create `deployments/users/table_construct.py`
    - Define Users table with PK and SK
    - Configure billing mode (on-demand recommended)
    - Configure TTL for idempotency table
    - _Requirements: 10.1, 10.3, 10.4, 11.3_
  
  - [x] 14.2 Create Lambda function constructs
    - Create constructs for all 7 Lambda functions in `deployments/users/`
    - Configure environment variables (USERS_TABLE_NAME, IDEMPOTENCY_TABLE_NAME, EVENT_BUS_NAME)
    - Configure IAM roles with least privilege permissions
    - Configure memory and timeout settings
    - Use Python 3.11 runtime
    - _Requirements: All requirements_
  
  - [x] 14.3 Create API Gateway construct
    - Create REST API in `deployments/users/api_construct.py`
    - Define all 7 endpoints with request validation
    - Configure authentication (Cognito or IAM)
    - Wire Lambda functions to endpoints
    - _Requirements: 9.1, 9.2, 9.3_
  
  - [x] 14.4 Create EventBridge bus construct
    - Create EventBridge bus for audit events in `deployments/users/`
    - Configure event rules if needed for audit storage
    - _Requirements: 6.1, 6.5_
  
  - [x] 14.5 Create main stack
    - Create `deployments/users/users_stack.py`
    - Instantiate all constructs
    - Export API endpoint URL
    - Configure stack tags and naming per conventions
    - _Requirements: All requirements_
  
  - [ ]* 14.6 Write CDK infrastructure tests
    - Test Lambda functions are wired to correct endpoints
    - Test IAM roles have correct permissions
    - Test DynamoDB table configuration
    - Test EventBridge bus configuration
    - _Requirements: All requirements_

- [ ] 15. Add logging and observability
  - [x] 15.1 Implement structured logging
    - Add correlation ID to all log statements
    - Log request start and completion with latency
    - Log errors with context (no sensitive data)
    - Use consistent log format across all Lambdas
    - _Requirements: 12.1, 12.2, 12.3, 12.4_
  
  - [x] 15.2 Add CloudWatch metrics
    - Emit custom metrics for request count per operation
    - Emit custom metrics for error rate per operation
    - Emit custom metrics for latency per operation
    - _Requirements: 12.5_

- [x] 16. Final checkpoint - Integration testing
  - Ensure all tests pass, ask the user if questions arise.
  - Verify end-to-end flows: register → get → update → status change → delete
  - Verify idempotency works across all write operations
  - Verify audit events are published for all changes

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Lambda code lives in `lambda/users/`, CDK code lives in `deployments/users/`
- All Lambda functions follow the pattern: handler → validation → service
- Property tests use Hypothesis library with 100+ iterations
- Checkpoints ensure incremental validation throughout implementation
- Python 3.11 runtime for all Lambda functions
- Use snake_case for Python file and function names
