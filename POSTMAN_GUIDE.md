# Postman Testing Guide

## ✅ API is Now Public - No Authentication Required!

The API has been updated to allow public access for testing in Postman.

---

## API Endpoint
```
https://ac9a51tp48.execute-api.ap-south-1.amazonaws.com/prod
```

---

## Testing in Postman

### 1. Create User (POST /users)

**Request:**
- **Method**: POST
- **URL**: `https://ac9a51tp48.execute-api.ap-south-1.amazonaws.com/prod/users`
- **Headers**:
  - `Content-Type: application/json`
- **Body** (raw JSON):
```json
{
  "email": "john.doe@example.com",
  "name": "John Doe",
  "idempotencyKey": "unique-key-001"
}
```

**Expected Response (201 Created):**
```json
{
  "userId": "01KH613P53Z1GG2JEX03CRHPPR",
  "email": "john.doe@example.com",
  "name": "John Doe",
  "status": "active",
  "roles": [],
  "metadata": {},
  "createdAt": "2026-02-11T10:00:00.000000Z",
  "updatedAt": "2026-02-11T10:00:00.000000Z"
}
```

---

### 2. Get User Profile (GET /users/{userId})

**Request:**
- **Method**: GET
- **URL**: `https://ac9a51tp48.execute-api.ap-south-1.amazonaws.com/prod/users/01KH613P53Z1GG2JEX03CRHPPR`
- **Headers**: None required

**Expected Response (200 OK):**
```json
{
  "userId": "01KH613P53Z1GG2JEX03CRHPPR",
  "email": "john.doe@example.com",
  "name": "John Doe",
  "status": "active",
  "roles": [],
  "metadata": {},
  "createdAt": "2026-02-11T10:00:00.000000Z",
  "updatedAt": "2026-02-11T10:00:00.000000Z"
}
```

---

### 3. Update User Profile (PATCH /users/{userId})

**Request:**
- **Method**: PATCH
- **URL**: `https://ac9a51tp48.execute-api.ap-south-1.amazonaws.com/prod/users/01KH613P53Z1GG2JEX03CRHPPR`
- **Headers**:
  - `Content-Type: application/json`
- **Body** (raw JSON):
```json
{
  "idempotencyKey": "update-key-001",
  "name": "John Updated Doe",
  "metadata": {
    "department": "Engineering",
    "location": "Mumbai"
  }
}
```

**Expected Response (200 OK):**
```json
{
  "userId": "01KH613P53Z1GG2JEX03CRHPPR",
  "email": "john.doe@example.com",
  "name": "John Updated Doe",
  "status": "active",
  "roles": [],
  "metadata": {
    "department": "Engineering",
    "location": "Mumbai"
  },
  "createdAt": "2026-02-11T10:00:00.000000Z",
  "updatedAt": "2026-02-11T10:05:00.000000Z"
}
```

---

### 4. Assign Role (POST /users/{userId}/roles)

**Request:**
- **Method**: POST
- **URL**: `https://ac9a51tp48.execute-api.ap-south-1.amazonaws.com/prod/users/01KH613P53Z1GG2JEX03CRHPPR/roles`
- **Headers**:
  - `Content-Type: application/json`
- **Body** (raw JSON):
```json
{
  "role": "admin"
}
```

**Expected Response (200 OK):**
```json
{
  "userId": "01KH613P53Z1GG2JEX03CRHPPR",
  "roles": ["admin"],
  "updatedAt": "2026-02-11T10:10:00.000000Z"
}
```

---

### 5. Update User Status (PUT /users/{userId}/status)

**Request:**
- **Method**: PUT
- **URL**: `https://ac9a51tp48.execute-api.ap-south-1.amazonaws.com/prod/users/01KH613P53Z1GG2JEX03CRHPPR/status`
- **Headers**:
  - `Content-Type: application/json`
- **Body** (raw JSON):
```json
{
  "status": "disabled"
}
```

**Valid status values**: `active`, `disabled`, `deleted`

**Expected Response (200 OK):**
```json
{
  "userId": "01KH613P53Z1GG2JEX03CRHPPR",
  "status": "disabled",
  "updatedAt": "2026-02-11T10:15:00.000000Z"
}
```

---

### 6. List Users (GET /users)

**Request:**
- **Method**: GET
- **URL**: `https://ac9a51tp48.execute-api.ap-south-1.amazonaws.com/prod/users?limit=10&status=active`
- **Headers**: None required
- **Query Parameters**:
  - `limit` (optional): Number of users to return (default: 20)
  - `status` (optional): Filter by status (active, disabled, deleted)
  - `nextToken` (optional): Pagination token

**Expected Response (200 OK):**
```json
{
  "users": [
    {
      "userId": "01KH613P53Z1GG2JEX03CRHPPR",
      "email": "john.doe@example.com",
      "name": "John Doe",
      "status": "active",
      "roles": ["admin"],
      "createdAt": "2026-02-11T10:00:00.000000Z"
    }
  ],
  "nextToken": null
}
```

