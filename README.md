# Bridge Town MCP Connector

Build financial models as code with cloud execution, Native Sheets, Google
Sheets, version control, and collaboration.

This public repository contains documentation, registry metadata, a minimal
stdio-to-HTTP shim, and versioned model-authoring helpers for the hosted Bridge
Town MCP connector. The commercial server implementation is operated by Bridge
Town and is not published here.

- Website: <https://www.bridgetown.builders>
- App: <https://app.bridgetown.builders>
- Documentation: <https://www.bridgetown.builders/docs/>
- MCP endpoint: `https://api.bridgetown.builders/mcp`
- Transport: MCP Streamable HTTP
- Authentication: OAuth for hosted connector flows; bearer tokens for manual
  client configuration

Bridge Town does not run a server-side LLM or proxy prompts. The user's chosen
AI client and model provider run the conversation; Bridge Town receives typed
MCP calls and executes deterministic platform operations.

## Connect

For Claude.ai, add `https://api.bridgetown.builders/mcp` as a custom connector
and approve the Bridge Town OAuth prompt.

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

Generate and revoke API tokens at <https://app.bridgetown.builders/connect>.
See [Getting Started](docs/getting-started.md) for setup, current task flows,
and troubleshooting.

## Canonical MCP surface

The production endpoint exposes the canonical 78-tool catalog across 18
domains. Use `search_tools` to find the correct current tool for a goal and
`get_tool` to retrieve its full schema. The catalog does not change based on
the client or user agent.

The canonical registry manifest for this public listing is [server.json](server.json).
It points to the hosted remote MCP server; it is not a copy of the proprietary
server implementation.

## Versioned model-authoring helpers

Small helper modules that are intended to run inside a model repository are
published as immutable, MIT-licensed releases:

- [`native_sheet_reader.py` v1.0.0](model-authoring-helpers/v1.0.0/native_sheet_reader.py)
  preserves Native Sheet missing/blank/formula states and emits bounded,
  value-free read identities.
- [`output_lineage.py` v1.0.0](model-authoring-helpers/v1.0.0/output_lineage.py)
  emits validated `output_lineage.json` dependency graphs.

The [v1.0.0 release directory](model-authoring-helpers/v1.0.0/) includes
runnable examples, a changelog, ownership, license, manifest, and
`SHA256SUMS`. Install a helper byte-for-byte at the manifest's `target_path`
and verify its digest before committing it to a model repository.

## Local stdio shim

Most clients should connect directly to the Streamable HTTP endpoint. A local
MCP host that requires stdio may use the minimal forwarding shim:

```bash
BRIDGE_TOWN_API_TOKEN=btk_YOUR_TOKEN npx github:Bridge-Town/financial-modeling-mcp
```

The shim does not read or write local files or spawn child processes. It only
forwards MCP JSON-RPC messages over HTTPS to the configured Bridge Town MCP
endpoint.

## Security

Financial model execution runs in an isolated container without outbound
network access. Google access uses `drive.file`, limiting Bridge Town to files
selected through the Bridge Town flow or created by Bridge Town.

Report vulnerabilities privately through [SECURITY.md](SECURITY.md). Do not
open a public issue or include customer data in a report.
