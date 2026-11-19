## ADDED Requirements

### Requirement: Release-please workflow for automated versioning
The repository SHALL have a GitHub Actions workflow at `.github/workflows/ci_release.yml` that runs on pushes to the `main` branch and uses the `googleapis/release-please-action` (pinned by commit SHA) to create release PRs with version bumps and changelog updates. The workflow SHALL define workflow-level `permissions: {}` and job-level `permissions` for `contents: write` and `pull-requests: write`.

#### Scenario: Push to main triggers release-please
- **WHEN** a commit is pushed to the `main` branch
- **THEN** the release-please action analyzes commits since the last tag and opens or updates a release PR if warranted

#### Scenario: Workflow permissions follow least privilege
- **WHEN** the ci_release.yml workflow is inspected
- **THEN** the workflow-level permissions are empty (`permissions: {}`), and the job defines only `contents: write` and `pull-requests: write`

### Requirement: Galaxy publish workflow for automated distribution
The repository SHALL have a GitHub Actions workflow at `.github/workflows/ci_galaxy_publish.yml` that triggers on `release` events of type `published`. It SHALL check out the repository, set up Python 3.12, install `ansible-core==2.17.8`, and run `ansible-galaxy role import` using the `GALAXY_API_KEY` secret. All action references SHALL be pinned by commit SHA.

#### Scenario: Release triggers Galaxy import
- **WHEN** a GitHub Release is published (by release-please or manually)
- **THEN** the workflow imports the role to Ansible Galaxy using the repository owner and name

#### Scenario: Galaxy workflow permissions follow least privilege
- **WHEN** the ci_galaxy_publish.yml workflow is inspected
- **THEN** the workflow-level permissions are empty (`permissions: {}`) and the job defines only `contents: read`

### Requirement: Dependabot configuration for GitHub Actions
The repository SHALL have a `.github/dependabot.yml` file that tracks the `github-actions` package ecosystem on a weekly schedule. Commit messages SHALL use the `chore` prefix with scope included.

#### Scenario: Dependabot file exists with correct configuration
- **WHEN** `.github/dependabot.yml` is inspected
- **THEN** it tracks `github-actions` with weekly interval and `chore` commit prefix

#### Scenario: Dependabot does not track unnecessary ecosystems
- **WHEN** `.github/dependabot.yml` is inspected
- **THEN** it does NOT include a `pip` ecosystem entry (unlike `ansible-role-ai`, this role has no CI pip dependencies)
