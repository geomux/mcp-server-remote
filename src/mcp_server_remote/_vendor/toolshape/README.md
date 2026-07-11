# toolshape — model-proof result receipts for mcp-server-remote

> ### ⚠️ EXTERNAL PACKAGE — NOT WRITTEN BY THIS REPO'S AUTHOR
> Everything under `_vendor/` is third-party code this project **uses** but did not
> hand-write. `toolshape` was designed, generated, and tested by **Claude Fable 5
> (Anthropic's AI model)** on 2026-07-09 and is vendored in-tree (pip-style `_vendor/`
> convention) rather than pulled from PyPI. It is stdlib-only, self-contained, and
> completely inert until `tools.py` opts in using the snippets below. All hand-written
> code in this repository lives outside `_vendor/`.

`toolshape` is a small, **opt-in**, stdlib-only companion package. It turns raw tool output
into "receipts": result strings a small local model (8B–14B) cannot misread. Nothing in the
server imports it yet — **adding this folder changes zero behavior** until you wire it into
`tools.py` yourself using the snippets below.

## Why this exists

Watching a local model use this server shows three repeatable failure patterns, all caused by
the *shape* of results rather than the tools themselves:

1. **Ambiguous emptiness.** A command that runs fine but prints nothing (a search with no
   matches, an empty file) comes back as near-empty text. Small models read that as "the tool
   glitched" and re-run the same call in a loop.
2. **No shell, but nobody says so.** `run_command` executes via `subprocess.run(tokens)` with
   **no shell**, so `*`, `|`, `2>/dev/null`, `~`, and `$VARS` reach the binary as literal text.
   The model then sees surreal errors like `ls: cannot access '/home/*'` and, with nothing
   explaining them, retries variations until it hits the step limit.
3. **Unframed errors.** stdout, stderr, and exit codes arrive as one blob. The model can't
   tell "the tool failed" from "the command ran and reported something," so it guesses.

Receipts fix all three **at the source**, for every client that ever connects — one clear
status line, labeled sections, explicit emptiness, plain-language exit codes, and an
automatic NO-SHELL hint whenever stderr smells like glob/operator confusion.

> The client repo's `_vendor/llm_shepherd` package already compensates for these client-side.
> `toolshape` is the at-the-source upgrade so *any* client benefits, not just the console.

## The status-prefix contract

Every receipt starts with one of three prefixes, matching the client system prompt's existing
rules for `DENIED`/`ERROR`:

| Prefix    | Meaning                                                                 |
|-----------|-------------------------------------------------------------------------|
| `OK:`     | The tool did its job. For `run_command` this means the command **executed** — a nonzero exit is reported inside the receipt as the *command* complaining, not the tool failing. (`grep` exiting 1 on "no matches" is not an error.) |
| `DENIED:` | Policy refusal (command not allowed, path outside allowed roots).       |
| `ERROR:`  | The tool itself could not do the job (timeout, missing binary, unparseable input). |

## What's in the package

| File              | Purpose                                                              |
|-------------------|----------------------------------------------------------------------|
| `receipt.py`      | `command_receipt`, `read_receipt`, `write_receipt`, `mkdir_receipt`, `denied`, `error` — pure string builders. |
| `descriptions.py` | Suggested tool descriptions, including the crucial `run_command` **NO SHELL** warning, a Windows-specific `RUN_COMMAND_DESCRIPTION_WINDOWS` (steers Unix habits like `find` toward `Get-ChildItem -Recurse`), and `CREATE_DIRECTORY_DESCRIPTION`. The default constants are **compact** (descriptions ride on *every* model call, and on CPU-only boxes prompt evaluation is the dominant cost — measured at ~620 extra prompt tokens for the long forms). `*_VERBOSE` variants keep the long-form teaching text for GPU/API setups. |
| `selftest.py`     | Offline unittest suite (no network, no model).                       |

Run the selftest from the repo root:

```bash
PYTHONPATH=src .venv/bin/python -m mcp_server_remote._vendor.toolshape.selftest
```

