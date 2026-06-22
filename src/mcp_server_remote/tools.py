# tools.py
# Defines tools for the MCP server to run.
# NOTE: may benefit from beefing up docstrings for future LLM content since they are passed through the functions that define the tools

import subprocess
from datetime import datetime # TEMP code for dev & testing, remove in prod
from pathlib import Path

# CONSTANTS
COMMAND_TIMEOUT_SECONDS = 60    # max time elapsed running each command to protect from hung processes
MAX_READ_BYTES = 100_000        # max file read in one call to protect LLM context window & tokens


### all tools register on MCP server through register_tools()
def register_tools(mcp_server, config):
    """Register MCP tools with MCP server instance and config file arguments"""
    allowed_commands = config["tools"]["allowed_commands"]
    allowed_roots = config["tools"]["allowed_roots"]


    def path_is_allowed(target_object: Path, allowed_roots: list[str]) -> bool:
        """Check if target_object filepath argument passed is under a root that is allowed to be acccessed"""
        for root in allowed_roots:
            resolved_root = Path(root).resolve()
            if target_object.is_relative_to(resolved_root): # .is_relative_to() checks if filepath is under resolved_root path
                return True
            return False

    ### -----------------
    ### --- MCP Tools ---
    ### -----------------
    @mcp_server.tool
    def read_file(filepath: str) -> str:
        """Read a text file in (utf-8 format) from the host and return its values as a string"""
        # confirm object at filepath is allowed to be accessed
        target_object = Path(filepath).resolve()
        if not path_is_allowed(target_object, allowed_roots):
            return f"DENIED: {target_object} not within filepaths allowed by config."
        #
        try: # error handling
            text_read = target_object.read_text(encoding="utf-8")[MAX_READ_BYTES]
            return text_read
        except:
            return f"ERROR: Cannot read file"




    ### TEMP code for dev & testing, remove in prod
    @mcp_server.tool
    def get_time() -> str:
        """Return the server's host machine current date and time"""
        date_time = datetime.now().isoformat(timespec="seconds")
        return date_time



