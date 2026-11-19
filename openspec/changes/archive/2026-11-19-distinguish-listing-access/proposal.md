# Proposal

## Why

Directory listings (`ls`, `find`, indexers) and metadata checks only enumerate
paths and attributes, but the watcher classifies them as successful reads and
raises notifications. That floods users with alerts that do not represent
content access.

## What Changes

- Classify metadata-enumeration syscalls and directory opens as `list`.
- Record listing events in the curated JSONL log but never notify on them.
- Keep content reads, writes, metadata changes, and denied attempts notified.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `monitored-paths`: listing access is logged and excluded from notifications.

## Impact

- `files/scripts/audit_watch.py`, `tests/fixtures/audit-monitor-sample.log`,
  `tests/test_audit_watch.py`, `README.md`.
