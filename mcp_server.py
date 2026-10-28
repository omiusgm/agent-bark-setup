#!/usr/bin/env python3
"""Stdio MCP: explicit calls only, no hooks, no background collection."""
from mcp.server.fastmcp import FastMCP
from bark_server import notify

mcp = FastMCP("agent-bark")

@mcp.tool()
def send_attention(kind: str, project: str, chat: str, host: str, message: str,
                   event_id: str, url: str = "", icon: str = "", dry_run: bool = False) -> dict:
    """Send only when the owner must answer, approve, review a finished task, or handle a serious blocker.

    kind: question, approval, review, error. Supply exact project, chat and machine names.
    message: concise, no private details or secrets. event_id: stable ID for this specific event;
    re-use it on retries. Optional url accepts only Telegram https links. icon: agent, approval,
    question, complete, warning, code, project, server, or empty. Server acceptance is not phone delivery.
    """
    try:
        return notify(kind, project, chat, host, message, event_id, url, icon, dry_run=dry_run)
    except (ValueError, RuntimeError) as exc:
        return {"status": "not_sent", "reason": str(exc)}

if __name__ == "__main__":
    mcp.run(transport="stdio")
