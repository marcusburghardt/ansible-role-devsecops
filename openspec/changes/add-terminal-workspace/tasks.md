# Tasks

## 1. Role defaults and variables

- [ ] 1.1 Add `install_terminal` and `configure_terminal` entries (`enabled: false`) to `devsecops_tasks` in `defaults/main.yml`. Verify by inspecting the file: both entries present and disabled.
- [ ] 1.2 Add the terminal variables to `defaults/main.yml`: `devsecops_terminal_packages` (`[kitty]`), `devsecops_zellij_version` (`v0.45.1`), `devsecops_zellij_install_dir` (`/usr/local/bin`), kitty variables (`config_dir`, `config_src`, `font_family`, `font_size`, `background_opacity`, `window_padding`, `launch_keybind`, `remote_control`, `hide_tab_bar`, `config_extra`), zellij variables (`config_dir`, `config_src`, `theme`, `mouse_mode`, `pane_frames`, `scroll_buffer_size`, `copy_command`, `config_extra`), workspace variables (`name`, `layout_name`, `launcher_name`, `repos`, `open_command`, `keep_shell`, `grid_columns`, `desktop_entry`), and attention variables (`attention_enabled`, `badges`, `notify_on_idle_when_focused`, `notify_command`). Verify each variable is present with the agreed default.
- [ ] 1.3 Create `vars/install_terminal.yml` and `vars/configure_terminal.yml` as task-specific variable files (matching the placeholder pattern of the other tasks). Verify the dispatcher's `include_vars` finds both files for the new task names.

## 2. Zellij and kitty installation

- [ ] 2.1 Create `tasks/install_terminal.yml`: ensure kitty via `ansible.builtin.package` over `devsecops_terminal_packages` with `become: true`. Verify with `ansible-playbook --syntax-check` and by running the task on a host without kitty.
- [ ] 2.2 Add zellij version resolution to `tasks/install_terminal.yml`: when `devsecops_zellij_version` is `latest`, query `https://api.github.com/repos/zellij-org/zellij/releases/latest` with `ansible.builtin.uri` and `set_fact` the `tag_name`; otherwise use the pinned value (strip a leading `v` for comparison). Verify by running with a pinned version and inspecting the resolved fact.
- [ ] 2.3 Add the installed-version check and guarded install: run `zellij --version` (failed_when false), skip install when it matches the target, otherwise `get_url` the arch-specific musl tarball with the release `.sha256sum` checksum, `unarchive` to a temp dir, copy the binary to `{{ devsecops_zellij_install_dir }}/zellij` (mode `0755`, `become: true`), and clean the temp files. Verify by running twice: second run reports no change for the zellij steps.
- [ ] 2.4 Add verification tasks: `command -v kitty` and `command -v zellij` succeed; `zellij --version` equals the resolved target; warn (not fail) when the resolved zellij path is under snap. Verify by running the task and checking the output.

## 3. Kitty and zellij configuration

- [ ] 3.1 Create `templates/kitty.conf.j2` rendering the generic kitty config from the variables: `font_family`, `font_size`, `background_opacity`, `window_padding_width`, hidden tab bar when enabled, `enable_audio_bell no`, `confirm_os_window_close 0`, `sync_to_monitor yes`, remote control (`allow_remote_control` + `listen_on`) when enabled, `shell_integration enabled`, the launch keybind running the workspace launcher, and `devsecops_kitty_config_extra`. Verify by rendering with `ansible-playbook` and reviewing the output for syntax and variable placement.
- [ ] 3.2 Create `templates/kitty-from-src.conf.j2` that emits `{{ ansible_managed }}` (a `#` header is valid for kitty) followed by `lookup('ansible.builtin.file', devsecops_kitty_config_src)`. Verify by deploying with a sample src file and diffing the deployed content.
- [ ] 3.3 Create `templates/zellij/config.kdl.j2` rendering the generic zellij config: optional `theme`, `mouse_mode`, `pane_frames`, `scroll_buffer_size`, optional `copy_command`, and `devsecops_zellij_config_extra`, with a `//`-style `ansible_managed` header (never `#`, which KDL rejects). Verify by running `zellij setup --check` against a config dir containing the rendered file.
- [ ] 3.4 Create `templates/zellij/config-from-src.kdl.j2` that emits a `//`-style `ansible_managed` header followed by `lookup('ansible.builtin.file', devsecops_zellij_config_src)`. Verify by deploying the author's config file and checking zellij still parses it (`zellij setup --check`).
- [ ] 3.5 Add the config deployment steps to `tasks/configure_terminal.yml`: ensure `~/.config/kitty` and `~/.config/zellij`, then deploy kitty and zellij configs (template vs from-src selected by the `config_src` variables) with `backup: true` and mode `0644`. Verify idempotency: a second run reports no change.

