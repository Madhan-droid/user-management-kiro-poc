# User Management Service - CDK Infrastructure

This directory contains the AWS CDK infrastructure code for the User Management Service.

## Architecture

The stack creates the following resources:

### DynamoDB Tables
- **Users Table**: Primary user data store with single-table design
  - Access patterns: Get by ID, Check email uniqueness, List by status
- **Idempotency Table**: Idempotency key tracking with 24h TTL

### EventBridge
- **Event Bus**: Custom event bus for audit events
- **CloudWatch Logs**: Audit event logging with 1-year retention
- **Event Archive**: 1-year archive for compliance and replay

### Lambda Functions (8 total)
1. `users-register-create`: User registration
2. `users-profile-get`: User profile retrieval
3. `users-profile-update`: User profile updates
4. `users-status-update`: User status management
5. `users-role-assign`: Role assignment
6. `users-role-remove`: Role removal
7. `users-list-query`: User listing with pagination
8. `users-audit-query`: Audit log retrieval

### API Gateway
- REST API with 8 endpoints
- IAM authentication on all endpoints
- Request validation at API Gateway level
- CloudWatch logging and X-Ray tracing enabled

## Prerequisites

1. Python 3.11 or later
2. AWS CDK CLI installed: `npm install -g aws-cdk`
3. AWS credentials configured
4. Python dependencies installed: `pip install -r requirements.txt`

## Project Structure

```
deployments/
├── app.py                          # CDK app entry point
├── cdk.json                        # CDK configuration
├── requirements.txt                # Python dependencies
└── users/
    ├── users_stack.py              # Main stack definition
    ├── table_construct.py          # DynamoDB tables construct
    ├── eventbridge_construct.py    # EventBridge bus construct
    ├── lambda_constructs.py        # Lambda functions construct
    └── api_construct.py            # API Gateway construct
```

## Deployment

### Development Environment

```bash
# Navigate to deployments directory
cd deployments

# Install dependencies
pip install -r requirements.txt

# Synthesize CloudFormation template
cdk synth users-dev-stack

# Deploy to AWS
cdk deploy users-dev-stack
```

### Production Environment

Uncomment the production stack in `app.py`, then:

```bash
cdk deploy users-prod-stack
```

### Deploy All Stacks

```bash
cdk deploy --all
```

## Stack Outputs

After deployment, the stack exports the following outputs:

- **ApiEndpointUrl**: API Gateway endpoint URL
- **ApiId**: API Gateway REST API ID
- **UsersTableName**: DynamoDB Users table name
- **IdempotencyTableName**: DynamoDB Idempotency table name
- **EventBusName**: EventBridge event bus name
- **EventBusArn**: EventBridge event bus ARN

Access outputs via:

```bash
aws cloudformation describe-stacks --stack-name users-dev-stack --query 'Stacks[0].Outputs'
```

## Configuration

### Environment Variables

Set AWS account and region via environment variables:

```bash
export CDK_DEFAULT_ACCOUNT=123456789012
export CDK_DEFAULT_REGION=us-east-1
```

### Stack Naming Convention

Stacks follow the naming convention: `<service>-<env>-stack`

Examples:
- `users-dev-stack` (development)
- `users-staging-stack` (staging)
- `users-prod-stack` (production)

## Resource Tagging

All resources are tagged with:
- `Service`: user-management
- `Environment`: dev/staging/prod
- `ManagedBy`: CDK
- `Domain`: users

## CDK Commands

```bash
# List all stacks
cdk list

# Synthesize CloudFormation template
cdk synth [stack-name]

# Show differences between deployed and local
cdk diff [stack-name]

# Deploy stack
cdk deploy [stack-name]

# Destroy stack (use with caution!)
cdk destroy [stack-name]

# Bootstrap CDK (first time only)
cdk bootstrap
```

## Testing

Infrastructure tests are located in the `users/` directory:

```bash
# Run infrastructure tests
pytest users/test_*.py
```

## Security

- All API endpoints require IAM authentication
- Lambda functions follow least privilege IAM permissions
- DynamoDB tables have point-in-time recovery enabled
- X-Ray tracing enabled for observability
- CloudWatch logging enabled for all components

## Cost Optimization

- DynamoDB tables use on-demand billing mode
- Lambda functions configured with appropriate memory (256 MB)
- API Gateway throttling configured (1000 req/s, 2000 burst)
- DynamoDB TTL enabled on Idempotency table for automatic cleanup

## Compliance

- Audit events archived for 1 year
- CloudWatch Logs retention: 1 year
- DynamoDB tables configured with RETAIN removal policy
- Point-in-time recovery enabled on all tables

## Troubleshooting

### CDK Bootstrap Required

If you see an error about missing bootstrap stack:

```bash
cdk bootstrap aws://ACCOUNT-ID/REGION
```

### Python Module Not Found

Ensure you're in the `deployments/` directory and dependencies are installed:

```bash
cd deployments
pip install -r requirements.txt
```

### Lambda Code Not Found

Ensure Lambda code exists in the correct directories:
- `lambda/users_register_create/`
- `lambda/users_profile_get/`
- `lambda/users_profile_update/`
- etc.

## Support

For issues or questions, refer to:
- Design document: `.kiro/specs/user-management/design.md`
- Requirements: `.kiro/specs/user-management/requirements.md`
- Tasks: `.kiro/specs/user-management/tasks.md`
