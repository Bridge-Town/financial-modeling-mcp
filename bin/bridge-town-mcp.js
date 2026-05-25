#!/usr/bin/env node

const DEFAULT_MCP_URL = "https://api.bridgetown.builders/mcp";
const mcpUrl = process.env.BRIDGE_TOWN_MCP_URL || DEFAULT_MCP_URL;
const token = process.env.BRIDGE_TOWN_API_TOKEN;

let sessionId = null;
let buffer = Buffer.alloc(0);
let pendingRequests = 0;
let inputEnded = false;

if (!token) {
  console.error(
    "BRIDGE_TOWN_API_TOKEN is required. Generate one at https://app.bridgetown.builders/connect.",
  );
  process.exit(1);
}

process.stdin.on("data", (chunk) => {
  buffer = Buffer.concat([buffer, chunk]);
  drainInput();
});

process.stdin.on("end", () => {
  inputEnded = true;
  maybeExit();
});

process.stdin.resume();

function drainInput() {
  while (true) {
    const headerEnd = buffer.indexOf("\r\n\r\n");
    if (headerEnd === -1) {
      return;
    }

    const header = buffer.subarray(0, headerEnd).toString("utf8");
    const lengthMatch = /^Content-Length:\s*(\d+)$/im.exec(header);
    if (!lengthMatch) {
      failAndExit("Invalid MCP stdio frame: missing Content-Length header.");
    }

    const length = Number.parseInt(lengthMatch[1], 10);
    const messageStart = headerEnd + 4;
    const messageEnd = messageStart + length;

    if (buffer.length < messageEnd) {
      return;
    }

    const payload = buffer.subarray(messageStart, messageEnd).toString("utf8");
    buffer = buffer.subarray(messageEnd);

    let message;
    try {
      message = JSON.parse(payload);
    } catch (error) {
      failAndExit(`Invalid MCP JSON payload: ${error.message}`);
    }

    pendingRequests += 1;
    forwardMessage(message)
      .catch((error) => {
        writeErrorResponse(message, -32603, error.message);
      })
      .finally(() => {
        pendingRequests -= 1;
        maybeExit();
      });
  }
}

async function forwardMessage(message) {
  const headers = {
    accept: "application/json, text/event-stream",
    authorization: `Bearer ${token}`,
    "content-type": "application/json",
  };

  if (sessionId) {
    headers["mcp-session-id"] = sessionId;
  }

  const response = await fetch(mcpUrl, {
    method: "POST",
    headers,
    body: JSON.stringify(message),
  });

  const nextSessionId = response.headers.get("mcp-session-id");
  if (nextSessionId) {
    sessionId = nextSessionId;
  }

  if (response.status === 202 || response.status === 204) {
    return;
  }

  const body = await response.text();

  if (!response.ok) {
    writeErrorResponse(
      message,
      response.status === 401 ? -32001 : -32603,
      `Bridge Town MCP request failed with HTTP ${response.status}.`,
    );
    return;
  }

  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("text/event-stream")) {
    writeSseMessages(body);
    return;
  }

  if (!body.trim()) {
    return;
  }

  writeJson(JSON.parse(body));
}

function writeSseMessages(body) {
  for (const event of body.split(/\n\n+/)) {
    const dataLines = event
      .split(/\r?\n/)
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trimStart());

    if (dataLines.length === 0) {
      continue;
    }

    const data = dataLines.join("\n").trim();
    if (!data || data === "[DONE]") {
      continue;
    }

    writeJson(JSON.parse(data));
  }
}

function writeErrorResponse(message, code, messageText) {
  if (!message || !Object.hasOwn(message, "id")) {
    console.error(messageText);
    return;
  }

  writeJson({
    jsonrpc: "2.0",
    id: message.id,
    error: {
      code,
      message: messageText,
    },
  });
}

function writeJson(message) {
  const body = JSON.stringify(message);
  process.stdout.write(`Content-Length: ${Buffer.byteLength(body)}\r\n\r\n${body}`);
}

function failAndExit(message) {
  console.error(message);
  process.exit(1);
}

function maybeExit() {
  if (inputEnded && pendingRequests === 0 && buffer.length === 0) {
    process.exit(0);
  }
}
