## Context

The `ansible-role-devsecops` repository currently contains a functional Ansible role with the correct dispatcher-based task architecture (`defaults/main.yml` task list, split task/vars files, OS-specific vars). However, it lacks the CI/CD, linting, release automation, and metadata standards that are identical across `ansible-role-ai`, `ansible-role-git`, and `ansible-role-vim`. Those three roles share byte-for-byte identical copies of workflow files, `.yamllint`, `.gitignore`, and `release-please-config.json`.

## Goals / Non-Goals

**Goals:**

- Bring `ansible-role-devsecops` to full parity with sibling roles on infrastructure files (CI, linting, release, metadata).
- Use the exact same file contents as the reference roles wherever the files are shared identically (workflows, `.yamllint`, `.gitignore`, `release-please-config.json`).
- Update `meta/main.yml` to match the standardized format (YAML document marker, Apache-2.0 license, structured platform entries).
- Add a LICENSE file and CHANGELOG.md scaffold.
- Update README.md section structure while preserving the role-specific content.

**Non-Goals:**

- Changing the role's functional behavior (tasks, defaults, handlers, vars logic).
- Adding Molecule tests (none of the reference roles use Molecule).
- Adding a Makefile or `.pre-commit-config.yaml` (none of the reference roles have these).
- Adding Debian/Ubuntu platform support (the role currently supports EL and Fedora only, matching `ansible-role-git` and `ansible-role-vim`).
- Modifying any task file logic or variable values.

## Decisions

### 1. Copy shared files verbatim from reference roles

**Decision**: Use byte-for-byte identical copies of `.yamllint`, `.gitignore`, `ci_release.yml`, `ci_galaxy_publish.yml`, `release-please-config.json`, and `dependabot.yml` from the reference roles.

**Rationale**: These files are already identical across three roles. Maintaining consistency eliminates drift and allows future bulk updates. No role-specific customization is needed.

**Alternative considered**: Customizing each file per role. Rejected because the reference roles demonstrate that one-size-fits-all works and reduces maintenance burden.

### 2. Dependabot tracks github-actions only (not pip)

**Decision**: The `dependabot.yml` will track only `github-actions`, not `pip`. This matches `ansible-role-git` and `ansible-role-vim`.

**Rationale**: The `pip` ecosystem entry exists only in `ansible-role-ai` because that role installs Python packages in CI. `ansible-role-devsecops` does not, so tracking pip is unnecessary.

### 3. License change from MPL-2.0 to Apache-2.0

**Decision**: Change the license to Apache-2.0 to match all sibling roles.

**Rationale**: Consistency across the role collection. Apache-2.0 is the established standard. The LICENSE file content will be the standard Apache-2.0 text.

### 4. Initial version in release-please manifest set to 0.1.0

**Decision**: Start the `.release-please-manifest.json` at version `0.1.0` since this role has no prior releases via release-please.

**Rationale**: Follows semver pre-1.0 convention for roles that haven't had a formal release yet. The first release-please PR will bump from this baseline.

### 5. meta/main.yml format alignment

**Decision**: Add the YAML document marker (`---`), change license to `Apache-2.0`, and ensure `platforms` entries use the `versions: [all]` sub-key format. Keep existing `galaxy_tags` but format as a YAML list.

**Rationale**: Direct alignment with the reference roles' format. The current `meta/main.yml` already has the correct platform names and tags; only formatting and license value need updating.

### 6. Preserve empty vars files with standard comment format

**Decision**: Keep all existing `vars/*.yml` files (including empty ones) but ensure they follow the standard format with a YAML document marker and comment.

**Rationale**: The dispatcher pattern loads these files dynamically. Removing them would cause runtime errors. The empty files serve as explicit declarations that a task has no additional vars.

## Risks / Trade-offs

- **License change**: Switching from MPL-2.0 to Apache-2.0 changes legal terms for existing users. **Mitigation**: This is an intentional decision by the author to align with the role collection.
- **GALAXY_API_KEY secret required**: The Galaxy publish workflow will fail if the secret is not configured. **Mitigation**: This is a one-time setup step documented in the README.
- **Release-please initial version**: Starting at 0.1.0 means the first automated release may not match any prior manual versioning. **Mitigation**: Acceptable for a role that hasn't had formal releases.
