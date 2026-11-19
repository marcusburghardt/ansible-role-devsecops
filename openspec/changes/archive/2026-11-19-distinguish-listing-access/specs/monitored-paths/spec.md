# Spec Delta

## ADDED Requirements

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
