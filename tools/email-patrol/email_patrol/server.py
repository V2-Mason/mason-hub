"""Gmail MCP Server for Email Patrol Agent.

Exposes Gmail operations as MCP tools via FastMCP.

Usage:
    python -m email_patrol.server              # stdio transport (local)
    python -m email_patrol.server --streamable  # streamable-http (Railway)
"""

import os
import sys
from typing import Optional

from fastmcp import FastMCP

from .gmail import GmailClient

mcp = FastMCP(
    "Email Patrol",
    instructions="Gmail MCP Server for daily email patrol automation",
)

_client: Optional[GmailClient] = None


def _get_client() -> GmailClient:
    global _client
    if _client is None:
        _client = GmailClient()
    return _client


@mcp.tool()
def search_emails(query: str, max_results: int = 50) -> list[dict]:
    """Search emails using Gmail query syntax.

    Args:
        query: Gmail search query (e.g. "is:unread", "from:user@example.com after:2026/04/01")
        max_results: Maximum number of results to return (default 50)
    """
    return _get_client().search_emails(query, max_results)


@mcp.tool()
def read_email(message_id: str) -> dict:
    """Read a single email's full content and metadata.

    Args:
        message_id: The Gmail message ID (from search_emails results)
    """
    return _get_client().read_email(message_id)


@mcp.tool()
def read_thread(thread_id: str) -> list[dict]:
    """Read all messages in an email thread.

    Args:
        thread_id: The Gmail thread ID
    """
    return _get_client().read_thread(thread_id)


@mcp.tool()
def delete_emails(message_ids: list[str]) -> list[dict]:
    """Move emails to trash (recoverable for 30 days).

    Args:
        message_ids: List of message IDs to trash
    """
    return _get_client().delete_emails(message_ids)


@mcp.tool()
def archive_emails(message_ids: list[str]) -> list[dict]:
    """Archive emails (remove from inbox, keep in All Mail).

    Args:
        message_ids: List of message IDs to archive
    """
    return _get_client().archive_emails(message_ids)


@mcp.tool()
def apply_label(message_ids: list[str], label_id: str) -> list[dict]:
    """Add a label to emails.

    Args:
        message_ids: List of message IDs
        label_id: The label ID to apply (from list_labels)
    """
    return _get_client().apply_label(message_ids, label_id)


@mcp.tool()
def remove_label(message_ids: list[str], label_id: str) -> list[dict]:
    """Remove a label from emails.

    Args:
        message_ids: List of message IDs
        label_id: The label ID to remove
    """
    return _get_client().remove_label(message_ids, label_id)


@mcp.tool()
def send_email(to: str, subject: str, body: str, thread_id: str = "") -> dict:
    """Send an email. RESTRICTED: only call after Mason approves reply report.

    Args:
        to: Recipient email address
        subject: Email subject line
        body: Email body text
        thread_id: Optional thread ID to reply within
    """
    return _get_client().send_email(to, subject, body, thread_id or None)


@mcp.tool()
def create_draft(to: str, subject: str, body: str, thread_id: str = "") -> dict:
    """Create an email draft.

    Args:
        to: Recipient email address
        subject: Email subject line
        body: Email body text
        thread_id: Optional thread ID to reply within
    """
    return _get_client().create_draft(to, subject, body, thread_id or None)


@mcp.tool()
def unsubscribe(message_id: str) -> dict:
    """Unsubscribe from a mailing list using multi-strategy approach.

    Tries in order: List-Unsubscribe header > body link > fail.
    Returns status and method used, or failure reason.

    Args:
        message_id: The Gmail message ID of a newsletter/subscription email
    """
    return _get_client().unsubscribe(message_id)


@mcp.tool()
def list_labels() -> list[dict]:
    """List all Gmail labels (system and user-created)."""
    return _get_client().list_labels()


@mcp.tool()
def get_profile() -> dict:
    """Get authenticated Gmail account profile info."""
    return _get_client().get_profile()


if __name__ == "__main__":
    if "--streamable" in sys.argv:
        host = os.environ.get("HOST", "0.0.0.0")
        port = int(os.environ.get("PORT", "8000"))
        mcp.run(transport="streamable-http", host=host, port=port)
    else:
        mcp.run(transport="stdio")
