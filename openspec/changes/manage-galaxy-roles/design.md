# Design

## Context

The role uses a two-pass dispatcher in `tasks/main.yml`: first loading
per-task variables from `vars/<task.name>.yml`, then including
`tasks/<task.name>.yml`. Every feature follows this pattern. See
`proposal.md` for motivation.

The sibling role `ansible-role-git` deploys scripts to `~/bin` via an
`add_supporting_scripts` task. This change introduces the same capability
to `ansible-role-devsecops` but scoped to a single cohesive task rather
than a generic script deployer, since the script and the requirements
template are tightly coupled.

Galaxy roles store install metadata in `meta/.galaxy_install_info` with
`version` and `install_date` fields. The update script relies on this file
to determine currently installed versions.

## Goals / Non-Goals

**Goals:**

- Follow the existing dispatcher pattern exactly (new task entry, vars
  file, task file).
- Match the `review_pr.py` coding style: Python 3, argparse, type hints,
  constants at module level, small focused functions.
- Provide a `requirements.yml` template managed by the role so the user
  only needs to declare roles in playbook variables.
- Provide a standalone script for ad-hoc updates between playbook runs
  with clear version diff output.

**Non-Goals:**

- Adding a generic `add_supporting_scripts` task to devsecops. The script
  deployment is part of `manage_galaxy_roles` itself.
- Managing Ansible collections (only roles).
- Querying the Galaxy API for available versions. The script relies on
  `ansible-galaxy install --force` to fetch the latest and compares
  before/after locally.
- Adding a Makefile. The project explicitly excludes Makefiles.

## Decisions

### 1. Single task vs. separate render/deploy/install tasks

**Decision**: One task `manage_galaxy_roles` handles all three steps
(render template, deploy script, run install).

**Rationale**: The requirements template, the script, and the install step
are tightly coupled. Splitting them would force users to enable multiple
tasks in the correct order. Every other feature in this role is a single
togglable unit.

**Alternative considered**: Separate `render_requirements` and
`install_galaxy_roles` tasks. Rejected because it adds configuration
complexity without benefit.

### 2. Script reads `requirements.yml` rather than accepting role names as arguments

**Decision**: The script always operates from a `requirements.yml` file.

**Rationale**: The file is the single source of truth for desired roles.
Accepting ad-hoc role names on the command line would create a second,
divergent source. The file is also what `ansible-galaxy` natively consumes.

**Alternative considered**: Accept role names as positional arguments.
Rejected because it duplicates the role list and risks drift.

### 3. Version detection via `meta/.galaxy_install_info`

**Decision**: Read `meta/.galaxy_install_info` in each installed role
directory to determine the current version.

**Rationale**: This is the file `ansible-galaxy` creates on install. It is
the canonical record of what version was installed and when. Parsing
`meta/main.yml` would not work because Galaxy roles do not embed their
version there (versions come from git tags).

**Alternative considered**: Run `ansible-galaxy role list` and parse its
output. Rejected because it mixes multiple roles paths and its output
format is not a stable API.

### 4. Script in `files/scripts/` deployed via `ansible.builtin.copy`

**Decision**: Place the script in `files/scripts/update_galaxy_roles.py`
and deploy it with `ansible.builtin.copy`, following the pattern from
`ansible-role-git`.

**Rationale**: Consistent with the established pattern across sibling
roles. The script has no template variables, so `copy` is correct (not
`template`).

### 5. Default roles path resolution

**Decision**: The script defaults to `./galaxy_roles` as the roles
installation path (matching the user's `ansible.cfg`). The Ansible task
uses `ansible-galaxy install -r <path> --force` without `-p`, letting
`ansible.cfg` determine the path.

**Rationale**: During playbook execution, `ansible.cfg` is already loaded
and `ansible-galaxy` respects it. The script, run standalone, needs a
sensible default but accepts `--roles-path` to override.

### 6. Template uses `ansible_managed` comment

**Decision**: The rendered `requirements.yml` includes the
`{{ ansible_managed | comment }}` header.

**Rationale**: Standard Ansible practice for templated files. Signals to
the user that the file is role-managed and manual edits will be
overwritten.

## Risks / Trade-offs

- **[Network dependency during playbook run]** The install step requires
  Galaxy API access. **Mitigation**: The task is opt-in (`enabled: false`
  by default). Users who enable it accept the network dependency, same as
  `update_images` which pulls Podman images.

- **[Updating roles mid-playbook]** If `manage_galaxy_roles` runs before
  other tasks that use Galaxy roles, the update is safe. If ordered after,
  a role could change under a running play. **Mitigation**: Document that
  `manage_galaxy_roles` should be listed first in `devsecops_tasks`.

- **[PyYAML dependency in the script]** The script needs to parse YAML.
  PyYAML is a transitive dependency of Ansible itself, so it is always
  available in an Ansible-managed environment. **Mitigation**: None needed;
  document the assumption.
