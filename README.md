# mcp-server-remote

MCP server that serves a remote MCP client, ready-to-run tools and preset configuration files.

*Intended for use within private network for Cybersecurity purposes.*

```
System:  {user} <--> mcp-client-console <--> network <--> {box} <--> mcp-server-remote <--> tools
Server:  mcp-client-console <--> {mcp SDK} <--> * <--> auth.py <--> server.py <--> tools.py
```

## User Guide | Installation

Users:

```bash
pipx install mcp-server-remote
mcp-server-remote
```

Developers:

```bash
git clone https://github.com/geomux/mcp-server-remote.git
cd mcp-server-remote
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
mcp-server-remote
```

## User Guide | Configuration

First run creates a default `config.toml` and prints its filepath (the `/config` command in the terminal chat prints it too). Edit it — populate with server name, url, token:

```toml
[server]
name = "Box_1"      # Label for this machine
host = "127.0.0.1"  # IP/Domain for this machine
port = 9000         # Choose port nginx proxies to
path = "/mcp"       # Leave this alone. /mcp is default for dependencies.
```

| OS      | Config filepath                                               |
| ------- | ------------------------------------------------------------- |
| Linux   | `~/.config/mcp-server-remote/config.toml`                     |
| macOS   | `~/Library/Application Support/mcp-server-remote/config.toml` |
| Windows | `%LOCALAPPDATA%\mcp-server-remote\config.toml`                |

## User Guide | Operation

Configure the MCP server first, then confirm the MCP client (see repos below) is configured to connect to it. The server accepts the connection, performs the MCP handshake, and lists the available tools to the client.

## Related / Required Repos

- [mcp-client-console](https://github.com/geomux/mcp-client-console)
- [mcp-gateway-remote](https://github.com/geomux/mcp-gateway-remote)

## Project Status

- [x] Create MCP server repo
- [x] Connect to MCP client locally
- [ ] Add additional tools to tools.py
- [ ] Connect to MCP server remotely with TLS + bearer auth
