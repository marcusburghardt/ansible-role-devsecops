# Spec Delta

## Purpose

Surfaces OpenCode session state in the zellij workspace grid: pane title
badges for working, waiting, done, and error states, plus desktop
notifications for events that need user action.

## ADDED Requirements

### Requirement: Attention plugin deployment

The `configure_terminal` task SHALL deploy an OpenCode plugin
(`zellij-attention.ts`) to `~/.config/opencode/plugins/` when
`devsecops_workspace_attention_enabled` is true and `~/.config/opencode`
exists. The plugin MUST NOT be deployed and the run MUST NOT fail when
OpenCode is not installed. The plugin MUST be self-contained, importing no
third-party packages.

#### Scenario: OpenCode is installed
- **WHEN** attention is enabled and `~/.config/opencode` exists
- **THEN** the plugin is deployed to `~/.config/opencode/plugins/`

#### Scenario: OpenCode is absent
- **WHEN** attention is enabled and `~/.config/opencode` does not exist
- **THEN** the plugin is not deployed and the role run succeeds with a
  warning

#### Scenario: Attention disabled
- **WHEN** `devsecops_workspace_attention_enabled` is false
- **THEN** no plugin is deployed

### Requirement: Session-to-pane mapping

For each OpenCode event, the plugin SHALL resolve the event's session to its
project directory, enumerate active zellij sessions, and match the pane
whose current working directory equals that project directory. Matching
panes SHALL be updated in every zellij session that contains them. When no
matching pane or no zellij session exists, the plugin MUST be a no-op.

#### Scenario: Pane matches the project directory
- **WHEN** an OpenCode event arrives for a project whose directory matches
  the working directory of a pane
- **THEN** that pane is updated in the zellij session containing it

#### Scenario: Project is open in no pane
- **WHEN** an OpenCode event arrives for a project with no matching pane
- **THEN** no pane is modified and no error is raised

#### Scenario: No zellij session is running
- **WHEN** an OpenCode event arrives while no zellij session exists
- **THEN** the plugin performs no action

### Requirement: Pane state badges

The plugin SHALL reflect OpenCode session state in the matched pane title by
prefixing the repo name with a configurable badge: busy while a turn is
running, waiting when a permission prompt is pending, done when the session
goes idle, and error when the session reports an error. A new busy state
MUST clear a previous waiting or done badge. Badge updates MUST NOT steal
pane focus.

#### Scenario: Turn starts
- **WHEN** a session transitions to busy
- **THEN** the matched pane title is prefixed with the busy badge

#### Scenario: Permission prompt appears
- **WHEN** a permission prompt is created for a session
- **THEN** the matched pane title is prefixed with the waiting badge

#### Scenario: Session finishes its turn
- **WHEN** a session transitions to idle
- **THEN** the matched pane title is prefixed with the done badge

#### Scenario: Session reports an error
- **WHEN** a session reports an error
- **THEN** the matched pane title is prefixed with the error badge

#### Scenario: Badge does not steal focus
- **WHEN** the plugin updates a pane title
- **THEN** the currently focused pane keeps focus

### Requirement: Desktop notifications

The plugin SHALL raise a desktop notification via
`devsecops_workspace_notify_command` (default `notify-send`) for permission
prompts regardless of pane focus, and for idle transitions only when the
matched pane is not focused. Notification failures MUST be ignored so they
never break the OpenCode session.

#### Scenario: Permission prompt notification
- **WHEN** a permission prompt is created
- **THEN** a desktop notification is raised including the repo name

#### Scenario: Idle with unfocused pane
- **WHEN** a session goes idle and its pane is not focused
- **THEN** a desktop notification is raised

#### Scenario: Idle with focused pane
- **WHEN** a session goes idle and its pane is focused
- **THEN** no desktop notification is raised

#### Scenario: Notification command is unavailable
- **WHEN** the notification command fails or is not installed
- **THEN** the pane badge still updates and the OpenCode session is
  unaffected
