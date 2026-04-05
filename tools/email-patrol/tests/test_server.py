"""Tests for MCP Server tool definitions."""

import asyncio
import pytest
from unittest.mock import MagicMock, patch


def test_server_has_all_tools():
    """Verify all required tools are registered."""
    with patch("email_patrol.server.GmailClient"):
        from email_patrol.server import mcp
        tools = asyncio.run(mcp.list_tools())
        tool_names = [t.name for t in tools]
        expected = [
            "search_emails",
            "read_email",
            "read_thread",
            "delete_emails",
            "archive_emails",
            "apply_label",
            "remove_label",
            "send_email",
            "create_draft",
            "unsubscribe",
            "list_labels",
            "get_profile",
        ]
        for name in expected:
            assert name in tool_names, f"Missing tool: {name}"
