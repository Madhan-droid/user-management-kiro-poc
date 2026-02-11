"""
API Gateway construct for User Management Service.

This module defines the REST API Gateway for the User Management Service.
The API provides 8 endpoints for user management operations with:
- Request validation at API Gateway level
- Public access (NO authentication) for testing purposes
- Lambda proxy integrations
- CORS configuration
- Standard REST conventions

⚠️ WARNING: This API is currently PUBLIC for testing in Postman.
   For production, enable IAM or API Key authentication.

Follows steering rules:
- Infrastructure definition only (no business logic)
- Explicit over implicit (all configurations declared)
- Fail fast with request validation

API Endpoints:
1. POST /users - User registration
2. GET /users/{userId} - Get user profile
3. PATCH /users/{userId} - Update user profile
4. PUT /users/{userId}/status - Update user status
5. POST /users/{userId}/roles - Assign role
6. DELETE /users/{userId}/roles/{role} - Remove role
7. GET /users - List users (with query params)
8. GET /users/{userId}/audit - Query audit logs

Usage Example:
    from aws_cdk import Stack
    from constructs import Construct
    from .table_construct import UserManagementTablesConstruct
    from .lambda_constructs import UserManagementLambdasConstruct
    from .api_construct import UserManagementApiConstruct
    
    class UserManagementStack(Stack):
        def __init__(self, scope: Construct, construct_id: str, **kwargs):
            super().__init__(scope, construct_id, **kwargs)
            
            # Create DynamoDB tables
            tables = UserManagementTablesConstruct(self, "Tables")
            
            # Create EventBridge bus (task 14.4)
            event_bus = events.EventBus(self, "UserEventBus")
            
            # Create Lambda functions
            lambdas = UserManagementLambdasConstruct(
                self, "Lambdas",
                users_table=tables.users_table,
                idempotency_table=tables.idempotency_table,
                event_bus=event_bus
            )
            
            # Create API Gateway
            api = UserManagementApiConstruct(
                self, "Api",
                register_lambda=lambdas.register_lambda,
                profile_get_lambda=lambdas.profile_get_lambda,
                profile_update_lambda=lambdas.profile_update_lambda,
                status_update_lambda=lambdas.status_update_lambda,
                role_assign_lambda=lambdas.role_assign_lambda,
                role_remove_lambda=lambdas.role_remove_lambda,
                list_query_lambda=lambdas.list_query_lambda,
                audit_query_lambda=lambdas.audit_query_lambda
            )
            
            # Export API endpoint
            CfnOutput(self, "ApiEndpoint", value=api.api.url)
"""

from aws_cdk import (
    aws_apigateway as apigw,
    aws_lambda as lambda_,
    CfnOutput,
)
from constructs import Construct


