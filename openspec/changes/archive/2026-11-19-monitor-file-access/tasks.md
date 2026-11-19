# Tasks

## 1. Role scaffolding

- [x] 1.1 Add the disabled `monitor_paths` entry to `devsecops_tasks` and the
      new monitored-path, notification, and auditd defaults to
      `defaults/main.yml`; verify with `yamllint defaults/main.yml` and
      `ansible-playbook tests/test.yml --syntax-check`.
- [x] 1.2 Create `vars/monitor_paths.yml` with the `audit`, `python3-audit`,
      and `libnotify` package list, the audit architecture list derived from
      `ansible_facts['architecture']`, and the managed file paths; verify the
      variables resolve with `ansible-inventory --host localhost` plus
      `--syntax-check`.

## 2. Audit rule generation

- [x] 2.1 Create `tasks/monitor_paths.yml` to validate each enabled path with
      `ansible.builtin.stat`, fail with the path name when missing, and derive
      file-vs-directory, audit key, and access mask facts; verify a deliberately
      missing path fails the play before any rule is written.
- [x] 2.2 Create `templates/audit-monitor.rules.j2` rendering `path=` rules for
      files and recursive `dir=` rules for directories, with `perm` success
      rules and `success=0` failure rules per architecture; verify with
      `auditctl -l | grep devsecops` and confirm the rule count matches the
      entries with both success and failure rules present.
- [x] 2.3 Add a rule-reload handler that runs `augenrules --load`; verify a
      changed path updates `auditctl -l` without changing auditd's start time
      (`systemctl show -p ActiveEnterTimestamp auditd`).

## 3. Auditd management

- [x] 3.1 Install the audit packages and ensure `auditd` is enabled and
      started; verify with `systemctl is-enabled auditd` and
      `systemctl is-active auditd`.
- [x] 3.2 Manage the defined `auditd.conf` retention and disk-pressure keys with
      `lineinfile` and add an `auditctl --signal reload` handler; verify the
      rendered keys with `grep` and the reload with `auditctl -s`.
- [x] 3.3 Detect a masked auditd unit, an immutable audit state (`enabled=2`),
      or a failed auditd start, and fail with an actionable message; verify the
      immutable branch by checking the task output when `auditctl -s` reports
      `enabled 2`.

## 4. Access watcher

- [x] 4.1 Implement `files/scripts/audit_watch.py` to tail the audit log with
      `auparse`, filter events by the `devsecops` key prefix, correlate
      `SYSCALL`/`CWD`/`PATH` records, classify read/write/metadata and
      success/denied, append JSONL, and send throttled desktop notifications via
      `runuser` while always emitting to journald; verify with a `--once`
      self-test against a captured audit-log sample and with `python3 -m py_compile`.
- [x] 4.2 Add `templates/audit-monitor.json.j2`,
      `templates/devsecops-audit-watch.service.j2`, and
      `templates/devsecops-monitor.logrotate.j2`; verify the unit with
      `systemd-analyze verify` and the rotation policy with `logrotate -d`.
- [x] 4.3 Add a watcher restart handler and ensure the service starts after
      `auditd` and restarts on failure; verify `systemctl status
      devsecops-audit-watch` and `journalctl -t devsecops-audit` after a
      triggered access.
- [x] 4.4 Document the watcher configuration file and service in the README;
      verify the documented paths and variable names match the deployed files.

## 5. Documentation

- [x] 5.1 Add the `monitor_paths` row to the README task table, the variable
      table entries, an example playbook snippet, and the verification commands;
      verify every documented command and variable name against the rendered
      configuration.

## 6. Integration checks

- [x] 6.1 Create a temporary monitored directory, run the role, read and write
      a file as the desktop user, and attempt a read as `nobody`; verify the
      JSONL log contains success and denied records with process identity, and
      that a desktop notification appears for each.
- [x] 6.2 Reboot the target and verify `auditctl -l` still lists the managed
      rules, `devsecops-audit-watch` is active, and a new access still produces
      a log entry and notification.
- [x] 6.3 Re-run the playbook with unchanged input and verify Ansible reports no
      changes.
- [x] 6.4 Exercise the rollback from `design.md` (remove the rules file, reload
      audit rules, stop the watcher) and verify monitoring stops without
      disrupting auditd.

## Workflow follow-up

- Run `openspec validate monitor-file-access --strict`.
- Archive the change after the project's review requirements are satisfied.