---

### 7. Remove Role (DELETE /users/{userId}/roles/{role})

**Request:**
- **Method**: DELETE
- **URL**: `https://ac9a51tp48.execute-api.ap-south-1.amazonaws.com/prod/users/01KH613P53Z1GG2JEX03CRHPPR/roles/admin`
- **Headers**: None required

**Expected Response (200 OK):**
```json
{
  "userId": "01KH613P53Z1GG2JEX03CRHPPR",
  "roles": [],
  "updatedAt": "2026-02-11T10:20:00.000000Z"
}
```

---

### 8. Query Audit Logs (GET /users/{userId}/audit)

**Request:**
- **Method**: GET
- **URL**: `https://ac9a51tp48.execute-api.ap-south-1.amazonaws.com/prod/users/01KH613P53Z1GG2JEX03CRHPPR/audit?limit=20`
- **Headers**: None required
- **Query Parameters**:
  - `limit` (optional): Number of audit events to return
  - `nextToken` (optional): Pagination token

**Expected Response (200 OK):**
```json
{
  "auditLogs": [],
  "nextToken": null
}
```

---

## Quick Test with cURL

Now you can test with simple cURL commands:

```bash
# Create User
curl -X POST https://ac9a51tp48.execute-api.ap-south-1.amazonaws.com/prod/users \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","name":"Test User","idempotencyKey":"test-001"}'

# Get User (replace USER_ID with actual ID from create response)
curl https://ac9a51tp48.execute-api.ap-south-1.amazonaws.com/prod/users/USER_ID

# List Users
curl https://ac9a51tp48.execute-api.ap-south-1.amazonaws.com/prod/users?limit=10
```

---

## Import Postman Collection

Save this as `user-management-api.postman_collection.json` and import into Postman:

```json
{
  "info": {
    "name": "User Management API",
    "description": "Public API for testing user management endpoints",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Create User",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"email\": \"john.doe@example.com\",\n  \"name\": \"John Doe\",\n  \"idempotencyKey\": \"unique-key-001\"\n}"
        },
        "url": {
          "raw": "https://ac9a51tp48.execute-api.ap-south-1.amazonaws.com/prod/users",
          "protocol": "https",
          "host": ["ac9a51tp48", "execute-api", "ap-south-1", "amazonaws", "com"],
          "path": ["prod", "users"]
        }
      }
    },
    {
      "name": "Get User",
      "request": {
        "method": "GET",
        "header": [],
        "url": {
          "raw": "https://ac9a51tp48.execute-api.ap-south-1.amazonaws.com/prod/users/{{userId}}",
          "protocol": "https",
          "host": ["ac9a51tp48", "execute-api", "ap-south-1", "amazonaws", "com"],
          "path": ["prod", "users", "{{userId}}"]
        }
      }
    },
    {
      "name": "List Users",
      "request": {
        "method": "GET",
        "header": [],
        "url": {
          "raw": "https://ac9a51tp48.execute-api.ap-south-1.amazonaws.com/prod/users?limit=10",
          "protocol": "https",
          "host": ["ac9a51tp48", "execute-api", "ap-south-1", "amazonaws", "com"],
          "path": ["prod", "users"],
          "query": [
            {
              "key": "limit",
              "value": "10"
            }
          ]
        }
      }
    }
  ]
}
```

---

## ⚠️ Important Security Note

**The API is currently PUBLIC for testing purposes.**

For production deployment:
1. Re-enable IAM authentication in `deployments/users/api_construct.py`
2. Change `authorization_type=apigw.AuthorizationType.NONE` back to `authorization_type=apigw.AuthorizationType.IAM`
3. Redeploy the stack

---

## Common Error Responses

### 400 Bad Request
```json
{
  "code": "VALIDATION_ERROR",
  "message": "Invalid request",
  "details": {
    "errors": [
      {
        "field": "email",
        "message": "Invalid email format"
      }
    ]
  }
}
```

### 404 Not Found
```json
{
  "code": "NOT_FOUND",
  "message": "User not found",
  "details": {
    "userId": "01KH613P53Z1GG2JEX03CRHPPR"
  }
}
```

### 409 Conflict
```json
{
  "code": "CONFLICT",
  "message": "Email 'john.doe@example.com' is already registered",
  "details": {
    "email": "john.doe@example.com"
  }
}
```

---

## Testing Tips

1. **Save userId**: After creating a user, save the `userId` from the response to use in other requests
2. **Unique emails**: Each email can only be registered once
3. **Idempotency keys**: Use unique idempotency keys for each create/update operation
4. **Metadata values**: All metadata values must be strings (not numbers or booleans)

---

**Happy Testing! 🚀**
