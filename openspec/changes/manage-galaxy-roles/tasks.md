# Tasks

## 1. Role defaults and variables

- [x] 1.1 Add `manage_galaxy_roles` entry (enabled: false) to `devsecops_tasks` in `defaults/main.yml`. Verify by inspecting the file and confirming the new entry is present with `enabled: false`.
- [x] 1.2 Add default variables to `defaults/main.yml`: `devsecops_galaxy_roles: []`, `devsecops_galaxy_requirements_dir: "{{ playbook_dir }}"`, `devsecops_scripts_dir: "{{ ansible_facts['user_dir'] }}/bin"`. Verify each variable is present with correct default values.
- [x] 1.3 Create `vars/manage_galaxy_roles.yml` as a placeholder file (matching the pattern of other vars files). Verify the file exists and the dispatcher's `include_vars` will not error.

## 2. Requirements template

- [x] 2.1 Create `templates/` directory and `templates/requirements.yml.j2` Jinja2 template. The template MUST iterate over `devsecops_galaxy_roles`, render `name` for each entry, conditionally render `version` when defined, and include the `{{ ansible_managed | comment }}` header. Verify by reviewing the template syntax for correctness.

## 3. Update script

- [x] 3.1 Create `files/scripts/` directory and `files/scripts/update_galaxy_roles.py`. The script MUST follow the `review_pr.py` pattern: Python 3, argparse, type hints, module-level constants, small focused functions. It MUST accept `--requirements` / `-r` (default: `./requirements.yml`), `--roles-path` / `-p` (default: `./galaxy_roles`), and `--check` (show versions without updating). Verify the script parses arguments correctly with `--help`.
- [x] 3.2 Implement version snapshot logic: parse `requirements.yml` with PyYAML, read `meta/.galaxy_install_info` from each installed role directory to determine current version. Handle missing roles (not yet installed) and missing info files. Verify by running the script with `--check` against a directory with installed roles.
- [x] 3.3 Implement the update and diff logic: snapshot before, run `ansible-galaxy role install -r <file> --force`, snapshot after, display a formatted table showing `role_name  old_version -> new_version  (status)` with a summary line. Verify by running the script against a test roles directory and confirming output format matches the spec.

## 4. Ansible task file

- [x] 4.1 Create `tasks/manage_galaxy_roles.yml` with three steps: (1) ensure `devsecops_scripts_dir` directory exists (mode 0750), (2) deploy `update_galaxy_roles.py` from `files/scripts/` (mode 0700, force: true), (3) render `requirements.yml.j2` to `devsecops_galaxy_requirements_dir` using `ansible.builtin.template`. Verify by reviewing the task file for correct module usage and variable references.
- [x] 4.2 Add a fourth step to the task file: execute `ansible-galaxy role install -r <rendered requirements.yml> --force` using `ansible.builtin.command`. Gate this step on `devsecops_galaxy_roles` being non-empty. Verify the task includes a `when` condition and uses the correct command.

## 5. Integration verification

- [x] 5.1 Run `yamllint` on all new and modified YAML files (`defaults/main.yml`, `vars/manage_galaxy_roles.yml`, `tasks/manage_galaxy_roles.yml`, `templates/requirements.yml.j2`). Verify zero lint errors.
- [x] 5.2 Run `ansible-playbook --syntax-check` against a minimal test playbook that enables the `manage_galaxy_roles` task with a sample `devsecops_galaxy_roles` list. Verify the syntax check passes.
