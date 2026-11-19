# Proposal

## Why

Ansible Galaxy roles installed locally go stale because there is no automated
mechanism to keep them updated. Users must manually run `ansible-galaxy install`
for each role, which is tedious and error-prone. This role already manages
developer environment tooling; managing Galaxy role lifecycles fits naturally
here.

## What Changes

- Add a new togglable task `manage_galaxy_roles` to the role's dispatcher.
- Introduce a Jinja2 template that renders a `requirements.yml` file from a
  user-defined variable (`devsecops_galaxy_roles`), following the same override
  pattern used by all other role features.
- Add a Python script (`update_galaxy_roles.py`) deployed to `~/bin` that reads
  `requirements.yml`, compares installed versions against updated versions, runs
  `ansible-galaxy role install --force`, and displays a before/after diff.
- The task itself renders the template, deploys the script, and executes the
  Galaxy install so roles are current on every playbook run.

## Capabilities

### New Capabilities

- `galaxy-role-management`: Declarative management of Ansible Galaxy roles via a
  rendered `requirements.yml` template and an update script with version diff
  reporting.

### Modified Capabilities

(none)

## Impact

- **New files**: `templates/requirements.yml.j2`, `files/scripts/update_galaxy_roles.py`,
  `tasks/manage_galaxy_roles.yml`, `vars/manage_galaxy_roles.yml`.
- **Modified files**: `defaults/main.yml` (new task entry and default variables).
- **Dependencies**: The script requires `ansible-galaxy` and `pyyaml` (both
  available in any Ansible-managed environment). No new external dependencies.
- **No breaking changes**: The new task defaults to `enabled: false`, so existing
  users are unaffected.
