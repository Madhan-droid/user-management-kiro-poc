# User Management Service

A serverless user management service built with AWS CDK, Lambda, DynamoDB, and API Gateway.

## 🚀 Deployment Status

✅ **DEPLOYED** - All APIs working correctly  
📍 **Region**: ap-south-1 (Mumbai)  
🔗 **API Endpoint**: https://ac9a51tp48.execute-api.ap-south-1.amazonaws.com/prod/

See [DEPLOYMENT_SUCCESS.md](DEPLOYMENT_SUCCESS.md) for complete deployment details.

---

## 📁 Project Structure

```
.
├── deployments/              # AWS CDK infrastructure code
│   ├── app.py               # CDK app entry point
│   ├── cdk.json             # CDK configuration
│   └── users/               # User management constructs
│       ├── api_construct.py          # API Gateway configuration
│       ├── lambda_constructs.py      # Lambda functions
│       ├── table_construct.py        # DynamoDB tables
│       ├── eventbridge_construct.py  # EventBridge bus
│       └── users_stack.py            # Main stack
│
├── lambda/                   # Lambda function code
│   ├── users_register_create/   # POST /users
│   ├── users_profile_get/       # GET /users/{userId}
│   ├── users_profile_update/    # PATCH /users/{userId}
│   ├── users_status_update/     # PUT /users/{userId}/status
│   ├── users_role_assign/       # POST /users/{userId}/roles
│   ├── users_role_remove/       # DELETE /users/{userId}/roles/{role}
│   ├── users_list_query/        # GET /users
│   ├── users_audit_query/       # GET /users/{userId}/audit
│   └── users_shared/            # Shared utilities
│
├── lambda_layer/            # Lambda Layer dependencies
│   └── python/
│       ├── ulid/
│       └── typing_extensions.py
│
├── tests/                   # Test suite
│   ├── test_validation.py       # Unit tests
│   ├── test_property_based.py   # Property-based tests
│   └── test_integration.py      # Integration tests
│
├── .kiro/specs/             # Feature specifications
│   └── user-management/
│       ├── requirements.md
│       ├── design.md
│       └── tasks.md
│
├── create_lambda_layer.py   # Create Lambda Layer with dependencies
├── package_lambdas.py       # Package Lambda functions for deployment
└── cleanup_lambda_deps.py   # Clean up Lambda dependencies
```

---

## 🛠️ Deployment Scripts

### 1. Create Lambda Layer
```bash
python create_lambda_layer.py
```
Creates a Lambda Layer with `python-ulid` and `typing-extensions` dependencies.

### 2. Package Lambda Functions
```bash
python package_lambdas.py
```
Copies shared code (`users_shared`) into each Lambda function directory.

### 3. Deploy to AWS
```bash
cd deployments
cdk deploy users-dev-stack --require-approval never
```

### 4. Clean Up Dependencies (Optional)
```bash
python cleanup_lambda_deps.py
```
Removes installed dependencies from Lambda folders (they're in the layer).

---

## 🔌 API Endpoints

All endpoints require AWS IAM authentication (SigV4).

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/users` | Register new user |
| GET | `/users/{userId}` | Get user profile |
| PATCH | `/users/{userId}` | Update user profile |
| PUT | `/users/{userId}/status` | Update user status |
| POST | `/users/{userId}/roles` | Assign role to user |
| DELETE | `/users/{userId}/roles/{role}` | Remove role from user |
| GET | `/users` | List users (with pagination) |
| GET | `/users/{userId}/audit` | Query audit logs |

---

## 🏗️ Architecture

### Components
- **API Gateway**: REST API with IAM authentication
- **Lambda Functions**: 8 functions (one per operation)
- **Lambda Layer**: Shared dependencies (python-ulid, typing-extensions)
- **DynamoDB**: 2 tables (Users, Idempotency)
- **EventBridge**: Audit event bus
- **CloudWatch**: Logging and metrics
- **X-Ray**: Distributed tracing

### Design Principles
- Lambda-per-operation pattern
- Separation of concerns (handler → service → data)
- Fail fast on invalid input
- Idempotency for write operations
- Structured logging with correlation IDs
- Domain-driven error handling

---

## 🧪 Testing

### Run Unit Tests
```bash
pytest tests/test_validation.py -v
```

### Run Property-Based Tests
```bash
pytest tests/test_property_based.py -v
```

### Run Integration Tests
```bash
pytest tests/test_integration.py -v
```

### Run All Tests
```bash
pytest tests/ -v
```

---

## 📊 Infrastructure Resources

### Lambda Functions
- Runtime: Python 3.11
- Memory: 256 MB
- Timeout: 30 seconds
- Layer: Shared dependencies layer

### DynamoDB Tables
- **UsersTable**: On-demand billing, Point-in-time recovery
- **IdempotencyTable**: On-demand billing, TTL enabled

### API Gateway
- Stage: prod
- Throttling: 1000 req/s, 2000 burst
- CORS: Enabled
- Logging: CloudWatch
- Tracing: X-Ray

---

## 🔐 Security

- IAM authentication required for all endpoints
- Request validation at API Gateway level
- Input validation in Lambda handlers
- No secrets in code (environment variables)
- Least privilege IAM roles
- CloudWatch logging (no sensitive data)

---

## 📝 Development Workflow

1. **Make changes** to Lambda code or infrastructure
2. **Run tests** to verify changes
3. **Package Lambda functions**: `python package_lambdas.py`
4. **Deploy**: `cd deployments && cdk deploy users-dev-stack`
5. **Verify** deployment in AWS Console or via API calls

---

## 🚨 Troubleshooting

### Lambda Import Errors
Run `python package_lambdas.py` before deployment to ensure shared code is copied.

### Missing Dependencies
Ensure Lambda Layer is created: `python create_lambda_layer.py`

### API 502 Errors
Check CloudWatch logs for the specific Lambda function.

### Authentication Failures
Verify AWS credentials are configured: `aws sts get-caller-identity`

---

## 📚 Documentation

- [DEPLOYMENT_SUCCESS.md](DEPLOYMENT_SUCCESS.md) - Complete deployment details
- [.kiro/specs/user-management/requirements.md](.kiro/specs/user-management/requirements.md) - Feature requirements
- [.kiro/specs/user-management/design.md](.kiro/specs/user-management/design.md) - System design
- [.kiro/specs/user-management/tasks.md](.kiro/specs/user-management/tasks.md) - Implementation tasks

---

## 🎯 Key Features

✅ User registration with email uniqueness  
✅ Profile management (get, update)  
✅ Status management (active, disabled, deleted)  
✅ Role-based access control  
✅ User listing with pagination  
✅ Audit logging  
✅ Idempotency for write operations  
✅ Structured logging with correlation IDs  
✅ CloudWatch metrics and X-Ray tracing  

---

## 📄 License

This project is part of a user management system implementation.

---

## 🤝 Contributing

1. Follow the existing code structure
2. Write tests for new features
3. Update documentation
4. Run all tests before committing
5. Follow AWS best practices

---

## 📞 Support

For issues or questions:
1. Check CloudWatch logs
2. Review API Gateway execution logs
3. Verify DynamoDB table data
4. Check EventBridge event delivery

---

**Last Updated**: February 11, 2026  
**Status**: ✅ Production Ready
