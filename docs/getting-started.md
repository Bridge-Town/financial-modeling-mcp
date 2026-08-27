# Getting Started with Bridge Town MCP

Bridge Town exposes one hosted MCP Streamable HTTP endpoint:

```text
https://api.bridgetown.builders/mcp
```

Bridge Town does not expose an SSE-only transport. A client limited to
spawn-based MCP configuration can connect through `mcp-remote`.

## 1. Create an account

Sign in at <https://app.bridgetown.builders>, then open **Models**. A model is a
git-versioned repository containing Python model files, data snapshots, Native
Sheets, and reusable `lib/` code.

## 2. Connect a client

For Claude.ai, add `https://api.bridgetown.builders/mcp` as a custom connector,
name it **Bridge Town**, and approve OAuth.

For Claude Code, Codex, Claude Desktop, Cursor, or another client that supports
HTTP headers, generate a `btk_` token at
<https://app.bridgetown.builders/connect> and configure:

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

Keep tokens out of model files and conversation examples. Revoke a token from
the same Connect page when it is no longer needed.

## 3. Build and run a model

Ask the connected client to create or select a model, write a Python file, and
run it. The normal current flow uses:

1. `list_models` or `create_model`.
2. `commit_files` to write an atomic set of files.
3. `run_model` to execute in the network-isolated sandbox.
4. `get_run` for status or `get_run_output` for one named output.

Use `search_tools` when you need a different goal and `get_tool` to inspect the
selected tool's complete schema. The production catalog contains exactly 78
tools across 18 domains.

## 4. Use Native Sheet inputs safely

Do not parse a committed `.btsheet.json` document directly from model code.
Install the immutable
[`native_sheet_reader.py` v1.0.0](../model-authoring-helpers/v1.0.0/native_sheet_reader.py)
at `lib/native_sheet_reader.py`, verify it against
[`SHA256SUMS`](../model-authoring-helpers/v1.0.0/SHA256SUMS), and read required
cells with `NativeSheetReader`. The helper preserves blank, formula, and zero
states while emitting bounded, value-free canonical read identities.

The task guide is published at
<https://www.bridgetown.builders/docs/guides/native-sheet-model-inputs>.

## 5. Add output lineage

Install the immutable
[`output_lineage.py` v1.0.0](../model-authoring-helpers/v1.0.0/output_lineage.py)
at `lib/output_lineage.py` and verify its digest. `OutputLineageBuilder` writes
a bounded `/outputs/output_lineage.json` graph so cell explanations can show
recorded precedents and dependents.

The task guide is published at
<https://www.bridgetown.builders/docs/guides/output-lineage-authoring>.

## 6. Google Sheets

Connect a spreadsheet through the Bridge Town Picker flow. Google `drive.file`
scope prevents Bridge Town from browsing files the user did not select or
Bridge Town did not create. Use `list_data_sources` and `query_data` for
snapshots, or the dedicated Google Sheets tools for metadata, bounded range
reads, spreadsheet creation, row appends, and run-output publication.

## Troubleshooting

### 401 Unauthorized

- Confirm the header is `Authorization: Bearer btk_...`.
- Generate a new token if the original was mistyped, expired, or revoked.
- For OAuth clients, disconnect and reconnect the connector.

### Tools are missing

- Confirm the URL ends in `/mcp`.
- Restart the client after changing configuration.
- Call `search_tools` for the current goal.

### GET /mcp returns 405

This is expected for a raw browser request. MCP clients use Streamable HTTP
POST requests. Do not add `/sse`, a provider name, or a version suffix.

## Related links

- Website: <https://www.bridgetown.builders>
- App: <https://app.bridgetown.builders>
- Docs: <https://www.bridgetown.builders/docs/>
- Security: <https://www.bridgetown.builders/security>
- Support: <mailto:support@bridgetown.builders>
