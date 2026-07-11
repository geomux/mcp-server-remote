# selftest.py
# Offline unittest suite for toolshape receipts. No network, no server, no model.
# Run from the repo root:  PYTHONPATH=src .venv/bin/python -m mcp_server_remote._vendor.toolshape.selftest

import unittest

from mcp_server_remote._vendor.toolshape.receipt import command_receipt
from mcp_server_remote._vendor.toolshape.receipt import read_receipt
from mcp_server_remote._vendor.toolshape.receipt import write_receipt
from mcp_server_remote._vendor.toolshape.receipt import mkdir_receipt
from mcp_server_remote._vendor.toolshape.receipt import denied
from mcp_server_remote._vendor.toolshape.receipt import error
from mcp_server_remote._vendor.toolshape.receipt import NO_SHELL_HINT
from mcp_server_remote._vendor.toolshape import descriptions


### -------------------------------
### --- COMMAND RECEIPT TESTS   ---
### -------------------------------

class CommandReceiptTests(unittest.TestCase):
    def test_success_with_output(self):
        receipt = command_receipt("ls /home", 0, "alice\n", "")
        self.assertTrue(receipt.startswith("OK:"))
        self.assertIn("exit code 0", receipt)
        self.assertIn("[stdout]", receipt)
        self.assertIn("alice", receipt)
        self.assertNotIn("[stderr]", receipt)

    def test_empty_stdout_success_says_no_matches(self):
        receipt = command_receipt("find /home -name nope -type d", 0, "", "")
        self.assertTrue(receipt.startswith("OK:"))
        self.assertIn("NO MATCHES", receipt)
        self.assertIn("empty stdout", receipt)

    def test_stderr_only_is_labeled_and_stdout_emptiness_explained(self):
        receipt = command_receipt("ls /nope", 2, "", "ls: cannot access '/nope': No such file or directory\n")
        self.assertTrue(receipt.startswith("OK:"))
        self.assertIn("[stderr]", receipt)
        self.assertIn("cannot access", receipt)
        self.assertIn("empty stdout", receipt)

    def test_nonzero_exit_gets_plain_language_meaning(self):
        receipt = command_receipt("grep beep /etc/hostname", 1, "", "")
        self.assertTrue(receipt.startswith("OK:"))
        self.assertIn("exit code 1", receipt)
        self.assertIn("nonzero exit means the command itself failed or found nothing", receipt)

    def test_truncated_note_present(self):
        receipt = command_receipt("cat big.txt", 0, "x" * 50, "", truncated=True)
        self.assertIn("cut at the size limit", receipt)

    def test_not_truncated_has_no_note(self):
        receipt = command_receipt("cat small.txt", 0, "x", "")
        self.assertNotIn("cut at the size limit", receipt)

    def test_no_shell_hint_on_glob_confusion(self):
        stderr = "ls: cannot access '/home/*': No such file or directory\n"
        receipt = command_receipt("ls -d /home/*", 2, "", stderr)
        self.assertIn(NO_SHELL_HINT, receipt)

    def test_no_shell_hint_on_redirection_token(self):
        stderr = "ls: cannot access '2>/dev/null': No such file or directory\n"
        receipt = command_receipt("ls -d /home 2>/dev/null", 2, "", stderr)
        self.assertIn(NO_SHELL_HINT, receipt)

    def test_no_shell_hint_on_pipe_token(self):
        stderr = "ls: cannot access '|': No such file or directory\n"
        receipt = command_receipt("ls /home | xargs echo", 2, "", stderr)
        self.assertIn(NO_SHELL_HINT, receipt)

    def test_no_hint_on_plain_missing_file(self):
        stderr = "ls: cannot access '/nope': No such file or directory\n"
        receipt = command_receipt("ls /nope", 2, "", stderr)
        self.assertNotIn(NO_SHELL_HINT, receipt)

    def test_no_hint_on_clean_success(self):
        receipt = command_receipt("ls /home", 0, "alice\n", "")
        self.assertNotIn(NO_SHELL_HINT, receipt)


