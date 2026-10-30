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
- Create `~/.ssh/config` file so users can define their own SSH settings;
- Optionally install and configure a terminal workspace: kitty, zellij, a
  multi-repository OpenCode grid layout, an attach-or-create launcher, and
  OpenCode session badges with desktop notifications (see
  [Terminal Workspace](#terminal-workspace)).

To install this role:
```
ansible-galaxy role install marcusburghardt.devsecops
```

Requirements
------------

- Python 3
- For the terminal workspace: kitty (EPEL is required on EL systems; the
  role does not manage EPEL), and OpenCode with `~/.config/opencode` present
  if you enable the attention plugin (see
  [ansible-role-ai](https://github.com/marcusburghardt/ansible-role-ai)).

> **Platform support:** This role currently supports Red Hat Enterprise Linux (EL)
> and Fedora only. There are no Debian/Ubuntu variables defined.

Role Variables
--------------

### Key Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `devsecops_tasks` | List of tasks to run (see [Task Selection](#task-selection)) | First 6 tasks enabled |
| `devsecops_base_dir` | Base directory for DevSecOps content | `~/DEVSecOps` |
| `devsecops_vagrant_dir` | Vagrant files directory | `~/DEVSecOps/Vagrant` |
| `devsecops_vagrant_dirs` | Vagrant OS directories to create | Fedora enabled |
| `devsecops_env_variables` | Custom environment variables for `~/.bashrc` | `GOPATH` enabled |
| `devsecops_env_aliases` | Custom aliases for `~/.bashrc` | None enabled |
| `devsecops_env_path` | PATH additions for `~/.bashrc` | `$GOPATH/bin` |
| `devsecops_linux_repos` | Additional YUM/DNF repositories | None enabled |
| `devsecops_ssh_settings` | SSH config entries for `~/.ssh/config` | `VerifyHostKeyDNS` enabled |
| `devsecops_pip_modules` | Python modules to install via pip | `setuptools` |
| `devsecops_terminal_packages` | Packages installed by `install_terminal` | `[kitty]` |
| `devsecops_zellij_version` | Zellij release tag (`v0.45.1`) or `latest` | `v0.45.1` |
| `devsecops_zellij_install_dir` | Where the zellij binary is installed | `/usr/local/bin` |
| `devsecops_kitty_config_src` | Deploy this kitty.conf file verbatim instead of the rendered one | Empty (rendered) |
| `devsecops_kitty_font_family` / `_font_size` | kitty font settings | `monospace` / `11.0` |
| `devsecops_kitty_background_opacity` | kitty window opacity | `0.95` |
| `devsecops_kitty_hide_tab_bar` | Hide the kitty tab bar even in multi-tab windows | `false` |
| `devsecops_kitty_launch_keybind` | kitty keybind that opens the workspace | `ctrl+shift+enter` |
| `devsecops_zellij_config_src` | Deploy this config.kdl verbatim instead of the rendered one | Empty (rendered) |
| `devsecops_zellij_theme` | Zellij theme name | Empty (zellij default) |
| `devsecops_zellij_pane_frames` | Show pane frames (needed for badges) | `true` |
| `devsecops_zellij_copy_command` | Clipboard command (e.g. `wl-copy` on Wayland) | Empty |
| `devsecops_workspace_name` | Zellij session name | `dev` |
| `devsecops_workspace_repos` | Repos rendered into the grid (name + path each) | Empty |
| `devsecops_workspace_grid_columns` | Columns in the grid layout | `2` |
| `devsecops_workspace_keep_shell` | Keep a shell in each pane after the open command exits | `true` |
| `devsecops_workspace_launcher_name` | Launcher script name in `~/bin` | `oc-workspace` |
| `devsecops_workspace_desktop_entry` | Deploy a `.desktop` entry for the launcher | `true` |
| `devsecops_workspace_attention_enabled` | Deploy the OpenCode attention plugin | `true` |
| `devsecops_workspace_badges` | Badge glyphs for busy/waiting/done/error | `▶ ⏳ ✅ ❌` |
| `devsecops_workspace_notify_command` | Notification command used by the plugin | `notify-send` |

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
  - { enabled: false, name: 'manage_galaxy_roles' }
  - { enabled: false, name: 'install_terminal' }
  - { enabled: false, name: 'configure_terminal' }
```

| Task | Purpose |
|------|---------|
| `install_tools` | Add YUM/DNF repositories and install packages |
| `configure_env` | Configure environment variables, aliases, and PATH in `~/.bashrc` |
| `configure_ssh` | Create/update `~/.ssh/config` with custom settings |
| `pip_install_modules` | Install Python modules via pip |
| `populate_dir` | Create DevSecOps directories and deploy Vagrant files |
| `update_images` | Update Podman container images and prune Vagrant boxes |
| `manage_galaxy_roles` | Render `requirements.yml` and keep Galaxy roles updated |
| `install_terminal` | Install kitty (package) and zellij (GitHub release binary) |
| `configure_terminal` | Deploy kitty/zellij configs, the grid layout, launcher, desktop entry, and attention plugin |

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

Terminal Workspace
------------------

The `install_terminal` and `configure_terminal` tasks build a multi-repository
OpenCode workspace: one kitty window running a persistent zellij session,
with one OpenCode pane per repository. The workspace window shows no kitty tab
bar because it has a single tab (kitty's default `tab_bar_min_tabs 2`); kitty
tabs in normal windows are unaffected.

```
┌─ kitty (tabs hidden) ──────────────────────────────┐
│ ┌─ repo-a ────────────────┬─ repo-b ──────────────┐ │
│ │ opencode                │ opencode              │ │
│ ├─ repo-c ────────────────┼─ repo-d ──────────────┤ │
│ │ opencode                │ opencode              │ │
│ └─────────────────────────┴───────────────────────┘ │
│              zellij status bar                       │
└─────────────────────────────────────────────────────┘
```

Enable it in your playbook:

```yaml
devsecops_tasks:
  # ...
  - { enabled: true, name: 'install_terminal' }
  - { enabled: true, name: 'configure_terminal' }

devsecops_workspace_repos:
  - { name: 'ansible-role-ai', path: '~/GIT/AnsibleRoles/ansible-role-ai' }
  - { name: 'ansible-role-devsecops', path: '~/GIT/AnsibleRoles/ansible-role-devsecops' }
  - { name: 'mbtech', path: '~/GIT/mbtech' }
  - { name: 'complyctl', path: '~/GIT/ProdSec/complyctl' }
```

Then start it with `oc-workspace` (deployed to `~/bin`, also available as a
desktop entry). The launcher attaches to the existing zellij session or
creates it with the grid layout; when started from the desktop entry it opens
its own kitty window first.

**Zellij installation.** Zellij is not packaged for Fedora/EL, so the role
installs the official GitHub release binary (sha256-verified) into
`/usr/local/bin`. If a snap-installed zellij exists, the role warns about it;
`/usr/local/bin` takes precedence in the default PATH, and you can remove the
snap with `snap remove zellij`.

**Configuration ownership.** Both `~/.config/kitty/kitty.conf` and
`~/.config/zellij/config.kdl` are managed by the role (with backups on
change). By default a minimal generic configuration is rendered from the
`devsecops_kitty_*` / `devsecops_zellij_*` variables. To deploy a full
configuration file from your playbook instead, point
`devsecops_kitty_config_src` / `devsecops_zellij_config_src` at a file on the
control node — it is deployed verbatim with an `ansible_managed` header and
the individual variables are ignored. On hosts with a hand-tuned config,
run once with `--check --diff` first; the transition keeps a timestamped
backup.

**Attention badges.** When OpenCode is installed
(`~/.config/opencode` exists), the role deploys a self-contained plugin to
`~/.config/opencode/plugins/zellij-attention.ts`. It mirrors session state
into the pane titles — `▶` busy, `⏳` waiting on a permission prompt, `✅`
turn finished, `❌` error — and raises desktop notifications (permission
prompts always; finished turns only when the pane is not focused). The
plugin is best-effort: without zellij running, without `notify-send`, or on
any error, it stays silent and never breaks a session.

**Daily workflow.**

```
oc-workspace            # start or reattach the 'dev' session
Ctrl-o d                # detach; everything keeps running
oc-workspace            # reattach later, panes and state intact
```

New zellij sessions pick up configuration changes; restart a running session
(`zellij kill-session dev`) after changing the layout or config.

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
