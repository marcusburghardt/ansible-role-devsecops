# Design

## Context

See `proposal.md` for motivation and `specs/monitored-paths/spec.md` for the
behavior contract. The role uses a task dispatcher: entries in
`devsecops_tasks` load `vars/<task>.yml` and then `tasks/<task>.yml`. The
feature must fit that pattern, default to disabled, and remain idempotent.

The target platforms are Fedora and EL. Both ship the `audit` userspace
package, and `python3-audit` provides the `auparse` bindings used by the
watcher. `auditd` is a system service; its unit sets `RefuseManualStop=yes`, so
`systemctl restart auditd` is not a valid configuration mechanism.

## Goals / Non-Goals

**Goals:**

- Capture successful and denied access with process identity using native,
  kernel-level auditing.
- Keep the user-facing configuration to a list of paths, an access mask, and an
  optional key.
- Deliver alerts as native desktop notifications without losing them when no
  graphical session exists.
- Keep auditd configuration and rule rollout idempotent and non-disruptive.

**Non-Goals:**

- Per-`read()` syscall tracing. Audit records the access-granting operation, not
  every read on an already-open file descriptor.
- Central log forwarding, immutable audit rules, or tamper resistance against
  root.
- Monitoring network filesystems, container-internal paths, or paths below a
  mount point.
- Replacing or reconfiguring an existing enterprise audit baseline.

## Decisions

### 1. Use auditd as the capture backend

**Decision:** Generate kernel audit rules and read events from auditd.

**Rationale:** auditd is the only native option that provides pid, ppid, comm,
exe, auid/uid, session, tty, syscall, and success/failure in one record.
inotify cannot identify the accessing process. fanotify could, but has no
supported CLI in the base repositories and no per-path filtering. eBPF is
capable but adds kernel/BPF dependencies, has no durable audit trail, and is
harder to keep stable across EL and Fedora kernels.

**Alternatives considered:** `inotify-tools` (rejected: no process identity),
`fatrace`/fanotify (rejected: EPEL-only and no path filter), `bpftrace`/`opensnoop`
(rejected: no forensic log and higher operational risk), osquery/Falco
(rejected: not native DNF packages).

### 2. Use syscall-based `path=`/`dir=` rules, not `-w`

**Decision:** Render explicit rules:

```text
# successful access (file)
-a always,exit -F arch=b64 -F path=/etc/shadow -F perm=rwa -F success=1 -k devsecops_shadow

# successful access (directory, recursive subtree)
-a always,exit -F arch=b64 -F dir=/srv/secrets -F perm=rwa -F success=1 -k devsecops_secrets

# denied attempts (same key, classified by the watcher)
-a always,exit -F arch=b64 -F dir=/srv/secrets \
   -S open,openat,openat2,creat,truncate,ftruncate,chmod,fchmod,fchmodat,\
chown,fchown,lchown,fchownat,rename,renameat,renameat2,unlink,unlinkat \
   -F success=0 -k devsecops_secrets
```

**Rationale:** On modern kernels, `auditctl` maps directory paths to the audit
tree implementation (`AUDIT_DIR`), which tags every inode in the subtree and
tracks new files dynamically. One rule per directory therefore covers the whole
tree, including files created later. `-w` is deprecated for performance and
merely expands to the same rule form. Splitting success and failure rules makes
denied-attempt capture explicit; `perm=` alone is not a reliable contract for
failures.

**Arch handling:** Render `b64` and `b32` rules on `x86_64` and `b32`/`b64`
according to the target architecture, so 32-bit applications are covered on
64-bit hosts. `vars/monitor_paths.yml` derives the list from
`ansible_facts['architecture']`.

**Rule file:** `/etc/audit/rules.d/50-devsecops-monitor.rules`.
`augenrules` version-sorts the directory and hoists any `-D` directive to the
top, so this file cannot be wiped by another file's reset.

### 3. Use a standalone watcher service, not an audisp plugin

**Decision:** Tail `/var/log/audit/audit.log` from a root-owned systemd service
that uses `auparse` to group and interpret records.

**Rationale:** A separate service keeps the watcher outside auditd's failure
domain: if it crashes or is slow, auditd keeps writing the raw log. Rules reload
without restarting auditd, whereas activating an audisp plugin requires an
auditd restart. The watcher can use `auparse` from `python3-audit` to correlate
`SYSCALL`, `CWD`, `PATH`, and `PROCTITLE` records and to interpret uid, syscall,
and open flags.

**Alternatives considered:** custom audisp plugin (rejected: auditd restart and
shared failure domain), `audisp-syslog` + rsyslog (rejected: extra packages and
fragile text matching), `ausearch` timer (rejected: not immediate).

**Log following:** `tail -F` or an equivalent inode-aware reader handles both
auditd's own rotation and the curated log rotation.

### 4. Write a curated JSONL log in addition to the raw audit log

**Decision:** The watcher appends one JSON object per event to
`/var/log/devsecops/monitored-access.log` (configurable), while auditd keeps the
authoritative record at `/var/log/audit/audit.log`.

**Rationale:** `ausearch -k` is the right forensic tool, but a JSONL stream is
easier to tail, ship, or aggregate. Keeping the raw log authoritative means a
watcher bug cannot destroy evidence.

