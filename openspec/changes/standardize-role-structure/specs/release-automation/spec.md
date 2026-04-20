## ADDED Requirements

### Requirement: Release-please configuration
The repository SHALL contain a `release-please-config.json` file that configures the root package (`.`) with release type `simple`, `include-component-in-tag: false`, `bump-minor-pre-major: true`, `bump-patch-for-minor-pre-major: true`, and changelog sections mapping `feat` to "Features", `fix` to "Bug Fixes", `chore` to "Miscellaneous", `docs` to "Documentation", and `refactor` to "Refactoring".

#### Scenario: Release-please config matches reference roles
- **WHEN** the `release-please-config.json` file is compared with the same file in `ansible-role-ai`, `ansible-role-git`, or `ansible-role-vim`
- **THEN** the content is byte-for-byte identical

### Requirement: Release-please manifest with initial version
The repository SHALL contain a `.release-please-manifest.json` file with the root package version set to `0.1.0`.

#### Scenario: Manifest file exists with correct initial version
- **WHEN** `.release-please-manifest.json` is inspected
- **THEN** it contains `{".": "0.1.0"}`

### Requirement: Changelog scaffold
The repository SHALL contain a `CHANGELOG.md` file that serves as the changelog scaffold. It SHALL have a top-level heading "Changelog" and be ready for release-please to append entries.

#### Scenario: CHANGELOG.md exists
- **WHEN** `CHANGELOG.md` is inspected
- **THEN** it exists and contains a "Changelog" heading
