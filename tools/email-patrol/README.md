# Email Patrol MCP Server

Self-hosted Gmail MCP Server for daily email patrol.

## Setup

1. Place `credentials.json` from Google Cloud Console in this directory
2. `pip install -e .`
3. `python -m email_patrol.auth` to generate token.json
4. `python -m email_patrol.server` to start MCP server