## 4. Workspace layout, launcher, and desktop entry

- [ ] 4.1 Create `templates/zellij/layouts/oc-workspace.kdl.j2`: `default_tab_template` with only the status bar, one tab, panes distributed over `devsecops_workspace_grid_columns` columns (each column a vertical stack), pane names from `name`, `cwd` from `path`, first pane focused, and the keep-shell wrapper (`bash -lc '<open_command>; exec bash'`) when `devsecops_workspace_keep_shell` is true. Verify by rendering for 4 repos and reviewing the KDL structure.
- [ ] 4.2 Add repo filtering to `tasks/configure_terminal.yml`: `stat` each `devsecops_workspace_repos` path, warn for missing ones, and pass only existing entries to the layout template; skip layout deployment with a warning when the list is empty. Verify by configuring one missing path and confirming the layout renders without it.
- [ ] 4.3 Create `templates/oc-workspace.j2` (bash launcher): re-exec inside kitty when `KITTY_WINDOW_ID` is unset (guarded by `OC_WORKSPACE_IN_KITTY`), then attach when `zellij list-sessions -n -s` contains the session name, otherwise create with `zellij --session <name> --layout <layout>`. Deploy to `{{ devsecops_scripts_dir }}/{{ devsecops_workspace_launcher_name }}` with mode `0755`. Verify with `bash -n` on the rendered script and by running it in a kitty window.
- [ ] 4.4 Create `templates/oc-workspace.desktop.j2` (Type=Application, absolute launcher path as Exec, `Terminal=false`) and deploy it to `~/.local/share/applications/` when `devsecops_workspace_desktop_entry` is true. Verify the file exists and references the absolute launcher path.
- [ ] 4.5 Add the attention gating and directory steps to `tasks/configure_terminal.yml`: ensure `~/.config/opencode` exists before deploying the plugin (skip with a warning when OpenCode is absent). Verify by running with and without `~/.config/opencode`.

## 5. Attention plugin

- [ ] 5.1 Create `templates/opencode/zellij-attention.ts.j2`: a zero-import plugin whose `event` hook maps `session.status`/`session.idle`/`permission.updated`/`permission.replied`/`session.error` to badges from `devsecops_workspace_badges`, resolves the session directory via `client.session.get`, enumerates `zellij list-sessions -n -s`, matches `pane_cwd` in `list-panes -a -j`, and calls `rename-pane -p <id>` with the badge and repo name. Verify by reviewing the rendered TypeScript for syntax and correct event mapping.
- [ ] 5.2 Add notifications to the plugin: run `devsecops_workspace_notify_command` for permission events always and for idle only when the matched pane is not focused, with all failures caught (`nothrow`/`try`). Verify by reviewing the rendered notification logic and triggering a permission prompt in a test session.
- [ ] 5.3 Deploy the plugin to `~/.config/opencode/plugins/zellij-attention.ts` (mode `0644`, `backup: true`) from `tasks/configure_terminal.yml`, gated on `devsecops_workspace_attention_enabled` and OpenCode presence. Verify idempotency on a second run.

## 6. Documentation and validation

- [ ] 6.1 Update `README.md`: add the two tasks to the task table, document all new variables in the Key Variables table, add a Terminal Workspace section with prerequisites (EPEL for kitty on EL, OpenCode and `notify-send` for attention), the config source override, the snap precedence note, and the daily workflow (`oc-workspace`, attach/detach, badges). Verify by reading the rendered README and checking every new variable is documented.
- [ ] 6.2 Run `yamllint` over all new and modified YAML files and `ansible-lint` over the role; fix all findings. Verify both commands exit clean.
- [ ] 6.3 Run `ansible-playbook --syntax-check` with a test playbook enabling both tasks and four repo entries. Verify the syntax check passes.
- [ ] 6.4 Run the role twice against a test target with the tasks enabled; verify the second run reports no changes (idempotency) and `zellij setup --check` succeeds.
- [ ] 6.5 Manual acceptance in a real kitty session: `oc-workspace` creates the 2×2 grid with named panes; detach and reattach preserves it; a permission prompt in one pane renames its title to the waiting badge and raises a notification; an idle turn shows the done badge and only notifies when the pane is unfocused. Verify each behavior in the live session.

## Workflow follow-up

- Archive the change with `/opsx-archive` after tasks 6.1–6.5 pass.
- In the author's playbook (mbtech), enable both tasks, set
  `devsecops_zellij_config_src` to the exported `config.kdl`, and set the
  four `devsecops_workspace_repos` entries.
- Optionally remove the snap zellij (`snap remove zellij`) once the binary
  install is verified.
