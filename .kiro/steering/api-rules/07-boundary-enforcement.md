# BOUNDARY & SCOPE ENFORCEMENT

## Core Boundaries

- deployments/** → infrastructure only
- lambda/** → business logic only

---

## Allowed Change Declaration (MANDATORY)

For each task, AI MUST be given:

Allowed:
- lambda/payments/refunds/**
- tests/payments/refunds/**

Implicitly Forbidden:
- deployments/**
- shared/**
- any other lambda domains

---

## CDK Change Rule

If Lambda changes require CDK updates:
1. STOP
2. Explain why infra must change
3. Ask for approval
4. Proceed only if approved

---

## No Silent Infra Changes

- CDK diffs MUST be intentional
- No auto-wiring, no guessing
