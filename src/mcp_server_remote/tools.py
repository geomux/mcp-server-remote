# tools.py
# Defines tools for the MCP server to run.
# NOTE: MAJOR benefit from beefing up docstrings for LLM context since they are passed through the functions that define the tools

import platform
import re
import shlex
import subprocess
from pathlib import Path
from mcp_server_remote._vendor import toolshape

# CONSTANTS
COMMAND_TIMEOUT_SECONDS = 60    # max time elapsed running each command to protect from hung processes
MAX_READ_BYTES = 100_000        # max file read in one call to protect LLM context window & tokens

# a "plain flag" (-Recurse, -Filter) is safe to leave bare in PowerShell; every other argument gets single-quoted literal
PLAIN_FLAG_PATTERN = re.compile(r"^-[A-Za-z][A-Za-z0-9]*$")
# catches Windows drive-letter paths (C:\..., d:/...) that have no leading / . ~ for the path check
DRIVE_LETTER_PATTERN = re.compile(r"^[A-Za-z]:")


### all tools register on MCP server through register_tools()
def register_tools(mcp_server, config):
    """Register MCP tools with MCP server instance and config file arguments"""
    os_key = {"Linux": "linux", "Windows": "windows", "Darwin": "macos"}[platform.system()]
    allowed_commands = config["tools"]["commands"][os_key]
    allowed_roots = config["tools"]["allowed_roots"]
    on_windows = os_key == "windows"


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

    # Windows gets its own run_command teaching text: the allowed commands there are PowerShell cmdlets
    run_command_description = (
        toolshape.RUN_COMMAND_DESCRIPTION_WINDOWS if on_windows else toolshape.RUN_COMMAND_DESCRIPTION
    )

    @mcp_server.tool(description=run_command_description)
    def run_command(command: str) -> str:
        """
            Run one allowed command on the host machine and return its output.
            NOTE: The command's binary (first word) must be in the config allowed_commands list.
            NOTE: Flags and non-path arguments are passed through unchecked. Any argument that looks like a filesystem path (starts with /, ~, ., a drive letter, or contains a slash) is checked against allowed_roots.
            NOTE: On Windows the allowed commands are PowerShell cmdlets. They run one at a time through powershell.exe with every argument passed as literal quoted text - no pipes, chaining, or variable expansion is possible.
            NOTE: If a command or path is denied, tool will return why.
        """
        try:
            # posix=False on Windows keeps backslashes in paths like C:\Users intact (posix mode strips them as escapes)
            tokens = shlex.split(command.strip(), posix=not on_windows)
        except ValueError as error:
            return f"ERROR: could not parse command: {error}"

        if not tokens:
            return "DENIED: empty command"

        if on_windows:
            # non-posix shlex keeps surrounding quotes attached to tokens - strip matching pairs
            tokens = [
                token[1:-1] if len(token) >= 2 and token[0] == token[-1] and token[0] in "\"'" else token
                for token in tokens
            ]

        cmd_binary = tokens[0]
        if on_windows:
            # Windows commands and cmdlets are case-insensitive - accept get-childitem for Get-ChildItem
            canonical_names = {name.lower(): name for name in allowed_commands}
            cmd_binary = canonical_names.get(cmd_binary.lower())
            if cmd_binary is None:
                return toolshape.denied(f"'{tokens[0]}' is not allowed.", allowed=allowed_commands)
        elif cmd_binary not in allowed_commands:
            return toolshape.denied(f"'{cmd_binary}' is not allowed.", allowed=allowed_commands)

        # check to see if any arguments are paths/look like paths
        for token in tokens[1:]:
            if token.startswith("-"):
                continue # argument is a flag
            looks_like_path = (
                "/" in token
                or "\\" in token
                or token.startswith("~")
                or token.startswith(".")
                or DRIVE_LETTER_PATTERN.match(token) is not None
            )
            if not looks_like_path:
                continue # argument is not a path
            target_object = Path(token).expanduser().resolve()
            if not path_is_allowed(target_object, allowed_roots):
                return f"DENIED: path '{target_object}' is not within filepaths allowed by config file."

        if on_windows:
            # PowerShell cmdlets (Get-ChildItem etc.) are not .exe binaries - they only exist inside PowerShell.
            # Preserve the no-shell contract while using one: the cmdlet name comes from the allowlist, plain
            # -Flags pass bare, and EVERY other argument is single-quoted literal ('' escapes a quote inside).
            # PowerShell expands nothing inside single quotes, so pipes/chaining/$vars in arguments stay inert text.
            rendered_arguments = []
            for token in tokens[1:]:
                if PLAIN_FLAG_PATTERN.match(token):
                    rendered_arguments.append(token)
                else:
                    rendered_arguments.append("'" + token.replace("'", "''") + "'")
            run_arguments = [
                "powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
                " ".join([cmd_binary] + rendered_arguments),
            ]
        else:
            run_arguments = tokens

        try:
            complete_command = subprocess.run(
                    run_arguments,
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
            complete_command.stdout[:MAX_READ_BYTES],
            complete_command.stderr[:10_000],
            truncated=len(complete_command.stdout) > MAX_READ_BYTES,
            )
