# tools.py
# Defines tools for the MCP server to run.
# NOTE: MAJOR benefit from beefing up docstrings for LLM context since they are passed through the functions that define the tools

import platform
import shlex
import subprocess
from pathlib import Path
from mcp_server_remote._vendor import toolshape

# CONSTANTS
COMMAND_TIMEOUT_SECONDS = 60    # max time elapsed running each command to protect from hung processes
MAX_READ_BYTES = 100_000        # max file read in one call to protect LLM context window & tokens


### all tools register on MCP server through register_tools()
def register_tools(mcp_server, config):
    """Register MCP tools with MCP server instance and config file arguments"""
    os = {"Linux": "linux", "Windows": "windows", "Darwin": "macos"[platform.system()]}
    allowed_commands = config["tools"]["commands"][os]
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
    @mcp_server.tool(description=toolshape.READ_FILE_DESCRIPTION)
    def read_file(filepath: str) -> str:
        """
            Read a file (in utf-8 format) from the host and return its values as a string
        """
        # confirm object at filepath is allowed to be accessed
        target_object = Path(filepath).resolve()
        if not path_is_allowed(target_object, allowed_roots):
            return f"DENIED: {target_object} not within filepaths allowed by config."
        try:
            text_read = target_object.read_text(encoding="utf-8",errors="replace")
            return toolshape.read_receipt(
                target_object,
                text_read[:MAX_READ_BYTES],
                truncated=len(text_read) > MAX_READ_BYTES,
                )
        except FileNotFoundError:
            return f"ERROR: {target_object} not found."
        except Exception as error:
            return f"ERROR: Cannot read {target_object}: {error}"

    @mcp_server.tool(description=toolshape.WRITE_FILE_DESCRIPTION)
    def write_file(filepath: str, data_write: str | int | float) -> str:
        """
            Write to a file (in utf-8 format) on the host and return confirmation that the write was completed.
        """
        target_object = Path(filepath).resolve()
        if not path_is_allowed(target_object, allowed_roots):
            return f"DENIED: {target_object} not within filepaths allowed by config."
        try:
            with open(target_object, "w", encoding="utf-8") as f:
                f.write(str(data_write)) # since data_write could be int/float, it must be converted to a string for open() to write to a file.
            return toolshape.write_receipt(target_object, len(str(data_write)))
        except FileNotFoundError:
            return f"ERROR: {target_object} not found."
        except Exception as error:
            return f"ERROR: Cannot write to {target_object}: {error}"

    @mcp_server.tool(description=toolshape.RUN_COMMAND_DESCRIPTION)
    def run_command(command: str) -> str:
        """
            Run one allowed command on the host machine and return its output.
            NOTE: The command's binary (first word) must be in the config allowed_commands list.
            NOTE: Flags and non-path arguments are passed through unchecked. Any argument that looks like a filesystem path (starts with /, ~, or .) is checked against allowed_roots.
            NOTE: If a command or path is denied, tool will return why.
        """
        try:
            tokens = shlex.split(command.strip())
        except ValueError as error:
            return f"ERROR: could not parse command: {error}"

        if not tokens:
            return "DENIED: empty command"

        cmd_binary = tokens[0]
        if cmd_binary not in allowed_commands:
            allowed_commands_string = ", ".join(allowed_commands)
            return toolshape.denied(f"'{cmd_binary}' is not allowed.", allowed=allowed_commands)

        # check to see if any arguments are paths/look like parths
        for token in tokens[1:]:
            if token.startswith("-"):
                continue # argument is a flag
            looks_like_path = (
                "/" in token
                or "\\" in token
                or token.startswith("~")
                or token.startswith(".")
            )
            if not looks_like_path:
                continue # argument is not a path
            target_object = Path(token).expanduser().resolve()
            if not path_is_allowed(target_object, allowed_roots):
                return f"DENIED: path '{target_object}' is not within filepaths allowed by config file."

        try:
            complete_command = subprocess.run(
                    tokens,
                    capture_output = True,
                    text = True,
                    timeout = COMMAND_TIMEOUT_SECONDS,
                )
        except subprocess.TimeoutExpired:
            return toolshape.error(f"'{command}' timed out after {COMMAND_TIMEOUT_SECONDS} seconds.")
        except FileNotFoundError:
            return f"ERROR: '{cmd_binary}' is allowed but not found on this remote machine."

        return toolshape.command_receipt(
            command,
            complete_command.returncode,
            complete_command.stout[:MAX_READ_BYTES],
            complete_command.stderr[:10_000]
            truncated=len(complete_command.stdout) > MAX_READ_BYTES,
            )




