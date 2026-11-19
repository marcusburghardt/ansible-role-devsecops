# Proposal

## Why

This role prepares developer and DevSecOps workstations but offers no way to
detect access to sensitive local paths such as secret files, keys, and
configuration directories. Users would have to assemble auditd rules and an
alerting mechanism themselves, which is error-prone: directory rules must be
recursive, denied attempts are easy to miss, and auditd notifies nobody by
default.

## What Changes

- Add a new togglable task `monitor_paths`, disabled by default.
- Let users declare files and directories in `devsecops_monitored_paths`. The
  role generates auditd rules, including recursive directory watches and
  explicit failed-access rules.
- Ensure `auditd` is installed, enabled, and configured with desktop-safe
  retention defaults.
- Deploy a root-owned `devsecops-audit-watch` systemd service that tails the
  audit log, filters role-managed events, writes a curated JSONL access log, and
  raises native desktop notifications for successful reads, writes, metadata
  changes, and denied attempts.
- Keep reconfiguration idempotent: rules reload with `augenrules --load` and
  auditd re-reads its configuration with `auditctl --signal reload`; no daemon
  restart is required.
- Document the feature in the README with variables, an example, and
  verification steps.

## Capabilities

### New Capabilities

- `monitored-paths`: Declarative declaration and kernel-level auditing of
  sensitive files and directory trees, including denied attempts, a curated
  JSONL access log, and immediate desktop notifications.

### Modified Capabilities

(none)

## Impact

- **New files**: `tasks/monitor_paths.yml`, `vars/monitor_paths.yml`,
  `templates/audit-monitor.rules.j2`, `templates/audit-monitor.json.j2`,
  `templates/devsecops-audit-watch.service.j2`,
  `templates/devsecops-monitor.logrotate.j2`,
  `files/scripts/audit_watch.py`.
- **Modified files**: `defaults/main.yml`, `handlers/main.yml`, `README.md`.
- **System impact**: installs `audit`, `python3-audit`, and `libnotify`; writes
  `/etc/audit/rules.d/50-devsecops-monitor.rules`, `/etc/devsecops/`, and
  `/var/log/devsecops/`; enables `auditd` and the watcher service.
- **No breaking changes**: the new task defaults to `enabled: false`, so
  existing users are unaffected.
