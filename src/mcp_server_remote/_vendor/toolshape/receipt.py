# receipt.py
# Pure string builders that shape raw tool output into model-proof "receipts".
# A receipt always starts with OK:, DENIED:, or ERROR: so the client's existing
# system-prompt rules (DENIED/ERROR prefixes) keep working unchanged.
# NOTE: nothing imports this module until you opt in from tools.py (see _vendor/toolshape/README.md).

### -----------------
### --- CONSTANTS ---
### -----------------

# Characters only a shell would expand. Seeing them inside a "cannot access" style
# complaint means the model tried shell syntax that this server passes through literally.
_SHELL_CHARS = "*|~$<>?"

# stderr phrases that mean "the command was handed a filename it could not find"
_CONFUSION_PHRASES = ("cannot access", "No such file or directory", "cannot stat", "cannot open")

NO_SHELL_HINT = (
    "[hint] This machine runs commands with NO SHELL. Characters like * | > < ~ $ are NOT\n"
    "expanded - they reach the command as literal text (example: ls /home/* asks ls for a\n"
    "file literally named '/home/*'). Do not use pipes, redirection, wildcards, ~, or $VARS.\n"
    "Run ONE plain command with literal absolute paths. To search for a folder, use:\n"
    "find <dir> -maxdepth 3 -name <name> -type d"
)


### ------------------------
### --- INTERNAL HELPERS ---
### ------------------------

def _smells_like_shell_confusion(command: str, stderr: str) -> bool:
    """True when stderr looks like the command received unexpanded shell syntax.
    command: the command line exactly as the model sent it
    stderr: captured stderr text from running it
    """
    haystack = stderr or ""
    if not any(phrase in haystack for phrase in _CONFUSION_PHRASES):
        return False
    if any(char in haystack for char in _SHELL_CHARS):
        return True
    return any(char in (command or "") for char in _SHELL_CHARS)


### -------------------------
### --- RECEIPT BUILDERS  ---
### -------------------------

def command_receipt(command: str, returncode: int, stdout: str, stderr: str, truncated: bool = False) -> str:
    """Shape one finished command run into a single unambiguous receipt string.
    command: the command line that ran
    returncode: the command's exit code
    stdout: captured stdout text (already cut to any size limit by the caller)
    stderr: captured stderr text
    truncated: True when the caller cut the output at a size limit
    NOTE: starts with OK: whenever the command actually EXECUTED - a nonzero exit is the
    command reporting a problem, not a tool fault. Tool faults (timeout, missing binary)
    belong in error(); policy refusals belong in denied().
    """
    stdout = stdout or ""
    stderr = stderr or ""
    lines = []
    if returncode == 0:
        lines.append(f"OK: ran `{command}` (exit code 0 = success).")
    else:
        lines.append(
            f"OK: ran `{command}` - it finished but reported a problem "
            f"(exit code {returncode}; a nonzero exit means the command itself failed or found nothing)."
        )
    lines.append("[stdout]")
    if stdout.strip():
        lines.append(stdout.rstrip("\n"))
    elif returncode == 0:
        lines.append(
            "(empty stdout - the command ran fine and printed nothing. "
            "For a search or list, this means: NO MATCHES.)"
        )
    else:
        lines.append("(empty stdout - the command printed nothing before failing.)")
    if stderr.strip():
        lines.append("[stderr]")
        lines.append(stderr.rstrip("\n"))
    if truncated:
        lines.append("[note] output was cut at the size limit; you are seeing the beginning of it.")
    if _smells_like_shell_confusion(command, stderr):
        lines.append(NO_SHELL_HINT)
    return "\n".join(lines)


def read_receipt(path, text: str, truncated: bool = False) -> str:
    """Shape a file read into a receipt that makes emptiness explicit.
    path: the resolved path that was read
    text: the file text (already cut to any size limit by the caller)
    truncated: True when the caller cut the text at a size limit
    """
    text = text or ""
    if not text:
        return (
            f"OK: read {path} - the file exists and is EMPTY (0 characters). "
            "This is the real content, not an error. Do not read it again expecting different text."
        )
    if not text.strip():
        return (
            f"OK: read {path} - the file contains ONLY whitespace "
            f"({len(text)} characters, no visible text). This is the real content, not an error."
        )
    size_note = " shown; the file was cut at the size limit" if truncated else ""
    lines = [f"OK: read {path} ({len(text)} characters{size_note})."]
    lines.append("[file content]")
    lines.append(text)
    return "\n".join(lines)


def write_receipt(path, chars_written: int) -> str:
    """Shape a completed file write into a receipt that discourages re-writing to 'confirm'.
    path: the resolved path that was written
    chars_written: how many characters were written
    """
    return (
        f"OK: wrote {chars_written} characters to {path}. "
        "The write is complete and saved - do NOT call write_file again to confirm. "
        "If you need to see the file, call read_file once."
    )


def mkdir_receipt(path, already_existed: bool = False) -> str:
    """Shape a completed folder creation into a receipt that discourages confirm-loops.
    path: the resolved folder path
    already_existed: True when the folder was already there before the call
    """
    if already_existed:
        return (
            f"OK: folder {path} ALREADY EXISTS - nothing needed creating. "
            "It is ready to use; do NOT call create_directory again for this path."
        )
    return (
        f"OK: created folder {path} (any missing parent folders were created too). "
        "The folder exists now - do NOT call create_directory again to confirm."
    )


def denied(reason: str, allowed=None) -> str:
    """Shape a policy refusal. Starts with DENIED: per the client prompt contract.
    reason: why the command or path was refused
    allowed: optional list of allowed alternatives to offer the model
    """
    lines = [f"DENIED: {reason}"]
    if allowed:
        lines.append(f"Allowed: {', '.join(allowed)}")
    lines.append("Do not retry variations of the denied call. Pick an allowed option or tell the user what was denied.")
    return "\n".join(lines)


def error(reason: str, hint: str | None = None) -> str:
    """Shape a real tool fault (timeout, missing binary, bad input). Starts with ERROR:.
    reason: what actually failed
    hint: optional one-line suggestion for the model
    """
    lines = [f"ERROR: {reason}"]
    if hint:
        lines.append(f"[hint] {hint}")
    lines.append("Report this to the user in one short line. Do not invent an explanation.")
    return "\n".join(lines)