## How to adopt it in tools.py (snippets — NOT applied)

> **Import the module, not bare names.** `tools.py` already uses local names like
> `except ValueError as error:` — a bare `from ... import error` would be shadowed inside
> those functions (and even raise `UnboundLocalError` if called earlier in the same
> function). `toolshape.error(...)` is immune.

Add one import near the top of `tools.py`:

```python
from mcp_server_remote._vendor import toolshape
```

### run_command

```diff
-    @mcp_server.tool
+    @mcp_server.tool(description=toolshape.RUN_COMMAND_DESCRIPTION)
     def run_command(command: str) -> str:
```

```diff
         cmd_binary = tokens[0]
         if cmd_binary not in allowed_commands:
-            allowed_commands_string = ", ".join(allowed_commands)
-            return f"DENIED: '{cmd_binary}' is not allowed. Allowed commands: {allowed_commands_string}"
+            return toolshape.denied(f"'{cmd_binary}' is not allowed.", allowed=allowed_commands)
```

```diff
-        command_output = complete_command.stdout
-
-        if complete_command.stderr:
-            command_output += f"\n[stderr]\n{complete_command.stderr}"
-        if complete_command.returncode != 0:
-            command_output += f"\n[exit code {complete_command.returncode}]"
-        return command_output[:MAX_READ_BYTES] if command_output.strip() else "(no command output)"
+        return toolshape.command_receipt(
+            command,
+            complete_command.returncode,
+            complete_command.stdout[:MAX_READ_BYTES],
+            complete_command.stderr[:10_000],
+            truncated=len(complete_command.stdout) > MAX_READ_BYTES,
+        )
```

(The two `ERROR:` returns for timeout / missing binary become
`toolshape.error(f"'{command}' timed out after {COMMAND_TIMEOUT_SECONDS} seconds.")` and
`toolshape.error(f"'{cmd_binary}' is allowed but not found on this remote machine.")`.)

### read_file

```diff
-    @mcp_server.tool
+    @mcp_server.tool(description=toolshape.READ_FILE_DESCRIPTION)
     def read_file(filepath: str) -> str:
```

```diff
         try:
             text_read = target_object.read_text(encoding="utf-8",errors="replace")
-            return text_read[:MAX_READ_BYTES]
+            return toolshape.read_receipt(
+                target_object,
+                text_read[:MAX_READ_BYTES],
+                truncated=len(text_read) > MAX_READ_BYTES,
+            )
```

### write_file

```diff
-    @mcp_server.tool
+    @mcp_server.tool(description=toolshape.WRITE_FILE_DESCRIPTION)
     def write_file(filepath: str, data_write: str | int | float) -> str:
```

```diff
             with open(target_object, "w", encoding="utf-8") as f:
                 f.write(str(data_write))
-            return f"OK: wrote {len(str(data_write))} characters to {target_object}."
+            return toolshape.write_receipt(target_object, len(str(data_write)))
```

The `DENIED:` path checks in all three tools can likewise become
`toolshape.denied(f"{target_object} not within filepaths allowed by config.")`.

## What adopting it changes for the model

Before (the loop trigger — command "succeeded" with garbage):

```
ls: cannot access '/home/*': No such file or directory
[exit code 2]
```

After (same run, receipt-shaped):

```
OK: ran `ls -d /home/*` - it finished but reported a problem (exit code 2; a nonzero exit means the command itself failed or found nothing).
[stdout]
(empty stdout - the command printed nothing before failing.)
[stderr]
ls: cannot access '/home/*': No such file or directory
[hint] This machine runs commands with NO SHELL. Characters like * | > < ~ $ are NOT
expanded - they reach the command as literal text (example: ls /home/* asks ls for a
file literally named '/home/*'). Do not use pipes, redirection, wildcards, ~, or $VARS.
Run ONE plain command with literal absolute paths. To search for a folder, use:
find <dir> -maxdepth 3 -name <name> -type d
```
