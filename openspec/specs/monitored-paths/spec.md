# monitored-paths Specification

## Purpose
Provide declarative, kernel-level auditing of user-selected files and directory
trees on a workstation, with a curated access log and native desktop
notifications for both successful and denied access.

## Requirements

### Requirement: Declarative path configuration

The role SHALL accept a list of monitored path entries. Each enabled entry MUST
define a path, an audit key, and an access mask composed of `r`, `w`, `x`, and
`a`. The `monitor_paths` task MUST be opt-in and disabled by default.

#### Scenario: Monitoring enabled for a directory

- **WHEN** the user enables `monitor_paths` and defines a directory in
  `devsecops_monitored_paths`
- **THEN** the role configures auditing for that directory tree without
  requiring the user to write audit rules

#### Scenario: Monitoring left disabled

- **WHEN** the user does not enable `monitor_paths`
- **THEN** the role changes no audit configuration and installs no watcher
  service

### Requirement: Path validation

The role SHALL fail with a clear message when an enabled monitored path does
not exist, and MUST NOT load a partially generated rule set. The role SHALL
treat directories as recursive trees and files as individual inodes.

#### Scenario: Missing monitored path

- **WHEN** an enabled entry references a path that does not exist on the target
- **THEN** the play fails and identifies the missing path

#### Scenario: Mixed file and directory entries

- **WHEN** the list contains both a file and a directory
- **THEN** the generated rules watch the file individually and the directory
  recursively

### Requirement: Successful access capture

While monitoring is enabled, the kernel audit rules SHALL record successful
read, write, and metadata operations on the configured paths. Each recorded
event MUST include a timestamp, the path, the access type, the process identity
(pid, ppid, comm, exe), the user identity (uid, auid), and the audit key.

#### Scenario: Reading a monitored file

- **WHEN** a process opens a monitored file for reading
- **THEN** an event with access type `read` and the process identity is
  recorded

#### Scenario: Writing a monitored file

- **WHEN** a process opens a monitored file for writing or truncates it
- **THEN** an event with access type `write` is recorded

#### Scenario: Metadata change

- **WHEN** a process changes permissions, ownership, or extended attributes on
  a monitored path
- **THEN** an event with access type `metadata` is recorded

#### Scenario: New file inside a monitored directory

- **WHEN** a file is created in a subdirectory of a monitored directory and is
  later accessed
- **THEN** access to that file is recorded without reloading the rules

### Requirement: Denied attempt capture

The audit rules SHALL record failed access attempts on monitored paths. Events
whose failure is `EACCES` or `EPERM` MUST be reported with result `denied` and
SHALL include the best available path and process identity.

#### Scenario: Unprivileged read denied

- **WHEN** an unprivileged user attempts to read a monitored file without
  permission
- **THEN** an event with result `denied` and the requesting process identity is
  recorded

#### Scenario: Denied metadata change

- **WHEN** a process attempts to change ownership or permissions on a monitored
  path without permission
- **THEN** an event with result `denied` is recorded

### Requirement: Curated access log

The watcher SHALL append one JSON object per access event to a configurable log
file, defaulting to `/var/log/devsecops/monitored-access.log`. Each object MUST
contain the event timestamp, path, access type, result, process identity, user
identity, and audit key. The log MUST be rotated with bounded retention and the
watcher MUST continue writing after rotation. The raw audit log SHALL remain the
authoritative forensic record.

#### Scenario: Event written as JSON

- **WHEN** a monitored path is accessed
- **THEN** a single JSON object describing the event is appended to the curated
  log

#### Scenario: Log rotation

- **WHEN** the curated log is rotated
- **THEN** subsequent events are written to the new log file without restarting
  the watcher

#### Scenario: Custom log location

- **WHEN** the user sets a custom log file path
- **THEN** events are written to that path with root-only permissions

### Requirement: Immediate notifications

The watcher SHALL raise a native desktop notification in the logged-in user's
session for every successful access matching the configured notification access
mask and for every denied attempt. It SHALL also emit a journald record for
every alert so that alerts are not lost when no graphical session exists. The
watcher MUST throttle notifications per path and result and SHALL report the
number of suppressed events in the next notification.

#### Scenario: Successful access notification

- **WHEN** a successful read matches the configured notification access mask
- **THEN** a desktop notification identifies the path, access type, and process

#### Scenario: Denied access notification

- **WHEN** an access attempt is denied
- **THEN** a high-urgency desktop notification is raised regardless of the
  successful-access notification mask

#### Scenario: No graphical session

- **WHEN** the target user has no active desktop session
- **THEN** the watcher still records the alert in journald and continues running

#### Scenario: Notification storm

- **WHEN** more events occur than the configured notification rate
- **THEN** notifications are suppressed and the next notification reports how
  many events were suppressed

### Requirement: Safe and idempotent auditd management

The role SHALL install and enable `auditd`, manage only a defined set of
retention settings in `auditd.conf`, and load rules without restarting the
daemon. Configuration changes MUST be applied by reloading auditd and rules MUST
be applied with `augenrules`. Disk-pressure actions MUST NOT halt the system or
suspend auditing on a workstation. Re-running the role with unchanged input
MUST NOT report changes.

#### Scenario: Applying new rules

- **WHEN** the generated rules file changes
- **THEN** the role loads the new rules without restarting `auditd`

#### Scenario: Auditd configuration change

- **WHEN** a managed `auditd.conf` setting changes
- **THEN** the role asks `auditd` to re-read its configuration

#### Scenario: Idempotent rerun

- **WHEN** the play runs twice with the same monitored paths
- **THEN** the second run reports no changes

### Requirement: Watcher resilience

The watcher MUST run as a root-owned systemd service that starts after
`auditd`, restarts automatically on failure, and follows audit log rotation. A
watcher failure MUST NOT stop kernel auditing or the writing of the raw audit
log.

#### Scenario: Watcher crash

- **WHEN** the watcher process exits unexpectedly
- **THEN** systemd restarts it and auditd continues recording events

#### Scenario: Audit log rotation

- **WHEN** auditd rotates its log file
- **THEN** the watcher continues reading events from the new file

### Requirement: Listing access classification

The watcher SHALL classify successful metadata-enumeration operations — stat,
readdir/getdents, readlink, extended-attribute enumeration, and opens of
directories or paths with `O_PATH` — as access type `list`. Listing events MUST
be written to the curated log and MUST NOT raise desktop or journald
notifications. Content reads, writes, metadata changes, and denied attempts
SHALL continue to notify according to the configured policy.

#### Scenario: Directory listing

- **WHEN** a process lists a monitored directory without reading file contents
- **THEN** the event is logged with access type `list` and no notification is
  raised

#### Scenario: Content read

- **WHEN** a process opens and reads a monitored regular file
- **THEN** the event is logged with access type `read` and the configured
  notification is raised

#### Scenario: Denied listing

- **WHEN** an unprivileged process is denied access while enumerating a
  monitored path
- **THEN** the event is logged with result `denied` and a notification is
  raised
