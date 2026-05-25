# Bridge Town MCP Connector

Build financial models as code. Cloud execution, GSheets MCP, version control,
collaboration.

This repository contains the public documentation and registry metadata for the
hosted Bridge Town MCP connector. The production server implementation is
proprietary and is operated by Bridge Town.

- Website: <https://bridgetown.builders>
- App: <https://app.bridgetown.builders>
- Documentation: <https://docs.bridgetown.builders>
- MCP endpoint: `https://api.bridgetown.builders/mcp`
- Transport: MCP Streamable HTTP
- Authentication: OAuth for hosted connector flows; bearer tokens for clients
  that need manual configuration

## What Bridge Town Does

Bridge Town is an MCP-native, git-versioned financial modeling platform for FP&A
teams and finance leaders. AI agents use Bridge Town tools to create projects,
write Python model files, run models in isolated cloud sandboxes, query data,
write outputs to Google Sheets, create dashboards, branch scenarios, and
collaborate with teammates.

Claude.ai is the most common connection path and uses OAuth. Claude Code, Claude
Desktop, Codex, OpenCode, Cursor, and custom MCP clients can connect to the same
Streamable HTTP endpoint with a Bridge Town API token.

Bridge Town does not run a server-side LLM or proxy your prompts. Your selected
AI client and model provider run the conversation; Bridge Town receives
structured MCP tool calls.

## Connect

### Claude.ai

1. Open Claude.ai.
2. Go to **Customize** -> **+** -> **Add custom connector**.
3. Paste:

   ```text
   https://api.bridgetown.builders/mcp
   ```

4. Name the connector **Bridge Town**.
5. Approve the Bridge Town OAuth prompt.

No API token is required for Claude.ai.

### Generic MCP Client

For clients that support Streamable HTTP plus headers:

```json
{
  "mcpServers": {
    "bridge-town": {
      "transport": {
        "type": "http",
        "url": "https://api.bridgetown.builders/mcp",
        "headers": {
          "Authorization": "Bearer btk_YOUR_TOKEN"
        }
      }
    }
  }
}
```

Generate tokens from <https://app.bridgetown.builders/connect>. Tokens start
with `btk_` and can be revoked from the same page.

For clients that only support spawn-based MCP configuration, use `mcp-remote`:

```json
{
  "mcpServers": {
    "bridge-town": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://api.bridgetown.builders/mcp",
        "--header",
        "Authorization: Bearer btk_YOUR_TOKEN"
      ]
    }
  }
}
```

See [Getting Started](docs/getting-started.md) for fuller setup instructions,
Google Sheets workflows, skills, and troubleshooting.

## MCP Surface

Bridge Town exposes a production MCP surface for financial modeling workflows:

- 75 tools across projects, models, runs, data, Google Sheets, dashboards,
  branches, pull requests, sharing, templates, billing, and metadata discovery
- MCP resources including `health://status`, `skills://`, `skill://{name}`,
  `templates://`, and `template://{name}`
- Workflow prompts and skill templates for common FP&A tasks

For large tool surfaces, start with these discovery tools:

- `search_tools` - find the right Bridge Town tool or skill for a task
- `get_tool` - retrieve a full tool schema
- `get_skill` - compatibility bridge for clients that cannot read MCP resources

## Registry Metadata

The canonical registry manifest for this public listing is
[server.json](server.json). It points to the hosted remote MCP server:

```text
https://api.bridgetown.builders/mcp
```

This repo exists so MCP directories that require a GitHub URL can link to a
stable public source of documentation and metadata without requiring Bridge Town
to open source its commercial server.

## Local Stdio Shim

Most hosted clients should connect directly to the Streamable HTTP endpoint.
For registries or local MCP hosts that require a stdio binary, this repository
also provides a minimal shim:

```bash
BRIDGE_TOWN_API_TOKEN=btk_YOUR_TOKEN npx github:Bridge-Town/financial-modeling-mcp
```

The shim exposes `bridge-town-mcp` over stdio and forwards MCP JSON-RPC messages
to:

```text
https://api.bridgetown.builders/mcp
```

Configuration:

| Variable | Required | Description |
| --- | --- | --- |
| `BRIDGE_TOWN_API_TOKEN` | yes | Bridge Town API token from <https://app.bridgetown.builders/connect> |
| `BRIDGE_TOWN_MCP_URL` | no | Override the hosted MCP URL, mainly for local development |

The shim does not read or write local files and does not spawn child processes.
It only makes HTTPS requests to the Bridge Town MCP API.

## Security

Bridge Town is tenant-isolated, OAuth-backed, and designed for financial data.
Financial model execution runs in isolated containers with no outbound network.
Google Sheets access uses Google's `drive.file` scope so Bridge Town can only
access Sheets a user selects through the Bridge Town flow or Sheets created by
Bridge Town.

Report security issues privately. Do not open public GitHub issues for
vulnerabilities. See [SECURITY.md](SECURITY.md).
