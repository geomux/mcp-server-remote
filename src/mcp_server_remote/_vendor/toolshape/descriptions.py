# descriptions.py
# Suggested (opt-in) tool descriptions written for small local models (8B-14B).
# These are plain constants - nothing here changes the server until you pass one to the
# tool decorator in tools.py, e.g.  @mcp_server.tool(description=toolshape.RUN_COMMAND_DESCRIPTION)
#
# The DEFAULT constants are COMPACT: tool descriptions ride along on EVERY model call, and
# on CPU-only machines prompt evaluation is the dominant cost (measured 2026-07-10: the
# verbose set added ~620 prompt tokens per call - several extra minutes per turn on a
# laptop CPU running a 14B model). The *_VERBOSE variants keep the original long-form
# teaching text for setups with headroom (GPU boxes, cloud APIs) - swap them in from
# tools.py if you have the budget.
#
# The run_command NO SHELL warning is the most important text in this package: the server
# executes commands via subprocess with no shell, and models loop badly when nothing tells them.

### -------------------------------------------
### --- COMPACT DESCRIPTIONS (the defaults) ---
### -------------------------------------------

RUN_COMMAND_DESCRIPTION = (
    "Run ONE allowed command on the host and return its output as a receipt.\n"
    "NO SHELL: pipes |  redirects > < 2>  chaining && ;  wildcards * ?  ~  $VARS  $(...)  backticks\n"
    "are NOT expanded - they reach the command as literal text and fail.\n"
    "  WRONG: ls -d /home/*/my-repo 2>/dev/null\n"
    "  WRONG: ls /home | grep my-repo\n"
    "  RIGHT: find /home -maxdepth 3 -name my-repo -type d\n"
    "(patterns passed as arguments to find/grep are fine)\n"
    "One plain command only: allowed binary first, then literal flags and literal absolute paths.\n"
    "DENIED: = refused by policy - do not retry variations. ERROR: = the tool could not run it.\n"
    "Empty stdout is a real result (ran fine, no matches) - rerunning cannot change it."
)

RUN_COMMAND_DESCRIPTION_WINDOWS = (
    "Run ONE allowed PowerShell command on this Windows host and return its output as a receipt.\n"
    "ONE command only: cmdlet first, then flags and literal absolute Windows paths (C:\\...).\n"
    "No pipes |  chaining ; &&  redirects > <  variables $  - arguments reach the cmdlet as literal text.\n"
    "Unix commands (find, ls, cat, grep, mkdir) do NOT exist here. To search for a file or folder:\n"
    "  WRONG: find C:\\Users -name auth.py\n"
    "  RIGHT: Get-ChildItem C:\\Users -Recurse -Filter auth.py\n"
    "DENIED: = refused by policy - do not retry variations. ERROR: = the tool could not run it.\n"
    "Empty stdout is a real result (ran fine, no matches) - rerunning cannot change it."
)

CREATE_DIRECTORY_DESCRIPTION = (
    "Create a folder (directory) on the host, including any missing parent folders.\n"
    "This is the ONLY way to make a folder - write_file creates files, never folders.\n"
    "Pass the exact literal absolute path of the folder to create.\n"
    "One OK: receipt means the folder exists now - never call again to confirm.\n"
    "DENIED: = path outside allowed roots. ERROR: = the create itself failed."
)

READ_FILE_DESCRIPTION = (
    "Read a file (utf-8) from the host and return its text as a receipt.\n"
    "Use the exact literal absolute path - ~ and $VARS are NOT expanded.\n"
    "A receipt saying the file is EMPTY is the real content - do not re-read expecting different text.\n"
    "DENIED: = path outside allowed roots. ERROR: = the read itself failed."
)

WRITE_FILE_DESCRIPTION = (
    "Write utf-8 text to a file on the host (replacing previous content) and return a receipt.\n"
    "Pass the exact literal absolute path (~ and $VARS are NOT expanded) plus the FULL new content.\n"
    "Missing parent folders are created automatically. To make an empty folder, use create_directory instead.\n"
    "One OK: receipt means the write is DONE and saved. Never call write_file again just to confirm it.\n"
    "DENIED: = path outside allowed roots. ERROR: = the write itself failed."
)

### ------------------------------------------------------
### --- VERBOSE DESCRIPTIONS (opt-in, for big budgets) ---
### ------------------------------------------------------

