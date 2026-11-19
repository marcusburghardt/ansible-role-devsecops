#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Watch the Linux audit log for access to role-managed paths.

The watcher tails the audit log, keeps the events whose audit key matches the
configured prefix, correlates the SYSCALL, CWD and PATH records of each event,
and appends one curated JSON object per access to a log file. Alerts are sent
to journald and, when a graphical session exists, as native desktop
notifications.

Only the access-granting operation is recorded. Reads and writes performed on
an already-open file descriptor do not carry a path and are therefore not
reported per call; auditd's raw log remains the authoritative record.
"""

from __future__ import annotations

import argparse
import collections
import datetime
import errno
import functools
import json
import logging
import logging.handlers
import os
import pwd
import re
import shlex
import stat
import subprocess
import sys
import time

try:
    import auparse
except ImportError:  # pragma: no cover - reported by main()
    auparse = None

DEFAULT_CONFIG_FILE = "/etc/devsecops/audit-monitor.json"
DEFAULT_CONFIG = {
    "audit_log_file": "/var/log/audit/audit.log",
    "log_file": "/var/log/devsecops/monitored-access.log",
    "key_prefix": "devsecops",
    "paths": {},
    "notify_desktop": True,
    "notify_user": "",
    "notify_access": "rwa",
    "notify_denied": True,
    "notify_throttle": 30,
    "notify_command": "notify-send",
}

EVENT_MESSAGE_RE = re.compile(r"msg=audit\((\d+(?:\.\d+)?):(\d+)\)")
HEX_VALUE_RE = re.compile(r"(?:[0-9A-Fa-f]{2})+")

OPEN_SYSCALLS = {"open", "openat", "openat2"}
READ_SYSCALLS = {
    "read",
    "pread64",
    "readv",
    "preadv",
    "preadv2",
    "execve",
    "execveat",
    "mmap",
}
LISTING_SYSCALLS = {
    "access",
    "faccessat",
    "faccessat2",
    "stat",
    "lstat",
    "fstat",
    "newfstatat",
    "statx",
    "readlink",
    "readlinkat",
    "getdents",
    "getdents64",
    "getxattr",
    "lgetxattr",
    "fgetxattr",
    "listxattr",
    "llistxattr",
    "flistxattr",
}
WRITE_SYSCALLS = {
    "creat",
    "write",
    "pwrite64",
    "writev",
    "pwritev",
    "pwritev2",
    "truncate",
    "ftruncate",
    "rename",
    "renameat",
    "renameat2",
    "unlink",
    "unlinkat",
    "rmdir",
    "mkdir",
    "mkdirat",
    "mknod",
    "mknodat",
    "link",
    "linkat",
    "symlink",
    "symlinkat",
    "copy_file_range",
    "sendfile",
}
METADATA_SYSCALLS = {
    "chmod",
    "fchmod",
    "fchmodat",
    "fchmodat2",
    "chown",
    "fchown",
    "lchown",
    "fchownat",
    "setxattr",
    "lsetxattr",
    "fsetxattr",
    "removexattr",
    "lremovexattr",
    "fremovexattr",
    "utime",
    "utimes",
    "futimesat",
    "utimensat",
}

ACCESS_MASKS = {"read": "r", "write": "w", "metadata": "a"}
EACCES = 13
EPERM = 1
O_ACCMODE = 0o3
O_CREAT = 0o100
O_TRUNC = 0o1000
O_APPEND = 0o2000
O_PATH = 0o10000000


class AuditParser:
    """Group the records of one event with auparse and interpret their fields."""

    def __init__(self):
        self._module = auparse

    def parse(self, lines):
        parser = self._module.AuParser(self._module.AUSOURCE_BUFFER_ARRAY, list(lines))
        if not parser.parse_next_event():
            return []

        records = []
        first_record = True
        while True:
            if not first_record and not parser.next_record():
                break
            first_record = False
            values = {}
            interpreted = {}
            for index in range(parser.get_num_fields()):
                parser.goto_field_num(index)
                field_name = parser.get_field_name()
                values[field_name] = parser.get_field_str()
                try:
                    interpreted[field_name] = parser.interpret_field()
                except Exception:  # noqa: BLE001 - auparse raises plain exceptions
                    interpreted[field_name] = values[field_name]
            records.append(
                {
                    "type": parser.get_type_name(),
                    "raw": values,
                    "value": interpreted,
                }
            )
        return records


class AuditLogFollower:
    """Read new audit log lines and follow rotation and truncation."""

    def __init__(self, path, logger, poll_interval=0.5):
        self._path = path
        self._logger = logger
        self._poll_interval = poll_interval
        self._handle = None
        self._identity = None

    def _open(self, from_start):
        self._close()
        self._handle = open(self._path, encoding="utf-8", errors="replace")  # noqa: SIM115
        status = os.fstat(self._handle.fileno())
        self._identity = (status.st_dev, status.st_ino)
        if not from_start:
            self._handle.seek(0, os.SEEK_END)

    def _close(self):
        if self._handle is not None:
            self._handle.close()
            self._handle = None

    def _reopen_if_needed(self):
        try:
            status = os.stat(self._path)
        except FileNotFoundError:
            return
        if (status.st_dev, status.st_ino) != self._identity:
            self._logger.info("%s was rotated; reopening it", self._path)
            self._open(from_start=True)
        elif status.st_size < self._handle.tell():
            self._logger.info("%s was truncated; reading it from the start", self._path)
            self._handle.seek(0)

    def stream(self, once=False):
        self._open(from_start=once)
        try:
            while True:
                line = self._handle.readline()
                if line:
                    yield line
                elif once:
                    return
                else:
                    self._reopen_if_needed()
                    time.sleep(self._poll_interval)
        finally:
            self._close()


class Notifier:
    """Send throttled desktop notifications and always log alerts to journald."""

    WINDOW_SECONDS = 60

    def __init__(self, config, logger, desktop_enabled=True):
        self._config = config
        self._logger = logger
        self._desktop_enabled = desktop_enabled
        self._buckets = {}
        self._suppressed = {}

    def notify(self, event):
        if not self._should_notify(event):
            return
        suppressed = self._throttle((event["path"], event["result"]))
        if suppressed is None:
            return

        title, body, urgency = _format_notification(event)
        if suppressed:
            body = f"{body}\n{suppressed} similar event(s) suppressed"
        self._logger.warning("%s", _format_journal(event))
        if self._desktop_enabled and self._config.get("notify_desktop"):
            self._send_desktop(title, body, urgency)

    def _should_notify(self, event):
        if event["result"] == "denied":
            return bool(self._config.get("notify_denied"))
        if event["result"] != "success":
            return False
        if event["access"] == "list":
            return False
        mask = self._config.get("notify_access") or ""
        return ACCESS_MASKS.get(event["access"], "") in mask

    def _throttle(self, key):
        try:
            limit = int(self._config.get("notify_throttle") or 0)
        except (TypeError, ValueError):
            limit = 0
        if limit <= 0:
            return 0

        now = time.monotonic()
        bucket = self._buckets.setdefault(key, collections.deque())
        while bucket and now - bucket[0] >= self.WINDOW_SECONDS:
            bucket.popleft()
        if len(bucket) >= limit:
            self._suppressed[key] = self._suppressed.get(key, 0) + 1
            return None
        bucket.append(now)
        return self._suppressed.pop(key, 0)

    def _send_desktop(self, title, body, urgency):
        user = self._config.get("notify_user") or ""
        command = self._config.get("notify_command") or "notify-send"
        if not user:
            return
        argv = shlex.split(command)
        if not argv:
            return
        try:
            user_id = pwd.getpwnam(user).pw_uid
        except KeyError:
            self._logger.warning("notification user %s does not exist", user)
            return

        runtime_dir = f"/run/user/{user_id}"
        if os.path.basename(argv[0]) == "notify-send":
            icon = "dialog-warning" if urgency == "critical" else "dialog-information"
            argv += ["-u", urgency, "-a", "devsecops", "-t", "10000", "-i", icon]
        argv += [title, body]
        argv = [
            "runuser",
            "-u",
            user,
            "--",
            "env",
            f"XDG_RUNTIME_DIR={runtime_dir}",
            f"DBUS_SESSION_BUS_ADDRESS=unix:path={runtime_dir}/bus",
            *argv,
        ]
        try:
            result = subprocess.run(argv, check=False, capture_output=True, timeout=10)
        except (OSError, subprocess.SubprocessError) as error:
            self._logger.warning("desktop notification failed: %s", error)
            return
        if result.returncode != 0:
            self._logger.info(
                "desktop notification unavailable: %s",
                result.stderr.decode("utf-8", "replace").strip(),
            )


def _normalize(value):
    if value is None:
        return None
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        return value[1:-1]
    return value


def _decode(value):
    """Decode audit hex-encoded strings; leave plain values untouched."""
    value = _normalize(value)
    if value is None:
        return None
    if HEX_VALUE_RE.fullmatch(value):
        try:
            return bytes.fromhex(value).decode("utf-8", "replace")
        except ValueError:
            return value
    return value


def _value(record, name, default=None):
    if name in record["value"]:
        return record["value"][name]
    if name in record["raw"]:
        return _decode(record["raw"][name])
    return default


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _iso_timestamp(epoch):
    moment = datetime.datetime.fromtimestamp(float(epoch), tz=datetime.timezone.utc)
    return moment.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _group_events(lines):
    """Yield line groups that share the same audit message id."""
    buffer = []
    current = None
    for line in lines:
        match = EVENT_MESSAGE_RE.search(line)
        if not match:
            continue
        serial = match.group(2)
        if current is not None and serial != current:
            yield buffer
            buffer = []
        current = serial
        buffer.append(line.rstrip("\n"))
    if buffer:
        yield buffer


def _is_directory(record):
    raw_mode = record["raw"].get("mode")
    if not raw_mode:
        return False
    try:
        return stat.S_ISDIR(int(raw_mode, 8))
    except (TypeError, ValueError):
        return False


def _classify_access(syscall, record, is_directory=False):
    if syscall in LISTING_SYSCALLS:
        return "list"
    if syscall in METADATA_SYSCALLS:
        return "metadata"
    if syscall in OPEN_SYSCALLS:
        return _classify_open_access(syscall, record, is_directory)
    if syscall in WRITE_SYSCALLS:
        return "write"
    if syscall in READ_SYSCALLS:
        return "read"
    return "read"


def _classify_open_access(syscall, record, is_directory=False):
    if is_directory:
        return "list"
    if syscall == "openat2":
        # openat2 takes a pointer to struct open_how; the flags are not in the
        # syscall arguments, so err on the side of reporting a write.
        return "write"
    flags_field = "a1" if syscall == "open" else "a2"
    try:
        flags = int(record["raw"].get(flags_field, ""), 16)
    except (TypeError, ValueError):
        return "write"
    if flags & O_PATH:
        return "list"
    if flags & O_ACCMODE:
        return "write"
    if flags & (O_CREAT | O_TRUNC | O_APPEND):
        return "write"
    return "read"


def _classify_result(record):
    if _value(record, "success", "yes") == "yes":
        return "success", 0

    exit_value = _to_int(record["raw"].get("exit"))
    errno_value = abs(exit_value) if exit_value is not None else None
    if errno_value in (EACCES, EPERM):
        return "denied", errno_value
    return "failed", errno_value


def _resolve_target(records, cwd):
    candidates = []
    for record in records:
        if record["type"] != "PATH":
            continue
        name = _value(record, "name")
        nametype = _value(record, "nametype")
        if not name or name in (".", ".."):
            continue
        if nametype == "PARENT":
            continue
        if not name.startswith("/") and cwd:
            name = os.path.join(cwd, name)
        candidates.append((nametype, name, _is_directory(record)))

    for preferred in ("NORMAL", "CREATE", "DELETE", "UNKNOWN"):
        for nametype, name, is_directory in candidates:
            if nametype == preferred:
                return name, is_directory
    if candidates:
        return candidates[-1][1], candidates[-1][2]
    return None, False


def build_event(lines, parser, config):
    match = EVENT_MESSAGE_RE.search(lines[0])
    if not match:
        return None

    records = parser.parse(lines)
    syscall_record = next((r for r in records if r["type"] == "SYSCALL"), None)
    if syscall_record is None:
        return None

    key = _value(syscall_record, "key")
    if not key or not key.startswith(config.get("key_prefix") or "devsecops"):
        return None

    syscall = _value(syscall_record, "syscall") or ""
    result, errno_value = _classify_result(syscall_record)

    cwd = next((_value(r, "cwd") for r in records if r["type"] == "CWD"), None)
    path, is_directory = _resolve_target(records, cwd)
    if path is None:
        path = (config.get("paths") or {}).get(key) or cwd or "unknown"

    access = _classify_access(syscall, syscall_record, is_directory)

    return {
        "ts": _iso_timestamp(match.group(1)),
        "path": path,
        "access": access,
        "result": result,
        "errno": errno_value,
        "syscall": syscall,
        "pid": _to_int(record_value(syscall_record, "pid")),
        "ppid": _to_int(record_value(syscall_record, "ppid")),
        "comm": _value(syscall_record, "comm"),
        "exe": _value(syscall_record, "exe"),
        "uid": _to_int(record_value(syscall_record, "uid")),
        "auid": _to_int(record_value(syscall_record, "auid")),
        "tty": _value(syscall_record, "tty"),
        "session": _to_int(record_value(syscall_record, "ses")),
        "key": key,
    }


def record_value(record, name):
    """Return the unquoted raw value, which is numeric for identity fields."""
    return _normalize(record["raw"].get(name))


UNSET_AUID = 4294967295


@functools.lru_cache(maxsize=128)
def _user_name(uid):
    if uid is None:
        return "unknown"
    if uid == UNSET_AUID:
        return "unset"
    try:
        return pwd.getpwuid(uid).pw_name
    except (KeyError, OSError):
        return str(uid)


def _user_label(uid):
    if uid is None:
        return "unknown"
    return f"{_user_name(uid)} ({uid})"


def _parent_label(ppid):
    if not ppid:
        return "unknown"
    try:
        with open(f"/proc/{ppid}/comm", encoding="utf-8", errors="replace") as handle:
            comm = handle.read().strip()
    except OSError:
        return str(ppid)
    return f"{ppid} {comm}" if comm else str(ppid)


def _process_name(event):
    exe = event.get("exe") or ""
    name = os.path.basename(exe)
    if name.endswith(" (deleted)"):
        name = name[: -len(" (deleted)")]
    return name or event.get("comm") or "unknown"


def _format_notification(event):
    process = _process_name(event)
    access = event["access"]
    if event["result"] == "denied":
        title = f"Denied: {process} -> {event['path']}"
        urgency = "critical"
    else:
        action = {"read": "read", "write": "wrote", "metadata": "changed"}.get(
            access, access
        )
        title = f"{process} {action} {event['path']}"
        urgency = "normal"

    user_line = f"user: {_user_label(event.get('uid'))}"
    auid = event.get("auid")
    if auid is not None and auid != event.get("uid") and auid != UNSET_AUID:
        user_line += f", login: {_user_label(auid)}"

    process_line = (
        f"process: {process} "
        f"(pid {event.get('pid', '?')}, parent {_parent_label(event.get('ppid'))})"
    )

    details = [f"exe: {event.get('exe') or 'unknown'}"]
    if event["result"] == "denied":
        errno_name = errno.errorcode.get(event.get("errno")) if event.get("errno") else None
        suffix = f" ({errno_name})" if errno_name else ""
        details.append(f"{access} denied{suffix}")
    else:
        details.append(access)
    if event.get("tty") and event["tty"] != "(none)":
        details.append(f"tty {event['tty']}")
    session = event.get("session")
    if session is not None and session != UNSET_AUID:
        details.append(f"session {session}")

    body = "\n".join([user_line, process_line, ", ".join(details)])
    return title, body, urgency


def _format_journal(event):
    process = _process_name(event)
    auid = event.get("auid")
    identity = (
        f"pid={event.get('pid')}, parent={_parent_label(event.get('ppid'))}, "
        f"uid={_user_label(event.get('uid'))}"
    )
    if auid is not None and auid != UNSET_AUID and auid != event.get("uid"):
        identity += f", auid={_user_label(auid)}"

    details = [f"exe={event.get('exe') or 'unknown'}"]
    if event.get("tty") and event["tty"] != "(none)":
        details.append(f"tty={event['tty']}")
    session = event.get("session")
    if session is not None and session != UNSET_AUID:
        details.append(f"ses={session}")

    return (
        f"{event['result']} {event['access']} on {event['path']} "
        f"by {process} ({identity}, {', '.join(details)}, "
        f"key={event.get('key') or 'unknown'})"
    )


def append_jsonl(path, payload):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, mode=0o750, exist_ok=True)
    data = (json.dumps(payload, sort_keys=True) + "\n").encode("utf-8")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.write(descriptor, data)
    finally:
        os.close(descriptor)


def _load_config(path):
    config = dict(DEFAULT_CONFIG)
    config["paths"] = {}
    candidate = path or DEFAULT_CONFIG_FILE
    if not path and not os.path.exists(candidate):
        return config
    try:
        with open(candidate, encoding="utf-8") as handle:
            loaded = json.load(handle)
    except FileNotFoundError:
        raise SystemExit(f"configuration file '{candidate}' does not exist") from None
    except (OSError, ValueError) as error:
        raise SystemExit(f"cannot read configuration '{candidate}': {error}") from error
    if not isinstance(loaded, dict):
        raise SystemExit(f"configuration '{candidate}' must be a JSON object")
    config.update(loaded)
    return config


def _setup_logging(journal=True):
    logger = logging.getLogger("devsecops-audit")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    stream_handler = logging.StreamHandler(sys.stderr)
    stream_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(stream_handler)

    if journal:
        try:
            syslog_handler = logging.handlers.SysLogHandler(
                address="/dev/log",
                facility=logging.handlers.SysLogHandler.LOG_AUTHPRIV,
            )
            syslog_handler.append_nul = False
            syslog_handler.ident = "devsecops-audit: "
            syslog_handler.setFormatter(logging.Formatter("%(message)s"))
            logger.addHandler(syslog_handler)
        except OSError as error:
            logger.warning("journald logging unavailable: %s", error)
    return logger


def _parse_args(argv):
    parser = argparse.ArgumentParser(description="Audit log watcher for monitored paths")
    parser.add_argument(
        "--config",
        help=f"JSON configuration file (default: {DEFAULT_CONFIG_FILE})",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="process the existing audit log and exit (self-test)",
    )
    parser.add_argument("--audit-log", help="override the audit log file")
    parser.add_argument("--log-file", help="override the curated JSONL log file")
    parser.add_argument(
        "--no-notify",
        action="store_true",
        help="log alerts but skip desktop notifications",
    )
    parser.add_argument(
        "--no-journal",
        action="store_true",
        help="skip syslog records (intended for tests)",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)
    config = _load_config(args.config)
    if args.audit_log:
        config["audit_log_file"] = args.audit_log
    if args.log_file:
        config["log_file"] = args.log_file

    logger = _setup_logging(journal=not args.no_journal)
    if auparse is None:
        logger.error("python3-audit is required; the 'auparse' module is missing")
        return 2
    if not args.once and os.geteuid() != 0:
        logger.error("the watcher must run as root to read the audit log")
        return 2

    parser = AuditParser()
    notifier = Notifier(config, logger, desktop_enabled=not args.no_notify)
    follower = AuditLogFollower(config["audit_log_file"], logger)
    logger.info(
        "watching %s for keys prefixed '%s' and writing %s",
        config["audit_log_file"],
        config.get("key_prefix"),
        config["log_file"],
    )
    processed = 0
    access_counts = collections.Counter()
    try:
        for group in _group_events(follower.stream(once=args.once)):
            event = build_event(group, parser, config)
            if event is None:
                continue
            try:
                append_jsonl(config["log_file"], event)
            except OSError as error:
                logger.error("cannot append to %s: %s", config["log_file"], error)
            notifier.notify(event)
            access_counts[event["access"]] += 1
            processed += 1
    except KeyboardInterrupt:
        logger.info("stopping on interrupt")
    except OSError as error:
        logger.error("cannot read %s: %s", config["audit_log_file"], error)
        return 1

    if args.once:
        summary = ", ".join(
            f"{name}={access_counts.get(name, 0)}"
            for name in ("read", "write", "metadata", "list")
        )
        print(f"processed {processed} event(s) ({summary})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
