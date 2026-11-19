# SPDX-License-Identifier: Apache-2.0
"""Unit tests for the monitored-path audit watcher."""

import importlib.util
import logging
import os
import pwd
import unittest
from pathlib import Path

WATCHER_PATH = Path(__file__).resolve().parents[1] / "files" / "scripts" / "audit_watch.py"
SPEC = importlib.util.spec_from_file_location("audit_watch", WATCHER_PATH)
audit_watch = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit_watch)


class ClassifyAccessTests(unittest.TestCase):
    def test_listing_syscalls(self):
        for syscall in (
            "access",
            "newfstatat",
            "statx",
            "readlink",
            "getdents64",
            "getxattr",
            "listxattr",
        ):
            with self.subTest(syscall=syscall):
                self.assertEqual(
                    audit_watch._classify_access(syscall, {"raw": {}}, False),
                    "list",
                )

    def test_read_open(self):
        record = {"raw": {"a2": "0"}}
        self.assertEqual(audit_watch._classify_access("openat", record, False), "read")

    def test_write_open(self):
        # O_WRONLY | O_CREAT | O_TRUNC
        record = {"raw": {"a2": "241"}}
        self.assertEqual(audit_watch._classify_access("openat", record, False), "write")

    def test_directory_open_is_listing(self):
        record = {"raw": {"a2": "10000"}}  # O_DIRECTORY | O_RDONLY
        self.assertEqual(audit_watch._classify_access("openat", record, True), "list")

    def test_path_open_is_listing(self):
        record = {"raw": {"a2": "200000"}}  # O_PATH
        self.assertEqual(audit_watch._classify_access("openat", record, False), "list")

    def test_metadata_syscall(self):
        self.assertEqual(
            audit_watch._classify_access("chmod", {"raw": {}}, False),
            "metadata",
        )


class DirectoryDetectionTests(unittest.TestCase):
    def test_directory_mode(self):
        self.assertTrue(audit_watch._is_directory({"raw": {"mode": "040700"}}))

    def test_regular_file_mode(self):
        self.assertFalse(audit_watch._is_directory({"raw": {"mode": "0100644"}}))

    def test_missing_mode(self):
        self.assertFalse(audit_watch._is_directory({"raw": {}}))


class NotifyPolicyTests(unittest.TestCase):
    def setUp(self):
        self.notifier = audit_watch.Notifier(
            {"notify_access": "rwa", "notify_denied": True},
            logging.getLogger("audit-watch-tests"),
            desktop_enabled=False,
        )

    def test_content_read_notifies(self):
        self.assertTrue(self.notifier._should_notify({"result": "success", "access": "read"}))

    def test_listing_does_not_notify(self):
        self.assertFalse(self.notifier._should_notify({"result": "success", "access": "list"}))

    def test_denied_listing_notifies(self):
        self.assertTrue(self.notifier._should_notify({"result": "denied", "access": "list"}))

    def test_notify_denied_can_be_disabled(self):
        notifier = audit_watch.Notifier(
            {"notify_access": "rwa", "notify_denied": False},
            logging.getLogger("audit-watch-tests"),
            desktop_enabled=False,
        )
        self.assertFalse(notifier._should_notify({"result": "denied", "access": "read"}))


class UserNameTests(unittest.TestCase):
    def test_current_user(self):
        expected = pwd.getpwuid(os.getuid()).pw_name
        self.assertEqual(audit_watch._user_name(os.getuid()), expected)

    def test_unset_audit_uid(self):
        self.assertEqual(audit_watch._user_name(4294967295), "unset")

    def test_unknown_user_falls_back(self):
        self.assertEqual(audit_watch._user_name(2**31 - 1), str(2**31 - 1))


class ParentLabelTests(unittest.TestCase):
    def test_parent_label_includes_pid(self):
        label = audit_watch._parent_label(os.getppid())
        self.assertTrue(label.startswith(str(os.getppid())))


class NotificationFormattingTests(unittest.TestCase):
    def _event(self, **overrides):
        event = {
            "result": "denied",
            "access": "read",
            "path": "/etc/shadow",
            "uid": 0,
            "auid": 1,
            "comm": "cat",
            "exe": "/usr/bin/cat",
            "pid": os.getpid(),
            "ppid": os.getppid(),
            "tty": "pts4",
            "session": 3,
            "errno": 13,
            "key": "devsecops_shadow",
        }
        event.update(overrides)
        return event

    def test_denied_notification_identifies_user_and_process(self):
        title, body, urgency = audit_watch._format_notification(self._event())
        self.assertEqual(title, "Denied: cat -> /etc/shadow")
        self.assertEqual(urgency, "critical")
        self.assertIn("user: root (0)", body)
        self.assertIn("login:", body)
        self.assertIn("process: cat", body)
        self.assertIn(f"parent {os.getppid()}", body)
        self.assertIn("exe: /usr/bin/cat", body)
        self.assertIn("read denied (EACCES)", body)
        self.assertIn("tty pts4", body)
        self.assertIn("session 3", body)

    def test_success_read_notification(self):
        title, body, urgency = audit_watch._format_notification(
            self._event(result="success", errno=0)
        )
        self.assertEqual(title, "cat read /etc/shadow")
        self.assertEqual(urgency, "normal")
        self.assertNotIn("denied", body)

    def test_metadata_notification(self):
        title, _, _ = audit_watch._format_notification(
            self._event(result="success", access="metadata", errno=0)
        )
        self.assertEqual(title, "cat changed /etc/shadow")

    def test_journal_line_includes_context(self):
        line = audit_watch._format_journal(self._event())
        self.assertIn("uid=root (0)", line)
        self.assertIn("auid=", line)
        self.assertIn("tty=pts4", line)
        self.assertIn("ses=3", line)


if __name__ == "__main__":
    unittest.main()
