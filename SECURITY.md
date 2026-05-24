# Security Policy

Bridge Town is a hosted financial modeling platform. This public repository
contains connector documentation and registry metadata only; it does not contain
the proprietary Bridge Town server implementation.

## Reporting a Vulnerability

Email security issues to:

```text
security@bridgetown.builders
```

Do not open a public GitHub issue for vulnerabilities.

Please include:

1. A description of the vulnerability
2. Steps to reproduce
3. Impact assessment
4. Affected surface, such as MCP server, OAuth flow, Google Sheets integration,
   web app, or infrastructure
5. Any relevant request IDs, timestamps, or tenant/project identifiers

## Security Model Summary

Bridge Town is designed for tenant-isolated financial modeling workloads:

- Authentication uses OAuth for hosted connector flows and Bridge Town API
  tokens for manual MCP clients.
- API tokens are revocable and should be treated as sensitive credentials.
- Tenant data is scoped through server-side tenant identity and PostgreSQL
  Row-Level Security.
- Every project belongs to one tenant.
- Model execution runs in isolated containers with no outbound network.
- Google Sheets access uses Google `drive.file` scope. Bridge Town can only
  access Sheets selected through the Bridge Town app or Sheets it creates.
- Tool calls and authentication events are audit logged.
- Bridge Town does not run a server-side LLM or proxy user prompts to an LLM
  provider.

## Public Documentation

- Security and trust: <https://bridgetown.builders/security>
- Privacy policy: <https://bridgetown.builders/privacy>
- Terms of service: <https://bridgetown.builders/terms>
- Documentation: <https://docs.bridgetown.builders>

