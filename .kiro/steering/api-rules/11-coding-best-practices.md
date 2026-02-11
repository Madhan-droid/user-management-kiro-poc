# CODING BEST PRACTICES (LAMBDA)

## General Principles

- Clarity over cleverness
- Explicit over implicit
- Readable > DRY

---

## Lambda Code

- One handler per file
- Business logic in services, not handlers
- No global mutable state
- Fail fast on invalid input

---

## Error Handling

- Domain errors must be explicit
- No generic catch-and-log
- Errors must map cleanly to API responses

---

## Dependencies

- Prefer small, explicit dependencies
- No unused libraries
- No runtime-only surprises

---

## Configuration

- Read once at startup
- Validate env vars on boot
- Never assume defaults silently
