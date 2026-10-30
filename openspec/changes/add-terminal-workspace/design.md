# Design

## Context

The role uses a two-pass dispatcher in `tasks/main.yml` (`devsecops_tasks` →
`vars/<task.name>.yml` + `tasks/<task.name>.yml`). Every feature is a single
togglable unit; `manage_galaxy_roles` is the closest precedent because it
also deploys a script to `devsecops_scripts_dir` and renders a template.

Packaging constraints discovered during exploration:

- kitty is packaged in Fedora (0.47.1) and EPEL 10 (0.47.1), but EPEL 9
  only ships 0.26.5. The role already assumes EPEL-level packages in
  `vars/redhat.yml` (`vagrant`, `flatpak`), so kitty fits `package`.
- zellij is not packaged in Fedora or EPEL at all. Official releases
  publish `zellij-{x86_64,aarch64}-unknown-linux-musl.tar.gz` plus a
  `.sha256sum` asset per tarball. Latest release: v0.45.1.

Behavioral constraints verified against zellij 0.44.1 on this host:

- `zellij --session <name> action list-panes -a -j` returns `id`, `title`,
  `pane_cwd`, and `is_focused` per pane.
- `zellij --session <name> action rename-pane -p <id> <name>` works from
  outside the session and does not steal focus.
- `zellij list-sessions -n -s` prints parseable session names.
- A session created with `zellij -s <name> --layout <layout>` requires a
  TTY; `zellij attach --create-background` creates detached sessions but
  accepts no layout. Therefore the launcher must branch on
  `zellij list-sessions` before starting.
- opencode leaves the pane title as the command name (`opencode`); it does
  not publish session state in the terminal title.

OpenCode V2 constraints (from `@opencode-ai/sdk` 1.4.7 and
`@opencode-ai/plugin` 1.4.7):

- The plugin `event` hook receives `{ event }` where events carry a
  `sessionID` (e.g. `session.status`, `session.idle`,
  `permission.updated`, `permission.replied`, `session.error`).
- `client.session.get({ path: { id } })` returns a `Session` containing
  `directory`, which maps an event to its project directory.
- Plugins run in the shared OpenCode server, not in the pane, so pane
  discovery must go through the zellij CLI rather than `$ZELLIJ_PANE_ID`.
- The plugin input provides a Bun-based `$` shell, so the plugin needs no
  child-process import.
- Local plugin files in `~/.config/opencode/plugins/` are the established
  loading mechanism (`ansible-role-ai` deploys `opencode-metrics.ts` there).

KDL uses `//` line comments, so the zellij templates must not use
`{{ ansible_managed | comment }}` (which emits `#`).

## Goals / Non-Goals

**Goals:**

- Follow the existing dispatcher pattern exactly (task entries, vars files,
  task files, `role_name | task.name |` task names).
- Keep role defaults generic; all personal configuration (repo list, full
  zellij config, font) happens through playbook variables.
- Make zellij installation idempotent by comparing the installed version
  with the resolved target before downloading.
- Keep the attention plugin dependency-free and fail-open: any zellij,
  notification, or client failure must degrade to a no-op.

**Non-Goals:**

- Managing EPEL, GNOME keybindings, or desktop fonts.
- Installing or configuring OpenCode itself (owned by `ansible-role-ai`).
- Uninstalling a snap-installed zellij (documented instead).
- Stacked/swap layouts in the grid (the existing fullscreen toggle covers
  focusing one pane; a swap layout can be a follow-up).
- Managing zellij session resurrection across reboots.

## Decisions

### 1. Two tasks: `install_terminal` and `configure_terminal`

**Decision**: Split installation (packages, zellij binary) from
configuration (configs, layout, launcher, plugin), mirroring the
install/configure split in `ansible-role-ai`.

**Rationale**: Users may want kitty and zellij installed without the
workspace files, and the install task needs `become` while configuration is
user-scoped. Separate entries keep each concern independently togglable.

