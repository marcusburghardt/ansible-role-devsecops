# Proposal

## Why

Running several OpenCode sessions in parallel today requires either several
terminal windows, IDE-embedded shells, or constant tab switching, and there is
no reliable signal when a session finishes a turn or blocks on a permission
prompt. A GPU-accelerated terminal (kitty) plus a scriptable multiplexer
(zellij) with a declaratively managed layout and an attention bridge solves
both problems reproducibly through Ansible.

## What Changes

- Add two new opt-in tasks to the role's dispatcher: `install_terminal` and
  `configure_terminal` (both `enabled: false` by default).
- `install_terminal` ensures kitty via the distribution package manager and
  installs zellij from the official GitHub release binary (pinned by default,
  `latest` optional, sha256-verified, architecture-aware) into
  `/usr/local/bin`.
- `configure_terminal` deploys:
  - a kitty configuration rendered from variables (with a file-source escape
    hatch);
  - a zellij configuration rendered from a minimal generic default or deployed
    verbatim from a playbook-supplied file (`devsecops_zellij_config_src`),
    making the playbook the source of truth;
  - a zellij layout rendering a two-column grid of OpenCode panes from
    `devsecops_workspace_repos`, with pane names, missing-path filtering, and
    a keep-shell command wrapper;
  - an `oc-workspace` launcher (`~/bin`) that attaches to an existing zellij
    session or creates it with the layout, and re-execs inside kitty when
    started from a desktop entry;
  - a `.desktop` entry for launching the workspace from the desktop
    environment (no global keybinding is managed).
- Deploy an OpenCode attention plugin (opt-in, zero third-party imports) that
  maps OpenCode events to zellij pane badges (`busy`, `waiting`, `done`,
  `error`) via pane titles and raises desktop notifications (permission
  prompts always; idle turns only when the pane is not focused).
- Update `README.md` with prerequisites (EPEL for kitty on EL, OpenCode for
  the attention plugin), the new variables, and the daily workflow.

## Capabilities

### New Capabilities

- `terminal-workspace`: Installation of kitty and zellij plus declarative
  deployment of their configurations, the multi-repository OpenCode grid
  layout, the `oc-workspace` launcher, and the desktop entry.
- `workspace-attention`: Event-driven pane badges and desktop notifications
  that surface OpenCode session state (working, waiting on permission, idle,
  error) in the zellij grid.

### Modified Capabilities

(none)

## Impact

- **New files**: `vars/install_terminal.yml`, `vars/configure_terminal.yml`,
  `tasks/install_terminal.yml`, `tasks/configure_terminal.yml`,
  `templates/kitty.conf.j2`, `templates/kitty-from-src.conf.j2`,
  `templates/zellij/config.kdl.j2`, `templates/zellij/config-from-src.kdl.j2`,
  `templates/zellij/layouts/oc-workspace.kdl.j2`, `templates/oc-workspace.j2`,
  `templates/oc-workspace.desktop.j2`,
  `templates/opencode/zellij-attention.ts.j2`.
- **Modified files**: `defaults/main.yml` (two task entries and the new
  variables), `README.md`.
- **Dependencies**: kitty requires EPEL on EL (the role does not manage EPEL);
  the attention plugin requires OpenCode and an existing
  `~/.config/opencode` directory (installed by `ansible-role-ai`) and
  `notify-send` for desktop notifications; zellij has no repository
  dependency (official release tarball).
- **No breaking changes**: both tasks default to `enabled: false`; existing
  users are unaffected.
- **Behavioral note**: when enabled, `configure_terminal` overwrites
  `~/.config/zellij/config.kdl` and `~/.config/kitty/kitty.conf` on every run
  (with backups), by design, so the playbook becomes the source of truth.
