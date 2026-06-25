# mcp-server-remote

MCP server that serves a remote MCP client, ready-to-run tools and preset configuration files. 

*Intented for use within private network for Cybersecurity purposes.*

### Remote MCP System Architecture Flowchart

{user} <--> mcp-client-console <--> network <--> {box} <--> mcp-server-remote <--> tools

### mcp-server-remote Architecture Flowchart

mcp-client-console <--> {mcp SDK} <--> * <--> auth.py <--> server.py <--> tools.py

## User Guide | Installation

### Users: install commands
    :~$ pipx install mcp-server-remote
    :~$ mcp-server-remote
    
### Developers: install commands
    :~$ git clone https://github.com/geomux/mcp-server-remote.git
    :~$ cd mcp-server-remote
    :~$ python3 -m venv .venv
    :~$ source .venv/bin/activate
    :~$ pip install -e .
    :~$ mcp-server-remote

## User Guide | Configuration

First run will create a default config.toml file and print the filepath to the config file.

Navigate to the filepath, edit the config file- populate with server name, url, token. 

*The client reads from "config.toml" to configure and define MCP server.*

EXAMPLE:
```
[server]
name = "Box_1"      # Label for this machine
host = "127.0.0.1"  # IP/Domain for this machine
port = 9000         # Choose port nginx proxies to
path = "/mcp"       # Leave this alone. /mcp is default for dependencies.
```
### OS Config Filepath
Linux: ~/.config/mcp-server-remote/config.toml
macOS: ~/Library/Application Support/mcp-server-remote/config.toml
Windows: %LOCALAPPDATA%\mcp-server-remote\config.toml

/config command may be used to print filepath within the termianl chat.

    
## User Guide | Operation

Configure MCP server first, see related / requires repos below.

Confirm the MCP client is configured to connect to server.

*The server connects, performs MCP handshake, lists the available tools to the client.*


## Related / Required Repos

### mcp-client-console
    https://github.com/geomux/mcp-client-console

### mcp-gateway-remote
    https://github.com/geomux/mcp-gateway-remote


## --
## Project Status
## --
- [x] Create MCP server repo
- [x] Connect to MCP client locally
- [ ] Add additional tools to Tools.py
- [ ] Connect to MCP server remotely with TLS + bearer auth


