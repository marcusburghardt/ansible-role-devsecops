# Spec Delta

## Purpose

Installs and configures kitty and zellij and delivers a declarative,
multi-repository OpenCode workspace: a rendered grid layout, an
attach-or-create launcher, and a desktop entry.

## ADDED Requirements

### Requirement: Opt-in task activation

The role SHALL provide `install_terminal` and `configure_terminal` entries in
`devsecops_tasks`, both disabled by default. No terminal workspace file is
deployed and no terminal package is installed unless the user enables the
corresponding task.

#### Scenario: Tasks disabled by default
- **WHEN** the role runs with default variables
- **THEN** neither `install_terminal` nor `configure_terminal` is executed and
  no kitty or zellij file is modified

#### Scenario: User enables both tasks
- **WHEN** the user enables `install_terminal` and `configure_terminal` in
  `devsecops_tasks`
- **THEN** kitty and zellij are installed and the workspace files are deployed

### Requirement: Kitty package installation

The `install_terminal` task SHALL ensure kitty is installed via the
distribution package manager from a configurable package list
(`devsecops_terminal_packages`, default `[kitty]`). Installation requires
EPEL on EL systems; the role MUST NOT manage EPEL itself.

#### Scenario: Kitty is not installed
- **WHEN** the task runs on a host without kitty
- **THEN** kitty is installed from the configured package list

#### Scenario: Kitty is already installed
- **WHEN** the task runs on a host with kitty already present
- **THEN** the package step reports no change

### Requirement: Zellij release binary installation

The `install_terminal` task SHALL install zellij from the official GitHub
release for the target architecture (`x86_64` or `aarch64`
`unknown-linux-musl`), verified against the release checksum, into
`devsecops_zellij_install_dir` (default `/usr/local/bin`). The version SHALL
be pinned by default (`devsecops_zellij_version`) with `latest` resolved via
the GitHub API.

#### Scenario: Zellij is not installed
- **WHEN** the task runs on a host without zellij
- **THEN** the release tarball is downloaded, the extracted binary is verified
  against the published release checksum, and installed with mode `0755`

#### Scenario: Installed version matches the target
- **WHEN** `zellij --version` already reports the resolved target version
- **THEN** no download or replacement happens and the task reports no change

#### Scenario: Pinned version differs from installed
- **WHEN** the installed zellij version differs from the resolved target
- **THEN** the binary is replaced with the target version

#### Scenario: Checksum verification fails
- **WHEN** the extracted binary does not match the published release checksum
- **THEN** the installation fails and no binary is replaced

### Requirement: Kitty configuration deployment

The `configure_terminal` task SHALL deploy `kitty.conf` to
`~/.config/kitty/`. By default it renders a generic configuration from
individual variables (font family and size, background opacity, window
padding, hidden tab bar, launch keybind, remote control). When
`devsecops_kitty_config_src` is set, the referenced file MUST be deployed
verbatim (prefixed with an `ansible_managed` header) and takes precedence
over the rendered defaults.

#### Scenario: Rendered default configuration
- **WHEN** `devsecops_kitty_config_src` is empty
- **THEN** `~/.config/kitty/kitty.conf` is rendered from the kitty variables

#### Scenario: Playbook-supplied configuration
- **WHEN** `devsecops_kitty_config_src` points to an existing file
- **THEN** that file is deployed verbatim with an `ansible_managed` header
  and the variable-driven settings are ignored

#### Scenario: Existing configuration is backed up
- **WHEN** the deployed content differs from the current `kitty.conf`
- **THEN** a timestamped backup of the previous file is kept

### Requirement: Zellij configuration deployment

The `configure_terminal` task SHALL deploy `config.kdl` to
`~/.config/zellij/`. By default it renders a minimal generic configuration
from variables (theme, mouse mode, pane frames, scroll buffer size, copy
command). When `devsecops_zellij_config_src` is set, the referenced file MUST
be deployed verbatim (prefixed with an `ansible_managed` header using KDL
`//` comments) and takes precedence over the rendered defaults.

#### Scenario: Rendered default configuration
- **WHEN** `devsecops_zellij_config_src` is empty
- **THEN** `~/.config/zellij/config.kdl` is rendered from the zellij
  variables with a `//`-style `ansible_managed` header

#### Scenario: Playbook-supplied configuration
- **WHEN** `devsecops_zellij_config_src` points to an existing file
- **THEN** that file is deployed verbatim with a `//`-style
  `ansible_managed` header and the variable-driven settings are ignored

#### Scenario: Existing configuration is backed up
- **WHEN** the deployed content differs from the current `config.kdl`
- **THEN** a timestamped backup of the previous file is kept

