# server.py
# Uses MCP (within Streamable HTTP packets) to coordinate with MCP client
# Entry point for remote connections, loads config, opens a session, runs tools, returns messages to client.
### ...lots of notes below because dense...

from fastmcp import FastMCP
from mcp_server_remote.config_loader import config_load, config_path
from mcp_server_remote.auth import resolve_auth
from mcp_server_remote.tools import register_tools
from mcp_server_remote import __version__
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

### Build the server, set up configuration, register tools, begin listening for client
def main():
    """Run MCP Server Instance, open entry point for remote connections, load config, open a session, run tools, return messages to client"""
    config = config_load() # config file dictionary
    server = config["server"] # server table (inside config file dict)
    auth = resolve_auth(config)

    print("_"*50)
    print(f"Starting {server['name']} v{__version__} on {server['host']}:{server['port']}{server['path']}.")
    print(f"Config: {config_path()}\n")
    print("Auth: bearer token required in config for authentication with client\n")
    print(f"Command tool: UNRESTRICTED shell access on remote host.")
    print("_"*50)

    ### ---------------------------
    ### --- MCP Server Instance ---
    ### ---------------------------
    mcp_server = FastMCP(
        name=server["name"],
        version=f"v{__version__}",
        auth=auth
        )

    register_tools(mcp_server, config) # register available tools

    ### --- CORS so browser-based MCP clients can connect (CLI clients ignore it) ---
    cors = [
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["mcp-protocol-version", "mcp-session-id", "Authorization", "Content-Type"],
            expose_headers=["mcp-session-id"],
        )
    ]

    ### ----------------------
    ### --- Run MCP Server ---
    ### ----------------------
    mcp_server.run(
        transport="http",
        host=server['host'],
        port=server['port'],
        path=server['path'],
        middleware=cors,
        )

if __name__ == "__main__":
    main()