**Alternative considered**: One `configure_terminal` task doing both.
Rejected because it forces the two concerns to share enablement.

### 2. Zellij from the GitHub release binary with checksum

**Decision**: `get_url` the musl tarball for
`ansible_facts['architecture']` with `checksum` pointing at the release
`.sha256sum` asset, `unarchive` to a temp directory, and copy the binary to
`/usr/local/bin/zellij` (mode `0755`). `devsecops_zellij_version` pins the
tag (`v0.45.1` default); `latest` resolves through the GitHub API, using
the same `uri` + `set_fact` pattern as `install_speckit.yml` in
`ansible-role-ai`.

**Rationale**: The only method that is honest for a Galaxy role targeting
EL and Fedora — snap needs snapd (not in RHEL base), and `cargo install`
compiles for minutes and needs `~/.cargo/bin` on PATH.

**Alternative considered**: snap (matches the author's current machine) and
cargo (role already installs rust). Both rejected for the reasons above;
documented so users can keep them.

**Version comparison**: `zellij --version` prints `zellij 0.45.1` (no `v`),
so the tag's leading `v` is stripped before comparing. When comparison
fails to parse, install proceeds (safe default).

### 3. File-source override for the zellij config

**Decision**: `devsecops_zellij_config_src` (default empty). Empty renders
`templates/zellij/config.kdl.j2` (generic: theme, mouse mode, pane frames,
scroll buffer, copy command, extras). When set, the referenced file is
deployed verbatim through `templates/zellij/config-from-src.kdl.j2`, which
prepends a `//`-style `ansible_managed` header to the content read via
`lookup('ansible.builtin.file', ...)` from the control node.

**Rationale**: A real zellij config is dominated by a
`keybinds clear-defaults=true` block of nested KDL; re-modelling it as YAML
variables would be brittle and lossy. A file in the playbook repo keeps the
playbook as the source of truth while Ansible still owns deployment. Kitty
gets the same escape hatch (`devsecops_kitty_config_src`) for symmetry,
though its rendered template is genuinely variable-driven.

**Alternative considered**: Fully structured variables plus a raw keybinds
block. Rejected: half YAML, half raw KDL, no added safety.

### 4. Layout generated from the repo list, two-column grid

**Decision**: `templates/zellij/layouts/oc-workspace.kdl.j2` renders panes
from `devsecops_workspace_repos` into `devsecops_workspace_grid_columns`
columns; each column is a vertical stack, so N=4 renders 2×2, N=3 renders
2+1, N=2 renders side by side. Repo paths are filtered through `stat`
before rendering; missing paths emit a warning. Panes use
`command="bash"` with `args "-lc" "<open_command>; exec bash"` when
`devsecops_workspace_keep_shell` is true. The layout uses a
`default_tab_template` with only the status bar (no tab bar) and focuses
the first pane.

**Rationale**: The role stays declarative (no runtime layout generation),
the grid adapts to any repo count, and the shell wrapper prevents an
opencode exit from collapsing the grid. Hiding the tab bar reclaims two
lines for pane content; with a single tab it carries no information.

**Alternative considered**: A manifest file plus a launcher that builds the
layout at runtime. Rejected for v1: more moving parts; rerunning the role
to change repos is acceptable. Upgrade path stays open.

### 5. Launcher: attach-or-create, kitty re-exec

**Decision**: `templates/oc-workspace.j2` (bash, mode `0755`) deployed as
`{{ devsecops_scripts_dir }}/{{ devsecops_workspace_launcher_name }}`. If
`KITTY_WINDOW_ID` is unset, `exec kitty --class <class> -- env
OC_WORKSPACE_IN_KITTY=1 "$0" "$@"`; the guard variable prevents recursion.
Inside kitty: if `zellij list-sessions -n -s` contains the session name,
`exec zellij attach <name>`; otherwise
`exec zellij --session <name> --layout <layout>`.

**Rationale**: `--layout` only applies at session creation, so the branch
is required. The kitty re-exec makes the same command work from a terminal,
a desktop entry, or a keybinding. `list-sessions -n -s` (no formatting,
short) is the stable parseable form.

### 6. Attention plugin: zero imports, mapping by `pane_cwd`

**Decision**: `templates/opencode/zellij-attention.ts.j2` renders a plugin
that uses only the plugin input's `client` and `$`. On each event it
resolves `sessionID` → `directory` via `client.session.get`, enumerates
`zellij list-sessions -n -s`, runs `zellij --session <s> action list-panes
-a -j` per session, matches `pane_cwd` against the project directory, and
calls `rename-pane -p <id> "<badge> <repo>"`. Badges come from
`devsecops_workspace_badges`; notifications from
`devsecops_workspace_notify_command` — permission events always, idle only
when the pane is not focused. All zellij/notify/client failures are caught
and logged, never thrown.

**Rationale**: The plugin runs in the shared server for all four TUIs, so
directory matching (not pane environment variables) is the only reliable
way to find the right pane. Mapping across all sessions keeps it working
with any workspace name. Zero imports decouple it from
`@opencode-ai/plugin` version drift.

**Alternative considered**: A standalone `systemd --user` watcher
subscribed to the OpenCode event stream. Rejected for v1: another service
to manage, same mapping logic, and no better failure isolation.

### 7. Config ownership: overwrite with backup

**Decision**: Both configs deploy with `backup: true` on every change, and
the README documents a `--check --diff` first run for machines with
hand-tuned configs.

**Rationale**: The user's chosen model is "playbook is the source of
truth"; the first role run replaces an existing hand-tuned `config.kdl`.
Backups plus a diff dry-run make that transition recoverable.

## Risks / Trade-offs

- **[EPEL 9 kitty 0.26.5 is ancient]** → Document Fedora/EPEL 10 as the
  supported target for kitty; the package list is a variable so users can
  adapt.
- **[GitHub API rate limits for `latest`]** → Same accepted trade-off as
  `install_speckit` in `ansible-role-ai`; pinning avoids the call.
- **[Checksum asset semantics]** → Verified during implementation: the release
  `.sha256sum` assets checksum the binary inside the tarball (the line
  references the cargo build path, e.g.
  `target/x86_64-unknown-linux-musl/release/zellij`), not the tarball, so
  `get_url`'s checksum matching cannot use them. The task therefore
  downloads the tarball, extracts it, and verifies the extracted binary's
  sha256 (via `stat`) against the value read with `uri` — a stronger
  end-artifact verification.
- **[Layout KDL syntax (`args`, nesting) is unvalidated against 0.45.1]**
  → Validation is a manual acceptance step in tasks.md; there is no CLI
  layout validator, and session creation needs a TTY.
- **[OpenCode V2 plugin API drift]** → Zero-import plugin, defensive
  `try/catch`, and the task is opt-out; failure degrades to missing badges.
- **[Desktop notifications depend on the server's DBus session]** →
  Pane badges are the reliable layer; notify failures are swallowed.
- **[Same repo open in multiple panes]** → First matching pane wins;
  documented.
- **[Snap zellij shadows confusion]** → `/usr/local/bin` precedes the snap
  bin in PATH; the install task warns when `command -v zellij` resolves to
  a snap path, and the README suggests `snap remove zellij`.
- **[No GUI tests in CI]** → CI covers syntax/lint only; grid, badges, and
  launcher are manual acceptance steps.

## Migration Plan

1. Enable both tasks in the playbook with the desired variables; on hosts
   with a hand-tuned `config.kdl`, run first with `--check --diff`.
2. Run the playbook; verify `zellij --version`, `zellij setup --check`,
   and `oc-workspace`.
3. Rollback: disable both task entries; previously deployed files remain
   but are no longer managed (restore from the timestamped backups if
   needed).
