marcusburghardt.devsecops
=========================

This Ansible role installs packages and configures settings targeting DevSecOps
activities on Red Hat Enterprise Linux and Fedora systems. Settings are
customizable through variables defined in `defaults/main.yml` or overridden in
your playbook.

This role will:
- Ensure a folder for DevSecOps stuff, by default in `~/DEVSecOps`;
- Populate the directory with Vagrant files;
- Install useful tools, such as podman, vagrant, git, etc;
- Update existing container images;
- Prune outdated Vagrant images;
- Configure custom environment variables and aliases defined by the user
  (the PATH variable can also be managed by this role);
- Create `~/.ssh/config` file so users can define their own SSH settings.

To install this role:
```
ansible-galaxy role install marcusburghardt.devsecops
```

Requirements
------------

- Python 3

> **Platform support:** This role currently supports Red Hat Enterprise Linux (EL)
> and Fedora only. There are no Debian/Ubuntu variables defined.

Role Variables
--------------

### Key Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `devsecops_tasks` | List of tasks to run (see [Task Selection](#task-selection)) | All 6 tasks enabled |
| `devsecops_base_dir` | Base directory for DevSecOps content | `~/DEVSecOps` |
| `devsecops_vagrant_dir` | Vagrant files directory | `~/DEVSecOps/Vagrant` |
| `devsecops_vagrant_dirs` | Vagrant OS directories to create | Fedora enabled |
| `devsecops_env_variables` | Custom environment variables for `~/.bashrc` | `GOPATH` enabled |
| `devsecops_env_aliases` | Custom aliases for `~/.bashrc` | None enabled |
| `devsecops_env_path` | PATH additions for `~/.bashrc` | `$GOPATH/bin` |
| `devsecops_linux_repos` | Additional YUM/DNF repositories | None enabled |
| `devsecops_ssh_settings` | SSH config entries for `~/.ssh/config` | `VerifyHostKeyDNS` enabled |
| `devsecops_pip_modules` | Python modules to install via pip | `setuptools` |

### Task Selection

The role uses a task dispatcher pattern. Each task can be individually enabled or
disabled via the `devsecops_tasks` variable:

```yaml
devsecops_tasks:
  - { enabled: true, name: 'install_tools' }
  - { enabled: true, name: 'configure_env' }
  - { enabled: true, name: 'configure_ssh' }
  - { enabled: true, name: 'pip_install_modules' }
  - { enabled: true, name: 'populate_dir' }
  - { enabled: true, name: 'update_images' }
```

| Task | Purpose |
|------|---------|
| `install_tools` | Add YUM/DNF repositories and install packages |
| `configure_env` | Configure environment variables, aliases, and PATH in `~/.bashrc` |
| `configure_ssh` | Create/update `~/.ssh/config` with custom settings |
| `pip_install_modules` | Install Python modules via pip |
| `populate_dir` | Create DevSecOps directories and deploy Vagrant files |
| `update_images` | Update Podman container images and prune Vagrant boxes |

Set `enabled: false` on any task to skip it.

Dependencies
------------

None.

Example Playbook
----------------

```yaml
---
- hosts: linux
  vars:
    devsecops_tasks:
      - { enabled: true, name: 'install_tools' }
      - { enabled: true, name: 'configure_env' }
      - { enabled: true, name: 'populate_dir' }
      - { enabled: true, name: 'update_images' }
      - { enabled: false, name: 'configure_ssh' }
      - { enabled: false, name: 'pip_install_modules' }
  roles:
    - marcusburghardt.devsecops
```

Commit Standards
----------------

This project follows the [Conventional Commits](https://www.conventionalcommits.org/)
specification. All commits to `main` must use the format:

```
<type>[optional scope]: <description>
```

Common types: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`.

Release Process
---------------

This project uses [release-please](https://github.com/googleapis/release-please)
for automated versioning and changelog generation. Commits to `main` must follow
the [Conventional Commits](https://www.conventionalcommits.org/) specification.

When a release PR is merged, a GitHub Release is created automatically, which
triggers publishing to Ansible Galaxy.

**Note:** The `GALAXY_API_KEY` repository secret must be configured for Galaxy
publishing to work.

License
-------

Apache-2.0

Author Information
------------------

Marcus Burghardt
- [https://buymeacoffee.com/marcusburghardt](https://buymeacoffee.com/marcusburghardt)
- [https://github.com/marcusburghardt](https://github.com/marcusburghardt)
- [https://www.linkedin.com/in/marcusburghardt](https://www.linkedin.com/in/marcusburghardt)
