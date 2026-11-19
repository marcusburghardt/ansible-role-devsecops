# SPDX-License-Identifier: Apache-2.0
"""Unit tests for the monitored-path audit watcher."""

import importlib.util
import logging
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


if __name__ == "__main__":
    unittest.main()
