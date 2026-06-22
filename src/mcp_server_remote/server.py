# server.py
# Uses MCP (within Streamable HTTP packets) to coordinate with MCP client
# Entry point for remote connections, loads config, opens a session, runs tools, returns messages to client.
### ...lots of notes below because dense...

from fastmcp import FastMCP
from mcp_server_remote.config_loader import config_load
from mcp_server_remote.auth import resolve_auth
from mcp_server_remote.tools import register_tools

### Build the server, set up configuration, register tools, begin listening for client
def main():
    """Run MCP Server Instance, open entry point for remote connections, load config, open a session, run tools, return messages to client"""
    config = config_load() # config file dictionary
    server = config["server"] # server table (inside config file dict)

    print("_"*50)
    print(f"Starting {server['name']} on {server['host']}:{server['port']}{server['path']}.")
    print("_"*50)

    ### ---------------------------
    ### --- MCP Server Instance ---
    ### ---------------------------
    mcp_server = FastMCP(
        name=server["name"],
        auth=resolve_auth(config)
        )

    register_tools(mcp_server, config) # register available tools

    mcp_server.run(
        transport="http",
        host=server['host'],
        port=server['port'],
        path=server['path']
        )

if __name__ == "__main__":
    main()

