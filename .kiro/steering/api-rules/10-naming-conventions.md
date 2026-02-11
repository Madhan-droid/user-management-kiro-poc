# NAMING CONVENTIONS

## Lambda Functions

Format:
<domain>-<capability>-<action>

Example:
payments-refund-create
users-profile-update

---

## CDK Stacks

Format:
<service>-<env>-stack

Example:
payments-prod-stack
users-dev-stack

---

## Environment Variables

- UPPER_SNAKE_CASE
- Prefix by domain when shared

Example:
PAYMENTS_TABLE_NAME

---

## Files & Folders

- lowercase-kebab-case
- No abbreviations
- No generic names like utils, common without context
