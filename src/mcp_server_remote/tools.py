# tools.py
# Defines tools for the MCP server to run.
# NOTE: MAJOR benefit from beefing up docstrings for LLM context since they are passed through the functions that define the tools

import shlex
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
        try:
            text_read = target_object.read_text(encoding="utf-8",errors="replace")
            return text_read[:MAX_READ_BYTES]
        except FileNotFoundError:
            return f"ERROR: {target_object} not found."
        except Exception as error:
            return f"ERROR: Cannot read {target_object}: {error}"

    @mcp_server.tool
    def run_command(command: str) -> str:
        """Run one allowed command on the host machine and return its output.
        Only commands in the config allowed_commands list may be run.
        Commands run must match allowed commands exactly- no extra arguments.
        If a command is denied, tool will return list of allowed commands so an allowed one may be selected."""
        command_selected = command.strip()
        if command_selected not in allowed_commands:
            allowed_commands_string = ", ".join(allowed_commands)
            return f"DENIED: '{command_selected}' is not allowed. Allowed commands: {allowed_commands_string}"
        try:
            complete_command = subprocess.run(
                shlex.split(command_selected),
                capture_output = True,
                text = True,
                timeout=COMMAND_TIMEOUT_SECONDS,
                )
        except subprocess.TimeoutExpired:
            return f"ERROR: '{command_selected}' timed out after {COMMAND_TIMEOUT_SECONDS}"

        command_output = complete_complete.stdout

        if complete_command.stderr:
            command_output += f"\n[stderr]\n{complete_command.stderr}"
        if complete.returncode != 0:
            command_output += f"\n[exit code {complete_command.returncode}]"
        return command_output[:MAX_READ_BYTES] if command_output.strip() else "(no command output)"