RUN_COMMAND_DESCRIPTION_VERBOSE = (
    "Run ONE allowed command on the host machine and return its output as a receipt.\n"
    "\n"
    "NO SHELL - READ THIS FIRST:\n"
    "Your command runs with NO shell (no bash, no sh, no cmd). Shell syntax DOES NOT WORK here.\n"
    "All of these are passed to the command as plain literal text, never expanded:\n"
    "  pipes: |    redirection: > < 2>    chaining: && ; ||\n"
    "  wildcards: * ?    home shortcut: ~    variables: $HOME $USER\n"
    "  command substitution: $(...) or `...`\n"
    "Example of the mistake: `ls /home/*` asks ls for a file literally named '/home/*', which\n"
    "does not exist, so it fails. Correct usage is one plain command: the binary first, then\n"
    "literal flags and literal absolute paths.\n"
    "  WRONG: ls -d /home/*/my-repo 2>/dev/null\n"
    "  WRONG: ls /home | grep my-repo\n"
    "  RIGHT: find /home -maxdepth 3 -name my-repo -type d\n"
    "(find and grep do their own pattern matching, so a pattern given as an ARGUMENT to them is fine.)\n"
    "\n"
    "RULES:\n"
    "- The command's binary (first word) must be in the config allowed_commands list.\n"
    "- Flags and non-path arguments are passed through unchecked. Any argument that looks like a\n"
    "  filesystem path (starts with /, ~, or .) is checked against allowed_roots.\n"
    "- A result starting with DENIED: names exactly what was refused - do not retry variations.\n"
    "- A result starting with ERROR: means the tool could not run the command at all\n"
    "  (timeout, missing binary, unparseable command).\n"
    "- Empty stdout is a REAL result: the command ran and printed nothing. For a search, that\n"
    "  means no matches - it is not a failure and rerunning the command will not change it.\n"
    "- To search for a file or folder, use: find <dir> -maxdepth 3 -name <name> -type d"
)

READ_FILE_DESCRIPTION_VERBOSE = (
    "Read a file (utf-8) from the host and return its text.\n"
    "- Pass the exact literal path. ~ and $VARS are NOT expanded - use the full absolute path.\n"
    "- If the receipt says the file is EMPTY, that is the file's real content. Do not read it\n"
    "  again expecting different text.\n"
    "- Very large files are cut at a size limit; the receipt says so when that happens.\n"
    "- DENIED: means the path is outside the allowed roots. ERROR: means the read itself failed."
)

WRITE_FILE_DESCRIPTION_VERBOSE = (
    "Write text (utf-8) to a file on the host, replacing any previous content, and return a receipt.\n"
    "- Pass the exact literal path (~ and $VARS are NOT expanded) and the FULL new file content.\n"
    "- Missing parent folders are created automatically, so writing into a brand-new folder works\n"
    "  in one call. To create an EMPTY folder (no file inside), use create_directory instead -\n"
    "  writing a file at a folder's path creates a FILE, never a folder.\n"
    "- One OK: receipt means the write is DONE and saved. Never call write_file again just to\n"
    "  confirm a write that already returned OK:.\n"
    "- DENIED: means the path is outside the allowed roots. ERROR: means the write itself failed."
)

CREATE_DIRECTORY_DESCRIPTION_VERBOSE = (
    "Create a folder (directory) on the host and return a receipt.\n"
    "- This is the ONLY way to make a folder. write_file creates FILES - calling write_file on a\n"
    "  folder path makes a file with that name, which then BLOCKS creating the real folder.\n"
    "- Pass the exact literal absolute path (~ and $VARS are NOT expanded). Any missing parent\n"
    "  folders are created in the same call.\n"
    "- One OK: receipt means the folder exists - creating it again cannot improve anything.\n"
    "- DENIED: means the path is outside the allowed roots. ERROR: means the create itself failed."
)

RUN_COMMAND_DESCRIPTION_WINDOWS_VERBOSE = (
    "Run ONE allowed PowerShell command on this Windows host and return its output as a receipt.\n"
    "\n"
    "HOW COMMANDS RUN HERE:\n"
    "The allowed commands are PowerShell cmdlets, executed one at a time with every argument\n"
    "passed as LITERAL text. Shell composition is blocked - none of these do anything:\n"
    "  pipes: |    redirection: > <    chaining: ; && ||    variables: $env: $HOME\n"
    "Unix commands (find, ls, cat, grep, mkdir, dir) do NOT exist on this host.\n"
    "  WRONG: find C:\\Users -name auth.py        (no find on Windows)\n"
    "  WRONG: Get-ChildItem C:\\ | Select-String x (no pipes)\n"
    "  RIGHT: Get-ChildItem C:\\Users\\Name -Recurse -Filter auth.py\n"
    "  RIGHT: Select-String -Path C:\\file.txt -Pattern 'word'\n"
    "(patterns and wildcards given as ARGUMENTS to a cmdlet are fine - the cmdlet expands them.)\n"
    "\n"
    "RULES:\n"
    "- The cmdlet (first word) must be in the config allowed_commands list (case-insensitive).\n"
    "- Any argument that looks like a filesystem path is checked against allowed_roots.\n"
    "- A result starting with DENIED: names exactly what was refused - do not retry variations.\n"
    "- A result starting with ERROR: means the tool could not run the command at all.\n"
    "- Empty stdout is a REAL result: the command ran and printed nothing. For a search, that\n"
    "  means no matches - it is not a failure and rerunning the command will not change it."
)
