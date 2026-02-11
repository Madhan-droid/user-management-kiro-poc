# API DESIGN RULES

## Contracts

- Every API MUST have an explicit contract
- Contracts are source of truth
- Implementation MUST conform to contract

---

## Versioning

- Breaking changes require new version
- Existing versions MUST remain stable

---

## Error Model

All APIs MUST return a consistent error shape:
{
  "code": "STRING",
  "message": "STRING",
  "details": "OBJECT"
}

---

## Idempotency

- Write operations MUST be safe against retries
- Client retries MUST NOT cause duplication
