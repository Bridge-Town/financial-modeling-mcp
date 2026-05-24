# Getting Started with Bridge Town MCP

Bridge Town exposes one hosted MCP endpoint:

```text
https://api.bridgetown.builders/mcp
```

Use this endpoint from Claude.ai, Claude Code, Claude Desktop, Codex, OpenCode,
Cursor, Smithery, Glama, mcp.so, or any MCP-compatible client that supports
Streamable HTTP.

## Connection Profile

| Field | Value |
| --- | --- |
| Transport | MCP Streamable HTTP |
| Cloud URL | `https://api.bridgetown.builders/mcp` |
| Local dev URL | `http://localhost:8000/mcp` |
| OAuth discovery | `https://api.bridgetown.builders/.well-known/oauth-authorization-server` |
| Health endpoint | `https://api.bridgetown.builders/health` |
| Health resource | `health://status` |

Bridge Town does not expose an SSE-only transport. Clients that only support
legacy spawn-based MCP configuration can connect through `mcp-remote`.

## 1. Create a Bridge Town Account

Sign up at:

```text
https://app.bridgetown.builders
```

Then open **Models** to view or create projects. A project is a versioned
workspace that holds model code, data sources, run outputs, dashboards, and
collaboration state.

## 2. Connect Claude.ai

Claude.ai is the recommended first path because it uses OAuth and does not
require an API token.

1. Open Claude.ai.
2. Click **Customize**.
3. Click **+** and choose **Add custom connector**.
4. Paste:

   ```text
   https://api.bridgetown.builders/mcp
   ```

5. Set the name to **Bridge Town**.
6. Click **Connect**.
7. Sign in to Bridge Town and approve the OAuth prompt.

Verify the connection by asking Claude:

```text
Check if Bridge Town is connected.
```

Claude should be able to read `health://status` and show the authenticated
workspace context.

## 3. Connect Other MCP Clients

For Claude Code, Claude Desktop, Codex, OpenCode, Cursor, custom agents, and
other MCP clients, generate a token first:

1. Sign in to <https://app.bridgetown.builders>.
2. Open <https://app.bridgetown.builders/connect>.
3. Generate an API token.
4. Copy it immediately. Tokens start with `btk_`.

### Native HTTP Configuration

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

### Spawn-Based Configuration with mcp-remote

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

### CLI Pattern

```bash
<client> mcp add bridge-town https://api.bridgetown.builders/mcp \
  --transport http \
  --header "Authorization: Bearer btk_YOUR_TOKEN"
```

For Claude Code, the concrete command is:

```bash
claude mcp add bridge-town https://api.bridgetown.builders/mcp \
  --transport http \
  --header "Authorization: Bearer btk_YOUR_TOKEN"
```

## 4. Build Your First Model

Ask your agent:

```text
Create a 12-month revenue forecast model in my forecasts project. Use three
product lines: SaaS, Services, and Marketplace. Start from January 2026.
```

The agent will typically:

1. Call `create_project` if the project does not exist.
2. Call `commit_files` or file editing tools to write Python model code.
3. Call `run` to execute the model in Bridge Town's sandbox.
4. Return stdout, structured outputs, files, or dashboards.

You can then iterate naturally:

```text
Add a 10% annual growth rate to the SaaS line and rerun the model.
```

## 5. Google Sheets Workflows

Bridge Town integrates with Google Sheets through a Picker-based flow and
Google `drive.file` scope. Bridge Town cannot browse or access Sheets you have
not selected through the Bridge Town app or Sheets it did not create.

### Connect a Sheet

1. Open <https://app.bridgetown.builders>.
2. Open the target project.
3. Go to **Data Sources** -> **Connect Google Sheet**.
4. Complete the Google sign-in flow.
5. Select a Sheet through Google Picker.
6. Bridge Town records the Sheet as a project data source with a `source_name`.

Then ask your agent to list connected sources:

```text
List the data sources in my revenue-model project.
```

### Import a Sheet Snapshot

The agent can call `ingest_data_source`:

```json
{
  "name": "ingest_data_source",
  "arguments": {
    "project_name": "revenue-model",
    "spec": {
      "kind": "google_sheet_snapshot",
      "source_name": "revenue_model_actuals",
      "tab_names": ["Sales", "Costs"]
    }
  }
}
```