**Format:** JSONL with `ts`, `path`, `access`, `result`, `errno`, `syscall`,
`pid`, `ppid`, `comm`, `exe`, `uid`, `auid`, and `key`. Rotation is daily with a
configurable retention (default 30 days), 0600 root-owned files, and no
`copytruncate`.

### 5. Notify through the user's session bus, with journald as the floor

**Decision:** The watcher invokes `notify-send` via `runuser` with
`XDG_RUNTIME_DIR` and `DBUS_SESSION_BUS_ADDRESS` set for the configured user.
Every alert is also emitted to `authpriv.warning` in journald.

**Rationale:** A root process cannot reach the user's notification daemon
without entering the session bus. `notify-send` satisfies the "native
notification" requirement. journald is always available, so alerts survive
lock-screen, logout, and SSH-only operation.

Notification policy:
- Denied attempts always notify, with `-u critical`.
- Successful accesses notify when they match `devsecops_monitor_notify_access`
  (default `rwa`).
- A token bucket throttles per path and result (default 30/minute) and the next
  notification reports how many events were suppressed.

### 6. Manage only a defined subset of `auditd.conf`

**Decision:** Use `lineinfile` for a small set of keys rather than templating
the whole file.

```text
max_log_file = 50
num_logs = 10
max_log_file_action = ROTATE
space_left_action = SYSLOG
admin_space_left_action = SYSLOG
disk_full_action = SYSLOG
disk_error_action = SYSLOG
log_format = ENRICHED
flush = INCREMENTAL
freq = 20
```

**Rationale:** A workstation must never halt or stop auditing because the disk
filled up. The retention window must be large enough to be useful. Managing only
these keys preserves distro defaults and future package updates. Configuration is
applied with `auditctl --signal reload`; rules are applied with
`augenrules --load`.

### 7. Keep the watcher resilient and the service self-contained

**Decision:** Deploy the watcher to `/usr/local/sbin/devsecops-audit-watch` with
config at `/etc/devsecops/audit-monitor.json` and a systemd unit with
`After=auditd.service`, `Restart=always`, and `RestartSec=5`.

**Rationale:** The watcher is stateless: it re-reads configuration at startup
and restarts cleanly. `Requires=auditd.service` is intentionally avoided so that
a watcher restart cannot affect auditd. The service runs as root because
`/var/log/audit/audit.log` is root-only.

### 8. Role interface

```yaml
devsecops_tasks:
  - { enabled: false, name: 'monitor_paths' }

devsecops_monitored_paths:
  - { enabled: true, path: '/srv/secrets', access: 'rwa', key: 'secrets' }
  - { enabled: true, path: '/etc/shadow',  access: 'rwa', key: 'shadow' }

devsecops_monitor_log_file: '/var/log/devsecops/monitored-access.log'
devsecops_monitor_log_retention_days: 30
devsecops_monitor_notify_desktop: true
devsecops_monitor_notify_user: "{{ ansible_env.SUDO_USER | default(ansible_facts['user_id']) }}"
devsecops_monitor_notify_access: 'rwa'
devsecops_monitor_notify_denied: true
devsecops_monitor_notify_throttle: 30
devsecops_monitor_notify_command: ''
devsecops_monitor_audit_log_file: '/var/log/audit/audit.log'
devsecops_monitor_rules_file: '/etc/audit/rules.d/50-devsecops-monitor.rules'
devsecops_monitor_key_prefix: 'devsecops'
devsecops_monitor_manage_auditd_conf: true
```

A per-path `access` mask lets users avoid `x` when only text files are present.
An optional `key` defaults to a sanitized form of the path.

## Risks / Trade-offs

- **Read notifications are noisy** → per-path+result throttle with suppression
  counts; `devsecops_monitor_notify_access` can be narrowed to `wa` without
  losing log entries.
- **Denials can occur before the final path is resolved** → the watcher reports
  the best available `PATH` record, falling back to `CWD`; the raw log remains
  authoritative.
- **Recreated or moved watched directories** → audit trees follow inodes, so a
  deleted-and-recreated directory may need `augenrules --load` to be watched
  again. Documented; a refresh timer is out of scope.
- **Mount points below a watched directory are not followed** → document that
  each filesystem subtree needs its own entry.
- **Root can tamper with rules, daemon, and watcher** → accepted for a local-only
  feature; no immutability or remote forwarding.
- **`auditd` may be masked or audit may be disabled** → the task detects this
  and fails with an actionable message instead of silently doing nothing.
- **Auditd restart is forbidden by the unit** → handlers use HUP and
  `augenrules --load`; `state: restarted` is never used for `auditd`.
- **Containers/CI cannot run auditd** → verification is documented as
  system-level manual checks rather than containerized tests.

## Migration Plan

1. Add the `monitor_paths` entry (disabled) and the new variables to
   `defaults/main.yml`.
2. Run the playbook with the task enabled and `--check --diff` first to inspect
   the managed auditd keys, rules file, watcher config, and unit.
3. Apply, then verify:
   - `auditctl -l | grep devsecops`
   - `cat <path>` produces a success event in the curated log
   - `sudo -u nobody cat <path>` produces a denied event and a desktop popup
   - `journalctl -t devsecops-audit -f` shows alerts
   - reboot and confirm `auditctl -l` still contains the rules
4. Rollback: disable the task and remove
   `/etc/audit/rules.d/50-devsecops-monitor.rules`, then run
   `augenrules --load`; stop and disable `devsecops-audit-watch`, or keep the
   task enabled with an empty path list.