### ----------------------------------
### --- READ / WRITE RECEIPT TESTS ---
### ----------------------------------

class ReadReceiptTests(unittest.TestCase):
    def test_empty_file_is_explicit_and_not_an_error(self):
        receipt = read_receipt("/tmp/empty.txt", "")
        self.assertTrue(receipt.startswith("OK:"))
        self.assertIn("EMPTY", receipt)
        self.assertIn("not an error", receipt)

    def test_whitespace_only_file_is_explicit(self):
        receipt = read_receipt("/tmp/blank.txt", "\n\n  \n")
        self.assertTrue(receipt.startswith("OK:"))
        self.assertIn("ONLY whitespace", receipt)

    def test_content_is_verbatim_with_length(self):
        receipt = read_receipt("/tmp/hello.txt", "hello world\n")
        self.assertTrue(receipt.startswith("OK:"))
        self.assertIn("12 characters", receipt)
        self.assertIn("[file content]", receipt)
        self.assertIn("hello world\n", receipt)

    def test_truncated_read_notes_the_cut(self):
        receipt = read_receipt("/tmp/big.txt", "x" * 10, truncated=True)
        self.assertIn("cut at the size limit", receipt)


class WriteReceiptTests(unittest.TestCase):
    def test_write_receipt_confirms_and_discourages_rewrite(self):
        receipt = write_receipt("/tmp/out.txt", 42)
        self.assertTrue(receipt.startswith("OK:"))
        self.assertIn("42 characters", receipt)
        self.assertIn("/tmp/out.txt", receipt)
        self.assertIn("do NOT call write_file again", receipt)


class MkdirReceiptTests(unittest.TestCase):
    def test_created_folder_confirms_and_discourages_retry(self):
        receipt = mkdir_receipt("/tmp/new-folder")
        self.assertTrue(receipt.startswith("OK:"))
        self.assertIn("/tmp/new-folder", receipt)
        self.assertIn("parent folders", receipt)
        self.assertIn("do NOT call create_directory again", receipt)

    def test_already_existing_folder_is_explicit_success(self):
        receipt = mkdir_receipt("/tmp/old-folder", already_existed=True)
        self.assertTrue(receipt.startswith("OK:"))
        self.assertIn("ALREADY EXISTS", receipt)
        self.assertIn("do NOT call create_directory again", receipt)


### -------------------------------
### --- DENIED / ERROR TESTS    ---
### -------------------------------

class DeniedErrorTests(unittest.TestCase):
    def test_denied_prefix_and_reason(self):
        receipt = denied("'rm' is not allowed.")
        self.assertTrue(receipt.startswith("DENIED:"))
        self.assertIn("'rm' is not allowed.", receipt)
        self.assertIn("Do not retry variations", receipt)

    def test_denied_lists_allowed_alternatives(self):
        receipt = denied("'rm' is not allowed.", allowed=["ls", "cat", "find"])
        self.assertIn("Allowed: ls, cat, find", receipt)

    def test_error_prefix_and_hint(self):
        receipt = error("'sl' is allowed but not found on this remote machine.", hint="try ls instead")
        self.assertTrue(receipt.startswith("ERROR:"))
        self.assertIn("[hint] try ls instead", receipt)


### ------------------------------
### --- CONTRACT-WIDE TESTS    ---
### ------------------------------

class PrefixContractTests(unittest.TestCase):
    def test_every_builder_starts_with_a_known_prefix(self):
        receipts = [
            command_receipt("ls", 0, "a", ""),
            command_receipt("ls", 2, "", "boom"),
            read_receipt("/f", "x"),
            read_receipt("/f", ""),
            write_receipt("/f", 1),
            mkdir_receipt("/f"),
            mkdir_receipt("/f", already_existed=True),
            denied("nope"),
            error("bad"),
        ]
        for receipt in receipts:
            self.assertTrue(
                receipt.startswith(("OK:", "DENIED:", "ERROR:")),
                f"receipt missing status prefix: {receipt[:60]!r}",
            )


