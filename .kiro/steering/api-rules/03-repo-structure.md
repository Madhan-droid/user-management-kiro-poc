# REPOSITORY STRUCTURE RULES

## deployments/ (CDK)

Purpose:
- Infrastructure definition only

Allowed:
- CDK stacks
- Constructs
- IAM, API Gateway, Lambda wiring
- Environment configuration

Forbidden:
- Business logic
- API request handling
- Data transformation logic

---

## lambda/ (Business Logic)

Purpose:
- Pure Lambda runtime code

Allowed:
- Request validation
- Domain logic
- Data access
- Error handling

Forbidden:
- CDK imports
- Stack configuration
- Environment-specific branching

---

## shared/

- Must be explicitly approved
- No domain logic
- Utilities only (logging, error helpers)

---

## Absolute Rule

> **deployments/ may reference lambda/  
> lambda/ must NEVER reference deployments/**
