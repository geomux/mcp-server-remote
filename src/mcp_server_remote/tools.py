# tools.py
# Defines tools for the MCP server to run.
# NOTE: MAJOR benefit from beefing up docstrings for LLM context since they are passed through the functions that define the tools

import platform
import subprocess
from pathlib import Path
from mcp_server_remote._vendor import toolshape

# CONSTANTS
COMMAND_TIMEOUT_SECONDS = 60    # max time elapsed running each command to protect from hung processes
MAX_READ_BYTES = 100_000        # max file read in one call to protect LLM context window & tokens

# run_command's teaching text lives here rather than in _vendor/toolshape: the vendored package is an
# add-only companion with its own provenance, and this escape hatch is local policy, not part of it.
RUN_COMMAND_DESCRIPTION = (
    "Run ANY command line on the host through a real shell and return its output as a receipt.\n"
    "SHELL SYNTAX WORKS here: pipes |  redirects > <  chaining && ;  wildcards *  $VARS all expand.\n"
    "Windows runs the line in PowerShell; Linux and macOS run it in the system shell.\n"
    "Each call costs the user a manual approval, so send ONE complete command line, not a probing sequence.\n"
    "ERROR: = the tool could not run it. Empty stdout is a real result - rerunning cannot change it."
)

### all tools register on MCP server through register_tools()
def register_tools(mcp_server, config):
    """Register MCP tools with MCP server instance and config file arguments"""
    allowed_roots = config["tools"]["allowed_roots"]
    on_windows = platform.system() == "Windows"

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
            NOTE: Missing parent folders are created automatically (the full path already passed the allowed_roots check).
        """
        target_object = Path(filepath).resolve()
        if not path_is_allowed(target_object, allowed_roots):
            return f"DENIED: {target_object} not within filepaths allowed by config."
        try:
            target_object.parent.mkdir(parents=True, exist_ok=True) # create missing parent folders so writes into brand-new folders work
            with open(target_object, "w", encoding="utf-8") as f:
                f.write(str(data_write)) # since data_write could be int/float, it must be converted to a string for open() to write to a file.
            return toolshape.write_receipt(target_object, len(str(data_write)))
        except FileExistsError:
            return toolshape.error(
                f"cannot write {target_object}: a FILE (not a folder) already exists at one of its parent paths.",
                hint="Pick a different folder name, or the conflicting file must be removed manually.",
                )
        except Exception as error:
            return f"ERROR: Cannot write to {target_object}: {error}"

    @mcp_server.tool(description=toolshape.CREATE_DIRECTORY_DESCRIPTION)
    def create_directory(directory_path: str) -> str:
        """
            Create a folder (directory) on the host, including any missing parent folders, and return confirmation.
        """
        target_object = Path(directory_path).resolve()
        if not path_is_allowed(target_object, allowed_roots):
            return f"DENIED: {target_object} not within filepaths allowed by config."
        try:
            already_existed = target_object.is_dir()
            target_object.mkdir(parents=True, exist_ok=True)
            return toolshape.mkdir_receipt(target_object, already_existed=already_existed)
        except FileExistsError:
            # mkdir(exist_ok=True) still raises when the existing object is a FILE, not a folder
            return toolshape.error(
                f"a FILE (not a folder) already exists at {target_object} or one of its parents.",
                hint="Pick a different folder name, or the conflicting file must be removed manually.",
                )
        except Exception as error:
            return f"ERROR: Cannot create folder {target_object}: {error}"

    ### ---------------------------------------
    ### --- UNRESTRICTED MODEL COMMAND MODE ---
    ### ---------------------------------------
    @mcp_server.tool(description=RUN_COMMAND_DESCRIPTION)
    def run_command(command: str) -> str:
        """
            Run any command line through a real shell on the host and return its output.
            NOTE: NO allowed-commands list and NO allowed_roots checks
            NOTE: Windows runs the line through powershell.exe and Linux/macOS through the system shell.
        """
        if not command.strip():
            return "DENIED: empty command"

        if on_windows:
            run_arguments = ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command]
            use_shell = False
        else:
            run_arguments = command
            use_shell = True

        try:
            complete_command = subprocess.run(
                    run_arguments,
                    shell = use_shell,
                    capture_output = True,
                    text = True,
                    timeout = COMMAND_TIMEOUT_SECONDS,
                )
        except subprocess.TimeoutExpired:
            return toolshape.error(f"'{command}' timed out after {COMMAND_TIMEOUT_SECONDS} seconds.")

        return toolshape.command_receipt(
            command,
            complete_command.returncode,
            complete_command.stdout[:MAX_READ_BYTES],
            complete_command.stderr[:10_000],
            truncated=len(complete_command.stdout) > MAX_READ_BYTES,
            )
