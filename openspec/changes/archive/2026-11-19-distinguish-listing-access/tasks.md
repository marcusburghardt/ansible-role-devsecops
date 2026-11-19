# Tasks

## 1. Classification

- [x] 1.1 Add listing syscalls and directory/`O_PATH` detection to
      `files/scripts/audit_watch.py`; verify with unit tests and a `--once`
      fixture run.
- [x] 1.2 Suppress notifications for successful `list` events while keeping
      denied notifications; verify with unit tests.

## 2. Tests and documentation

- [x] 2.1 Extend `tests/fixtures/audit-monitor-sample.log` with `newfstatat`
      and directory-open events; verify the access types and `--once` summary.
- [x] 2.2 Add `tests/test_audit_watch.py` and run
      `python3 -m unittest discover -s tests`.
- [x] 2.3 Update the README access types and notification behavior; verify with
      `openspec validate distinguish-listing-access --strict`.