### Requirement: Workspace grid layout rendering

The `configure_terminal` task SHALL render a zellij layout file
(`devsecops_workspace_layout_name`, default `oc-workspace`) into
`~/.config/zellij/layouts/` from `devsecops_workspace_repos`. Panes SHALL be
distributed across `devsecops_workspace_grid_columns` columns (default 2),
each pane named after its repo entry and started in the repo path. The first
pane SHALL be focused.

#### Scenario: Four repos render a two-by-two grid
- **WHEN** four existing repo paths are configured with two grid columns
- **THEN** the layout contains four panes arranged as two columns of two,
  each pane named after its repo

#### Scenario: Three repos render an asymmetric grid
- **WHEN** three existing repo paths are configured with two grid columns
- **THEN** the layout contains one column with two panes and one column with
  one pane

### Requirement: Missing repo path handling

Repo paths that do not exist on the target MUST be skipped with a warning,
and the rendered layout MUST remain valid for the remaining repos. When no
configured repo path exists, the role MUST NOT deploy a layout and MUST
report a warning.

#### Scenario: Missing repo path is skipped
- **WHEN** a configured repo path does not exist on the target
- **THEN** the layout omits that pane, includes the remaining repos, and the
  run reports a warning

#### Scenario: Empty repo list
- **WHEN** `devsecops_workspace_repos` is empty
- **THEN** no layout file is deployed and the task reports a warning

### Requirement: Pane command shell persistence

When `devsecops_workspace_keep_shell` is true, each pane SHALL run the open
command through a shell that persists after the command exits.

#### Scenario: Pane survives open command exit
- **WHEN** `devsecops_workspace_keep_shell` is true and the open command
  exits
- **THEN** the pane remains open as a shell instead of closing

### Requirement: Workspace launcher

The `configure_terminal` task SHALL deploy an `oc-workspace` launcher script
(`devsecops_workspace_launcher_name`) to the user scripts directory
(`devsecops_scripts_dir`, default `~/bin`) with mode `0755`. The launcher
MUST attach to the configured zellij session when it already exists and
create it with the configured layout otherwise. When started outside kitty
(for example from a desktop entry), the launcher MUST re-exec itself inside
a new kitty window instead of failing.

#### Scenario: Session already exists
- **WHEN** the configured session name is listed by `zellij list-sessions`
- **THEN** the launcher attaches to that session without reapplying the
  layout

#### Scenario: Session does not exist
- **WHEN** no session with the configured name exists
- **THEN** the launcher starts a new zellij session with the configured
  layout

#### Scenario: Started outside kitty
- **WHEN** the launcher runs without `KITTY_WINDOW_ID` in its environment
- **THEN** it starts a kitty window and continues inside it

#### Scenario: Started inside kitty
- **WHEN** the launcher runs with `KITTY_WINDOW_ID` set
- **THEN** it runs zellij in the current window without spawning another
  kitty instance

### Requirement: Desktop entry

The `configure_terminal` task SHALL deploy a `.desktop` entry (default
enabled) to `~/.local/share/applications/` that launches the workspace
launcher. The Exec value MUST use the absolute launcher path. The role MUST
NOT manage desktop environment keybindings.

#### Scenario: Desktop entry deployed
- **WHEN** `devsecops_workspace_desktop_entry` is true
- **THEN** a `.desktop` file referencing the absolute launcher path exists in
  `~/.local/share/applications/`

#### Scenario: Desktop entry disabled
- **WHEN** `devsecops_workspace_desktop_entry` is false
- **THEN** no `.desktop` file is deployed for the workspace

### Requirement: Idempotency of terminal workspace tasks

Both terminal tasks SHALL be idempotent: a second consecutive run with
unchanged variables MUST NOT report changes for package installation,
zellij installation (when the version matches), or any deployed workspace
file.

#### Scenario: Consecutive runs
- **WHEN** the tasks run twice in a row with unchanged variables
- **THEN** the second run reports no changes

### Requirement: Installation verification

The `install_terminal` task SHALL verify after installation that `kitty` and
`zellij` resolve on PATH and that `zellij --version` reports the resolved
target version. When the resolved zellij binary is a snap path, the task
MUST report a warning explaining the precedence of
`devsecops_zellij_install_dir`.

#### Scenario: Verification passes
- **WHEN** installation completes
- **THEN** `command -v kitty` and `command -v zellij` succeed and the
  reported zellij version equals the resolved target version

#### Scenario: Snap zellij detected
- **WHEN** `command -v zellij` resolves to a snap path after installation
- **THEN** the run reports a warning about binary precedence
