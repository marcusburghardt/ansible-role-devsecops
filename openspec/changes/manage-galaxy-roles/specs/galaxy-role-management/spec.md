# Spec Delta

## Purpose

Declarative management of Ansible Galaxy roles through a rendered requirements
file and a companion update script that reports version changes.

## ADDED Requirements

### Requirement: Declarative role list variable

The role SHALL expose a default variable `devsecops_galaxy_roles` (empty list)
that users override in their playbook to declare desired Galaxy roles. Each entry
MUST support `name` (required) and `version` (optional, defaults to latest).

#### Scenario: User defines roles without version pinning
- **WHEN** the user sets `devsecops_galaxy_roles` to a list of entries each
  containing only `name`
- **THEN** the role treats each entry as requesting the latest available version

#### Scenario: User pins a specific version
- **WHEN** the user sets an entry with `name: marcusburghardt.vim` and
  `version: "v1.0.0"`
- **THEN** the rendered requirements file pins that role to version `v1.0.0`

#### Scenario: User tracks a branch
- **WHEN** the user sets an entry with `name: marcusburghardt.vscode` and
  `version: main`
- **THEN** the rendered requirements file pins that role to the `main` branch

### Requirement: Requirements file rendering

The role SHALL render a `requirements.yml` file from a Jinja2 template using
the `devsecops_galaxy_roles` variable. The output path MUST be configurable
via `devsecops_galaxy_requirements_dir` (default: `{{ playbook_dir }}`).

#### Scenario: Template renders valid requirements file
- **WHEN** the task runs with a non-empty `devsecops_galaxy_roles` list
- **THEN** a valid `requirements.yml` is written to the configured directory
  containing all declared roles

#### Scenario: Empty role list renders minimal file
- **WHEN** the task runs with an empty `devsecops_galaxy_roles` list
- **THEN** a valid `requirements.yml` is written with an empty roles list

### Requirement: Update script deployment

The role SHALL deploy an `update_galaxy_roles.py` script to a configurable
directory (`devsecops_scripts_dir`, default: `~/bin`). The script MUST be
executable (mode `0700`).

#### Scenario: Script is deployed to target directory
- **WHEN** the `manage_galaxy_roles` task runs
- **THEN** the script exists at `<devsecops_scripts_dir>/update_galaxy_roles.py`
  with mode `0700`

### Requirement: Galaxy role installation during playbook run

The task SHALL execute `ansible-galaxy role install` with the rendered
`requirements.yml` and `--force` to ensure roles are current on every run.

#### Scenario: Roles are installed on first run
- **WHEN** the playbook runs and no Galaxy roles exist locally
- **THEN** all declared roles are installed to the Galaxy roles path

#### Scenario: Roles are updated on subsequent runs
- **WHEN** the playbook runs and a newer version of a role is available on Galaxy
- **THEN** the role is updated to the latest version (or pinned version)

### Requirement: Update script version diff

The update script SHALL display a before/after comparison of installed role
versions when run manually. It MUST read `requirements.yml`, snapshot current
versions from `meta/.galaxy_install_info`, run the Galaxy install, snapshot
new versions, and display results.

#### Scenario: Script shows updated roles
- **WHEN** the user runs the script and a role has a newer version available
- **THEN** the output shows the role name, old version, new version, and
  status `(updated)`

#### Scenario: Script shows up-to-date roles
- **WHEN** the user runs the script and a role is already at the latest version
- **THEN** the output shows the role name, current version, and
  status `(up to date)`

#### Scenario: Script shows newly installed roles
- **WHEN** the user runs the script and a role is not yet installed locally
- **THEN** the output shows the role name, `(not installed)` as old version,
  the installed version, and status `(installed)`

### Requirement: Task is opt-in by default

The `manage_galaxy_roles` task MUST default to `enabled: false` in
`defaults/main.yml` so existing users are unaffected.

#### Scenario: Task disabled by default
- **WHEN** a user runs the role without overriding `devsecops_tasks`
- **THEN** the `manage_galaxy_roles` task does not execute
