## 1. Linting and Ignore Configuration

- [x] 1.1 Create `.yamllint` file (copy verbatim from reference roles)
- [x] 1.2 Create `.gitignore` file (copy verbatim from reference roles)

## 2. CI/CD Workflows

- [x] 2.1 Create `.github/workflows/ci_release.yml` (copy verbatim from reference roles)
- [x] 2.2 Create `.github/workflows/ci_galaxy_publish.yml` (copy verbatim from reference roles)
- [x] 2.3 Create `.github/dependabot.yml` (github-actions only, no pip entry)

## 3. Release Automation

- [x] 3.1 Create `release-please-config.json` (copy verbatim from reference roles)
- [x] 3.2 Create `.release-please-manifest.json` with initial version `0.1.0`
- [x] 3.3 Create `CHANGELOG.md` scaffold with "Changelog" heading

## 4. License and Metadata

- [x] 4.1 Create `LICENSE` file with full Apache License 2.0 text
- [x] 4.2 Update `meta/main.yml`: add YAML document marker, change license to Apache-2.0, format platforms with `versions: [all]` sub-keys, format galaxy_tags as YAML list

## 5. File Format Cleanup

- [x] 5.1 Update `handlers/main.yml` to use standard empty-placeholder format (YAML document marker + descriptive comment)
- [x] 5.2 Verify all `vars/*.yml` files have YAML document markers and consistent comment format
- [x] 5.3 Update `README.md` section structure to match reference roles (add Release Process section, update License section to Apache-2.0)