class DescriptionTests(unittest.TestCase):
    def test_run_command_description_teaches_no_shell(self):
        text = descriptions.RUN_COMMAND_DESCRIPTION
        self.assertIn("NO SHELL", text)
        self.assertIn("literal", text)
        self.assertIn("|", text)
        self.assertIn("*", text)
        self.assertIn("WRONG:", text)
        self.assertIn("RIGHT:", text)
        self.assertIn("find", text)
        self.assertIn("-maxdepth", text)

    def test_read_description_covers_empty_and_literal_paths(self):
        text = descriptions.READ_FILE_DESCRIPTION
        self.assertIn("EMPTY", text)
        self.assertIn("NOT expanded", text)

    def test_write_description_discourages_confirm_rewrites(self):
        text = descriptions.WRITE_FILE_DESCRIPTION
        self.assertIn("DONE", text)
        self.assertIn("Never call write_file again", text)
        self.assertIn("create_directory", text)

    def test_create_directory_description_owns_folder_making(self):
        text = descriptions.CREATE_DIRECTORY_DESCRIPTION
        self.assertIn("folder", text)
        self.assertIn("write_file", text)
        self.assertIn("never call again", text.lower())

    def test_windows_run_description_redirects_unix_habits(self):
        text = descriptions.RUN_COMMAND_DESCRIPTION_WINDOWS
        self.assertIn("PowerShell", text)
        self.assertIn("find", text)
        self.assertIn("Get-ChildItem", text)
        self.assertIn("-Recurse", text)
        self.assertIn("WRONG:", text)
        self.assertIn("RIGHT:", text)

    def test_default_descriptions_stay_prompt_budget_compact(self):
        # descriptions ride on EVERY model call; on CPU boxes prompt eval dominates,
        # so the default set must stay small. Only ONE run_command variant is registered
        # at a time, so budget the worst case of the two plus the three file tools.
        total = max(
            len(descriptions.RUN_COMMAND_DESCRIPTION),
            len(descriptions.RUN_COMMAND_DESCRIPTION_WINDOWS),
        ) + len(
            descriptions.READ_FILE_DESCRIPTION
            + descriptions.WRITE_FILE_DESCRIPTION
            + descriptions.CREATE_DIRECTORY_DESCRIPTION
        )
        self.assertLess(total, 2300, f"compact description set grew to {total} chars")

    def test_verbose_variants_keep_the_long_form_teaching(self):
        self.assertIn("NO SHELL - READ THIS FIRST", descriptions.RUN_COMMAND_DESCRIPTION_VERBOSE)
        self.assertIn("RULES:", descriptions.RUN_COMMAND_DESCRIPTION_VERBOSE)
        self.assertIn("RULES:", descriptions.RUN_COMMAND_DESCRIPTION_WINDOWS_VERBOSE)
        self.assertIn("EMPTY", descriptions.READ_FILE_DESCRIPTION_VERBOSE)
        self.assertIn("Never call write_file again", descriptions.WRITE_FILE_DESCRIPTION_VERBOSE)
        for compact, verbose in (
            (descriptions.RUN_COMMAND_DESCRIPTION, descriptions.RUN_COMMAND_DESCRIPTION_VERBOSE),
            (descriptions.RUN_COMMAND_DESCRIPTION_WINDOWS, descriptions.RUN_COMMAND_DESCRIPTION_WINDOWS_VERBOSE),
            (descriptions.READ_FILE_DESCRIPTION, descriptions.READ_FILE_DESCRIPTION_VERBOSE),
            (descriptions.WRITE_FILE_DESCRIPTION, descriptions.WRITE_FILE_DESCRIPTION_VERBOSE),
            (descriptions.CREATE_DIRECTORY_DESCRIPTION, descriptions.CREATE_DIRECTORY_DESCRIPTION_VERBOSE),
        ):
            self.assertLess(len(compact), len(verbose), "compact variant must be the smaller one")


if __name__ == "__main__":
    unittest.main()
