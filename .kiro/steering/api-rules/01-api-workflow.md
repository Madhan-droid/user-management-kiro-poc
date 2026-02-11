# API DEVELOPMENT WORKFLOW (CDK + LAMBDA)

## Mandatory Flow

1. Understand business intent
2. Identify target Lambda(s)
3. Identify CDK stack impact (if any)
4. Propose API contract
5. Get human approval
6. Implement Lambda logic
7. Update CDK only if required
8. Add tests
9. Summarize impact

---

## Restrictions

- Lambda code MUST NOT contain CDK logic
- CDK code MUST NOT contain business logic
- Lambda changes MUST NOT force CDK refactors unless approved
