# SECURITY RULES

## Authentication

- All APIs require authentication unless explicitly declared public
- Auth strategy MUST be explicit and documented

---

## Authorization

- Least privilege only
- No broad roles without justification

---

## Input Validation

- Validate all external input
- Reject invalid data early

---

## Secrets

- No secrets in code
- All secrets via environment or secret manager
