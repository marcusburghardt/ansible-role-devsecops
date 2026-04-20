## ADDED Requirements

### Requirement: Yamllint configuration file
The repository SHALL have a `.yamllint` file that extends the `default` ruleset with the following customizations: `line-length` max of 200 (warning level), `truthy` allowing only `'true'` and `'false'` with `check-keys: false`, `comments` requiring starting space with shebangs ignored and `min-spaces-from-content: 1`, `braces` with `max-spaces-inside: 1`, and `octal-values` with `forbid-implicit-octal: true`. The file SHALL ignore `.opencode/` and `openspec/` directories.

#### Scenario: Yamllint config matches reference roles
- **WHEN** the `.yamllint` file is compared with the same file in `ansible-role-ai`, `ansible-role-git`, or `ansible-role-vim`
- **THEN** the content is byte-for-byte identical

#### Scenario: Yamllint ignores tool-managed directories
- **WHEN** yamllint runs against the repository
- **THEN** files under `.opencode/` and `openspec/` are not linted

### Requirement: Gitignore file for tool-managed artifacts
The repository SHALL have a `.gitignore` file that excludes SpecKit/OpenSpec framework infrastructure (`.specify/extensions/.cache/`, `.specify/extensions/.backup/`, local configs, scripts, templates), OpenCode framework commands (`.opencode/command/speckit.*`, `.opencode/command/opsx-*`), OpenCode plugin artifacts (`node_modules`, `package.json`, `package-lock.json`, `bun.lock`, `.gitignore`), agent tool directories (`.cursor`, `.claude`), and agent-specific files (`CLAUDE.md`).

#### Scenario: Gitignore matches reference roles
- **WHEN** the `.gitignore` file is compared with the same file in `ansible-role-ai`, `ansible-role-git`, or `ansible-role-vim`
- **THEN** the content is byte-for-byte identical

### Requirement: Metadata file format standardization
The `meta/main.yml` file SHALL begin with a YAML document marker (`---`), use `Apache-2.0` as the license value, and format platforms with explicit `versions: [all]` sub-keys. The `galaxy_tags` SHALL be formatted as a YAML list (one tag per line with `-` prefix).

#### Scenario: meta/main.yml has YAML document marker
- **WHEN** `meta/main.yml` is inspected
- **THEN** the first line is `---`

#### Scenario: meta/main.yml uses Apache-2.0 license
- **WHEN** `meta/main.yml` is inspected
- **THEN** the `license` field value is `Apache-2.0`

#### Scenario: Platform entries use structured format
- **WHEN** `meta/main.yml` is inspected
- **THEN** each platform entry has a `name` key and a `versions` key with `- all` as a sub-item

### Requirement: LICENSE file
The repository SHALL contain a `LICENSE` file with the full Apache License 2.0 text.

#### Scenario: LICENSE file exists with correct content
- **WHEN** the `LICENSE` file is inspected
- **THEN** it contains the standard Apache License, Version 2.0 text

### Requirement: Handlers placeholder format
The `handlers/main.yml` file SHALL follow the standard empty-placeholder format with a YAML document marker and a descriptive comment.

#### Scenario: Handlers file uses standard format
- **WHEN** `handlers/main.yml` is inspected
- **THEN** it starts with `---` and contains a comment identifying it as the handlers file