Omit `tab_names` to import all tabs. Use `query_data` to inspect the snapshot:

```sql
SELECT product_line, SUM(revenue) AS total
FROM revenue_model_actuals_Sales
GROUP BY product_line
ORDER BY total DESC
```

### Write Results Back to Google Sheets

Use `write_gsheet` to write model output to a connected Sheet:

```json
{
  "name": "write_gsheet",
  "arguments": {
    "project_name": "revenue-model",
    "spec": {
      "mode": "replace",
      "run_id": "uuid-from-run",
      "output_name": "forecast.json",
      "source_name": "revenue_model_actuals",
      "cell_range": "Forecast!A1"
    }
  }
}
```

Use `format_gsheet` and `modify_gsheet_structure` for finance-grade statement
layouts, sheet structure, column widths, number formats, and visual styling.

## 6. Skills and Agent Guidance

Bridge Town ships bundled skill templates for common FP&A workflows. The
canonical MCP resources are:

| Resource URI | Purpose |
| --- | --- |
| `skills://` | Catalog of bundled skills |
| `skill://{name}` | Full metadata and raw template body for one skill |

Some hosted MCP clients cannot read MCP resources autonomously during a
conversation. For those hosts, Bridge Town exposes `get_skill` as a compatibility
tool that reads from the same canonical skill registry.

Recommended Claude.ai flow:

1. Ask naturally, for example:

   ```text
   Format my P&L Google Sheet using standard financial statement styles.
   ```

2. Claude calls `search_tools` and receives `skill_matches`.
3. Claude calls `get_skill(name="bridge-town-gsheet-formatting",
   include_template=true)`.
4. Claude applies the returned guidance and calls related tools such as
   `write_gsheet`, `format_gsheet`, and `modify_gsheet_structure`.

## 7. Tool Discovery

Bridge Town exposes 75 MCP tools. For clients that prefer a small initial tool
set, load these hot tools first and defer the rest:

```text
search_tools, get_tool, list_projects, create_project, list_files, read_file,
describe_model, commit_files, patch_file, run, get_run, list_runs,
list_data_sources, query_data
```

When the user asks for something outside that set, call:

```json
{
  "name": "search_tools",
  "arguments": {
    "query": "what the user wants to do"
  }
}
```

Then call `get_tool` for the selected tool schema before invoking it.

## 8. Smithery

Bridge Town is listed on Smithery at:

```text
https://smithery.ai/servers/bridge-town/finance
```

Connection profile:

| Field | Value |
| --- | --- |
| Namespace | `bridge-town` |
| Server ID | `finance` |
| MCP endpoint | `https://api.bridgetown.builders/mcp` |
| Transport | MCP Streamable HTTP |
| Authentication | OAuth through Bridge Town |
| Session parameters | None required |

Do not paste Bridge Town API tokens into Smithery. Use the Bridge Town OAuth
flow.

## 9. Troubleshooting

### 401 Unauthorized

- Token is missing, mistyped, expired, or revoked.
- Confirm the header is exactly `Authorization: Bearer btk_...`.
- Generate a new token at <https://app.bridgetown.builders/connect>.

### Tools Not Showing Up

- Confirm the URL ends with `/mcp`.
- Restart the client after editing config.
- Ask the agent to call `search_tools`.
- If using Claude.ai, disconnect and reconnect the connector.

### Transport Not Supported

Bridge Town serves Streamable HTTP. If your client only supports legacy SSE or
spawn-based configuration, use `mcp-remote`.

### GET /mcp Returns 405

This is expected. Bridge Town's MCP endpoint is Streamable HTTP and expects MCP
client requests to use POST. Use the URL exactly:

```text
https://api.bridgetown.builders/mcp
```

Do not add `/sse`, `/v1`, or another suffix.

### Google Sheet Not Found

Bridge Town uses `drive.file` scope. Complete the Picker flow in the web app
first, then call `list_data_sources` to confirm the connected `source_name`.

## Related Links

- Website: <https://bridgetown.builders>
- App: <https://app.bridgetown.builders>
- Docs: <https://docs.bridgetown.builders>
- Smithery listing: <https://smithery.ai/servers/bridge-town/finance>
- Security: <https://bridgetown.builders/security>
- Support: <mailto:support@bridgetown.builders>

