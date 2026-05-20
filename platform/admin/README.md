# PlantLab Admin

Separate admin diagnostics frontend for support and operations.

It is intentionally not linked from the normal web dashboard. Access is enforced
by the platform backend with `PLANTLAB_ADMIN_EMAILS`.

Local Docker URL:

```bash
http://localhost:5174
```

Local admin login:

```text
dev@plantlab.local
password
```

Production setup:

1. Set `PLANTLAB_ADMIN_EMAILS` on the platform backend to a comma-separated
   list of allowed admin emails.
2. Serve this frontend from an internal or restricted admin URL.
3. Make sure the admin frontend origin is allowed by
   `PLANTLAB_STANDALONE_WEB_ORIGIN_REGEX` if Google sign-in is used.
