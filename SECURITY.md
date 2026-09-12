# Security Policy

MRPL Sovereign Industrial AI Workbench is a self-hosted, air-gapped engineering AI workbench with privileged local capabilities for refinery operations. Please do not run it as a public, unauthenticated service.

## Supported Versions

Security fixes and statutory compliance updates are maintained on the default branch.

## Deployment Guidance

- Keep `AUTH_ENABLED=true` for any network-accessible deployment.
- Keep `LOCALHOST_BYPASS=false` outside local development.
- Leave `SECURE_COOKIES` unset unless you need to override it: session cookies are marked `Secure` whenever the request arrives over HTTPS. Set `SECURE_COOKIES=true` to force it on (for a proxy that cannot see the scheme), or `SECURE_COOKIES=false` to force it off while serving plain HTTP on internal LANs.
- Use HTTPS when exposing the app beyond localhost on refinery networks.
- Put the authenticated web/API entrypoint behind a trusted reverse proxy or corporate VPN/intranet gateway.
- Keep ChromaDB, SearXNG, ntfy, Ollama, vLLM, llama.cpp, databases, and raw model/provider APIs strictly internal-only and air-gapped.
- Protect `.env`, `data/`, `logs/`, uploads, generated reports, backups, auth/session files, database files, and Merkle audit logs.
- Disable open signup on production installations.
- Keep demo/test users non-admin, and remove them entirely on plant deployments.
- Give admin accounts strong passwords and enforce MFA / 2FA.
- Maintain departmental RBAC (`OPERATIONS_TAR`, `PROCESS_ENGINEERING`, `RELIABILITY_INSPECTION`, `HSE_SAFETY`, `EXECUTIVE_MANAGEMENT`).
- Rotate API keys, internal tokens, and session secrets if they appear in logs or screenshots.
- Common internal-only ports are Workbench `7000`, SearXNG `8080`, ntfy `8091`, ChromaDB `8100`, Ollama `11434`, and local model APIs such as `8000-8020`.

## Pre-Release Sanitization

Before packaging or pushing the repository, run:

```bash
git status --short
git check-ignore -v .env data/auth.json data/app.db logs/app.log
git grep -n -I -E "(sk-[A-Za-z0-9_-]{20,}|xox[baprs]-|AIza[0-9A-Za-z_-]{20,}|Bearer [A-Za-z0-9._~+/-]{20,})" -- . ':!static/lib/**' ':!package-lock.json'
```

Only `.env.example`, documentation, source code, tests, and static assets should be committed. Never commit live `.env` values, `data/` contents, local databases, uploaded plant schematics, logs, backups, auth/session files, API keys, password hashes, or confidential crude assays.

## Reporting Vulnerabilities

Please report security issues privately to the MRPL project administrators or by opening a minimal confidential issue.