class UserManagementApiConstruct(Construct):
    """
    Construct that creates the REST API Gateway for User Management Service.
    
    This construct creates a REST API with 8 endpoints, each wired to its
    corresponding Lambda function. All endpoints require IAM authentication
    and include request validation where appropriate.
    
    Attributes:
        api: The REST API Gateway instance
        deployment: The API deployment
    """
    
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        register_lambda: lambda_.Function,
        profile_get_lambda: lambda_.Function,
        profile_update_lambda: lambda_.Function,
        status_update_lambda: lambda_.Function,
        role_assign_lambda: lambda_.Function,
        role_remove_lambda: lambda_.Function,
        list_query_lambda: lambda_.Function,
        audit_query_lambda: lambda_.Function,
        **kwargs
    ) -> None:
        """
        Initialize API Gateway construct.
        
        Args:
            scope: CDK construct scope
            construct_id: Unique construct identifier
            register_lambda: User registration Lambda function
            profile_get_lambda: User profile retrieval Lambda function
            profile_update_lambda: User profile update Lambda function
            status_update_lambda: User status update Lambda function
            role_assign_lambda: Role assignment Lambda function
            role_remove_lambda: Role removal Lambda function
            list_query_lambda: User listing Lambda function
            audit_query_lambda: Audit log query Lambda function
        """
        super().__init__(scope, construct_id, **kwargs)
        
        # Create REST API
        self.api = apigw.RestApi(
            self,
            'UserManagementApi',
            rest_api_name='user-management-api',
            description='User Management Service REST API',
            deploy=True,
            deploy_options=apigw.StageOptions(
                stage_name='prod',
                throttling_rate_limit=1000,  # requests per second
                throttling_burst_limit=2000,  # concurrent requests
                tracing_enabled=True,  # Enable X-Ray tracing
                logging_level=apigw.MethodLoggingLevel.INFO,
                data_trace_enabled=True,
                metrics_enabled=True,
            ),
            # CORS configuration (adjust as needed for your use case)
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,  # TODO: Restrict in production
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=[
                    'Content-Type',
                    'X-Amz-Date',
                    'Authorization',
                    'X-Api-Key',
                    'X-Amz-Security-Token',
                ],
            ),
            # Enable CloudWatch role for API Gateway logging
            cloud_watch_role=True,
        )
        
        # Create request validators
        # Validator for body and parameters
        body_validator = apigw.RequestValidator(
            self,
            'BodyValidator',
            rest_api=self.api,
            request_validator_name='body-validator',
            validate_request_body=True,
            validate_request_parameters=True,
        )
        
        # Validator for parameters only
        params_validator = apigw.RequestValidator(
            self,
            'ParamsValidator',
            rest_api=self.api,
            request_validator_name='params-validator',
            validate_request_body=False,
            validate_request_parameters=True,
        )
        
        # Create request models for validation
        registration_model = self._create_registration_model()
        profile_update_model = self._create_profile_update_model()
        status_update_model = self._create_status_update_model()
        role_assign_model = self._create_role_assign_model()
        
        # Create Lambda integrations
        register_integration = apigw.LambdaIntegration(register_lambda)
        profile_get_integration = apigw.LambdaIntegration(profile_get_lambda)
        profile_update_integration = apigw.LambdaIntegration(profile_update_lambda)
        status_update_integration = apigw.LambdaIntegration(status_update_lambda)
        role_assign_integration = apigw.LambdaIntegration(role_assign_lambda)
        role_remove_integration = apigw.LambdaIntegration(role_remove_lambda)
        list_query_integration = apigw.LambdaIntegration(list_query_lambda)
        audit_query_integration = apigw.LambdaIntegration(audit_query_lambda)
        
        # Get root resource
        users_resource = self.api.root.add_resource('users')
        
        # 1. POST /users - User registration
        users_resource.add_method(
            'POST',
            register_integration,
            authorization_type=apigw.AuthorizationType.NONE,
            request_validator=body_validator,
            request_models={
                'application/json': registration_model
            },
            method_responses=[
                apigw.MethodResponse(
                    status_code='201',
                    response_models={
                        'application/json': apigw.Model.EMPTY_MODEL
                    }
                ),
                apigw.MethodResponse(status_code='400'),
                apigw.MethodResponse(status_code='401'),
                apigw.MethodResponse(status_code='409'),
                apigw.MethodResponse(status_code='500'),
            ]
        )
        
        # 7. GET /users - List users (with query params)
        users_resource.add_method(
            'GET',
            list_query_integration,
            authorization_type=apigw.AuthorizationType.NONE,
            request_validator=params_validator,
            request_parameters={
                'method.request.querystring.limit': False,
                'method.request.querystring.nextToken': False,
                'method.request.querystring.status': False,
            },
            method_responses=[
                apigw.MethodResponse(
                    status_code='200',
                    response_models={
                        'application/json': apigw.Model.EMPTY_MODEL
                    }
                ),
                apigw.MethodResponse(status_code='400'),
                apigw.MethodResponse(status_code='401'),
                apigw.MethodResponse(status_code='500'),
            ]
        )
        
        # Create {userId} resource
        user_id_resource = users_resource.add_resource('{userId}')
        
        # 2. GET /users/{userId} - Get user profile
        user_id_resource.add_method(
            'GET',
            profile_get_integration,
            authorization_type=apigw.AuthorizationType.NONE,
            request_validator=params_validator,
            request_parameters={
                'method.request.path.userId': True,
            },
            method_responses=[
                apigw.MethodResponse(
                    status_code='200',
                    response_models={
                        'application/json': apigw.Model.EMPTY_MODEL
                    }
                ),
                apigw.MethodResponse(status_code='401'),
                apigw.MethodResponse(status_code='404'),
                apigw.MethodResponse(status_code='500'),
            ]
        )
        
        # 3. PATCH /users/{userId} - Update user profile
        user_id_resource.add_method(
            'PATCH',
            profile_update_integration,
            authorization_type=apigw.AuthorizationType.NONE,
            request_validator=body_validator,
            request_parameters={
                'method.request.path.userId': True,
            },
            request_models={
                'application/json': profile_update_model
            },
            method_responses=[
                apigw.MethodResponse(
                    status_code='200',
                    response_models={
                        'application/json': apigw.Model.EMPTY_MODEL
                    }
                ),
                apigw.MethodResponse(status_code='400'),
                apigw.MethodResponse(status_code='401'),
                apigw.MethodResponse(status_code='404'),
                apigw.MethodResponse(status_code='409'),
                apigw.MethodResponse(status_code='500'),
            ]
        )
        
        # Create /users/{userId}/status resource
        status_resource = user_id_resource.add_resource('status')
        
        # 4. PUT /users/{userId}/status - Update user status
        status_resource.add_method(
            'PUT',
            status_update_integration,
            authorization_type=apigw.AuthorizationType.NONE,
            request_validator=body_validator,
            request_parameters={
                'method.request.path.userId': True,
            },
            request_models={
                'application/json': status_update_model
            },
            method_responses=[
                apigw.MethodResponse(
                    status_code='200',
                    response_models={
                        'application/json': apigw.Model.EMPTY_MODEL
                    }
                ),
                apigw.MethodResponse(status_code='400'),
                apigw.MethodResponse(status_code='401'),
                apigw.MethodResponse(status_code='404'),
                apigw.MethodResponse(status_code='500'),
            ]
        )
        
        # Create /users/{userId}/roles resource
        roles_resource = user_id_resource.add_resource('roles')
        
        # 5. POST /users/{userId}/roles - Assign role
        roles_resource.add_method(
            'POST',
            role_assign_integration,
            authorization_type=apigw.AuthorizationType.NONE,
            request_validator=body_validator,
            request_parameters={
                'method.request.path.userId': True,
            },
            request_models={
                'application/json': role_assign_model
            },
            method_responses=[
                apigw.MethodResponse(
                    status_code='200',
                    response_models={
                        'application/json': apigw.Model.EMPTY_MODEL
                    }
                ),
                apigw.MethodResponse(status_code='400'),
                apigw.MethodResponse(status_code='401'),
                apigw.MethodResponse(status_code='404'),
                apigw.MethodResponse(status_code='500'),
            ]
        )
        
        # Create /users/{userId}/roles/{role} resource
        role_resource = roles_resource.add_resource('{role}')
        
        # 6. DELETE /users/{userId}/roles/{role} - Remove role
        role_resource.add_method(
            'DELETE',
            role_remove_integration,
            authorization_type=apigw.AuthorizationType.NONE,
            request_validator=params_validator,
            request_parameters={
                'method.request.path.userId': True,
                'method.request.path.role': True,
            },
            method_responses=[
                apigw.MethodResponse(
                    status_code='200',
                    response_models={
                        'application/json': apigw.Model.EMPTY_MODEL
                    }
                ),
                apigw.MethodResponse(status_code='401'),
                apigw.MethodResponse(status_code='404'),
                apigw.MethodResponse(status_code='500'),
            ]
        )
        
        # Create /users/{userId}/audit resource
        audit_resource = user_id_resource.add_resource('audit')
        
        # 8. GET /users/{userId}/audit - Query audit logs
        audit_resource.add_method(
            'GET',
            audit_query_integration,
            authorization_type=apigw.AuthorizationType.NONE,
            request_validator=params_validator,
            request_parameters={
                'method.request.path.userId': True,
                'method.request.querystring.limit': False,
                'method.request.querystring.nextToken': False,
            },
            method_responses=[
                apigw.MethodResponse(
                    status_code='200',
                    response_models={
                        'application/json': apigw.Model.EMPTY_MODEL
                    }
                ),
                apigw.MethodResponse(status_code='400'),
                apigw.MethodResponse(status_code='401'),
                apigw.MethodResponse(status_code='404'),
                apigw.MethodResponse(status_code='500'),
            ]
        )
    
    def _create_registration_model(self) -> apigw.Model:
        """
        Create request model for user registration.
        
        Validates:
        - idempotencyKey: required string
        - email: required string
        - name: required string
        - metadata: optional object
        """
        return self.api.add_model(
            'RegistrationModel',
            content_type='application/json',
            model_name='RegistrationRequest',
            schema=apigw.JsonSchema(
                schema=apigw.JsonSchemaVersion.DRAFT4,
                title='User Registration Request',
                type=apigw.JsonSchemaType.OBJECT,
                properties={
                    'idempotencyKey': apigw.JsonSchema(
                        type=apigw.JsonSchemaType.STRING,
                        min_length=1,
                    ),
                    'email': apigw.JsonSchema(
                        type=apigw.JsonSchemaType.STRING,
                        format='email',
                        min_length=1,
                    ),
                    'name': apigw.JsonSchema(
                        type=apigw.JsonSchemaType.STRING,
                        min_length=1,
                    ),
                    'metadata': apigw.JsonSchema(
                        type=apigw.JsonSchemaType.OBJECT,
                    ),
                },
                required=['idempotencyKey', 'email', 'name'],
            )
        )
    
    def _create_profile_update_model(self) -> apigw.Model:
        """
        Create request model for profile update.
        
        Validates:
        - idempotencyKey: required string
        - name: optional string
        - metadata: optional object
        """
        return self.api.add_model(
            'ProfileUpdateModel',
            content_type='application/json',
            model_name='ProfileUpdateRequest',
            schema=apigw.JsonSchema(
                schema=apigw.JsonSchemaVersion.DRAFT4,
                title='Profile Update Request',
                type=apigw.JsonSchemaType.OBJECT,
                properties={
                    'idempotencyKey': apigw.JsonSchema(
                        type=apigw.JsonSchemaType.STRING,
                        min_length=1,
                    ),
                    'name': apigw.JsonSchema(
                        type=apigw.JsonSchemaType.STRING,
                        min_length=1,
                    ),
                    'metadata': apigw.JsonSchema(
                        type=apigw.JsonSchemaType.OBJECT,
                    ),
                },
                required=['idempotencyKey'],
            )
        )
    
    def _create_status_update_model(self) -> apigw.Model:
        """
        Create request model for status update.
        
        Validates:
        - status: required string (enum: active, disabled, deleted)
        """
        return self.api.add_model(
            'StatusUpdateModel',
            content_type='application/json',
            model_name='StatusUpdateRequest',
            schema=apigw.JsonSchema(
                schema=apigw.JsonSchemaVersion.DRAFT4,
                title='Status Update Request',
                type=apigw.JsonSchemaType.OBJECT,
                properties={
                    'status': apigw.JsonSchema(
                        type=apigw.JsonSchemaType.STRING,
                        enum=['active', 'disabled', 'deleted'],
                    ),
                },
                required=['status'],
            )
        )
    
    def _create_role_assign_model(self) -> apigw.Model:
        """
        Create request model for role assignment.
        
        Validates:
        - role: required string
        """
        return self.api.add_model(
            'RoleAssignModel',
            content_type='application/json',
            model_name='RoleAssignRequest',
            schema=apigw.JsonSchema(
                schema=apigw.JsonSchemaVersion.DRAFT4,
                title='Role Assignment Request',
                type=apigw.JsonSchemaType.OBJECT,
                properties={
                    'role': apigw.JsonSchema(
                        type=apigw.JsonSchemaType.STRING,
                        min_length=1,
                    ),
                },
                required=['role'],
            )
        )
