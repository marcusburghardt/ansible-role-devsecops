## Why

The `ansible-role-devsecops` role lacks CI/CD workflows, linting configuration, release automation, and other infrastructure files that are standardized across sibling roles (`ansible-role-ai`, `ansible-role-git`, `ansible-role-vim`). Without these, the role cannot be automatically released to Ansible Galaxy, has no consistent linting enforcement, and diverges in metadata and documentation format from the rest of the role collection. Standardizing now ensures uniform quality, maintainability, and release processes across all roles.

## What Changes

- Add `.github/workflows/ci_release.yml` and `ci_galaxy_publish.yml` for automated release and Galaxy publishing.
- Add `.github/dependabot.yml` for automated dependency updates on GitHub Actions.
- Add `.yamllint` linting configuration (matching the shared standard).
- Add `.gitignore` (matching the shared standard).
- Add `release-please-config.json` and `.release-please-manifest.json` for release automation.
- Add `CHANGELOG.md` scaffold.
- Add `LICENSE` file (Apache-2.0, aligning with sibling roles). **BREAKING**: License changes from MPL-2.0 to Apache-2.0.
- Update `meta/main.yml` to match the standardized format (structured `platforms`, Apache-2.0 license, consistent `galaxy_tags` list format).
- Update `README.md` to follow the standard section structure (Role Variables, Dependencies, Example Playbook, Release Process, License, Author Information).
- Clean up empty `vars/` placeholder files to use the standard comment format.
- Ensure `handlers/main.yml` follows the standard empty-placeholder format.

## Capabilities

### New Capabilities

- `ci-workflows`: GitHub Actions workflows for release-please and Ansible Galaxy publishing, plus Dependabot configuration.
- `linting-config`: Yamllint configuration and `.gitignore` aligned with the shared standard across all roles.
- `release-automation`: Release-please configuration files (`release-please-config.json`, `.release-please-manifest.json`, `CHANGELOG.md`) for automated versioning and changelog generation.

### Modified Capabilities

(No existing specs to modify -- `openspec/specs/` is empty.)

## Impact

- **CI/CD**: New GitHub Actions workflows will run on push to `main` and on release events. Requires `GALAXY_API_KEY` secret to be configured in the GitHub repository settings.
- **License**: Changing from MPL-2.0 to Apache-2.0 affects legal terms for downstream consumers.
- **Metadata**: `meta/main.yml` changes may affect Ansible Galaxy listing (description, tags, platform display).
- **Documentation**: README restructuring changes the user-facing documentation but not role behavior.
- **No functional changes**: The role's tasks, defaults, vars, handlers, and runtime behavior remain unchanged.
